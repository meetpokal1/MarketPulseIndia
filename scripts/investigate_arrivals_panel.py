import duckdb
import pandas as pd
import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')
PARQUET = r"C:\Users\Meet Pokal\.gemini\antigravity\scratch\portfolio_research_oct2026\samples\all_market_history.parquet"
con = duckdb.connect()

print("="*80, flush=True)
print("INVESTIGATION C: ARRIVALS AND PRICES PANEL ECONOMETRIC REGRESSION", flush=True)
print("="*80, flush=True)

def run_panel_for_commodity(commodity_name, state=None, min_records_per_market=100):
    state_filter = f"AND state = '{state}'" if state else ""
    
    query = f"""
        SELECT 
            market_id,
            market,
            date,
            representative_price as price,
            arrivals_tonnes as arrivals
        FROM '{PARQUET}'
        WHERE commodity = '{commodity_name}'
          {state_filter}
          AND representative_price > 10.0
          AND arrivals_tonnes > 0.05
    """
    df = con.execute(query).df()
    
    m_counts = df['market_id'].value_counts()
    valid_markets = m_counts[m_counts >= min_records_per_market].index
    df = df[df['market_id'].isin(valid_markets)].copy()
    
    if len(df) < 500:
        print(f"Insufficient sample for {commodity_name}: {len(df)} rows.", flush=True)
        return None
        
    df['y'] = np.log(df['price'])
    df['x'] = np.log(df['arrivals'])
    df['year_month'] = pd.to_datetime(df['date']).dt.to_period('M').astype(str)
    
    N = len(df)
    G = df['market_id'].nunique()
    T = df['year_month'].nunique()
    
    # 1. Pooled OLS
    x_mean = df['x'].mean()
    y_mean = df['y'].mean()
    beta_pooled = np.sum((df['x'] - x_mean) * (df['y'] - y_mean)) / np.sum((df['x'] - x_mean)**2)
    
    # 2. Two-Way Fixed Effects via Two-Way Demeaning (Frisch-Waugh-Lovell)
    mean_y_m = df.groupby('market_id')['y'].transform('mean')
    mean_y_t = df.groupby('year_month')['y'].transform('mean')
    y_tilde = df['y'] - mean_y_m - mean_y_t + y_mean
    
    mean_x_m = df.groupby('market_id')['x'].transform('mean')
    mean_x_t = df.groupby('year_month')['x'].transform('mean')
    x_tilde = df['x'] - mean_x_m - mean_x_t + x_mean
    
    sum_xx = np.sum(x_tilde**2)
    beta_twfe = np.sum(x_tilde * y_tilde) / sum_xx
    
    # Residuals
    residuals = y_tilde - beta_twfe * x_tilde
    r2_within = 1.0 - (np.sum(residuals**2) / np.sum(y_tilde**2))
    
    # Cameron-Miller Cluster-Robust Standard Errors clustered by market_id
    df['x_e'] = x_tilde * residuals
    cluster_sums = df.groupby('market_id')['x_e'].sum().values
    meat = np.sum(cluster_sums**2)
    dfc = (N - 1) / (N - G - T - 1) * (G / (G - 1))
    var_beta = dfc * (meat / (sum_xx**2))
    se_twfe = np.sqrt(var_beta)
    
    t_stat = beta_twfe / se_twfe
    ci_lower = beta_twfe - 1.96 * se_twfe
    ci_upper = beta_twfe + 1.96 * se_twfe
    
    pct_for_10pct = ((1.10 ** beta_twfe) - 1.0) * 100.0
    pct_drop_10pct = ((0.90 ** beta_twfe) - 1.0) * 100.0
    
    print(f"\n--- {commodity_name} (State: {state or 'Multi-State Panel'}) ---", flush=True)
    print(f"Observations: N = {N:,} across {G:,} APMC markets ({T} months)", flush=True)
    print(f"Naive Pooled OLS Elasticity:        β = {beta_pooled:.4f}", flush=True)
    print(f"Two-Way Fixed Effects Elasticity:   β = {beta_twfe:.4f} (Cluster SE = {se_twfe:.4f}, t = {t_stat:.2f})", flush=True)
    print(f"95% Confidence Interval:            [{ci_lower:.4f}, {ci_upper:.4f}]", flush=True)
    print(f"Within R²:                          {r2_within:.4f}", flush=True)
    print(f"Price Response to +10% Arrivals:    {pct_for_10pct:+.2f}%", flush=True)
    print(f"Price Response to -10% Arrivals:    {pct_drop_10pct:+.2f}%", flush=True)
    
    return {
        "commodity": commodity_name,
        "state": state or "Multi-State",
        "N": N,
        "markets": G,
        "beta": beta_twfe,
        "se": se_twfe,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "pct_drop_10pct": pct_drop_10pct
    }

for comm in ['Onion', 'Tomato', 'Potato', 'Green Chilli', 'Banana', 'Brinjal']:
    run_panel_for_commodity(comm)

# Maharashtra specifically
run_panel_for_commodity('Onion', state='Maharashtra')
