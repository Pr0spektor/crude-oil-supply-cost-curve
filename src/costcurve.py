"""Global crude-oil supply cost curve — breakeven benchmarking engine.

An Energy-Solutions-style analytical tool: rank supply nodes by *economic*
breakeven ($/bbl), build the cumulative supply cost curve, find the marginal
barrel that clears a demand scenario, and quantify how much production is
uneconomic at a given oil price — with an explicit treatment of uncertainty.

Breakeven conventions (see docs/METHODS.md):
* breakeven_full  -> full-cycle economic breakeven: price to sanction NEW supply.
* cash_cost       -> half-cycle operating cost: price below which EXISTING output
                     is shut in.
* (breakeven_low, breakeven_high) -> the plausible range around the full-cycle
  point estimate, used for Monte-Carlo uncertainty. NOT to be confused with a
  government *fiscal* breakeven, which is a different concept.

Pure-Python / stdlib only, so every figure is auditable and unit-tested.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence
import random


@dataclass
class Segment:
    name: str
    region: str
    production_mmbd: float          # crude + condensate, million barrels/day
    breakeven_full: float           # full-cycle economic breakeven, $/bbl
    cash_cost: float                # half-cycle / operating cash cost, $/bbl
    note: str = ""
    breakeven_low: Optional[float] = None    # low end of plausible range
    breakeven_high: Optional[float] = None   # high end of plausible range
    source: str = ""

    def band(self):
        """(low, high) range for the full-cycle breakeven; default +/-20%."""
        lo = self.breakeven_low if self.breakeven_low is not None else self.breakeven_full * 0.8
        hi = self.breakeven_high if self.breakeven_high is not None else self.breakeven_full * 1.2
        return lo, hi


# ---------------------------------------------------------------- core curve ---
def build_curve(segments: Sequence[Segment], cost: str = "full") -> List[dict]:
    """Sort segments cheapest-first with cumulative production (mmb/d)."""
    key = "breakeven_full" if cost == "full" else "cash_cost"
    rows = []
    for s in segments:
        lo, hi = s.band()
        rows.append({"name": s.name, "region": s.region,
                     "production_mmbd": s.production_mmbd,
                     "cost": getattr(s, key), "cost_view": cost,
                     "low": lo, "high": hi})
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
    """Cost of the last barrel needed to meet ``demand_mmbd`` (the clearing cost)."""
    for r in curve:
        if demand_mmbd <= r["cum_end"] + 1e-12:
            return {"demand_mmbd": demand_mmbd, "marginal_cost": r["cost"],
                    "marginal_segment": r["name"], "supplied": True}
    last = curve[-1]
    return {"demand_mmbd": demand_mmbd, "marginal_cost": last["cost"],
            "marginal_segment": last["name"], "supplied": False}


def uneconomic_volume(segments: Sequence[Segment], price: float, cost: str = "full") -> dict:
    """Production whose (chosen) cost exceeds the oil price."""
    key = "breakeven_full" if cost == "full" else "cash_cost"
    at_risk = sum(s.production_mmbd for s in segments if getattr(s, key) > price)
    economic = sum(s.production_mmbd for s in segments if getattr(s, key) <= price)
    tot = at_risk + economic
    return {"price": price, "cost_view": cost,
            "at_risk_mmbd": at_risk, "economic_mmbd": economic,
            "at_risk_share": at_risk / tot if tot else 0.0}


def price_sensitivity(segments: Sequence[Segment], prices: Sequence[float],
                      cost: str = "cash") -> List[dict]:
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


# ----------------------------------------------------------------- scenarios ---
def apply_cost_inflation(segments: Sequence[Segment], inflation: float) -> List[Segment]:
    """Return a new segment list with all breakevens/cash costs scaled by (1+inflation)."""
    f = 1.0 + inflation
    out = []
    for s in segments:
        lo, hi = s.band()
        out.append(Segment(s.name, s.region, s.production_mmbd,
                           s.breakeven_full * f, s.cash_cost * f, s.note,
                           lo * f, hi * f, s.source))
    return out


# ------------------------------------------------------------- uncertainty  ---
def _triangular(lo, mode, hi, rng):
    if hi <= lo:
        return mode
    mode = min(max(mode, lo), hi)
    return rng.triangular(lo, hi, mode)


def monte_carlo_at_risk(segments: Sequence[Segment], price: float,
                        n: int = 10000, seed: int = 42, cost: str = "full") -> dict:
    """Distribution of at-risk volume (mmb/d) at ``price``, sampling each segment's
    full-cycle breakeven from a triangular(low, point, high). Deterministic via seed.

    Returns mean and P10/P50/P90 of the at-risk volume.
    """
    rng = random.Random(seed)
    draws = []
    bands = [(s.production_mmbd, *s.band(), getattr(s, "breakeven_full" if cost == "full" else "cash_cost"))
             for s in segments]
    for _ in range(n):
        at_risk = 0.0
        for prod, lo, hi, mode in bands:
            be = _triangular(lo, mode, hi, rng)
            if be > price:
                at_risk += prod
        draws.append(at_risk)
    draws.sort()

    def pct(p):
        idx = min(int(p / 100.0 * n), n - 1)
        return draws[idx]

    return {"price": price, "n": n, "mean_at_risk_mmbd": sum(draws) / n,
            "p10": pct(10), "p50": pct(50), "p90": pct(90),
            "min": draws[0], "max": draws[-1]}


def breakeven_percentile(segments: Sequence[Segment], demand_mmbd: float) -> float:
    """The clearing/marginal breakeven to meet demand (point estimate)."""
    return marginal_barrel(build_curve(segments, "full"), demand_mmbd)["marginal_cost"]
