"""
MarketPulse India - Data Reliability & Reporting Quality Audit Engine
Investigation D: Repeated prices, frozen streaks, reporting gaps, and candidate anomaly queues.
"""
from typing import Dict, Any, List
import pandas as pd
from src.ingestion.loader import get_loader
from src.config import STALE_PRICE_STREAK_DAYS, REPORTING_BLACKOUT_DAYS


class ReliabilityAuditor:
    """Audits market reporting reliability, detecting frozen prices, blackouts, and flat quotes."""

    def __init__(self, loader=None):
        self.loader = loader or get_loader()

    def get_frozen_price_streaks(
        self,
        min_streak_days: int = STALE_PRICE_STREAK_DAYS,
        commodity: str = None,
        state: str = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Find uninterrupted consecutive trading days with frozen representative price."""
        filters = []
        params = []
        if commodity:
            filters.append("commodity = ?")
            params.append(commodity)
        if state:
            filters.append("state = ?")
            params.append(state)

        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

        sql = f"""
            WITH ordered AS (
                SELECT 
                    market_id,
                    canonical_market_name,
                    state,
                    district,
                    commodity,
                    date,
                    modal_price_quintal,
                    LAG(modal_price_quintal) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_price,
                    LAG(date) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_date
                FROM vw_clean_market_history
                {where_clause}
            ),
            flags AS (
                SELECT *,
                    CASE WHEN modal_price_quintal = prev_price AND (date - prev_date) <= 4 THEN 0 ELSE 1 END as is_new_streak
                FROM ordered
            ),
            groups AS (
                SELECT *,
                    SUM(is_new_streak) OVER (PARTITION BY market_id, commodity ORDER BY date) as streak_id
                FROM flags
            ),
            streak_summary AS (
                SELECT 
                    market_id,
                    canonical_market_name,
                    state,
                    district,
                    commodity,
                    modal_price_quintal as frozen_price,
                    MIN(date) as streak_start,
                    MAX(date) as streak_end,
                    COUNT(*) as streak_days
                FROM groups
                GROUP BY market_id, canonical_market_name, state, district, commodity, modal_price_quintal, streak_id
            )
            SELECT 
                state,
                district,
                canonical_market_name,
                commodity,
                frozen_price,
                streak_start,
                streak_end,
                streak_days,
                -- Plausible explanation
                CASE 
                    WHEN commodity = 'Paddy (Common)' AND frozen_price IN (2183.0, 2203.0, 2300.0, 2320.0) 
                        THEN 'MSP Statutory Procurement Quote: Consistent with government MSP procurement floor.'
                    WHEN LOWER(canonical_market_name) LIKE '%uzhavar sandhai%' 
                        THEN 'Administrative Price Ceiling: Farmers market fixed daily price board.'
                    WHEN streak_days > 60 
                        THEN 'Likely Reporting Inactivity: Stale price carried forward across reporting cycles.'
                    ELSE 'Candidate Price Stickiness: Real price stability or infrequent auction revision.'
                END as plausible_explanation,
                CASE 
                    WHEN streak_days >= 30 THEN 'HIGH REVIEW'
                    WHEN streak_days >= 14 THEN 'MEDIUM REVIEW'
                    ELSE 'LOW NOTICE'
                END as audit_priority
            FROM streak_summary
            WHERE streak_days >= {min_streak_days}
            ORDER BY streak_days DESC
            LIMIT {limit}
        """
        return self.loader.execute_df(sql, params)

    def get_reporting_blackouts(
        self,
        min_gap_days: int = REPORTING_BLACKOUT_DAYS,
        commodity: str = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Find long reporting blackouts between consecutive market reports."""
        filter_clause = "WHERE commodity = ?" if commodity else ""
        params = [commodity] if commodity else []

        sql = f"""
            WITH lag_dates AS (
                SELECT 
                    market_id,
                    canonical_market_name,
                    state,
                    district,
                    commodity,
                    date,
                    LAG(date) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_date
                FROM vw_clean_market_history
                {filter_clause}
            )
            SELECT 
                state,
                canonical_market_name,
                commodity,
                prev_date as blackout_start,
                date as blackout_end,
                (date - prev_date) as blackout_days,
                CASE 
                    WHEN (date - prev_date) >= 180 THEN 'Seasonal Crop Hibernation or Prolonged Discontinuation'
                    WHEN (date - prev_date) >= 60 THEN 'Major Multi-Month Mandi Reporting Hiatus'
                    ELSE 'Intermittent Reporting Suspension'
                END as diagnostic_category
            FROM lag_dates
            WHERE prev_date IS NOT NULL AND (date - prev_date) >= {min_gap_days}
            ORDER BY blackout_days DESC
            LIMIT {limit}
        """
        return self.loader.execute_df(sql, params)

    def get_state_flat_quote_summary(self) -> pd.DataFrame:
        """Percentage of market records where min == max == modal price."""
        sql = """
            SELECT 
                state,
                COUNT(*) as total_records,
                SUM(CASE WHEN min_price = max_price AND min_price = modal_price_quintal THEN 1 ELSE 0 END) as flat_quote_records,
                ROUND(SUM(CASE WHEN min_price = max_price AND min_price = modal_price_quintal THEN 1 ELSE 0 END) / COUNT(*) * 100.0, 2) as flat_quote_pct,
                ROUND(AVG(modal_price_quintal), 1) as avg_price,
                COUNT(DISTINCT market_id) as total_markets
            FROM vw_clean_market_history
            WHERE is_valid_price
            GROUP BY state
            ORDER BY flat_quote_pct DESC
        """
        return self.loader.execute_df(sql)
