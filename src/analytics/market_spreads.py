"""
MarketPulse India - Market Price Spreads & Variety Matching Engine
Investigation A: Lasalgaon vs. Mumbai and generalized APMC corridor price comparisons.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.ingestion.loader import get_loader
from src.cleaning.pipeline import PipelineAuditor


class MarketSpreadEngine:
    """Computes pair-wise market price spreads with strict variety compatibility controls."""

    def __init__(self, loader=None):
        self.loader = loader or get_loader()
        PipelineAuditor(self.loader) # ensure view is initialized

    def compare_markets(
        self,
        commodity: str,
        source_market_id: str,
        dest_market_id: str,
        variety_filter_mode: str = "ALL",  # "ALL", "EXACT", or specific variety string
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare prices and arrivals between source and destination market.
        variety_filter_mode options:
          - "ALL": All overlapping trading dates (unadjusted)
          - "EXACT": Strict exact string match on standardized_variety
          - "OTHER_ONLY": Both markets reporting 'Other / Unspecified'
          - "UNHALI": Lasalgaon Unhali crop
          - "RED": Lasalgaon Red crop
        """
        date_clause = ""
        params = [commodity, source_market_id, commodity, dest_market_id]
        if start_date:
            date_clause += " AND s.date >= ?"
            params.append(start_date)
        if end_date:
            date_clause += " AND s.date <= ?"
            params.append(end_date)

        sql = f"""
            SELECT 
                s.date,
                s.canonical_market_name as source_market_name,
                s.raw_market_name as source_raw_name,
                s.raw_variety as source_raw_variety,
                s.standardized_variety as source_std_variety,
                s.variety_granularity as source_variety_tier,
                s.modal_price_quintal as source_price,
                s.arrivals_tonnes as source_arrivals,
                d.canonical_market_name as dest_market_name,
                d.raw_market_name as dest_raw_name,
                d.raw_variety as dest_raw_variety,
                d.standardized_variety as dest_std_variety,
                d.variety_granularity as dest_variety_tier,
                d.modal_price_quintal as dest_price,
                d.arrivals_tonnes as dest_arrivals,
                (d.modal_price_quintal - s.modal_price_quintal) as price_spread_quintal,
                ROUND((d.modal_price_quintal - s.modal_price_quintal) / 100.0, 2) as price_spread_kg,
                ROUND((d.modal_price_quintal - s.modal_price_quintal) / NULLIF(s.modal_price_quintal, 0) * 100.0, 2) as spread_pct
            FROM (
                SELECT * FROM vw_clean_market_history 
                WHERE commodity = ? AND market_id = ? AND is_valid_price
            ) s
            INNER JOIN (
                SELECT * FROM vw_clean_market_history 
                WHERE commodity = ? AND market_id = ? AND is_valid_price
            ) d ON s.date = d.date
            WHERE 1=1 {date_clause}
            ORDER BY s.date ASC
        """
        df = self.loader.execute_df(sql, params)

        # Apply variety filter
        if variety_filter_mode == "EXACT":
            df = df[df["source_std_variety"] == df["dest_std_variety"]].copy()
        elif variety_filter_mode == "OTHER_ONLY":
            df = df[(df["source_std_variety"] == "Other / Unspecified") & (df["dest_std_variety"] == "Other / Unspecified")].copy()
        elif variety_filter_mode in ("Unhali", "Red"):
            df = df[df["source_raw_variety"] == variety_filter_mode].copy()

        if df.empty:
            return {
                "commodity": commodity,
                "source_market_id": source_market_id,
                "dest_market_id": dest_market_id,
                "n_overlapping_days": 0,
                "df": df,
                "message": "No overlapping trading days found for the selected variety and date criteria."
            }

        # Calculate robust statistical summary
        spread = df["price_spread_quintal"]
        n_days = len(df)
        negative_days = int((spread < 0).sum())
        positive_days = int((spread > 0).sum())
        zero_days = int((spread == 0).sum())

        source_name = df["source_market_name"].iloc[0]
        dest_name = df["dest_market_name"].iloc[0]

        summary = {
            "commodity": commodity,
            "source_market_id": source_market_id,
            "source_market_name": source_name,
            "dest_market_id": dest_market_id,
            "dest_market_name": dest_name,
            "filter_mode": variety_filter_mode,
            "n_overlapping_days": n_days,
            "min_date": str(df["date"].min())[:10],
            "max_date": str(df["date"].max())[:10],
            "source_mean_price": round(float(df["source_price"].mean()), 2),
            "dest_mean_price": round(float(df["dest_price"].mean()), 2),
            "mean_spread_quintal": round(float(spread.mean()), 2),
            "median_spread_quintal": round(float(spread.median()), 2),
            "std_spread_quintal": round(float(spread.std()), 2),
            "min_spread_quintal": round(float(spread.min()), 2),
            "max_spread_quintal": round(float(spread.max()), 2),
            "negative_spread_days": negative_days,
            "negative_spread_pct": round(negative_days / n_days * 100.0, 2),
            "positive_spread_days": positive_days,
            "positive_spread_pct": round(positive_days / n_days * 100.0, 2),
            "price_correlation": round(float(df["source_price"].corr(df["dest_price"])), 4),
            "source_variety_distribution": df["source_raw_variety"].value_counts().to_dict(),
            "dest_variety_distribution": df["dest_raw_variety"].value_counts().to_dict(),
            "df": df,
        }
        return summary
