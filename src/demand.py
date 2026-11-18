"""Demand side of the crude-oil market.

Why this module exists
----------------------
The original model set ``DEMAND_MMBD = 82.0`` against a modelled supply of 82.1 mmb/d,
described as "balances snapshot supply". That makes demand a function of supply, so the
marginal barrel is *by construction* the most expensive node on the curve: the last barrel
needed is always the last barrel available. A 0.01 mmb/d change in the assumption moved the
headline from $70 to $78, and the result carried no uncertainty.

Here demand is an independent, price-elastic curve, anchored on published refinery runs
rather than on the supply build-up. The clearing price is where that curve meets the cost
curve, and three outcomes are distinguished:

* ``interior``       — demand is met inside the curve; price = cost of the marginal node.
* ``supply_capped``  — demand exceeds everything the curve can deliver at any price. The
                       price is then a scarcity price above the top of the curve, not a cost
                       of production, and the model says so instead of pretending otherwise.
* ``demand_capped``  — even the cheapest node covers demand; price = cheapest cost.

Anchor
------
``ANCHOR_MMBD = 82.3`` is world crude + condensate demand in 2024 (EIA STEO), with the
2025 IEA refinery-throughput figure of 83.2 mb/d as the top of the plausible range. It is
deliberately *not* derived from the 23 supply segments.

Elasticity
----------
Short-run price elasticity of oil demand is small; the literature clusters around 0.03-0.10
in the first year. ``ELASTICITY = 0.06`` is the central value, and the range is carried
through the Monte Carlo rather than hidden in a point estimate.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Sequence

from costcurve import Segment, build_curve, total_supply


@dataclass(frozen=True)
class DemandCurve:
    """Constant-elasticity demand: Q(p) = anchor * (p / anchor_price) ** -elasticity."""

    anchor_mmbd: float
    anchor_price: float
    elasticity: float

    def __post_init__(self) -> None:
        if self.anchor_mmbd <= 0:
            raise ValueError("anchor demand must be positive")
        if self.anchor_price <= 0:
            raise ValueError("anchor price must be positive")
        if self.elasticity < 0:
            raise ValueError("elasticity must be non-negative")

    def quantity(self, price: float) -> float:
        """Demand (mmb/d) at a given price ($/bbl)."""
        if price <= 0:
            raise ValueError("price must be positive")
        return self.anchor_mmbd * (price / self.anchor_price) ** (-self.elasticity)

    def price_for(self, quantity: float) -> float:
        """Inverse demand: the price at which ``quantity`` is demanded."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.elasticity == 0:
            raise ValueError("a perfectly inelastic curve has no inverse")
        return self.anchor_price * (quantity / self.anchor_mmbd) ** (-1.0 / self.elasticity)


# Central case and the ranges carried into the Monte Carlo.
ANCHOR_MMBD = 82.3
ANCHOR_PRICE = 80.0
ELASTICITY = 0.06
ANCHOR_SD_MMBD = 0.45
ELASTICITY_RANGE = (0.03, 0.10)

DEFAULT_DEMAND = DemandCurve(ANCHOR_MMBD, ANCHOR_PRICE, ELASTICITY)


def clearing(curve: Sequence[dict], demand: DemandCurve = DEFAULT_DEMAND) -> dict:
    """Market-clearing price for a cost curve and a demand curve.

    ``curve`` must be sorted cheapest-first and carry ``cost``, ``cum_end`` and ``name``
    (the output of :func:`costcurve.build_curve`).
    """
    if not curve:
        raise ValueError("empty cost curve")

    steps = [(float(r["cost"]), float(r["cum_end"]), r["name"]) for r in curve]
    capacity = steps[-1][1]
    top_cost = steps[-1][0]

    # Demand at the top of the curve still exceeds what the curve can deliver: the price is
    # set by rationing, not by production cost.
    q_top = demand.quantity(top_cost)
    if q_top > capacity + 1e-12:
        price = demand.price_for(capacity)
        return {
            "state": "supply_capped",
            "price": round(price, 2),
            "quantity_mmbd": round(capacity, 3),
            "marginal_segment": steps[-1][2],
            "marginal_cost": round(top_cost, 2),
            "scarcity_rent": round(price - top_cost, 2),
            "shortfall_at_marginal_cost_mmbd": round(q_top - capacity, 3),
            "cost_bracket": [round(steps[-2][0], 2) if len(steps) > 1 else round(top_cost, 2),
                             round(top_cost, 2)],
            "demand_at_marginal_cost_mmbd": round(q_top, 3),
            # A constant-elasticity curve is a local approximation: when the shortfall is
            # large the implied price runs away, so flag anything beyond a 50% rent rather
            # than presenting it as a cost-curve result.
            "extrapolated": bool(price > 1.5 * top_cost),
        }

    prev_cost, prev_cum = steps[0][0], 0.0
    for cost, cum, name in steps:
        q = demand.quantity(cost)
        if cum >= q - 1e-12:
            # First node whose cumulative volume covers demand at its own cost.
            state = "demand_capped" if prev_cum <= 0.0 and cost == steps[0][0] else "interior"
            return {
                "state": state,
                "price": round(cost, 2),
                "quantity_mmbd": round(q, 3),
                "marginal_segment": name,
                "marginal_cost": round(cost, 2),
                "scarcity_rent": 0.0,
                "shortfall_at_marginal_cost_mmbd": 0.0,
                "cost_bracket": [round(prev_cost, 2), round(cost, 2)],
                "demand_at_marginal_cost_mmbd": round(q, 3),
                "extrapolated": False,
            }
        prev_cost, prev_cum = cost, cum

    # Unreachable for a sorted curve, but keep the contract explicit.
    raise RuntimeError("clearing failed: curve not sorted or empty")


def _perturb(segments: Sequence[Segment], rng) -> list[Segment]:
    out = []
    for s in segments:
        lo, hi = s.band()
        mode = min(max(s.breakeven_full, lo), hi)
        be = rng.triangular(lo, hi, mode)
        out.append(replace(s, breakeven_full=be))
    return out


def clearing_distribution(segments: Sequence[Segment],
                          demand: DemandCurve = DEFAULT_DEMAND,
                          n: int = 10000, seed: int = 42,
                          anchor_sd: float = ANCHOR_SD_MMBD,
                          elasticity_range: tuple[float, float] = ELASTICITY_RANGE) -> dict:
    """Monte Carlo over demand level, elasticity and every breakeven band.

    Returns the price distribution and, more usefully, the probability that each node is the
    one that sets the price — the question the old single-number answer could not express.
    """
    rng = __import__("random").Random(seed)
    prices: list[float] = []
    nodes: Counter = Counter()
    states: Counter = Counter()

    for _ in range(n):
        segs = _perturb(segments, rng)
        anchor = max(1.0, rng.gauss(demand.anchor_mmbd, anchor_sd))
        elast = rng.uniform(*elasticity_range)
        d = DemandCurve(anchor, demand.anchor_price, elast)
        r = clearing(build_curve(segs, "full"), d)
        prices.append(r["price"])
        nodes[r["marginal_segment"]] += 1
        states[r["state"]] += 1

    prices.sort()

    def pct(p: float) -> float:
        idx = min(int(round(p / 100.0 * (n - 1))), n - 1)
        return prices[idx]

    return {
        "n": n,
        "seed": seed,
        "anchor_mmbd": demand.anchor_mmbd,
        "anchor_sd_mmbd": anchor_sd,
        "elasticity_range": list(elasticity_range),
        "price_p10": round(pct(10), 2),
        "price_p50": round(pct(50), 2),
        "price_p90": round(pct(90), 2),
        "price_mean": round(sum(prices) / n, 2),
        "state_share": {k: round(v / n, 3) for k, v in states.most_common()},
        "marginal_node_probability": {k: round(v / n, 3) for k, v in nodes.most_common(8)},
    }


def summary(segments: Sequence[Segment], demand: DemandCurve = DEFAULT_DEMAND,
            n: int = 10000, seed: int = 42) -> dict:
    """Convenience wrapper: point clearing plus its distribution."""
    curve = build_curve(segments, "full")
    point = clearing(curve, demand)
    point["demand_curve"] = {
        "anchor_mmbd": demand.anchor_mmbd,
        "anchor_price": demand.anchor_price,
        "elasticity": demand.elasticity,
        "source": "EIA STEO crude+condensate demand 2024; IEA OMR refinery runs 2025 as the upper bound",
    }
    point["capacity_mmbd"] = round(total_supply(segments), 3)
    point["distribution"] = clearing_distribution(segments, demand, n=n, seed=seed)
    return point
