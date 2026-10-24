"""
MarketPulse India - Unit Tests: Reliability & Reporting Quality (Investigation D)
"""
import pytest
from src.analytics.reliability_audit import ReliabilityAuditor


@pytest.fixture(scope="module")
def auditor():
    return ReliabilityAuditor()


def test_frozen_price_streaks_identification(auditor):
    """
    Verifies detection of prolonged frozen price streaks (>= 7 days).
    """
    df = auditor.get_frozen_price_streaks(min_streak_days=7, limit=50)
    assert len(df) > 0
    assert "streak_days" in df.columns
    assert "plausible_explanation" in df.columns
    assert "audit_priority" in df.columns

    # Verify that the longest streaks exceed 300 days (e.g. Pattukottai Banana or Telangana Paddy)
    assert df["streak_days"].max() > 300


def test_reporting_blackouts_detection(auditor):
    """
    Verifies detection of large reporting gaps (>= 30 days).
    """
    df = auditor.get_reporting_blackouts(min_gap_days=30, limit=50)
    assert len(df) > 0
    assert df["blackout_days"].max() >= 30
    assert "diagnostic_category" in df.columns


def test_state_flat_quote_rate_divergence(auditor):
    """
    Verifies state-level differences in flat quotes (min == max == modal).
    Telangana has highest rate (> 30%), Maharashtra has lowest (< 10%).
    """
    df = auditor.get_state_flat_quote_summary()
    assert len(df) == 6

    state_dict = dict(zip(df["state"], df["flat_quote_pct"]))
    assert state_dict["Telangana"] > 30.0
    assert state_dict["Maharashtra"] < 10.0
