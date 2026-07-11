"""Carbon-cost overlay — the energy-transition lens on the supply cost curve.

Adds a carbon price ($/tCO2e) to each barrel in proportion to its *upstream*
(production) carbon intensity, then re-ranks the curve. A carbon price penalises
high-intensity supply (oil sands, extra-heavy, high-flaring) and improves the
relative position of low-intensity barrels (e.g. Brazil pre-salt, low-flare Gulf) —
i.e. it reshuffles the merit order, not just lifts it uniformly.

Intensities are upstream tCO2e/bbl, following the ranges in Masnadi et al. (2018),
"Global carbon intensity of crude oil production", *Science* 361:851 (volume-weighted
global average ~0.06 tCO2e/bbl upstream; oil sands / extra-heavy / heavy-flaring at
the high end). Illustrative point values — see SOURCES.md.
"""
from __future__ import annotations
from typing import List, Sequence
from costcurve import Segment

# Upstream carbon intensity, tCO2e/bbl (production only; excludes combustion Scope 3).
INTENSITY = {
    "Saudi Arabia (onshore)": 0.040, "Iraq": 0.065, "UAE": 0.035, "Kuwait": 0.050,
    "Iran": 0.075, "Other Middle East": 0.060,
    "Russia (conventional onshore)": 0.075, "Kazakhstan": 0.060, "Other CIS": 0.060,
    "US tight oil — Permian": 0.050, "US tight oil — other basins": 0.055,
    "US Gulf of Mexico + conventional": 0.040, "Canada oil sands": 0.110,
    "Canada conventional": 0.050, "Brazil pre-salt (deepwater)": 0.030,
    "Other Latin America": 0.060, "Venezuela extra-heavy": 0.120,
    "West Africa offshore": 0.050, "Other Africa onshore": 0.065,
    "North Sea (mature offshore)": 0.040, "Asia-Pacific": 0.055,
    "Arctic / frontier": 0.060, "Other conventional (RoW)": 0.050,
}
DEFAULT_INTENSITY = 0.06


def intensity(node_name: str) -> float:
    return INTENSITY.get(node_name, DEFAULT_INTENSITY)


def carbon_adjusted_breakeven(seg: Segment, carbon_price: float) -> float:
    """Full-cycle breakeven plus the carbon cost of the barrel ($/bbl)."""
    return seg.breakeven_full + carbon_price * intensity(seg.name)


def carbon_adjusted_curve(segments: Sequence[Segment], carbon_price: float) -> List[dict]:
    """Supply curve re-ranked on carbon-adjusted cost, with cumulative production."""
    rows = [{"name": s.name, "region": s.region, "production_mmbd": s.production_mmbd,
             "base": s.breakeven_full, "carbon_cost": carbon_price * intensity(s.name),
             "cost": carbon_adjusted_breakeven(s, carbon_price),
             "intensity": intensity(s.name)} for s in segments]
    rows.sort(key=lambda r: r["cost"])
    cum = 0.0
    for r in rows:
        r["cum_start"] = cum; cum += r["production_mmbd"]; r["cum_end"] = cum
    return rows


def merit_order_shift(segments: Sequence[Segment], carbon_price: float) -> List[dict]:
    """Rank change of each node when a carbon price is applied (positive = worse)."""
    base = {s.name: i for i, s in enumerate(
        sorted(segments, key=lambda s: s.breakeven_full))}
    adj = carbon_adjusted_curve(segments, carbon_price)
    out = []
    for i, r in enumerate(adj):
        out.append({"name": r["name"], "rank_change": i - base[r["name"]],
                    "carbon_cost": r["carbon_cost"], "intensity": r["intensity"]})
    out.sort(key=lambda x: -abs(x["rank_change"]))
    return out


if __name__ == "__main__":
    from data import SEGMENTS
    cp = 100.0
    print(f"Carbon-adjusted merit-order shift @ ${cp:.0f}/tCO2e (top movers):")
    for m in merit_order_shift(SEGMENTS, cp)[:6]:
        print("  %-30s rank %+d  (+$%.1f/bbl, %.3f tCO2/bbl)"
              % (m["name"], m["rank_change"], m["carbon_cost"], m["intensity"]))
