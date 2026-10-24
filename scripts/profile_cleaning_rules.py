import duckdb
import pandas as pd
import sys

from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = str(BASE_DIR / "data" / "raw" / "all_market_history.parquet")
con = duckdb.connect()

print("=== DATA PROFILING & ANOMALY CHECKS ===")

# 1. Total rows & primary key uniqueness (market_id, commodity, date, example_variety)
pk_check = con.execute(f"""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT market_id || '::' || commodity || '::' || date::VARCHAR) as unique_market_comm_date,
        COUNT(DISTINCT market_id || '::' || commodity || '::' || date::VARCHAR || '::' || example_variety) as unique_market_comm_date_var
    FROM '{PARQUET}'
""").fetchone()
print(f"Total Rows: {pk_check[0]:,}")
print(f"Unique (market_id, commodity, date): {pk_check[1]:,}")
print(f"Unique (market_id, commodity, date, variety): {pk_check[2]:,}")

# Are there duplicate (market_id, commodity, date)?
if pk_check[0] == pk_check[1]:
    print("-> Exactly 1 record per (market_id, commodity, date)! No grain collisions.")
else:
    diff = pk_check[0] - pk_check[1]
    print(f"-> Found {diff:,} multi-variety or duplicate records on same market-date.")

# 2. Price validity checks:
# min_price <= 0? representative_price <= 0? min_price > max_price? representative_price outside [min, max]?
price_audit = con.execute(f"""
    SELECT 
        SUM(CASE WHEN min_price <= 0 THEN 1 ELSE 0 END) as zero_min_price,
        SUM(CASE WHEN max_price <= 0 THEN 1 ELSE 0 END) as zero_max_price,
        SUM(CASE WHEN representative_price <= 0 THEN 1 ELSE 0 END) as zero_rep_price,
        SUM(CASE WHEN min_price > max_price THEN 1 ELSE 0 END) as inverted_min_max,
        SUM(CASE WHEN representative_price < min_price OR representative_price > max_price THEN 1 ELSE 0 END) as rep_outside_range,
        SUM(CASE WHEN min_price < 10.0 THEN 1 ELSE 0 END) as extreme_low_price,
        SUM(CASE WHEN representative_price > 50000.0 THEN 1 ELSE 0 END) as extreme_high_price
    FROM '{PARQUET}'
""").fetchone()

print("\nPrice Audit:")
print(f"  Zero or negative min_price: {price_audit[0]:,}")
print(f"  Zero or negative max_price: {price_audit[1]:,}")
print(f"  Zero or negative representative_price: {price_audit[2]:,}")
print(f"  Inverted min > max: {price_audit[3]:,}")
print(f"  Representative price outside [min, max]: {price_audit[4]:,}")
print(f"  Extreme low price (< ₹10/quintal): {price_audit[5]:,}")
print(f"  Extreme high price (> ₹50,000/quintal): {price_audit[6]:,}")

# 3. Arrivals audit:
# arrivals_tonnes == 0, null, or extreme?
arrival_audit = con.execute(f"""
    SELECT 
        SUM(CASE WHEN arrivals_tonnes = 0 THEN 1 ELSE 0 END) as zero_arrivals,
        SUM(CASE WHEN arrivals_tonnes < 0 THEN 1 ELSE 0 END) as negative_arrivals,
        SUM(CASE WHEN arrivals_tonnes IS NULL THEN 1 ELSE 0 END) as null_arrivals,
        SUM(CASE WHEN arrivals_tonnes > 10000 THEN 1 ELSE 0 END) as extreme_high_arrivals
    FROM '{PARQUET}'
""").fetchone()

print("\nArrivals Audit:")
print(f"  Zero arrivals: {arrival_audit[0]:,} ({arrival_audit[0]/pk_check[0]*100:.2f}%)")
print(f"  Negative arrivals: {arrival_audit[1]:,}")
print(f"  Null arrivals: {arrival_audit[2]:,}")
print(f"  Extreme high arrivals (>10k tonnes): {arrival_audit[3]:,}")

# 4. Anomaly score & is_anomaly flag distribution
anomaly_audit = con.execute(f"""
    SELECT 
        is_anomaly,
        COUNT(*) as cnt,
        ROUND(AVG(anomaly_score), 4) as avg_score,
        ROUND(MIN(anomaly_score), 4) as min_score,
        ROUND(MAX(anomaly_score), 4) as max_score
    FROM '{PARQUET}'
    GROUP BY is_anomaly
""").fetchall()

print("\nAnomaly Flag Audit:")
for row in anomaly_audit:
    print(f"  is_anomaly={row[0]}: {row[1]:,} rows, avg_score={row[2]}, min={row[3]}, max={row[4]}")
