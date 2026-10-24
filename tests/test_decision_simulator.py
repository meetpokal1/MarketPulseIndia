"""
MarketPulse India - Unit Tests: Decision Simulator
"""
import pytest
from src.simulator.decision_simulator import DecisionSimulator


def test_simulation_accounting_and_delivered_cost():
    """
    Verifies that delivered cost accounting is mathematically consistent:
    Capital Outlay = Procurement + Cess + Freight + Handling
    Delivered Quantity = Procured Quantity * (1 - Shrinkage)
    Breakeven Unit Cost = Capital Outlay / Delivered Quantity
    """
    res = DecisionSimulator.simulate_procurement_and_transit(
        source_market_name="Lasalgaon APMC",
        dest_market_name="Mumbai APMC",
        commodity="Onion",
        purchase_price_quintal=2000.0,
        dest_reference_price_quintal=2300.0,
        quantity_tonnes=10.0,            # 100 quintals
        freight_cost_per_quintal=120.0,   # ₹12,000
        handling_cost_per_quintal=30.0,   # ₹3,000
        mandi_cess_pct=1.05,             # 1.05% of ₹200,000 = ₹2,100
        transit_shrinkage_pct=2.0,       # 2% loss -> 98 quintals delivered
    )

    costs = res["costs"]
    delivered = res["delivered"]

    # Verify outlays
    assert costs["gross_procurement_cost"] == 200_000.0
    assert costs["mandi_cess_cost"] == 2_100.0
    assert costs["total_freight_cost"] == 12_000.0
    assert costs["total_handling_cost"] == 3_000.0
    assert costs["total_landed_capital"] == 217_100.0

    # Verify physical delivered quantity
    assert delivered["saleable_quantity_quintals"] == 98.0
    assert delivered["saleable_quantity_tonnes"] == 9.8

    # Verify breakeven unit cost
    expected_be = round(217_100.0 / 98.0, 2) # ₹2,215.31/quintal
    assert delivered["breakeven_cost_per_quintal"] == expected_be

    # Verify differential
    expected_rev = 2300.0 * 98.0 # ₹225,400.0
    expected_diff = round(expected_rev - 217_100.0, 2) # ₹8,300.0
    assert delivered["hypothetical_net_differential"] == expected_diff
    assert delivered["is_economically_viable"] is True

    # Disclaimer check
    assert "HYPOTHETICAL" in res["disclaimer"]


def test_sensitivity_matrix_structure():
    """Verifies sensitivity matrix covers multiple freight rates and shrinkage levels."""
    res = DecisionSimulator.simulate_procurement_and_transit(
        source_market_name="Lasalgaon APMC",
        dest_market_name="Mumbai APMC",
        commodity="Onion",
        purchase_price_quintal=2000.0,
        dest_reference_price_quintal=2100.0, # Lower destination price
    )
    matrix = res["sensitivity_matrix"]
    assert len(matrix) == 16 # 4 freight rates x 4 shrinkage rates
    assert "breakeven_cost_quintal" in matrix.columns
    assert "scenario_differential" in matrix.columns
    assert "is_viable" in matrix.columns
