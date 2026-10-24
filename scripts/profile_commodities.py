import duckdb
import sys

sys.stdout.reconfigure(encoding='utf-8')
PARQUET = r"C:\Users\Meet Pokal\.gemini\antigravity\scratch\portfolio_research_oct2026\samples\all_market_history.parquet"
con = duckdb.connect()

res = con.execute(f"""
    SELECT 
        commodity,
        COUNT(*) as row_count,
        ROUND(MIN(representative_price), 1) as min_p,
        ROUND(MEDIAN(representative_price), 1) as median_p,
        ROUND(MAX(representative_price), 1) as max_p,
        ROUND(AVG(arrivals_tonnes), 1) as avg_arr,
        ROUND(MAX(arrivals_tonnes), 1) as max_arr
    FROM '{PARQUET}'
    GROUP BY commodity
    ORDER BY row_count DESC
""").fetchall()

header = f"{'Commodity':<18} | {'Count':>9} | {'Min P':>7} | {'Median P':>9} | {'Max P':>9} | {'Avg Arr (T)':>12} | {'Max Arr (T)':>12}"
print(header)
print("-" * len(header))
for r in res:
    print(f"{r[0]:<18} | {r[1]:>9,} | {r[2]:>7.1f} | {r[3]:>9.1f} | {r[4]:>9.1f} | {r[5]:>12.1f} | {r[6]:>12.1f}")
