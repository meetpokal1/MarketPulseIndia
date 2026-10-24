"""
MarketPulse India - Unit Tests: Market Spreads & Variety Matching (Investigation A)
"""
import pytest
from src.analytics.market_spreads import MarketSpreadEngine
from src.config import LASALGAON_MAIN_ID, MUMBAI_ONION_POTATO_ID


@pytest.fixture(scope="module")
def spread_engine():
    return MarketSpreadEngine()


def test_lasalgaon_vs_mumbai_overlap_reproduction(spread_engine):
    """
    Reproduces the 467-day historical text overlap and verifies
    the full 507-day overlap under persistent invariant market IDs.
    """
    # 1. Under persistent market_id matching across the full 25-month span
    res_id = spread_engine.compare_markets(
        commodity="Onion",
        source_market_id=LASALGAON_MAIN_ID,
        dest_market_id=MUMBAI_ONION_POTATO_ID,
        variety_filter_mode="ALL",
    )
    assert res_id["n_overlapping_days"] == 507
    assert res_id["min_date"] == "2024-08-30"
    assert res_id["max_date"] == "2026-09-26"
    assert res_id["negative_spread_pct"] > 70.0  # Over 70% negative spread days

    # 2. Under exact text match on previous name up to 2026-07-31
    res_text = spread_engine.loader.execute_df(f"""
        SELECT COUNT(*) as cnt
        FROM (SELECT date FROM raw_history WHERE commodity = 'Onion' AND market = 'Lasalgaon APMC') l
        INNER JOIN (SELECT date FROM raw_history WHERE commodity = 'Onion' AND market = 'Mumbai-Onion & Potato Market APMC') m
        ON l.date = m.date
    """)
    assert res_text.iloc[0]["cnt"] == 467, "Failed to reproduce exact 467-day historical text overlap!"


def test_variety_heterogeneity_distribution(spread_engine):
    """
    Verifies that Mumbai APMC aggregates 100% of arrivals under 'Other',
    while Lasalgaon distinguishes 'Unhali', 'Red', and 'Other'.
    """
    res = spread_engine.compare_markets(
        commodity="Onion",
        source_market_id=LASALGAON_MAIN_ID,
        dest_market_id=MUMBAI_ONION_POTATO_ID,
        variety_filter_mode="ALL",
    )
    mum_vars = res["dest_variety_distribution"]
    las_vars = res["source_variety_distribution"]

    # Mumbai is 100% 'Other'
    assert "Other" in mum_vars
    assert mum_vars["Other"] == 507
    assert len(mum_vars) == 1

    # Lasalgaon has granular cultivars
    assert "Unhali" in las_vars
    assert "Red" in las_vars
    assert "Other" in las_vars
    assert las_vars["Unhali"] == 110
    assert las_vars["Red"] == 150
    assert las_vars["Other"] == 247


def test_controlled_variety_spread_filtering(spread_engine):
    """
    Verifies that filtering by exact variety or sub-categories executes correctly.
    """
    res_unhali = spread_engine.compare_markets(
        commodity="Onion",
        source_market_id=LASALGAON_MAIN_ID,
        dest_market_id=MUMBAI_ONION_POTATO_ID,
        variety_filter_mode="Unhali",
    )
    assert res_unhali["n_overlapping_days"] == 110
    assert res_unhali["mean_spread_quintal"] < 0 # Lasalgaon Unhali trades at premium over Mumbai Other
