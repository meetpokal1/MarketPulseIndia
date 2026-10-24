"""
MarketPulse India - Data Cleaning & Standardization Pipeline
Preserves raw values while providing standardized identifiers, validity flags, and quality ledgers.
"""
from typing import Dict, Any, Tuple
import pandas as pd
import duckdb
from src.config import MIN_PLAUSIBLE_PRICE, MIN_PLAUSIBLE_ARRIVALS
from src.ingestion.loader import get_loader


# Canonical market name mapping for historical text shifts
CANONICAL_MARKET_NAMES = {
    "20-161": "Lasalgaon APMC",
    "20-2703": "Mumbai-Onion & Potato Market APMC",
    "20-2139": "Lasalgaon(Niphad) APMC",
    "20-3448": "Lasalgaon(Vinchur) APMC",
    "20-162": "Pimpalgaon Baswant APMC",
    "20-110": "Pune APMC",
}


def create_standardized_analytical_view(con: duckdb.DuckDBPyConnection) -> None:
    """
    Creates a clean, standardized analytical view `vw_clean_market_history` in DuckDB.
    Preserves original labels while attaching:
      - canonical_market_name
      - is_valid_price (bool)
      - is_valid_arrival (bool)
      - variety_tier ('Specific Variety' vs 'Generic Other')
      - price_per_kg
      - arrivals_quintals
    """
    con.execute(f"""
        CREATE OR REPLACE VIEW vw_clean_market_history AS
        SELECT 
            h.state_id,
            h.state,
            h.district,
            h.market_id,
            h.market as raw_market_name,
            -- Invariant canonical market name
            CASE 
                WHEN h.market_id = '20-161' THEN 'Lasalgaon APMC'
                WHEN h.market_id = '20-2703' THEN 'Mumbai-Onion & Potato Market APMC'
                WHEN h.market_id = '20-2139' THEN 'Lasalgaon(Niphad) APMC'
                WHEN h.market_id = '20-3448' THEN 'Lasalgaon(Vinchur) APMC'
                WHEN h.market_id = '20-162' THEN 'Pimpalgaon Baswant APMC'
                ELSE h.market
            END as canonical_market_name,
            h.commodity,
            h.date,
            h.min_price,
            h.max_price,
            h.representative_price as modal_price_quintal,
            ROUND(h.representative_price / 100.0, 2) as modal_price_kg,
            h.arrivals_tonnes,
            ROUND(h.arrivals_tonnes * 10.0, 2) as arrivals_quintals,
            h.variety_count,
            h.example_variety as raw_variety,
            -- Variety standardization
            CASE 
                WHEN LOWER(h.example_variety) IN ('other', 'others', 'n/a', '') THEN 'Other / Unspecified'
                ELSE h.example_variety
            END as standardized_variety,
            CASE 
                WHEN LOWER(h.example_variety) IN ('other', 'others', 'n/a', '') THEN 'Generic Other'
                ELSE 'Specific Variety'
            END as variety_granularity,
            h.aggregation_method,
            h.arrival_coverage,
            h.anomaly_score,
            h.is_anomaly,
            -- Data Quality Flags
            (
                h.representative_price IS NOT NULL
                AND h.min_price IS NOT NULL
                AND h.max_price IS NOT NULL
                AND h.representative_price >= {MIN_PLAUSIBLE_PRICE}
                AND h.min_price >= {MIN_PLAUSIBLE_PRICE}
                AND h.min_price <= h.max_price
            ) as is_valid_price,
            (h.arrivals_tonnes IS NOT NULL AND h.arrivals_tonnes > 0) as is_valid_arrival,
            CASE
                WHEN h.representative_price < {MIN_PLAUSIBLE_PRICE} OR h.min_price < {MIN_PLAUSIBLE_PRICE} THEN 'SCALE_ERROR_LOW_PRICE'
                WHEN h.min_price > h.max_price THEN 'INVERTED_PRICE_RANGE'
                WHEN h.arrivals_tonnes <= 0 THEN 'ZERO_ARRIVALS'
                WHEN h.representative_price IS NULL OR h.min_price IS NULL OR h.max_price IS NULL THEN 'NULL_PRICE'
                WHEN h.arrivals_tonnes IS NULL THEN 'NULL_ARRIVALS'
                ELSE 'VALID'
            END as record_quality_status
        FROM raw_history h
    """)


class PipelineAuditor:
    """Computes transparent data assurance, row conservation, and anomaly breakdowns."""

    def __init__(self, loader=None):
        self.loader = loader or get_loader()
        create_standardized_analytical_view(self.loader._con)

    def get_row_conservation_ledger(self) -> Dict[str, Any]:
        """Verify row conservation across raw, quarantined, and clean records."""
        df = self.loader.execute_df("""
            SELECT 
                COUNT(*) as total_raw_records,
                SUM(CASE WHEN record_quality_status = 'VALID' THEN 1 ELSE 0 END) as valid_records,
                SUM(CASE WHEN record_quality_status = 'SCALE_ERROR_LOW_PRICE' THEN 1 ELSE 0 END) as scale_errors,
                SUM(CASE WHEN record_quality_status = 'INVERTED_PRICE_RANGE' THEN 1 ELSE 0 END) as inverted_prices,
                SUM(CASE WHEN record_quality_status = 'ZERO_ARRIVALS' THEN 1 ELSE 0 END) as zero_arrivals,
                SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) as statistical_anomalies
            FROM vw_clean_market_history
        """)
        row = df.iloc[0].to_dict()
        row["preservation_rate_pct"] = round(row["valid_records"] / row["total_raw_records"] * 100.0, 4)
        return row

    def get_quarantined_records_sample(self, limit: int = 50) -> pd.DataFrame:
        """Sample records quarantined for scale errors or data defects."""
        return self.loader.execute_df(f"""
            SELECT 
                state, market_id, canonical_market_name, commodity, date, 
                modal_price_quintal, arrivals_tonnes, raw_variety, record_quality_status, anomaly_score
            FROM vw_clean_market_history
            WHERE record_quality_status != 'VALID'
            ORDER BY modal_price_quintal ASC
            LIMIT {limit}
        """)
