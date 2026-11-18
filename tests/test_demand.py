"""Tests for the demand curve and the market-clearing price.

The point of this module is that demand is independent of the supply build-up and that the
clearing price comes from the balance. These tests pin both properties.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from costcurve import Segment, build_curve
from demand import DemandCurve, clearing, clearing_distribution, summary
from data import SEGMENTS


def seg(name: str, production: float, breakeven: float) -> Segment:
    return Segment(name=name, region="test", production_mmbd=production,
                   breakeven_full=breakeven, cash_cost=breakeven * 0.6)


TWO_NODES = [seg("cheap", 10.0, 40.0), seg("dear", 10.0, 60.0)]


def test_quantity_falls_as_price_rises():
    d = DemandCurve(82.3, 80.0, 0.06)
    assert d.quantity(60) > d.quantity(80) > d.quantity(120)


def test_inverse_demand_round_trips():
    d = DemandCurve(82.3, 80.0, 0.06)
    for price in (40.0, 80.0, 130.0):
        assert d.price_for(d.quantity(price)) == pytest.approx(price, rel=1e-9)


def test_interior_clearing_uses_the_node_that_covers_demand():
    # At $40 demand (15) exceeds the cheap node (10); at $60 demand (14.75) fits in 20.
    d = DemandCurve(15.0, 40.0, 0.06)
    r = clearing(build_curve(TWO_NODES, "full"), d)
    assert r["state"] == "interior"
    assert r["price"] == 60.0
    assert r["marginal_segment"] == "dear"
    assert r["quantity_mmbd"] == pytest.approx(d.quantity(60.0), abs=1e-3)


def test_demand_capped_when_the_cheapest_node_is_enough():
    d = DemandCurve(5.0, 40.0, 0.06)
    r = clearing(build_curve(TWO_NODES, "full"), d)
    assert r["state"] == "demand_capped"
    assert r["price"] == 40.0
    assert r["scarcity_rent"] == 0.0


def test_supply_capped_prices_the_shortfall_above_marginal_cost():
    d = DemandCurve(22.0, 80.0, 0.06)
    r = clearing(build_curve(TWO_NODES, "full"), d)
    assert r["state"] == "supply_capped"
    assert r["price"] > r["marginal_cost"]
    assert r["scarcity_rent"] == pytest.approx(r["price"] - r["marginal_cost"], abs=0.01)
    assert r["shortfall_at_marginal_cost_mmbd"] > 0


def test_clearing_price_rises_with_demand():
    curve = build_curve(TWO_NODES, "full")
    low = clearing(curve, DemandCurve(15.0, 80.0, 0.06))["price"]
    high = clearing(curve, DemandCurve(22.0, 80.0, 0.06))["price"]
    assert high > low


def test_more_elastic_demand_clears_lower_when_short():
    curve = build_curve(TWO_NODES, "full")
    inelastic = clearing(curve, DemandCurve(22.0, 80.0, 0.03))["price"]
    elastic = clearing(curve, DemandCurve(22.0, 80.0, 0.10))["price"]
    assert elastic < inelastic


def test_distribution_probabilities_sum_to_one():
    dist = clearing_distribution(TWO_NODES, DemandCurve(15.0, 80.0, 0.06), n=400, seed=7)
    assert sum(dist["marginal_node_probability"].values()) == pytest.approx(1.0, abs=0.02)
    assert sum(dist["state_share"].values()) == pytest.approx(1.0, abs=0.02)
    assert dist["price_p10"] <= dist["price_p50"] <= dist["price_p90"]


def test_distribution_is_seeded_and_reproducible():
    a = clearing_distribution(TWO_NODES, n=300, seed=3)
    b = clearing_distribution(TWO_NODES, n=300, seed=3)
    assert a == b


def test_summary_on_the_real_curve_is_consistent():
    s = summary(SEGMENTS, n=500, seed=42)
    assert s["capacity_mmbd"] == pytest.approx(82.1, abs=0.05)
    assert s["price"] > 0
    assert s["distribution"]["price_p10"] <= s["price"] <= s["distribution"]["price_p90"]
    assert s["demand_curve"]["anchor_mmbd"] == pytest.approx(82.3)


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        DemandCurve(0.0, 80.0, 0.06)
    with pytest.raises(ValueError):
        DemandCurve(82.3, 0.0, 0.06)
    with pytest.raises(ValueError):
        DemandCurve(82.3, 80.0, -0.1)
    with pytest.raises(ValueError):
        DemandCurve(82.3, 80.0, 0.06).quantity(0)


if __name__ == "__main__":
    import inspect

    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                if inspect.signature(fn).parameters:
                    continue
                fn()
                print("ok  ", name)
            except Exception as exc:  # pragma: no cover - standalone runner
                failed += 1
                print("FAIL", name, exc)
    sys.exit(1 if failed else 0)


# ---------------------------------------------------------------- spare capacity ---

def test_spare_curve_is_monotone_and_bounded():
    from spare import SpareCapacity
    s = SpareCapacity(capacity_mmbd=4.0, floor_price=80.0, ceiling_price=120.0)
    assert s.quantity(79.0) == 0.0
    assert s.quantity(80.0) == 0.0
    assert s.quantity(100.0) == pytest.approx(2.0)
    assert s.quantity(130.0) == 4.0
    assert s.quantity(90.0) < s.quantity(110.0)
    assert s.price_for(2.0) == pytest.approx(100.0)


def test_spare_closes_a_small_gap_without_repricing_the_whole_curve():
    from spare import SpareCapacity
    # Demand 21.0 against 20.0 of cost-curve capacity: the 1.0 mmb/d gap is swing supply.
    d = DemandCurve(21.0, 60.0, 0.06)
    sp = SpareCapacity(4.0, 60.0, 120.0)
    r = clearing(build_curve(TWO_NODES, "full"), d, sp)
    assert r["state"] == "spare_marginal"
    assert 60.0 < r["price"] < 120.0
    assert 0.0 < r["spare_mmbd"] < 4.0
    assert r["scarcity_rent"] == 0.0


def test_without_spare_the_same_gap_becomes_a_scarcity_price():
    d = DemandCurve(21.0, 60.0, 0.06)
    no_spare = clearing(build_curve(TWO_NODES, "full"), d)
    with_spare = clearing(build_curve(TWO_NODES, "full"), d, __import__("spare").DEFAULT_SPARE)
    assert no_spare["state"] == "supply_capped"
    assert with_spare["price"] < no_spare["price"]


def test_spare_exhaustion_returns_a_rationing_price():
    from spare import SpareCapacity
    d = DemandCurve(40.0, 60.0, 0.06)
    r = clearing(build_curve(TWO_NODES, "full"), d, SpareCapacity(2.0, 60.0, 120.0))
    assert r["state"] == "supply_capped"
    assert r["price"] > 120.0
    assert r["spare_mmbd"] == pytest.approx(2.0)


def test_real_curve_clears_on_spare_not_on_the_top_node():
    from spare import DEFAULT_SPARE
    s = summary(SEGMENTS, spare=DEFAULT_SPARE, n=600, seed=42)
    assert s["state"] in {"spare_marginal", "interior"}
    assert s["price"] < 100
    assert s["distribution"]["spare_capacity_mmbd"] == pytest.approx(4.0)
    assert "OPEC+ spare" in s["distribution"]["marginal_node_probability"]
