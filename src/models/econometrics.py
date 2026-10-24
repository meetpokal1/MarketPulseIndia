"""
MarketPulse India - Econometric Panel Model
Investigation C: Two-Way Fixed Effects Panel Regression of Prices on Arrivals.
"""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from src.ingestion.loader import get_loader


class PanelEconometricEngine:
    """
    Fits two-way fixed effects panel regression:
    log(price_it) = beta * log(arrivals_it) + alpha_i (market FE) + gamma_t (month FE) + eps_it
    with cluster-robust standard errors clustered at the market level.
    """

    def __init__(self, loader=None):
        self.loader = loader or get_loader()

    def fit_panel_model(
        self,
        commodity: str,
        state: Optional[str] = None,
        min_market_observations: int = 50,
    ) -> Dict[str, Any]:
        """
        Fit two-way fixed effects panel model for the chosen commodity.
        """
        state_clause = "AND state = ?" if state else ""
        params = [commodity, state] if state else [commodity]

        sql = f"""
            SELECT 
                market_id,
                canonical_market_name,
                state,
                district,
                date,
                modal_price_quintal as price,
                arrivals_tonnes as arrivals
            FROM vw_clean_market_history
            WHERE commodity = ? {state_clause}
              AND is_valid_price
              AND is_valid_arrival
        """
        df = self.loader.execute_df(sql, params)

        # Filter markets with sufficient observations
        market_counts = df["market_id"].value_counts()
        valid_markets = market_counts[market_counts >= min_market_observations].index
        df = df[df["market_id"].isin(valid_markets)].copy()

        if len(df) < 200 or df["market_id"].nunique() < 2:
            return {
                "error": f"Insufficient panel observations for {commodity} (N={len(df)}, Markets={df['market_id'].nunique()})."
            }

        df["y"] = np.log(df["price"])
        df["x"] = np.log(df["arrivals"])
        df["year_month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)

        N = len(df)
        G = df["market_id"].nunique()
        T = df["year_month"].nunique()

        # 1. Naive Pooled OLS
        x_mean = df["x"].mean()
        y_mean = df["y"].mean()
        beta_pooled = float(np.sum((df["x"] - x_mean) * (df["y"] - y_mean)) / np.sum((df["x"] - x_mean) ** 2))

        # 2. Two-Way Fixed Effects via Frisch-Waugh-Lovell demeaning
        mean_y_m = df.groupby("market_id")["y"].transform("mean")
        mean_y_t = df.groupby("year_month")["y"].transform("mean")
        y_tilde = df["y"] - mean_y_m - mean_y_t + y_mean

        mean_x_m = df.groupby("market_id")["x"].transform("mean")
        mean_x_t = df.groupby("year_month")["x"].transform("mean")
        x_tilde = df["x"] - mean_x_m - mean_x_t + x_mean

        sum_xx = float(np.sum(x_tilde ** 2))
        beta_twfe = float(np.sum(x_tilde * y_tilde) / sum_xx)

        # Residuals & Within R-squared
        residuals = y_tilde - beta_twfe * x_tilde
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum(y_tilde ** 2))
        r2_within = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        # Cameron-Miller Cluster-Robust Standard Errors (clustered by market_id)
        df["x_e"] = x_tilde * residuals
        cluster_sums = df.groupby("market_id")["x_e"].sum().values
        meat = float(np.sum(cluster_sums ** 2))
        dfc = ((N - 1) / max(1, N - G - T - 1)) * (G / max(1, G - 1))
        var_beta = dfc * (meat / (sum_xx ** 2))
        se_twfe = float(np.sqrt(max(1e-12, var_beta)))

        t_stat = beta_twfe / se_twfe
        ci_lower = beta_twfe - 1.96 * se_twfe
        ci_upper = beta_twfe + 1.96 * se_twfe

        # Estimated price responses
        price_change_plus_10 = float(((1.10 ** beta_twfe) - 1.0) * 100.0)
        price_change_minus_10 = float(((0.90 ** beta_twfe) - 1.0) * 100.0)
        price_change_minus_25 = float(((0.75 ** beta_twfe) - 1.0) * 100.0)

        return {
            "commodity": commodity,
            "state_scope": state or "Multi-State",
            "n_observations": N,
            "n_markets": G,
            "n_months": T,
            "min_date": str(df["date"].min()),
            "max_date": str(df["date"].max()),
            "pooled_ols_beta": round(beta_pooled, 4),
            "twfe_elasticity_beta": round(beta_twfe, 4),
            "cluster_robust_se": round(se_twfe, 4),
            "t_statistic": round(t_stat, 2),
            "p_value_approx": "< 0.001" if abs(t_stat) > 3.29 else ("< 0.05" if abs(t_stat) > 1.96 else round(float(2 * (1 - 0.975)), 3)),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4),
            "within_r2": round(r2_within, 4),
            "price_response_plus_10pct_arrivals": round(price_change_plus_10, 2),
            "price_response_minus_10pct_arrivals": round(price_change_minus_10, 2),
            "price_response_minus_25pct_arrivals": round(price_change_minus_25, 2),
            "sample_df": df[["date", "canonical_market_name", "price", "arrivals", "x", "y"]].sample(min(1500, len(df)), random_state=42),
        }
