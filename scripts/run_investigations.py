import duckdb
import pandas as pd
import numpy as np
import sys

from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = str(BASE_DIR / "data" / "raw" / "all_market_history.parquet")
con = duckdb.connect()

print("="*80)
print("INVESTIGATION A: LASALGAON VS MUMBAI ONION PRICE COMPARISON & VARIETY CONFOUNDING")
print("="*80)

# 1. Lasalgaon (20-161) vs Mumbai (20-2703) on invariant market_id
df_pairs = con.execute(f"""
    SELECT 
        l.date,
        l.example_variety as las_variety,
        l.representative_price as las_price,
        l.arrivals_tonnes as las_arrivals,
        m.example_variety as mum_variety,
        m.representative_price as mum_price,
        m.arrivals_tonnes as mum_arrivals,
        (m.representative_price - l.representative_price) as spread_mumbai_minus_las,
        ROUND((m.representative_price - l.representative_price) / l.representative_price * 100.0, 2) as spread_pct
    FROM (
        SELECT date, example_variety, representative_price, arrivals_tonnes
        FROM '{PARQUET}'
        WHERE commodity = 'Onion' AND market_id = '20-161'
    ) l
    INNER JOIN (
        SELECT date, example_variety, representative_price, arrivals_tonnes
        FROM '{PARQUET}'
        WHERE commodity = 'Onion' AND market_id = '20-2703'
    ) m ON l.date = m.date
    ORDER BY l.date
""").df()

print(f"Total overlapping trading days: {len(df_pairs)}")
print(f"Date range: {df_pairs['date'].min()} to {df_pairs['date'].max()}")

print("\n--- Summary by Lasalgaon Variety (Mumbai is 100% 'Other') ---")
summary_by_var = df_pairs.groupby("las_variety").agg(
    n_days=("date", "count"),
    mean_las_price=("las_price", "mean"),
    mean_mum_price=("mum_price", "mean"),
    mean_spread=("spread_mumbai_minus_las", "mean"),
    median_spread=("spread_mumbai_minus_las", "median"),
    std_spread=("spread_mumbai_minus_las", "std"),
    min_spread=("spread_mumbai_minus_las", "min"),
    max_spread=("spread_mumbai_minus_las", "max"),
    negative_spread_days=("spread_mumbai_minus_las", lambda s: (s < 0).sum())
).reset_index()

summary_by_var["pct_negative"] = (summary_by_var["negative_spread_days"] / summary_by_var["n_days"] * 100).round(1)
print(summary_by_var.to_string(index=False))

# Overall unadjusted spread:
print("\n--- Overall Unadjusted Spread (All 507 Days) ---")
print(f"Mean Spread: ₹{df_pairs['spread_mumbai_minus_las'].mean():.2f}/quintal")
print(f"Median Spread: ₹{df_pairs['spread_mumbai_minus_las'].median():.2f}/quintal")
print(f"Std Dev: ₹{df_pairs['spread_mumbai_minus_las'].std():.2f}/quintal")
print(f"Days where Mumbai < Lasalgaon (Negative Spread): {(df_pairs['spread_mumbai_minus_las'] < 0).sum()} of {len(df_pairs)} ({(df_pairs['spread_mumbai_minus_las'] < 0).mean()*100:.1f}%)")

# Compare with Lasalgaon Niphad (20-2139) and Lasalgaon Vinchur (20-3448)
print("\n--- Sub-Yards Check ---")
for sub_id, name in [('20-2139', 'Lasalgaon(Niphad)'), ('20-3448', 'Lasalgaon(Vinchur)')]:
    sub_df = con.execute(f"""
        SELECT 
            AVG(m.representative_price - s.representative_price) as mean_spread,
            COUNT(*) as n_days
        FROM (SELECT date, representative_price FROM '{PARQUET}' WHERE commodity = 'Onion' AND market_id = '{sub_id}') s
        INNER JOIN (SELECT date, representative_price FROM '{PARQUET}' WHERE commodity = 'Onion' AND market_id = '20-2703') m
        ON s.date = m.date
    """).fetchone()
    print(f"{name} vs Mumbai: {sub_df[1]} overlapping days, Mean Spread = ₹{sub_df[0]:.2f}/quintal")
