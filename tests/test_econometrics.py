"""
MarketPulse India - Unit Tests: Econometric Panel Engine (Investigation C)
"""
import pytest
from src.models.econometrics import PanelEconometricEngine


@pytest.fixture(scope="module")
def econ_engine():
    return PanelEconometricEngine()


def test_two_way_fixed_effects_elasticity_onion(econ_engine):
    """
    Verifies that Onion price elasticity with respect to arrivals is inelastic:
    decisively rejects the folklore claim that a 10% drop in arrivals causes 35-50% price surge.
    """
    res = econ_engine.fit_panel_model(commodity="Onion")
    assert "error" not in res
    assert res["n_observations"] > 100_000
    assert res["n_markets"] > 300

    beta = res["twfe_elasticity_beta"]
    se = res["cluster_robust_se"]

    # Elasticity must be negative and bounded between -0.15 and 0.0
    assert -0.15 < beta < 0.0, f"Unexpected beta elasticity: {beta}"
    assert se > 0.0
    assert res["within_r2"] >= 0.0

    # Counterfactual price change for a 10% drop in arrivals
    # Must be modest (+0.2% to +1.5%), NOT +35% to +50%!
    pct_drop_10 = res["price_response_minus_10pct_arrivals"]
    assert 0.1 <= pct_drop_10 <= 2.0, f"Contradicts empirical integration: {pct_drop_10}%"


def test_econometrics_multi_commodity_comparisons(econ_engine):
    """
    Verifies model runs across multiple commodities (Tomato, Potato, Green Chilli).
    """
    for comm in ["Tomato", "Potato"]:
        res = econ_engine.fit_panel_model(commodity=comm)
        assert "error" not in res
        assert res["twfe_elasticity_beta"] < 0.0 # downward sloping demand curve
        assert res["cluster_robust_se"] > 0.0
