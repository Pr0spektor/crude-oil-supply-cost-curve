"""Global crude-oil supply cost curve — breakeven benchmarking engine.

An Energy-Solutions-style analytical tool: rank supply segments by breakeven
($/bbl), build the cumulative supply cost curve, find the marginal barrel needed
to meet demand, and quantify how much production is uneconomic at a given oil
price. Two cost views are supported:

* full-cycle breakeven  -> the price needed to sanction NEW investment
* cash cost (half-cycle) -> the price below which EXISTING output is shut in

Pure-Python / stdlib only, so every figure is auditable and unit-tested.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class Segment:
    name: str
    region: str
    production_mmbd: float      # million barrels/day
    breakeven_full: float       # full-cycle breakeven, $/bbl
    cash_cost: float            # half-cycle / operating cash cost, $/bbl
    note: str = ""


def build_curve(segments: Sequence[Segment], cost: str = "full") -> List[dict]:
    """Sort segments cheapest-first and attach cumulative production (mmb/d).

    ``cost`` = "full" (breakeven_full) or "cash" (cash_cost).
    """
    key = "breakeven_full" if cost == "full" else "cash_cost"
    rows = [{"name": s.name, "region": s.region,
             "production_mmbd": s.production_mmbd,
             "cost": getattr(s, key), "cost_view": cost} for s in segments]
    rows.sort(key=lambda r: r["cost"])
    cum = 0.0
    for r in rows:
        r["cum_start"] = cum
        cum += r["production_mmbd"]
        r["cum_end"] = cum
    return rows


def total_supply(segments: Sequence[Segment]) -> float:
    return sum(s.production_mmbd for s in segments)


def marginal_barrel(curve: Sequence[dict], demand_mmbd: float) -> dict:
    """The cost of the last barrel needed to meet ``demand_mmbd`` (the clearing cost)."""
    for r in curve:
        if demand_mmbd <= r["cum_end"] + 1e-12:
            return {"demand_mmbd": demand_mmbd, "marginal_cost": r["cost"],
                    "marginal_segment": r["name"], "supplied": True}
    # demand exceeds total supply
    last = curve[-1]
    return {"demand_mmbd": demand_mmbd, "marginal_cost": last["cost"],
            "marginal_segment": last["name"], "supplied": False}


def uneconomic_volume(segments: Sequence[Segment], price: float, cost: str = "full") -> dict:
    """Production whose (chosen) cost exceeds the oil price.

    With ``cost="full"`` this is volume that cannot justify new investment; with
    ``cost="cash"`` it is volume at risk of being shut in (cash-negative).
    """
    key = "breakeven_full" if cost == "full" else "cash_cost"
    at_risk = sum(s.production_mmbd for s in segments if getattr(s, key) > price)
    economic = sum(s.production_mmbd for s in segments if getattr(s, key) <= price)
    tot = at_risk + economic
    return {"price": price, "cost_view": cost,
            "at_risk_mmbd": at_risk, "economic_mmbd": economic,
            "at_risk_share": at_risk / tot if tot else 0.0}


def price_sensitivity(segments: Sequence[Segment], prices: Sequence[float],
                      cost: str = "cash") -> List[dict]:
    """At-risk volume across a range of oil prices (default: cash-cost shut-in view)."""
    return [uneconomic_volume(segments, p, cost) for p in prices]


def average_cost_to_meet(curve: Sequence[dict], demand_mmbd: float) -> float:
    """Volume-weighted average cost of the cheapest barrels meeting demand ($/bbl)."""
    remaining, weighted = demand_mmbd, 0.0
    for r in curve:
        if remaining <= 0:
            break
        take = min(r["production_mmbd"], remaining)
        weighted += take * r["cost"]
        remaining -= take
    supplied = demand_mmbd - max(remaining, 0.0)
    return weighted / supplied if supplied > 0 else float("nan")
