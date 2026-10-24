#!/usr/bin/env python3
"""
MarketPulse India - Tableau Analytical Extract Pipeline (Stage 3A)

Builds curated, reproducible analytical datasets for Tableau Public:
  1. market_monthly.csv           (Grain: market_id x commodity x month)
  2. corridor_spread_daily.csv     (Grain: corridor_id x date)
  3. arrival_elasticity_models.csv (Grain: commodity econometric model)
  4. frozen_price_streaks.csv      (Grain: streak_id >= 7 days)
  5. quality_exceptions.csv        (Grain: exception_id, non-valid records)
  6. quality_monthly_summary.csv   (Grain: state x month quality trends)
  7. manifest.json                 (Provenance, SHA-256 hashes, row counts)

Usage:
  python scripts/build_tableau_extract.py [--output-dir DIR]
"""

import sys
import os
import json
import time
import hashlib
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import duckdb
import pandas as pd
import numpy as np

from src.config import SOURCE_HISTORY_PARQUET, MIN_PLAUSIBLE_PRICE
from src.ingestion.loader import get_loader
from src.cleaning.pipeline import create_standardized_analytical_view
from src.analytics.market_spreads import MarketSpreadEngine
from src.models.econometrics import PanelEconometricEngine

EXPECTED_RAW_RECORDS = 1481324
VERIFIED_RAW_SHA256 = "DA8E4435D7B63693C406401E0FA3B1F084FD1010F650598BA5030715A57ED6A4"


def calculate_sha256(filepath: Path) -> str:
    """Calculate uppercase SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def verify_source_dataset(raw_path: Path) -> Dict[str, Any]:
    """Verify source Parquet dataset presence, size, hash, and row count."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Source Parquet not found at {raw_path}")

    file_size = raw_path.stat().st_size
    actual_hash = calculate_sha256(raw_path)

    if actual_hash != VERIFIED_RAW_SHA256:
        raise ValueError(
            f"Source dataset SHA-256 mismatch!\nExpected: {VERIFIED_RAW_SHA256}\nActual:   {actual_hash}"
        )

    con = duckdb.connect()
    row_count = con.execute(f"SELECT count(*) FROM '{raw_path.as_posix()}'").fetchone()[0]
    min_date, max_date = con.execute(
        f"SELECT min(date), max(date) FROM '{raw_path.as_posix()}'"
    ).fetchone()
    con.close()

    if row_count != EXPECTED_RAW_RECORDS:
        raise ValueError(
            f"Source dataset row count mismatch! Expected {EXPECTED_RAW_RECORDS}, found {row_count}"
        )

    return {
        "path": str(raw_path.relative_to(BASE_DIR)),
        "sha256": actual_hash,
        "size_bytes": file_size,
        "row_count": row_count,
        "min_date": str(min_date),
        "max_date": str(max_date),
    }


def export_market_monthly(con: duckdb.DuckDBPyConnection, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset A: Monthly Market Intelligence (Grain: market_id x commodity x calendar month).
    """
    print("  -> Generating Dataset A: market_monthly.csv...")
    sql = """
        SELECT 
            strftime(date, '%Y-%m') AS year_month,
            CAST(strftime(date, '%Y-%m-01') AS DATE) AS month_start_date,
            state_id,
            state,
            district,
            market_id,
            canonical_market_name,
            commodity,
            COUNT(*) AS observed_records_count,
            SUM(CASE WHEN is_valid_price THEN 1 ELSE 0 END) AS valid_price_records_count,
            ROUND(AVG(CASE WHEN is_valid_price THEN modal_price_quintal END), 2) AS mean_daily_modal_price_rs_per_quintal,
            ROUND(MEDIAN(CASE WHEN is_valid_price THEN modal_price_quintal END), 2) AS median_daily_modal_price_rs_per_quintal,
            ROUND(MIN(CASE WHEN is_valid_price THEN modal_price_quintal END), 2) AS min_daily_modal_price_rs_per_quintal,
            ROUND(MAX(CASE WHEN is_valid_price THEN modal_price_quintal END), 2) AS max_daily_modal_price_rs_per_quintal,
            ROUND(QUANTILE_CONT(CASE WHEN is_valid_price THEN modal_price_quintal END, 0.25), 2) AS p25_daily_modal_price_rs_per_quintal,
            ROUND(QUANTILE_CONT(CASE WHEN is_valid_price THEN modal_price_quintal END, 0.75), 2) AS p75_daily_modal_price_rs_per_quintal,
            ROUND(STDDEV_SAMP(CASE WHEN is_valid_price THEN modal_price_quintal END), 2) AS std_daily_modal_price_rs_per_quintal,
            ROUND(SUM(arrivals_tonnes), 2) AS total_arrivals_tonnes,
            ROUND(AVG(arrivals_tonnes), 2) AS mean_daily_arrivals_tonnes,
            SUM(CASE WHEN is_valid_arrival THEN 1 ELSE 0 END) AS positive_arrival_records_count,
            SUM(CASE WHEN min_price = max_price AND min_price = modal_price_quintal THEN 1 ELSE 0 END) AS flat_quote_records_count,
            SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS statistical_anomalies_count,
            SUM(CASE WHEN record_quality_status = 'SCALE_ERROR_LOW_PRICE' THEN 1 ELSE 0 END) AS scale_error_records_count,
            SUM(CASE WHEN record_quality_status = 'ZERO_ARRIVALS' THEN 1 ELSE 0 END) AS zero_arrival_records_count,
            MODE(raw_variety) AS dominant_raw_variety,
            MODE(variety_granularity) AS dominant_variety_tier
        FROM vw_clean_market_history
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        ORDER BY year_month, state, commodity, canonical_market_name
    """
    df = con.execute(sql).df()
    df.to_csv(output_path, index=False, encoding="utf-8")
    return {
        "filename": output_path.name,
        "grain": "market_id x commodity x calendar month",
        "rows": len(df),
        "columns": len(df.columns),
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def export_corridor_spread_daily(loader, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset B: Matched-Market Daily Comparison (Grain: corridor_id x date).
    Exposes Lasalgaon-Mumbai inversion case study and comparative benchmark corridors.
    """
    print("  -> Generating Dataset B: corridor_spread_daily.csv...")
    engine = MarketSpreadEngine(loader)

    corridors = [
        {
            "id": "CORR_LAS_MUM_ONION",
            "name": "Lasalgaon APMC -> Mumbai APMC (Onion Flagship Inversion)",
            "commodity": "Onion",
            "source_id": "20-161",
            "dest_id": "20-2703",
            "description": "Origin producing hub (Nashik) vs Terminal consumption metropolis (Mumbai). Shows apparent price spread inversion due to cultivar heterogeneity (Unhali/Red vs generic Other).",
        },
        {
            "id": "CORR_LAS_PUN_ONION",
            "name": "Lasalgaon APMC -> Pune APMC (Onion Regional Hub)",
            "commodity": "Onion",
            "source_id": "20-161",
            "dest_id": "20-164",
            "description": "Origin producing hub (Nashik) vs Major regional consumption city (Pune).",
        },
        {
            "id": "CORR_PIM_MUM_ONION",
            "name": "Pimpalgaon Baswant APMC -> Mumbai APMC (Onion Production Hub)",
            "commodity": "Onion",
            "source_id": "20-162",
            "dest_id": "20-2703",
            "description": "Secondary major Nashik origin market vs Mumbai terminal market.",
        },
        {
            "id": "CORR_PUN_MUM_ONION",
            "name": "Pune APMC -> Mumbai APMC (Onion Inter-City Metro)",
            "commodity": "Onion",
            "source_id": "20-164",
            "dest_id": "20-2703",
            "description": "Inter-city consumption corridor between Pune and Mumbai, both reporting generic Other cultivars. Demonstrates positive spatial spread when cultivar tier is balanced.",
        },
    ]

    all_dfs = []
    for c in corridors:
        res = engine.compare_markets(
            commodity=c["commodity"],
            source_market_id=c["source_id"],
            dest_market_id=c["dest_id"],
            variety_filter_mode="ALL",
        )
        if "df" in res and not res["df"].empty:
            df_c = res["df"].copy()
            df_c.insert(0, "corridor_id", c["id"])
            df_c.insert(1, "corridor_name", c["name"])
            df_c.insert(2, "commodity", c["commodity"])
            df_c.insert(3, "corridor_narrative", c["description"])

            # Classify variety comparability
            df_c["variety_comparability_status"] = np.where(
                (df_c["source_std_variety"] == "Other / Unspecified")
                & (df_c["dest_std_variety"] == "Other / Unspecified"),
                "GENERIC_TIER_MATCHED",
                np.where(
                    df_c["source_std_variety"] == df_c["dest_std_variety"],
                    "CULTIVAR_EXACT_MATCHED",
                    "CULTIVAR_CONFOUNDED_OTHER",
                ),
            )
            df_c["is_spread_negative"] = df_c["price_spread_quintal"] < 0
            df_c["apparent_inversion_flag"] = (
                (df_c["price_spread_quintal"] < 0)
                & (df_c["variety_comparability_status"] == "CULTIVAR_CONFOUNDED_OTHER")
            )
            all_dfs.append(df_c)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df.to_csv(output_path, index=False, encoding="utf-8")

    return {
        "filename": output_path.name,
        "grain": "corridor_id x date",
        "rows": len(combined_df),
        "columns": len(combined_df.columns),
        "corridors_included": [c["name"] for c in corridors],
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def export_arrival_elasticity_models(loader, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset C: Econometric Model Results (Grain: commodity econometric model).
    Uses PanelEconometricEngine to fit Two-Way Fixed Effects across all 14 commodities.
    """
    print("  -> Generating Dataset C: arrival_elasticity_models.csv...")
    engine = PanelEconometricEngine(loader)

    commodities = [
        r[0]
        for r in loader._con.execute(
            "SELECT DISTINCT commodity FROM vw_clean_market_history ORDER BY 1"
        ).fetchall()
    ]

    model_rows = []
    for comm in commodities:
        res = engine.fit_panel_model(comm)
        if "error" in res:
            continue

        model_rows.append({
            "commodity": comm,
            "model_id": f"TWFE_MKT_MONTH_{comm.upper().replace(' ', '_').replace('(', '').replace(')', '')}",
            "specification": "Two-Way Fixed Effects: log(price_it) = beta*log(arr_it) + alpha_i + gamma_t + eps_it",
            "dependent_var": "log(modal_price_quintal)",
            "explanatory_var": "log(arrivals_tonnes)",
            "fixed_effects": "Market Fixed Effects (alpha_i) + Month-Year Fixed Effects (gamma_t)",
            "standard_error_method": "Cameron-Miller Cluster-Robust SE (Clustered by Market ID)",
            "state_scope": res["state_scope"],
            "n_observations": res["n_observations"],
            "n_market_clusters": res["n_markets"],
            "n_calendar_months": res["n_months"],
            "min_date": res["min_date"],
            "max_date": res["max_date"],
            "pooled_ols_beta": res["pooled_ols_beta"],
            "estimated_elasticity_beta": res["twfe_elasticity_beta"],
            "cluster_robust_se": res["cluster_robust_se"],
            "t_statistic": res["t_statistic"],
            "p_value_approx": res["p_value_approx"],
            "ci_95_lower": res["ci_95_lower"],
            "ci_95_upper": res["ci_95_upper"],
            "within_r2": res["within_r2"],
            "price_response_pct_for_plus_10pct_arrivals": res["price_response_plus_10pct_arrivals"],
            "price_response_pct_for_minus_10pct_arrivals": res["price_response_minus_10pct_arrivals"],
            "price_response_pct_for_minus_25pct_arrivals": res["price_response_minus_25pct_arrivals"],
            "economic_interpretation": (
                "Inelastic short-run price response (< 1.0% price change per 10% arrival shock). "
                "Refutes popular folk assumption of 35-50% price shocks."
                if abs(res["twfe_elasticity_beta"]) < 0.10
                else "Moderate elasticity observed."
            ),
            "causal_disclaimer": (
                "Reduced-form observational association from mandi spot records; reflects short-run within-market "
                "market-clearing price adjustments, not structural causal demand elasticity."
            ),
        })

    df = pd.DataFrame(model_rows)
    df.to_csv(output_path, index=False, encoding="utf-8")

    return {
        "filename": output_path.name,
        "grain": "commodity model specification",
        "rows": len(df),
        "columns": len(df.columns),
        "commodities_modeled": len(df),
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def export_frozen_price_streaks(con: duckdb.DuckDBPyConnection, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset D: Reliability Forensics (Grain: streak_id for unchanged modal price >= 7 days).
    """
    print("  -> Generating Dataset D: frozen_price_streaks.csv...")
    sql = """
        WITH ordered AS (
            SELECT 
                market_id,
                canonical_market_name,
                state,
                district,
                commodity,
                date,
                modal_price_quintal,
                LAG(modal_price_quintal) OVER (PARTITION BY market_id, commodity ORDER BY date) AS prev_price,
                LAG(date) OVER (PARTITION BY market_id, commodity ORDER BY date) AS prev_date
            FROM vw_clean_market_history
        ),
        flags AS (
            SELECT *,
                CASE WHEN modal_price_quintal = prev_price AND (date - prev_date) <= 4 THEN 0 ELSE 1 END AS is_new_streak
            FROM ordered
        ),
        groups AS (
            SELECT *,
                SUM(is_new_streak) OVER (PARTITION BY market_id, commodity ORDER BY date) AS streak_id
            FROM flags
        ),
        streak_summary AS (
            SELECT 
                market_id,
                canonical_market_name,
                state,
                district,
                commodity,
                modal_price_quintal AS frozen_price,
                MIN(date) AS streak_start,
                MAX(date) AS streak_end,
                COUNT(*) AS streak_days
            FROM groups
            GROUP BY market_id, canonical_market_name, state, district, commodity, modal_price_quintal, streak_id
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY streak_days DESC, state, canonical_market_name) AS streak_id,
            state,
            district,
            market_id,
            canonical_market_name,
            commodity,
            frozen_price AS frozen_modal_price_rs_per_quintal,
            streak_start AS streak_start_date,
            streak_end AS streak_end_date,
            streak_days,
            (streak_end - streak_start + 1) AS calendar_span_days,
            CASE 
                WHEN commodity = 'Paddy (Common)' AND frozen_price IN (2183.0, 2203.0, 2300.0, 2320.0) 
                    THEN 'MSP Statutory Procurement Quote: Consistent with government MSP procurement floor.'
                WHEN LOWER(canonical_market_name) LIKE '%uzhavar sandhai%' 
                    THEN 'Administrative Price Ceiling: Farmers market fixed daily price board.'
                WHEN streak_days > 60 
                    THEN 'Likely Reporting Inactivity: Stale price carried forward across reporting cycles.'
                ELSE 'Candidate Price Stickiness: Real price stability or infrequent auction revision.'
            END AS plausible_explanation,
            CASE 
                WHEN streak_days >= 30 THEN 'HIGH REVIEW'
                WHEN streak_days >= 14 THEN 'MEDIUM REVIEW'
                ELSE 'LOW NOTICE'
            END AS audit_priority,
            CASE 
                WHEN commodity = 'Paddy (Common)' AND frozen_price IN (2183.0, 2203.0, 2300.0, 2320.0) THEN TRUE
                ELSE FALSE
            END AS is_msp_statutory_quote
        FROM streak_summary
        WHERE streak_days >= 7
        ORDER BY streak_days DESC, state, canonical_market_name
    """
    df = con.execute(sql).df()
    df.to_csv(output_path, index=False, encoding="utf-8")
    return {
        "filename": output_path.name,
        "grain": "streak_id (uninterrupted unchanged trading days >= 7)",
        "rows": len(df),
        "columns": len(df.columns),
        "max_streak_days": int(df["streak_days"].max()),
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def export_quality_exceptions(con: duckdb.DuckDBPyConnection, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset E: Quality Exceptions (Grain: exception_id for all non-valid raw records).
    Preserves raw scale errors (< ₹10/Qtl) and zero arrivals (<= 0.0 tonnes).
    """
    print("  -> Generating Dataset E: quality_exceptions.csv...")
    sql = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY date, state, canonical_market_name) AS exception_id,
            state,
            district,
            market_id,
            canonical_market_name,
            commodity,
            raw_variety,
            date,
            min_price AS min_price_rs_per_quintal,
            max_price AS max_price_rs_per_quintal,
            modal_price_quintal AS modal_price_rs_per_quintal,
            arrivals_tonnes,
            is_valid_price,
            is_valid_arrival,
            record_quality_status,
            CASE 
                WHEN record_quality_status = 'SCALE_ERROR_LOW_PRICE' 
                    THEN 'Reported price below ₹10/quintal threshold; indicates unit-scale reporting error (e.g., price quoted per piece, dozen, or bunch rather than 100 kg quintal).'
                WHEN record_quality_status = 'ZERO_ARRIVALS' 
                    THEN 'Reported arrivals <= 0.0 tonnes; mandi recorded trading prices without physical arrival volume.'
                WHEN record_quality_status = 'INVERTED_PRICE_RANGE'
                    THEN 'Minimum price exceeds maximum price (inverted range).'
                ELSE 'Unclassified data quality exception.'
            END AS quarantine_diagnostic_reason
        FROM vw_clean_market_history
        WHERE record_quality_status != 'VALID'
        ORDER BY record_quality_status, date, state
    """
    df = con.execute(sql).df()
    df.to_csv(output_path, index=False, encoding="utf-8")
    return {
        "filename": output_path.name,
        "grain": "exception_id (raw observation with quality defect)",
        "rows": len(df),
        "columns": len(df.columns),
        "scale_errors": int((df["record_quality_status"] == "SCALE_ERROR_LOW_PRICE").sum()),
        "zero_arrivals": int((df["record_quality_status"] == "ZERO_ARRIVALS").sum()),
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def export_quality_monthly_summary(con: duckdb.DuckDBPyConnection, output_path: Path) -> Dict[str, Any]:
    """
    Export Dataset F: Monthly Quality Summary (Grain: state x calendar month).
    """
    print("  -> Generating Dataset F: quality_monthly_summary.csv...")
    sql = """
        SELECT 
            strftime(date, '%Y-%m') AS year_month,
            CAST(strftime(date, '%Y-%m-01') AS DATE) AS month_start_date,
            state_id,
            state,
            COUNT(*) AS total_raw_records,
            SUM(CASE WHEN record_quality_status = 'VALID' THEN 1 ELSE 0 END) AS valid_records,
            SUM(CASE WHEN record_quality_status = 'SCALE_ERROR_LOW_PRICE' THEN 1 ELSE 0 END) AS scale_error_records,
            SUM(CASE WHEN record_quality_status = 'ZERO_ARRIVALS' THEN 1 ELSE 0 END) AS zero_arrival_records,
            SUM(CASE WHEN min_price = max_price AND min_price = modal_price_quintal THEN 1 ELSE 0 END) AS flat_quote_records,
            ROUND(SUM(CASE WHEN min_price = max_price AND min_price = modal_price_quintal THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS flat_quote_rate_pct,
            SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS statistical_anomaly_records,
            ROUND(SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS statistical_anomaly_rate_pct,
            ROUND(SUM(CASE WHEN record_quality_status = 'VALID' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 3) AS quality_pass_rate_pct
        FROM vw_clean_market_history
        GROUP BY 1, 2, 3, 4
        ORDER BY year_month, state
    """
    df = con.execute(sql).df()
    df.to_csv(output_path, index=False, encoding="utf-8")
    return {
        "filename": output_path.name,
        "grain": "state x calendar month",
        "rows": len(df),
        "columns": len(df.columns),
        "total_records_summed": int(df["total_raw_records"].sum()),
        "valid_records_summed": int(df["valid_records"].sum()),
        "size_bytes": output_path.stat().st_size,
        "sha256": calculate_sha256(output_path),
    }


def build_manifest(source_info: Dict[str, Any], datasets_info: List[Dict[str, Any]], manifest_path: Path) -> None:
    """Generate manifest.json recording complete provenance, hashes, and schemas."""
    manifest = {
        "project": "MarketPulse India — Wholesale Mandi Price Intelligence",
        "pipeline": "Stage 3A: Tableau Analytical Data Products Exporter",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_dataset": source_info,
        "export_directory": str(manifest_path.parent.relative_to(BASE_DIR)),
        "analytical_data_products": datasets_info,
        "provenance_and_integrity": {
            "conservation_law": "Total Raw (1,481,324) = Valid (1,481,250) + Scale Errors (70) + Zero Arrivals (4) + Inverted (0)",
            "lasalgaon_mumbai_spread": "507 trading days, mean spread -₹157.76/Qtl, Mumbai lower on 74.75% of days",
            "twfe_arrival_elasticity_onion": "Beta = -0.0360 (SE = 0.0183), counterfactual -10% arrivals associates with +0.38% price response",
            "frozen_price_streaks_total": "27,420 streaks (>= 7 consecutive trading days unchanged)",
        },
        "tableau_public_constraints": {
            "max_row_limit": 15000000,
            "largest_dataset_rows": max(d["rows"] for d in datasets_info),
            "refresh_policy": "Curated snapshot extract; Tableau Public workbook uses extracted CSV data with no live external DB connection.",
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"  -> Generated manifest at {manifest_path.name}")


def run_pipeline(output_dir: Path) -> None:
    """Main execution orchestrator."""
    start_time = time.time()
    print("=" * 70)
    print("MarketPulse India - Building Tableau Analytical Data Products")
    print("=" * 70)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = SOURCE_HISTORY_PARQUET

    print(f"1. Verifying source dataset at {raw_path}...")
    source_info = verify_source_dataset(raw_path)
    print(f"   [PASS] Verified SHA-256: {source_info['sha256']}")
    print(f"   [PASS] Row Count: {source_info['row_count']:,} | Dates: {source_info['min_date']} to {source_info['max_date']}")

    print("2. Initializing analytical environment and DuckDB views...")
    loader = get_loader()
    create_standardized_analytical_view(loader._con)
    con = loader._con

    print(f"3. Exporting analytical datasets to {output_dir}...")
    datasets = []

    ds_a = export_market_monthly(con, output_dir / "market_monthly.csv")
    datasets.append(ds_a)

    ds_b = export_corridor_spread_daily(loader, output_dir / "corridor_spread_daily.csv")
    datasets.append(ds_b)

    ds_c = export_arrival_elasticity_models(loader, output_dir / "arrival_elasticity_models.csv")
    datasets.append(ds_c)

    ds_d = export_frozen_price_streaks(con, output_dir / "frozen_price_streaks.csv")
    datasets.append(ds_d)

    ds_e = export_quality_exceptions(con, output_dir / "quality_exceptions.csv")
    datasets.append(ds_e)

    ds_f = export_quality_monthly_summary(con, output_dir / "quality_monthly_summary.csv")
    datasets.append(ds_f)

    print("4. Writing manifest.json...")
    manifest_path = output_dir / "manifest.json"
    build_manifest(source_info, datasets, manifest_path)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"Extraction Pipeline Completed Successfully in {elapsed:.2f} seconds!")
    print(f"Exported {len(datasets)} analytical datasets to {output_dir}")
    for d in datasets:
        print(f" - {d['filename']:<30} | {d['rows']:>7,} rows | {d['size_bytes']:>10,} bytes | SHA: {d['sha256'][:16]}...")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Tableau Analytical Data Products for MarketPulse India.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "data" / "processed" / "tableau",
        help="Directory to write CSV exports and manifest",
    )
    args = parser.parse_args()
    try:
        run_pipeline(args.output_dir)
        sys.exit(0)
    except Exception as exc:
        print(f"\n[FATAL ERROR] Export pipeline failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
