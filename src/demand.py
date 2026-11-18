"""Demand side of the crude-oil market, and the balance that sets the price.

Why this module exists
----------------------
The original model set ``DEMAND_MMBD = 82.0`` against a modelled supply of 82.1 mmb/d,
described as "balances snapshot supply". That makes demand a function of supply, so the
marginal barrel is *by construction* the most expensive node on the curve: the last barrel
needed is always the last barrel available. A 0.01 mmb/d change in the assumption moved the
headline from $70 to $78, and the result carried no uncertainty.

Here demand is an independent, price-elastic curve anchored on published refinery runs
rather than on the supply build-up. Supply is the cost curve *plus* OPEC+ spare capacity,
and the clearing price is where the two meet:

* ``interior``       — demand is met inside the cost curve; price = cost of the marginal node.
* ``spare_marginal`` — the gap is closed by swing capacity; price = the spare curve's price
                       at that volume, just above the floor. This is the normal state of the
                       market and the one the old model could not express.
* ``supply_capped``  — demand exceeds cost-curve output *and* all spare. The price is then a
                       rationing price, not a cost of production, and the model says so.
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
from spare import (CAPACITY_RANGE_MMBD, CAPACITY_SD_MMBD, DEFAULT_SPARE,
                   FLOOR_SD_USD, SpareCapacity)


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


def _supply_at(steps: Sequence[tuple], price: float) -> float:
    """Cumulative cost-curve output (mmb/d) available at ``price``."""
    total = 0.0
    for cost, cum, _name in steps:
        if cost <= price + 1e-12:
            total = cum
    return total


def _steps(curve: Sequence[dict]) -> list[tuple]:
    return [(float(r["cost"]), float(r["cum_end"]), r["name"]) for r in curve]


def clearing(curve: Sequence[dict], demand: DemandCurve = DEFAULT_DEMAND,
             spare: SpareCapacity | None = None) -> dict:
    """Market-clearing price for a cost curve, a demand curve and swing capacity.

    ``curve`` must be sorted cheapest-first and carry ``cost``, ``cum_end`` and ``name``
    (the output of :func:`costcurve.build_curve`). ``spare=None`` reproduces the
    cost-curve-only result, which is kept for comparison and for the tests that pin the
    step behaviour.
    """
    if not curve:
        raise ValueError("empty cost curve")

    steps = _steps(curve)
    capacity = steps[-1][1]
    top_cost = steps[-1][0]

    if spare is None or spare.is_empty:
        return _clearing_cost_only(steps, demand, capacity, top_cost)

    total_capacity = capacity + spare.capacity_mmbd

    # Demand at the top of the spare curve still exceeds everything deliverable.
    q_ceiling = demand.quantity(spare.ceiling_price)
    if q_ceiling > total_capacity + 1e-12:
        price = demand.price_for(total_capacity)
        return {
            "state": "supply_capped",
            "price": round(price, 2),
            "quantity_mmbd": round(total_capacity, 3),
            "marginal_segment": f"{spare.label} (exhausted)",
            "marginal_cost": round(spare.ceiling_price, 2),
            "scarcity_rent": round(price - spare.ceiling_price, 2),
            "shortfall_at_marginal_cost_mmbd": round(q_ceiling - total_capacity, 3),
            "cost_bracket": [round(steps[-1][0], 2), round(spare.ceiling_price, 2)],
            "demand_at_marginal_cost_mmbd": round(q_ceiling, 3),
            "spare_mmbd": round(spare.capacity_mmbd, 3),
            "spare_share_of_gap": 1.0,
            "extrapolated": bool(price > 1.5 * max(top_cost, spare.ceiling_price)),
        }

    def excess(p: float) -> float:
        return (demand.quantity(p)
                - _supply_at(steps, p)
                - spare.quantity(p))

    lo = steps[0][0]
    hi = max(top_cost, spare.ceiling_price) * 1.5
    # excess is non-increasing in price; bisection is safe and gives a continuous price
    # instead of snapping to the next node on the curve.
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if excess(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    price = 0.5 * (lo + hi)
    spare_q = spare.quantity(price)
    q = demand.quantity(price)

    if spare_q > 1e-6:
        state = "spare_marginal"
        marginal_segment = spare.label
        marginal_cost = round(spare.price_for(spare_q), 2)
        bracket = [round(spare.floor_price, 2), round(spare.ceiling_price, 2)]
    else:
        node = None
        for cost, cum, name in steps:
            if cost <= price + 1e-9:
                node = (cost, cum, name)
        if node is None:
            node = steps[0]
        state = "demand_capped" if node[0] == steps[0][0] and price <= node[0] + 1e-9 else "interior"
        marginal_segment = node[2]
        marginal_cost = round(node[0], 2)
        idx = steps.index(node)
        bracket = [round(steps[max(0, idx - 1)][0], 2), round(node[0], 2)]

    gap_closed = max(0.0, demand.quantity(top_cost) - capacity)
    return {
        "state": state,
        "price": round(price, 2),
        "quantity_mmbd": round(q, 3),
        "marginal_segment": marginal_segment,
        "marginal_cost": marginal_cost,
        "scarcity_rent": 0.0,
        "shortfall_at_marginal_cost_mmbd": 0.0,
        "cost_bracket": bracket,
        "demand_at_marginal_cost_mmbd": round(demand.quantity(marginal_cost), 3),
        "spare_mmbd": round(spare_q, 3),
        "spare_share_of_gap": round(spare_q / gap_closed, 3) if gap_closed > 1e-9 else 0.0,
        "spare_capacity_mmbd": round(spare.capacity_mmbd, 3),
        "spare_utilisation": round(spare_q / spare.capacity_mmbd, 3) if spare.capacity_mmbd else 0.0,
        "extrapolated": False,
    }


def _clearing_cost_only(steps: Sequence[tuple], demand: DemandCurve,
                        capacity: float, top_cost: float) -> dict:
    """Original behaviour: the cost curve is the whole world."""
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
            "spare_mmbd": 0.0,
            "extrapolated": bool(price > 1.5 * top_cost),
        }

    prev_cost, prev_cum = steps[0][0], 0.0
    for cost, cum, name in steps:
        q = demand.quantity(cost)
        if cum >= q - 1e-12:
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
                "spare_mmbd": 0.0,
                "extrapolated": False,
            }
        prev_cost, prev_cum = cost, cum

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
                          spare: SpareCapacity | None = DEFAULT_SPARE,
                          n: int = 10000, seed: int = 42,
                          anchor_sd: float = ANCHOR_SD_MMBD,
                          elasticity_range: tuple[float, float] = ELASTICITY_RANGE,
                          capacity_sd: float = CAPACITY_SD_MMBD) -> dict:
    """Monte Carlo over demand level, elasticity, every breakeven band and spare capacity.

    Returns the price distribution and the probability that each source is the one that
    sets the price — including the probability that spare, not a production node, is
    marginal.
    """
    rng = __import__("random").Random(seed)
    prices: list[float] = []
    nodes: Counter = Counter()
    states: Counter = Counter()
    spare_used: list[float] = []

    for _ in range(n):
        segs = _perturb(segments, rng)
        anchor = max(1.0, rng.gauss(demand.anchor_mmbd, anchor_sd))
        elast = rng.uniform(*elasticity_range)
        d = DemandCurve(anchor, demand.anchor_price, elast)
        sp = spare
        if spare is not None:
            cap = min(max(rng.gauss(spare.capacity_mmbd, capacity_sd), CAPACITY_RANGE_MMBD[0]),
                      CAPACITY_RANGE_MMBD[1])
            floor = max(40.0, rng.gauss(spare.floor_price, FLOOR_SD_USD))
            sp = SpareCapacity(cap, floor, max(floor + 10.0, spare.ceiling_price), spare.label)
        r = clearing(build_curve(segs, "full"), d, sp)
        prices.append(r["price"])
        nodes[r["marginal_segment"]] += 1
        states[r["state"]] += 1
        spare_used.append(r.get("spare_mmbd", 0.0))

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
        "spare_capacity_mmbd": round(spare.capacity_mmbd, 2) if spare else 0.0,
        "spare_capacity_sd_mmbd": capacity_sd if spare else 0.0,
        "price_p10": round(pct(10), 2),
        "price_p50": round(pct(50), 2),
        "price_p90": round(pct(90), 2),
        "price_mean": round(sum(prices) / n, 2),
        "spare_used_mean_mmbd": round(sum(spare_used) / n, 3),
        "spare_used_p90_mmbd": round(sorted(spare_used)[int(0.9 * (n - 1))], 3),
        "state_share": {k: round(v / n, 3) for k, v in states.most_common()},
        "marginal_node_probability": {k: round(v / n, 3) for k, v in nodes.most_common(8)},
    }


def summary(segments: Sequence[Segment], demand: DemandCurve = DEFAULT_DEMAND,
            spare: SpareCapacity | None = DEFAULT_SPARE,
            n: int = 10000, seed: int = 42) -> dict:
    """Convenience wrapper: point clearing plus its distribution."""
    curve = build_curve(segments, "full")
    point = clearing(curve, demand, spare)
    point["demand_curve"] = {
        "anchor_mmbd": demand.anchor_mmbd,
        "anchor_price": demand.anchor_price,
        "elasticity": demand.elasticity,
        "source": "EIA STEO crude+condensate demand 2024; IEA OMR refinery runs 2025 as the upper bound",
    }
    if spare is not None:
        point["spare_curve"] = {
            "capacity_mmbd": spare.capacity_mmbd,
            "floor_price": spare.floor_price,
            "ceiling_price": spare.ceiling_price,
            "source": "EIA STEO / IEA OMR effective OPEC+ spare 2024-25; IMF fiscal breakevens",
        }
    point["capacity_mmbd"] = round(total_supply(segments), 3)
    point["distribution"] = clearing_distribution(segments, demand, spare, n=n, seed=seed)
    return point
