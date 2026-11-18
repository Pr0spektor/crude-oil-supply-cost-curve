"""OPEC+ spare capacity as the swing supplier of last resort.

Why this module exists
----------------------
Without spare capacity the cost curve is the whole world: if demand runs past the last
node, the clearing price is a rationing price with no economic content. In reality OPEC+
holds several million barrels a day of idle capacity that can be brought online within
weeks, and that capacity is what clears a small imbalance. Ignoring it turns a 0.2 mmb/d
shortfall into a $83 print and a large shortfall into a runaway number.

Shape of the curve
------------------
Spare is not free and it is not flat. The swing producer needs a price above its fiscal
breakeven to justify opening the taps, and the last barrel of spare costs more than the
first because the cheap, quick volumes go first. A linear ramp between a floor and a
ceiling captures both features with two parameters that can be defended:

* ``floor_price``  — the price at which the first spare barrel appears. Saudi Arabia's
  fiscal breakeven has sat near $80-96/bbl through the 2020s (IMF Fiscal Monitor), so
  $80 is the conservative end: spare starts moving early rather than late.
* ``ceiling_price`` — the price at which spare is exhausted. $120/bbl is the level at
  which demand destruction becomes visible in the historical record (2008, 2022).

The capacity figure follows EIA STEO and IEA OMR: effective (not nominal) spare among
OPEC+ producers with the ability to raise output within 30 days has run 3-5 mmb/d in
2024-25, concentrated in Saudi Arabia, the UAE and Kuwait. ``4.0`` is the midpoint.

What this changes in the answer
-------------------------------
With spare, a 0.2 mmb/d gap is closed by 0.2 mmb/d of spare at a price just above the
floor, instead of by re-pricing the entire marginal barrel. The clearing price becomes a
balance quantity, which is what the model claims to compute.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpareCapacity:
    """Linear spare-capacity supply curve between a floor and a ceiling price."""

    capacity_mmbd: float = 4.0
    floor_price: float = 80.0
    ceiling_price: float = 120.0
    label: str = "OPEC+ spare"

    def __post_init__(self) -> None:
        if self.capacity_mmbd < 0:
            raise ValueError("spare capacity cannot be negative")
        if self.floor_price <= 0 or self.ceiling_price <= 0:
            raise ValueError("spare prices must be positive")
        if self.ceiling_price <= self.floor_price:
            raise ValueError("ceiling price must exceed the floor")

    def quantity(self, price: float) -> float:
        """Spare barrels offered (mmb/d) at a given price."""
        if price <= self.floor_price:
            return 0.0
        if price >= self.ceiling_price:
            return self.capacity_mmbd
        share = (price - self.floor_price) / (self.ceiling_price - self.floor_price)
        return self.capacity_mmbd * share

    def price_for(self, quantity: float) -> float:
        """Inverse: the price needed to bring ``quantity`` mmb/d of spare online."""
        if quantity <= 0:
            return self.floor_price
        if quantity >= self.capacity_mmbd:
            return self.ceiling_price
        share = quantity / self.capacity_mmbd
        return self.floor_price + share * (self.ceiling_price - self.floor_price)

    @property
    def is_empty(self) -> bool:
        return self.capacity_mmbd <= 0


DEFAULT_SPARE = SpareCapacity()

# Uncertainty carried through the Monte Carlo. Capacity is the dominant term: the
# difference between 3 and 5 mmb/d moves the clearing price more than any single
# breakeven band does.
CAPACITY_SD_MMBD = 0.5
CAPACITY_RANGE_MMBD = (2.0, 5.5)
FLOOR_SD_USD = 6.0
