"""Self-check / data-validation harness. Run in CI to catch bad inputs early.

Verifies curve invariants and reconciliation against the published supply total,
so a data edit that breaks the model fails loudly instead of silently.

Run:  python src/validate.py   (exit 1 on any failure)
"""
from __future__ import annotations
import sys
from data import SEGMENTS, TOTAL_LIQUIDS_2024
from costcurve import build_curve, total_supply, uneconomic_volume
from carbon import intensity, INTENSITY


def checks():
    errs = []
    # 1) production positive; cash cost <= full-cycle for every node
    for s in SEGMENTS:
        if s.production_mmbd <= 0:
            errs.append(f"{s.name}: non-positive production")
        if s.cash_cost > s.breakeven_full:
            errs.append(f"{s.name}: cash cost > full-cycle breakeven")
        lo, hi = s.band()
        if not (lo <= s.breakeven_full <= hi):
            errs.append(f"{s.name}: point estimate outside (low, high) band")
    # 2) curve cumulative continuity + final == total
    curve = build_curve(SEGMENTS, "full")
    for a, b in zip(curve, curve[1:]):
        if abs(a["cum_end"] - b["cum_start"]) > 1e-9:
            errs.append("cumulative discontinuity in curve")
            break
    if abs(curve[-1]["cum_end"] - total_supply(SEGMENTS)) > 1e-9:
        errs.append("final cumulative != total supply")
    # 3) curve is sorted cheapest-first
    if any(a["cost"] > b["cost"] + 1e-9 for a, b in zip(curve, curve[1:])):
        errs.append("curve not sorted ascending by cost")
    # 4) at-risk + economic == total at several prices
    for p in (30, 50, 70, 90):
        u = uneconomic_volume(SEGMENTS, p, "full")
        if abs(u["at_risk_mmbd"] + u["economic_mmbd"] - total_supply(SEGMENTS)) > 1e-9:
            errs.append(f"at-risk+economic != total at ${p}")
    # 5) crude+condensate reconciles below total liquids
    if not (0.70 * TOTAL_LIQUIDS_2024 <= total_supply(SEGMENTS) <= TOTAL_LIQUIDS_2024):
        errs.append("modelled supply does not reconcile with total liquids")
    # 6) every node has a carbon intensity
    for s in SEGMENTS:
        if s.name not in INTENSITY:
            errs.append(f"{s.name}: missing carbon intensity")
        if not (0.0 < intensity(s.name) < 0.3):
            errs.append(f"{s.name}: implausible carbon intensity")
    return errs


def main():
    errs = checks()
    if errs:
        print("VALIDATION FAILED:")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print("Validation passed: %d nodes, %.1f mmb/d, all invariants hold."
          % (len(SEGMENTS), total_supply(SEGMENTS)))


if __name__ == "__main__":
    main()
