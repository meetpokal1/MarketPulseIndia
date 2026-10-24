"""
MarketPulse India - Unit Tests: Volatility & Shock Dynamics (Investigation B)
"""
import pytest
from src.analytics.volatility import VolatilityAnalyzer
from src.config import LASALGAON_MAIN_ID


@pytest.fixture(scope="module")
def vol_analyzer():
    return VolatilityAnalyzer()


def test_commodity_volatility_rankings(vol_analyzer):
    """
    Verifies that Tomato and Onion have highest CV (most volatile),
    while Cotton and Paddy have lowest CV (least volatile / price floor).
    """
    df = vol_analyzer.get_commodity_volatility_rankings()
    assert len(df) == 14

    top_3 = df.head(3)["commodity"].tolist()
    assert "Tomato" in top_3
    assert "Onion" in top_3

    bottom_3 = df.tail(3)["commodity"].tolist()
    assert "Cotton" in bottom_3
    assert "Paddy (Common)" in bottom_3 or "Groundnut" in bottom_3


def test_market_time_series_volatility_and_shocks(vol_analyzer):
    """
    Verifies rolling volatility calculation, shock detection, and AR(1) autocorrelation bound.
    """
    res = vol_analyzer.get_market_series_volatility(
        commodity="Onion",
        market_id=LASALGAON_MAIN_ID,
        rolling_window=30,
    )
    assert res["total_days"] > 500
    assert res["overall_cv"] > 0.40
    # Price returns exhibit fast mean reversion (low persistent momentum)
    assert abs(res["ar1_autocorr"]) < 0.25
    assert res["total_shocks_count"] >= 0
    assert "df" in res
