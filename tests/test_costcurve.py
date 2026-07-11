import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from costcurve import (Segment, build_curve, total_supply, marginal_barrel,
                       uneconomic_volume, price_sensitivity, average_cost_to_meet,
                       apply_cost_inflation, monte_carlo_at_risk)

def approx(a, b, rel=1e-6, abs_=1e-9):
    """Returns True if a and b are approximately equal."""
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), abs_)

# Fixture: 3 segments with hand-checkable numbers
# Sorted by breakeven_full: A(20), C(35), B(50) => cumulative 0-10, 10-15, 15-20
# Sorted by cash_cost: A(10), C(25), B(30) => cumulative 0-10, 10-15, 15-20
fixture_segments = [
    Segment("A", "R", 10, 20, 10),
    Segment("B", "R", 5, 50, 30),
    Segment("C", "R", 5, 35, 25),
]

def test_total_supply():
    """Test that total_supply sums production_mmbd correctly."""
    result = total_supply(fixture_segments)
    assert result == 20, f"Expected total_supply=20, got {result}"

def test_sorting_by_full_cost():
    """Test that build_curve sorts by breakeven_full (cost='full')."""
    curve = build_curve(fixture_segments, cost="full")
    assert len(curve) == 3
    assert curve[0]["name"] == "A", f"First should be A (cost 20), got {curve[0]['name']}"
    assert curve[1]["name"] == "C", f"Second should be C (cost 35), got {curve[1]['name']}"
    assert curve[2]["name"] == "B", f"Third should be B (cost 50), got {curve[2]['name']}"

def test_sorting_by_cash_cost():
    """Test that build_curve sorts by cash_cost (cost='cash')."""
    curve = build_curve(fixture_segments, cost="cash")
    assert len(curve) == 3
    assert curve[0]["name"] == "A", f"First should be A (cost 10), got {curve[0]['name']}"
    assert curve[1]["name"] == "C", f"Second should be C (cost 25), got {curve[1]['name']}"
    assert curve[2]["name"] == "B", f"Third should be B (cost 30), got {curve[2]['name']}"

def test_cumulative_continuity():
    """Test that cum_start == previous cum_end for all segments."""
    curve = build_curve(fixture_segments, cost="full")
    for i in range(1, len(curve)):
        prev_cum_end = curve[i-1]["cum_end"]
        curr_cum_start = curve[i]["cum_start"]
        assert prev_cum_end == curr_cum_start, \
            f"Segment {i}: cum_start {curr_cum_start} != prev cum_end {prev_cum_end}"

def test_final_cumulative_equals_total_supply():
    """Test that final cum_end == total_supply()."""
    curve = build_curve(fixture_segments, cost="full")
    total = total_supply(fixture_segments)
    final_cum_end = curve[-1]["cum_end"]
    assert final_cum_end == total, \
        f"Final cum_end {final_cum_end} != total_supply {total}"

def test_cumulative_values():
    """Test exact cumulative values for 'full' cost sorting."""
    curve = build_curve(fixture_segments, cost="full")
    assert curve[0]["cum_start"] == 0 and curve[0]["cum_end"] == 10, \
        f"A: expected cum (0, 10), got ({curve[0]['cum_start']}, {curve[0]['cum_end']})"
    assert curve[1]["cum_start"] == 10 and curve[1]["cum_end"] == 15, \
        f"C: expected cum (10, 15), got ({curve[1]['cum_start']}, {curve[1]['cum_end']})"
    assert curve[2]["cum_start"] == 15 and curve[2]["cum_end"] == 20, \
        f"B: expected cum (15, 20), got ({curve[2]['cum_start']}, {curve[2]['cum_end']})"

def test_marginal_barrel_within_supply():
    """Test marginal_barrel at demand within total supply."""
    curve = build_curve(fixture_segments, cost="full")
    # sorted full-cycle curve: A(0-10), C(10-15), B(15-20); demand 12 clears in C
    result = marginal_barrel(curve, 12)
    assert result["supplied"] == True, "Should be able to supply 12 mmbd (total 20)"
    assert result["marginal_segment"] == "C", f"Marginal segment should be C, got {result['marginal_segment']}"
    assert result["marginal_cost"] == 35, f"Marginal cost should be 35, got {result['marginal_cost']}"

def test_marginal_barrel_exceeds_supply():
    """Test marginal_barrel at demand exceeding total supply."""
    curve = build_curve(fixture_segments, cost="full")
    result = marginal_barrel(curve, 25)
    assert result["supplied"] == False, "Should not be able to supply 25 mmbd (total 20)"

def test_uneconomic_volume_low_price():
    """Test uneconomic_volume at low price (high at-risk)."""
    result = uneconomic_volume(fixture_segments, price=15, cost="full")
    assert result["price"] == 15
    assert result["at_risk_mmbd"] == 20, f"At price 15, all 20 should be at risk, got {result['at_risk_mmbd']}"
    assert result["economic_mmbd"] == 0, f"At price 15, none should be economic, got {result['economic_mmbd']}"
    assert approx(result["at_risk_share"], 1.0), \
        f"At price 15, at_risk_share should be 1.0, got {result['at_risk_share']}"

def test_uneconomic_volume_high_price():
    """Test uneconomic_volume at high price (low/no at-risk)."""
    result = uneconomic_volume(fixture_segments, price=60, cost="full")
    assert result["price"] == 60
    assert result["at_risk_mmbd"] == 0, f"At price 60, none should be at risk, got {result['at_risk_mmbd']}"
    assert result["economic_mmbd"] == 20, f"At price 60, all 20 should be economic, got {result['economic_mmbd']}"
    assert approx(result["at_risk_share"], 0.0), \
        f"At price 60, at_risk_share should be 0.0, got {result['at_risk_share']}"

def test_uneconomic_volume_sum():
    """Test that at_risk + economic == total supply."""
    prices = [10, 25, 40, 60]
    for price in prices:
        result = uneconomic_volume(fixture_segments, price=price, cost="full")
        total = result["at_risk_mmbd"] + result["economic_mmbd"]
        assert total == 20, \
            f"At price {price}: at_risk ({result['at_risk_mmbd']}) + economic ({result['economic_mmbd']}) != 20"

def test_cost_cash_vs_full_different():
    """Test that cost='cash' vs cost='full' give different at_risk volumes."""
    price = 25
    result_full = uneconomic_volume(fixture_segments, price=price, cost="full")
    result_cash = uneconomic_volume(fixture_segments, price=price, cost="cash")
    # They should differ because the sorting order is different
    assert result_full["at_risk_mmbd"] != result_cash["at_risk_mmbd"], \
        f"cost='full' and cost='cash' should give different at_risk, both got {result_full['at_risk_mmbd']}"

def test_average_cost_to_meet_monotonic():
    """Test that average_cost increases monotonically with demand."""
    curve = build_curve(fixture_segments, cost="full")
    demands = [5, 10, 15, 20]
    prev_avg_cost = 0
    for demand in demands:
        avg_cost = average_cost_to_meet(curve, demand)
        assert avg_cost >= prev_avg_cost, \
            f"Average cost should increase: prev={prev_avg_cost}, demand={demand}, curr={avg_cost}"
        prev_avg_cost = avg_cost

def test_band_default_pm20():
    """A segment with no explicit low/high gets a +/-20% band."""
    s = Segment("A", "R", 10, 50, 30)
    lo, hi = s.band()
    assert approx(lo, 40.0) and approx(hi, 60.0)

def test_band_explicit():
    s = Segment("A", "R", 10, 50, 30, "", 45, 58)
    assert s.band() == (45, 58)

def test_apply_cost_inflation_scales():
    segs = [Segment("A", "R", 10, 50, 30), Segment("B", "R", 5, 20, 10)]
    up = apply_cost_inflation(segs, 0.10)
    assert approx(up[0].breakeven_full, 55.0) and approx(up[0].cash_cost, 33.0)
    assert approx(up[1].breakeven_full, 22.0)
    # original list is unchanged
    assert segs[0].breakeven_full == 50

def test_monte_carlo_deterministic_and_bounded():
    segs = [Segment("A", "R", 10, 20, 10, "", 15, 25),
            Segment("B", "R", 5, 50, 30, "", 40, 60),
            Segment("C", "R", 5, 35, 25, "", 30, 40)]
    a = monte_carlo_at_risk(segs, 45, n=2000, seed=7)
    b = monte_carlo_at_risk(segs, 45, n=2000, seed=7)
    assert a == b, "same seed must give identical result"
    # at-risk volume is between 0 and total supply, ordering p10<=p50<=p90
    assert 0.0 <= a["p10"] <= a["p50"] <= a["p90"] <= total_supply(segs) + 1e-9

def test_monte_carlo_price_monotone():
    """Higher price => less (or equal) expected at-risk volume."""
    segs = [Segment("A", "R", 10, 20, 10, "", 15, 25),
            Segment("B", "R", 5, 50, 30, "", 40, 60)]
    lo = monte_carlo_at_risk(segs, 30, n=2000, seed=3)["mean_at_risk_mmbd"]
    hi = monte_carlo_at_risk(segs, 70, n=2000, seed=3)["mean_at_risk_mmbd"]
    assert lo >= hi

def test_carbon_overlay_adds_intensity_cost():
    from carbon import carbon_adjusted_breakeven, intensity
    s = Segment("Canada oil sands", "NA", 3.3, 70, 45)
    # at $100/tCO2e a 0.11 tCO2/bbl barrel gains ~$11/bbl
    got = carbon_adjusted_breakeven(s, 100.0)
    assert approx(got, 70 + 100 * intensity("Canada oil sands"))
    assert carbon_adjusted_breakeven(s, 0.0) == 70

def test_carbon_curve_reranks_and_conserves_volume():
    from carbon import carbon_adjusted_curve
    from data import SEGMENTS
    c0 = carbon_adjusted_curve(SEGMENTS, 0.0)
    c1 = carbon_adjusted_curve(SEGMENTS, 150.0)
    tot0 = sum(r["production_mmbd"] for r in c0)
    tot1 = sum(r["production_mmbd"] for r in c1)
    assert approx(tot0, tot1)                      # volume conserved
    assert [r["name"] for r in c0] != [r["name"] for r in c1]  # order changes

def test_validation_passes_on_shipped_data():
    import validate
    assert validate.checks() == []

if __name__ == "__main__":
    # Collect all test functions
    test_functions = [
        (name, func) for name, func in sorted(globals().items())
        if name.startswith("test_") and callable(func)
    ]

    passed = 0
    failed = 0

    for name, func in test_functions:
        try:
            func()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    total = passed + failed
    print(f"{passed}/{total} tests passed.")
    sys.exit(1 if failed else 0)
