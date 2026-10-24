"""
MarketPulse India - Price Volatility & Market Shock Analytics
Investigation B: Rolling volatility, price return distributions, shock persistence, and cross-market contagion.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.ingestion.loader import get_loader


class VolatilityAnalyzer:
    """Analyzes price stability, volatility dynamics, and market shocks."""

    def __init__(self, loader=None):
        self.loader = loader or get_loader()

    def get_commodity_volatility_rankings(self) -> pd.DataFrame:
        """Calculate overall volatility (CV) ranking across all commodities."""
        sql = """
            SELECT 
                commodity,
                COUNT(*) as total_observations,
                COUNT(DISTINCT market_id) as reporting_markets,
                ROUND(AVG(modal_price_quintal), 2) as mean_price,
                ROUND(MEDIAN(modal_price_quintal), 2) as median_price,
                ROUND(STDDEV(modal_price_quintal), 2) as std_price,
                ROUND(STDDEV(modal_price_quintal) / NULLIF(AVG(modal_price_quintal), 0), 4) as price_cv,
                ROUND(AVG(arrivals_tonnes), 2) as avg_arrivals,
                ROUND(STDDEV(arrivals_tonnes) / NULLIF(AVG(arrivals_tonnes), 0), 4) as arrivals_cv
            FROM vw_clean_market_history
            WHERE is_valid_price
            GROUP BY commodity
            ORDER BY price_cv DESC
        """
        return self.loader.execute_df(sql)

    def get_market_series_volatility(
        self,
        commodity: str,
        market_id: str,
        rolling_window: int = 30,
    ) -> Dict[str, Any]:
        """
        Compute daily log returns, rolling volatility, and shock anomalies for a single market series.
        """
        sql = """
            SELECT 
                date,
                canonical_market_name,
                state,
                district,
                modal_price_quintal as price,
                arrivals_tonnes as arrivals,
                standardized_variety as variety
            FROM vw_clean_market_history
            WHERE commodity = ? AND market_id = ? AND is_valid_price
            ORDER BY date ASC
        """
        df = self.loader.execute_df(sql, [commodity, market_id])
        if len(df) < 15:
            return {"error": "Insufficient records for time-series volatility analysis."}

        df["log_price"] = np.log(df["price"])
        df["price_return"] = df["log_price"].diff()
        df["rolling_std"] = df["price"].rolling(window=rolling_window, min_periods=5).std()
        df["rolling_mean"] = df["price"].rolling(window=rolling_window, min_periods=5).mean()
        df["rolling_cv"] = df["rolling_std"] / df["rolling_mean"]

        # Shock detection: daily log return magnitude > 3x rolling standard error or > 25%
        return_std = df["price_return"].std()
        df["is_shock"] = df["price_return"].abs() > max(0.20, 2.5 * return_std)

        shocks_df = df[df["is_shock"]].copy()

        # AR(1) Persistence
        valid_returns = df["price_return"].dropna()
        ar1_corr = float(valid_returns.autocorr(lag=1)) if len(valid_returns) > 10 else 0.0

        return {
            "commodity": commodity,
            "market_id": market_id,
            "market_name": df["canonical_market_name"].iloc[0],
            "total_days": len(df),
            "mean_price": round(float(df["price"].mean()), 2),
            "std_price": round(float(df["price"].std()), 2),
            "overall_cv": round(float(df["price"].std() / df["price"].mean()), 4),
            "ar1_autocorr": round(ar1_corr, 4),
            "total_shocks_count": len(shocks_df),
            "shocks": shocks_df[["date", "price", "price_return", "arrivals"]].to_dict(orient="records"),
            "df": df,
        }
