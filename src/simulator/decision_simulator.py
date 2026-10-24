"""
MarketPulse India - Market Decision & Transport Logistics Simulator
Hypothetical scenario tool for procurement and spatial transport economics.
"""
from typing import Dict, Any, List
import pandas as pd
from src.config import CORRIDOR_DISTANCES_KM


class DecisionSimulator:
    """
    Computes hypothetical delivered costs, transit shrinkage, handling fees, and scenario margins.
    Clearly distinguishes observed market quotes from user-entered hypothetical logistics assumptions.
    """

    @staticmethod
    def simulate_procurement_and_transit(
        source_market_name: str,
        dest_market_name: str,
        commodity: str,
        purchase_price_quintal: float,       # ₹/Quintal
        dest_reference_price_quintal: float, # ₹/Quintal
        quantity_tonnes: float = 10.0,       # Default: 10 MT truckload (100 quintals)
        freight_cost_per_quintal: float = 120.0, # ₹/Quintal (~₹1,200/Tonne for ~200 km)
        handling_cost_per_quintal: float = 35.0, # Loading, unloading, gunny bags
        mandi_cess_pct: float = 1.05,        # Standard Maharashtra APMC cess (1.05%)
        transit_shrinkage_pct: float = 2.0,  # Moisture loss & damage during transit (2.0%)
    ) -> Dict[str, Any]:
        """
        Run deterministic scenario model.
        """
        quantity_quintals = quantity_tonnes * 10.0 # 1 Tonne = 10 Quintals

        # 1. Procurement Outlay
        gross_procurement_cost = purchase_price_quintal * quantity_quintals
        mandi_cess_cost = gross_procurement_cost * (mandi_cess_pct / 100.0)

        # 2. Logistics & Handling Outlay
        total_freight_cost = freight_cost_per_quintal * quantity_quintals
        total_handling_cost = handling_cost_per_quintal * quantity_quintals

        # 3. Total Capital Outlay
        total_landed_capital = (
            gross_procurement_cost + mandi_cess_cost + total_freight_cost + total_handling_cost
        )

        # 4. Physical Volume Dynamics (Transit Shrinkage)
        saleable_quantity_quintals = quantity_quintals * (1.0 - (transit_shrinkage_pct / 100.0))
        saleable_quantity_tonnes = saleable_quantity_quintals / 10.0

        # 5. Breakeven Landed Unit Cost
        breakeven_cost_per_quintal = total_landed_capital / max(0.01, saleable_quantity_quintals)
        breakeven_cost_per_kg = breakeven_cost_per_quintal / 100.0

        # 6. Destination Market Comparison
        destination_gross_revenue = dest_reference_price_quintal * saleable_quantity_quintals
        hypothetical_net_differential = destination_gross_revenue - total_landed_capital
        scenario_margin_per_quintal = dest_reference_price_quintal - breakeven_cost_per_quintal
        scenario_margin_pct = (hypothetical_net_differential / total_landed_capital) * 100.0

        # 7. Sensitivity Matrix (Freight Cost vs Transit Shrinkage)
        sensitivity_rows = []
        freight_variations = [
            round(freight_cost_per_quintal * 0.75, 1),
            round(freight_cost_per_quintal * 1.00, 1),
            round(freight_cost_per_quintal * 1.25, 1),
            round(freight_cost_per_quintal * 1.50, 1),
        ]
        shrinkage_variations = [0.0, 1.5, 3.0, 5.0]

        for fc in freight_variations:
            for sh in shrinkage_variations:
                t_capital = (
                    gross_procurement_cost
                    + mandi_cess_cost
                    + (fc * quantity_quintals)
                    + total_handling_cost
                )
                saleable_q = quantity_quintals * (1.0 - (sh / 100.0))
                be_cost = t_capital / max(0.01, saleable_q)
                diff = (dest_reference_price_quintal - be_cost) * saleable_q
                sensitivity_rows.append({
                    "freight_per_quintal": fc,
                    "shrinkage_pct": sh,
                    "breakeven_cost_quintal": round(be_cost, 2),
                    "scenario_differential": round(diff, 2),
                    "is_viable": diff > 0,
                })

        return {
            "inputs": {
                "source_market": source_market_name,
                "dest_market": dest_market_name,
                "commodity": commodity,
                "purchase_price_quintal": purchase_price_quintal,
                "dest_reference_price_quintal": dest_reference_price_quintal,
                "quantity_tonnes": quantity_tonnes,
                "quantity_quintals": quantity_quintals,
                "freight_cost_per_quintal": freight_cost_per_quintal,
                "handling_cost_per_quintal": handling_cost_per_quintal,
                "mandi_cess_pct": mandi_cess_pct,
                "transit_shrinkage_pct": transit_shrinkage_pct,
            },
            "costs": {
                "gross_procurement_cost": round(gross_procurement_cost, 2),
                "mandi_cess_cost": round(mandi_cess_cost, 2),
                "total_freight_cost": round(total_freight_cost, 2),
                "total_handling_cost": round(total_handling_cost, 2),
                "total_landed_capital": round(total_landed_capital, 2),
            },
            "delivered": {
                "saleable_quantity_quintals": round(saleable_quantity_quintals, 2),
                "saleable_quantity_tonnes": round(saleable_quantity_tonnes, 2),
                "breakeven_cost_per_quintal": round(breakeven_cost_per_quintal, 2),
                "breakeven_cost_per_kg": round(breakeven_cost_per_kg, 2),
                "destination_gross_revenue": round(destination_gross_revenue, 2),
                "scenario_margin_per_quintal": round(scenario_margin_per_quintal, 2),
                "hypothetical_net_differential": round(hypothetical_net_differential, 2),
                "scenario_margin_pct": round(scenario_margin_pct, 2),
                "is_economically_viable": hypothetical_net_differential > 0,
            },
            "sensitivity_matrix": pd.DataFrame(sensitivity_rows),
            "disclaimer": (
                "HYPOTHETICAL SCENARIO COMPARISON ONLY. Does not represent guaranteed commercial profit or proven "
                "arbitrage. Freight rates, transit loss, handling charges, and destination clearance prices vary "
                "daily with vehicle availability, weather, and grade discounts."
            ),
        }
