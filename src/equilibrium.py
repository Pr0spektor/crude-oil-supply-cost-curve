"""Partial-equilibrium market-clearing model on top of the supply cost curve.

The cost curve gives supply as a (step) function of price: everything with a
breakeven at or below the price is economic. Pairing it with a downward-sloping,
constant-elasticity demand curve lets us solve for the *market-clearing price* — the
price at which economic supply equals demand — rather than assuming a fixed demand.

This turns the curve from a static ranking into a small economic model: shift demand
or shock costs and read the new equilibrium price and volume. Stdlib only; unit-tested.
"""
from __future__ import annotations
from typing import Sequence
from costcurve import Segment


def economic_supply(segments: Sequence[Segment], price: float, cost: str = "full") -> float:
    """Volume (mmb/d) whose breakeven is at or below `price` (i.e. economic to produce)."""
    key = "breakeven_full" if cost == "full" else "cash_cost"
    return sum(s.production_mmbd for s in segments if getattr(s, key) <= price)


def demand(price: float, ref_quantity: float, ref_price: float, elasticity: float) -> float:
    """Constant-elasticity demand: Q = Qref * (P/Pref)^(-|elasticity|).

    Short-run oil demand is very inelastic (|elasticity| ≈ 0.05-0.10).
    """
    e = abs(elasticity)
    if price <= 0:
        return float("inf")
    return ref_quantity * (price / ref_price) ** (-e)


def clear_market(segments: Sequence[Segment], ref_quantity: float, ref_price: float,
                 elasticity: float = 0.08, cost: str = "full",
                 p_lo: float = 1.0, p_hi: float = 200.0, tol: float = 1e-4) -> dict:
    """Find the market-clearing price where economic supply meets demand.

    Excess supply E(p) = economic_supply(p) - demand(p) is non-decreasing in p
    (supply rises stepwise, demand falls), so a bisection converges on the crossing.
    """
    def excess(p):
        return economic_supply(segments, p, cost) - demand(p, ref_quantity, ref_price, elasticity)

    lo, hi = p_lo, p_hi
    # if demand exceeds total supply even at the top price, the market can't clear
    if excess(hi) < 0:
        return {"cleared": False, "price": hi, "quantity": economic_supply(segments, hi, cost),
                "demand": demand(hi, ref_quantity, ref_price, elasticity)}
    if excess(lo) > 0:
        lo_price = lo
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if excess(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    price = 0.5 * (lo + hi)
    q = demand(price, ref_quantity, ref_price, elasticity)
    # marginal segment = cheapest one whose breakeven is just at/above the clearing price
    key = "breakeven_full" if cost == "full" else "cash_cost"
    marginal = min((s for s in segments if getattr(s, key) >= price - 1e-6),
                   key=lambda s: getattr(s, key), default=None)
    return {"cleared": True, "price": round(price, 2), "quantity": round(q, 2),
            "economic_supply": round(economic_supply(segments, price, cost), 2),
            "marginal_segment": marginal.name if marginal else None}


if __name__ == "__main__":
    from data import SEGMENTS, DEMAND_MMBD
    for shock, label in [(1.00, "base"), (1.05, "demand +5%"), (0.95, "demand -5%")]:
        r = clear_market(SEGMENTS, DEMAND_MMBD * shock, ref_price=65.0, elasticity=0.08)
        print(f"{label:12s} -> clearing price ${r['price']:.1f}/bbl, "
              f"volume {r['quantity']:.1f} mmb/d, marginal {r['marginal_segment']}")
