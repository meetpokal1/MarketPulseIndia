"""
MarketPulse India - Data Loader
High-performance DuckDB and Polars interface to source parquet files.
"""
from typing import Optional, List, Dict, Any
import duckdb
import polars as pl
import pandas as pd
from src.config import (
    SOURCE_HISTORY_PARQUET,
    SOURCE_COVERAGE_PARQUET,
    SOURCE_LEDGER_PARQUET,
)


class MarketDataLoader:
    """Thread-safe, read-only analytical loader using DuckDB and Polars."""

    def __init__(self, history_path: Optional[str] = None):
        self.history_path = str(history_path or SOURCE_HISTORY_PARQUET)
        self.coverage_path = str(SOURCE_COVERAGE_PARQUET)
        self.ledger_path = str(SOURCE_LEDGER_PARQUET)
        self._con = duckdb.connect(database=":memory:", read_only=False)
        self._init_views()

    def _init_views(self):
        """Register views directly over Parquet files for instant analytical queries."""
        self._con.execute(f"""
            CREATE VIEW IF NOT EXISTS raw_history AS 
            SELECT * FROM read_parquet('{self.history_path}');
        """)
        if SOURCE_COVERAGE_PARQUET.exists():
            self._con.execute(f"""
                CREATE VIEW IF NOT EXISTS raw_coverage AS 
                SELECT * FROM read_parquet('{self.coverage_path}');
            """)
        if SOURCE_LEDGER_PARQUET.exists():
            self._con.execute(f"""
                CREATE VIEW IF NOT EXISTS raw_ledger AS 
                SELECT * FROM read_parquet('{self.ledger_path}');
            """)
        # Register clean view
        from src.cleaning.pipeline import create_standardized_analytical_view
        create_standardized_analytical_view(self._con)

    def execute_df(self, sql: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute query and return Pandas DataFrame."""
        if params:
            return self._con.execute(sql, params).df()
        return self._con.execute(sql).df()

    def execute_polars(self, sql: str) -> pl.DataFrame:
        """Execute query and return Polars DataFrame."""
        arrow_table = self._con.execute(sql).arrow()
        return pl.from_arrow(arrow_table)

    def get_metadata(self) -> Dict[str, Any]:
        """Return dataset row counts, columns, and date ranges."""
        res = self._con.execute("""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT state) as unique_states,
                COUNT(DISTINCT market_id) as unique_market_ids,
                COUNT(DISTINCT market) as unique_market_names,
                COUNT(DISTINCT commodity) as unique_commodities,
                MIN(date) as min_date,
                MAX(date) as max_date,
                COUNT(DISTINCT date) as unique_dates
            FROM raw_history
        """).fetchone()

        return {
            "total_rows": res[0],
            "unique_states": res[1],
            "unique_market_ids": res[2],
            "unique_market_names": res[3],
            "unique_commodities": res[4],
            "min_date": str(res[5]),
            "max_date": str(res[6]),
            "unique_dates": res[7],
            "history_file": self.history_path,
        }

    def get_commodities(self) -> List[Dict[str, Any]]:
        """List all commodities with their record count and date ranges."""
        return self._con.execute("""
            SELECT 
                commodity,
                COUNT(*) as record_count,
                COUNT(DISTINCT market_id) as market_count,
                ROUND(AVG(representative_price), 1) as avg_price,
                ROUND(MEDIAN(representative_price), 1) as median_price,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM raw_history
            GROUP BY commodity
            ORDER BY record_count DESC
        """).df().to_dict(orient="records")

    def get_markets_for_commodity(self, commodity: str, state: Optional[str] = None) -> pd.DataFrame:
        """Get list of markets with coverage statistics for a given commodity."""
        state_clause = "AND state = ?" if state else ""
        params = [commodity, state] if state else [commodity]
        
        sql = f"""
            SELECT 
                market_id,
                MAX(market) as market_name,
                state,
                district,
                COUNT(*) as total_observations,
                COUNT(DISTINCT date) as trading_days,
                ROUND(AVG(representative_price), 2) as avg_modal_price,
                ROUND(MEDIAN(representative_price), 2) as median_modal_price,
                ROUND(STDDEV(representative_price) / NULLIF(AVG(representative_price), 0), 4) as price_cv,
                ROUND(AVG(arrivals_tonnes), 2) as avg_arrivals_tonnes,
                MIN(date) as first_reported_date,
                MAX(date) as last_reported_date
            FROM raw_history
            WHERE commodity = ? {state_clause}
            GROUP BY market_id, state, district
            ORDER BY trading_days DESC
        """
        return self.execute_df(sql, params)


# Singleton instance helper
_LOADER_INSTANCE = None

def get_loader() -> MarketDataLoader:
    global _LOADER_INSTANCE
    if _LOADER_INSTANCE is None:
        _LOADER_INSTANCE = MarketDataLoader()
    return _LOADER_INSTANCE
