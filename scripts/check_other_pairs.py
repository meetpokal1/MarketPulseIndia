import duckdb
import pandas as pd
import sys

from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = str(BASE_DIR / "data" / "raw" / "all_market_history.parquet")
con = duckdb.connect()

print("=== SPATIAL SPREAD ACROSS OTHER PRODUCER-CONSUMER PAIRS ===")

# Check Top Markets for Onion in Maharashtra
onion_markets = con.execute(f"""
    SELECT market_id, market, COUNT(*) as cnt, ROUND(AVG(representative_price), 1) as avg_p
    FROM '{PARQUET}'
    WHERE commodity = 'Onion' AND state = 'Maharashtra'
    GROUP BY market_id, market
    HAVING COUNT(*) > 450
    ORDER BY avg_p DESC
""").df()
print("Top Maharashtra Onion Markets by Avg Price:")
print(onion_markets.head(10).to_string(index=False))

# Check Lasalgaon (20-161) vs Pune APMC (20-110)
pune_pair = con.execute(f"""
    SELECT 
        COUNT(*) as n_days,
        ROUND(AVG(p.representative_price - l.representative_price), 2) as mean_spread,
        ROUND(MEDIAN(p.representative_price - l.representative_price), 2) as median_spread,
        SUM(CASE WHEN p.representative_price > l.representative_price THEN 1 ELSE 0 END) as positive_spread_days
    FROM (SELECT date, representative_price FROM '{PARQUET}' WHERE commodity = 'Onion' AND market_id = '20-161') l
    INNER JOIN (SELECT date, representative_price FROM '{PARQUET}' WHERE commodity = 'Onion' AND LOWER(market) LIKE 'pune apmc%') p
    ON l.date = p.date
""").df()
print("\nLasalgaon (20-161) vs Pune APMC:")
print(pune_pair.to_string(index=False))

# Check Tomato in Tamil Nadu: Producer (e.g. Dharmapuri or Krishnagiri) vs Chennai / Koyambedu
tomato_pairs = con.execute(f"""
    SELECT 
        market_id, market, COUNT(*) as cnt, ROUND(AVG(representative_price), 1) as avg_p
    FROM '{PARQUET}'
    WHERE commodity = 'Tomato' AND state = 'Tamil Nadu'
    GROUP BY market_id, market
    HAVING COUNT(*) > 400
    ORDER BY avg_p DESC
""").df()
print("\nTop Tamil Nadu Tomato Markets:")
print(tomato_pairs.head(10).to_string(index=False))
