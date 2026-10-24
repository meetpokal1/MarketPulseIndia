import duckdb
import pandas as pd
import numpy as np
import sys

from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = str(BASE_DIR / "data" / "raw" / "all_market_history.parquet")
con = duckdb.connect()

print("="*80, flush=True)
print("INVESTIGATION D: REPORTING RELIABILITY & STALE PRICE AUDIT", flush=True)
print("="*80, flush=True)

# 1. Repeated / Frozen Price Streaks
# Find consecutive trading days where representative_price is identical for a market-commodity series
repeated_streaks = con.execute(f"""
    WITH ordered AS (
        SELECT 
            market_id,
            market,
            state,
            commodity,
            date,
            representative_price,
            LAG(representative_price) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_price,
            LAG(date) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_date
        FROM '{PARQUET}'
    ),
    flags AS (
        SELECT *,
            CASE WHEN representative_price = prev_price AND (date - prev_date) <= 4 THEN 0 ELSE 1 END as is_new_streak
        FROM ordered
    ),
    groups AS (
        SELECT *,
            SUM(is_new_streak) OVER (PARTITION BY market_id, commodity ORDER BY date) as streak_id
        FROM flags
    ),
    streak_lengths AS (
        SELECT 
            market_id,
            market,
            state,
            commodity,
            representative_price,
            MIN(date) as streak_start,
            MAX(date) as streak_end,
            COUNT(*) as streak_days
        FROM groups
        GROUP BY market_id, market, state, commodity, representative_price, streak_id
    )
    SELECT *
    FROM streak_lengths
    WHERE streak_days >= 7
    ORDER BY streak_days DESC
""").df()

print(f"Total frozen price streaks (>= 7 consecutive trading days): {len(repeated_streaks):,}", flush=True)
print("\nTop 10 Longest Frozen Price Streaks:")
print(repeated_streaks.head(10)[['state', 'market', 'commodity', 'representative_price', 'streak_start', 'streak_end', 'streak_days']].to_string(index=False), flush=True)

# 2. Coverage gaps: Maximum gap between reported trading days
max_gaps = con.execute(f"""
    WITH lag_dates AS (
        SELECT 
            market_id, market, state, commodity, date,
            LAG(date) OVER (PARTITION BY market_id, commodity ORDER BY date) as prev_date
        FROM '{PARQUET}'
    )
    SELECT 
        market_id, market, state, commodity,
        MAX(date - prev_date) as max_gap_days,
        COUNT(*) as total_reported_days
    FROM lag_dates
    WHERE prev_date IS NOT NULL
    GROUP BY market_id, market, state, commodity
    HAVING MAX(date - prev_date) >= 30
    ORDER BY max_gap_days DESC
""").df()

print(f"\nTotal series with prolonged reporting blackout (>= 30-day gap): {len(max_gaps):,}", flush=True)
print("Top 10 Reporting Blackouts:")
print(max_gaps.head(10).to_string(index=False), flush=True)

# 3. Flat quote rates: min_price == max_price == representative_price
flat_quotes = con.execute(f"""
    SELECT 
        state,
        COUNT(*) as total_rows,
        SUM(CASE WHEN min_price = max_price AND min_price = representative_price THEN 1 ELSE 0 END) as flat_quote_rows,
        ROUND(SUM(CASE WHEN min_price = max_price AND min_price = representative_price THEN 1 ELSE 0 END) / COUNT(*) * 100.0, 2) as flat_quote_pct
    FROM '{PARQUET}'
    GROUP BY state
    ORDER BY flat_quote_pct DESC
""").df()

print("\n--- Flat Quote Percentage by State (Single Price Reported for Min, Max & Modal) ---", flush=True)
print(flat_quotes.to_string(index=False), flush=True)
