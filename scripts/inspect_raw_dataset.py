import pyarrow.parquet as pq
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET_PATH = str(BASE_DIR / "data" / "raw" / "all_market_history.parquet")

def inspect():
    parquet_file = pq.ParquetFile(PARQUET_PATH)
    schema = parquet_file.schema_arrow
    num_rows = parquet_file.metadata.num_rows
    num_cols = parquet_file.metadata.num_columns
    
    print(f"Total Rows: {num_rows:,}")
    print(f"Total Columns: {num_cols}")
    print("\nSchema:")
    for field in schema:
        print(f"  - {field.name}: {field.type}")
        
    # Read sample or full table in chunks/table
    # The file is ~8.2MB compressed, fits easily into memory
    print("\nLoading dataset into pandas...")
    df = pd.read_parquet(PARQUET_PATH)
    print("DataFrame shape:", df.shape)
    print("\nFirst 3 rows:")
    print(df.head(3).to_dict(orient="records"))
    
    print("\nColumn Summary & Missing Values:")
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        null_pct = (null_count / len(df)) * 100
        n_unique = int(df[col].nunique())
        print(f"  {col}: {n_unique:,} unique values, {null_count:,} nulls ({null_pct:.2f}%)")
        
    # Dates
    if "date" in df.columns:
        date_col = "date"
    elif "Arrival_Date" in df.columns:
        date_col = "Arrival_Date"
    else:
        date_col = [c for c in df.columns if "date" in c.lower()][0]
        
    df[date_col] = pd.to_datetime(df[date_col])
    print(f"\nDate column: {date_col}")
    print(f"Min Date: {df[date_col].min()}")
    print(f"Max Date: {df[date_col].max()}")
    print(f"Total Unique Dates: {df[date_col].nunique()}")
    
    # Check Commodities
    comm_cols = [c for c in df.columns if "commodity" in c.lower()]
    print(f"\nCommodity columns: {comm_cols}")
    comm_col = comm_cols[0]
    top_comms = df[comm_col].value_counts().head(10)
    print("Top 10 commodities by record count:")
    for k, v in top_comms.items():
        print(f"  - {k}: {v:,}")
        
    # Check Markets
    market_cols = [c for c in df.columns if "market" in c.lower()]
    print(f"\nMarket columns: {market_cols}")
    market_col = market_cols[0]
    top_markets = df[market_col].value_counts().head(10)
    print("Top 10 markets by record count:")
    for k, v in top_markets.items():
        print(f"  - {k}: {v:,}")
        
    # Check Lasalgaon vs Mumbai Onion
    onion_mask = df[comm_col].astype(str).str.contains("onion", case=False)
    df_onion = df[onion_mask]
    print(f"\nTotal Onion Records: {len(df_onion):,}")
    
    lasalgaon_mask = df_onion[market_col].astype(str).str.contains("lasalgaon", case=False)
    mumbai_mask = df_onion[market_col].astype(str).str.contains("mumbai", case=False)
    
    df_lasalgaon_onion = df_onion[lasalgaon_mask]
    df_mumbai_onion = df_onion[mumbai_mask]
    
    print(f"Lasalgaon Onion Records: {len(df_lasalgaon_onion):,}")
    print(f"Lasalgaon Markets detected: {df_lasalgaon_onion[market_col].unique()}")
    print(f"Lasalgaon Varieties detected: {df_lasalgaon_onion['Variety'].unique() if 'Variety' in df.columns else 'N/A'}")
    
    print(f"\nMumbai Onion Records: {len(df_mumbai_onion):,}")
    print(f"Mumbai Markets detected: {df_mumbai_onion[market_col].unique()}")
    print(f"Mumbai Varieties detected: {df_mumbai_onion['Variety'].unique() if 'Variety' in df.columns else 'N/A'}")
    
    las_dates = set(df_lasalgaon_onion[date_col].dt.date)
    mum_dates = set(df_mumbai_onion[date_col].dt.date)
    overlap_dates = sorted(list(las_dates.intersection(mum_dates)))
    print(f"\nUnique Lasalgaon onion trading dates: {len(las_dates)}")
    print(f"Unique Mumbai onion trading dates: {len(mum_dates)}")
    print(f"Overlapping trading dates count: {len(overlap_dates)}")
    if overlap_dates:
        print(f"Overlap date range: {overlap_dates[0]} to {overlap_dates[-1]}")
        
    # Check Price columns and values
    price_cols = [c for c in df.columns if "price" in c.lower()]
    print(f"\nPrice columns: {price_cols}")
    for p in price_cols:
        print(f"  {p}: Min={df[p].min()}, Max={df[p].max()}, Median={df[p].median()}, Mean={df[p].mean():.2f}")
        
    # Check Arrival columns
    arrival_cols = [c for c in df.columns if "arrival" in c.lower()]
    print(f"\nArrival columns: {arrival_cols}")
    for a in arrival_cols:
        print(f"  {a}: Min={df[a].min()}, Max={df[a].max()}, Median={df[a].median()}, Mean={df[a].mean():.2f}")

if __name__ == "__main__":
    inspect()
