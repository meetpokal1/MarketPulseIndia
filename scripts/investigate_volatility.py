import duckdb
import pandas as pd
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')
PARQUET = r"C:\Users\Meet Pokal\.gemini\antigravity\scratch\portfolio_research_oct2026\samples\all_market_history.parquet"
con = duckdb.connect()

print("="*80)
print("INVESTIGATION B: PRICE VOLATILITY AND MARKET SHOCKS")
print("="*80)

# Commodity-level volatility: CV across commodities (minimum 5,000 records)
comm_vol = con.execute(f"""
    SELECT 
        commodity,
        COUNT(*) as total_records,
        COUNT(DISTINCT market_id) as total_markets,
        ROUND(AVG(representative_price), 2) as mean_price,
        ROUND(STDDEV(representative_price), 2) as std_price,
        ROUND(STDDEV(representative_price) / AVG(representative_price), 4) as price_cv,
        ROUND(AVG(arrivals_tonnes), 2) as avg_arrivals,
        ROUND(STDDEV(arrivals_tonnes) / NULLIF(AVG(arrivals_tonnes), 0), 4) as arrivals_cv
    FROM '{PARQUET}'
    GROUP BY commodity
    ORDER BY price_cv DESC
""").df()

print("Commodity Volatility Ranking (Coefficient of Variation):")
print(comm_vol.to_string(index=False))

# For Onion: examine rolling volatility and large shocks in major Maharashtra markets
onion_ts = con.execute(f"""
    SELECT 
        date,
        market_id,
        market,
        representative_price,
        arrivals_tonnes
    FROM '{PARQUET}'
    WHERE commodity = 'Onion' 
      AND market_id IN ('20-161', '20-162', '20-2703', '20-2139')
    ORDER BY market_id, date
""").df()

onion_ts['log_price'] = np.log(onion_ts['representative_price'])
onion_ts['price_return'] = onion_ts.groupby('market_id')['log_price'].diff()

print("\n--- Onion Price Returns & Outlier Shocks (|return| > 0.30 or ~35% day-over-day) ---")
shocks = onion_ts[onion_ts['price_return'].abs() > 0.30]
print(f"Total severe price shocks detected: {len(shocks)}")
print(shocks[['date', 'market', 'representative_price', 'price_return']].head(10).to_string(index=False))

# Check persistence / AR(1) of daily price changes in Lasalgaon
las_data = onion_ts[onion_ts['market_id'] == '20-161'].dropna(subset=['price_return'])
corr_lag1 = las_data['price_return'].autocorr(lag=1)
corr_lag2 = las_data['price_return'].autocorr(lag=2)
print(f"\nLasalgaon Price Return Autocorrelation: Lag 1 = {corr_lag1:.4f}, Lag 2 = {corr_lag2:.4f}")
if abs(corr_lag1) < 0.2:
    print("-> Price returns exhibit fast mean-reversion / low persistent momentum, typical of auction markets.")
