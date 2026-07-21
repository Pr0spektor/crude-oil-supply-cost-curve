# Data sources & provenance

All figures are **publicly-anchored, illustrative planning inputs**, not proprietary
asset-level data. They reproduce the *shape and level* of published cost curves.

## Primary anchors
- **Federal Reserve Bank of Dallas — Energy Survey, Q1 2025** (fielded 12–20 Mar 2025):
  average new-well breakeven **$65/bbl** (whole sample); **Permian Midland $61**,
  **Permian Delaware $62**, **Other US shale $63**; operating/shut-in prices
  **$33–41/bbl** ($35 Midland, $33 Delaware, $41 other shale).
  https://www.dallasfed.org/research/surveys/des/2025/2501
- **U.S. Energy Information Administration (EIA)** — Short-Term Energy Outlook: total
  world liquids production ≈**103 mmb/d** (2024); crude + condensate ≈82 mmb/d.
  https://www.eia.gov/outlooks/steo/
- **International Energy Agency (IEA)** — Oil Market Report / World Energy Outlook:
  regional production shares and relative production-cost ordering.
  https://www.iea.org/
- **Rystad Energy** — public cost-curve commentary: segment breakeven ordering
  (Middle East onshore lowest; Brazil pre-salt low-cost deepwater; oil sands / Arctic
  highest; US shale mid-curve).

## How figures were set
- US shale nodes use the Dallas Fed Q1 2025 means directly.
- Non-US nodes use IEA/Rystad public *ranges*; the point estimate is the mid-range and
  (low, high) bracket the plausible spread for Monte-Carlo.
- Production is apportioned to sum to ≈82 mmb/d crude + condensate.

## Carbon intensity
- **Masnadi et al. (2018), "Global carbon intensity of crude oil production",
  *Science* 361(6405):851–853** — upstream (production) carbon intensity of crude;
  global volume-weighted average ≈0.06 tCO2e/bbl, with oil sands, extra-heavy and
  high-flaring supply at the high end. Used for the carbon-cost overlay (point values
  illustrative).

## Explicitly NOT used
- **Fiscal breakevens** (e.g. IMF Regional Economic Outlook) — a government-budget
  metric, different from project economics. Noted in METHODS to prevent conflation.

> Replace these with a licensed asset-level dataset (e.g. Rystad UCube, Wood Mackenzie)
> before any commercial decision.
