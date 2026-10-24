import duckdb
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES = str(BASE_DIR / "data" / "raw")
con = duckdb.connect()

for name in ['all_market_coverage.parquet', 'source_quality_ledger.parquet', 'market_history_sample.parquet']:
    path = os.path.join(SAMPLES, name)
    cols = con.execute(f"DESCRIBE SELECT * FROM '{path}'").fetchall()
    cnt = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    print(f"\n=== {name} === ({cnt:,} rows)")
    for col in cols:
        print(f"  {col[0]} ({col[1]})")
