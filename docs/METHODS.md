# Methods note

## What this model is
A **supply cost curve** ranks the world's crude + condensate supply from cheapest
to most expensive on a per-barrel breakeven, then reads the *clearing* (marginal)
cost off the cumulative curve. It is the standard lens for judging price floors,
capital discipline and which barrels are economic.

## Breakeven definitions — do not conflate these
| Term | Meaning | Used here |
|---|---|---|
| **Full-cycle economic breakeven** | Oil price at which a *new* project earns its required return (CAPEX + OPEX + return). Governs sanction / FID decisions. | Yes — the main curve |
| **Half-cycle / cash cost** | Operating cost of *existing* output. Below this, barrels are shut in. | Yes — shut-in view |
| **Fiscal breakeven** | Oil price a *government* needs to balance its budget. A macro/political metric, **not** a project economics metric. | **No** — explicitly excluded to avoid a common error |

Because full-cycle > cash cost for almost every asset, a price fall stalls **new
investment** long before it curtails **current production**. The model reports both.

## Uncertainty
Each node's full-cycle breakeven is a point estimate inside a plausible **(low, high)**
range. `monte_carlo_at_risk` samples each node's breakeven from a triangular
distribution (low, mode, high) over 10,000 seeded draws and reports the mean and
**P10 / P50 / P90** of the at-risk volume — so the answer is a distribution, not a
false-precision point.

## Scenarios
- **Price**: stress $40, base $65, high $85 (Brent-equivalent).
- **Cost inflation**: a multiplicative shock to every breakeven (e.g. +15% supply-chain
  inflation, −10% deflation) — a cost shock is, at the margin, price-equivalent.

## Marginal barrel
`marginal_barrel(curve, demand)` walks the sorted curve and returns the cost of the
last barrel needed to meet demand — the market-clearing cost — and flags a shortfall
if demand exceeds modelled supply.

## Validation
- Modelled crude + condensate (~82 mmb/d) reconciles with total liquids (~103 mmb/d,
  EIA STEO) once NGLs, biofuels and refinery gain are added.
- Curve **shape and ordering** match published cost curves (Middle East cheapest;
  oil sands / Arctic most expensive; US shale mid-curve at the Dallas-Fed level).
- Excel and Python outputs are cross-checked by recalculating the workbook headless
  in LibreOffice.

## Carbon-cost overlay (transition lens)
Each node carries an **upstream carbon intensity** (tCO2e/bbl, production only —
excludes combustion Scope 3), following Masnadi et al. (2018). A carbon price adds
`carbon_price × intensity` to each barrel and the curve is **re-ranked**, so a carbon
price penalises high-intensity supply (oil sands, extra-heavy, high-flaring) and
improves the relative position of low-intensity barrels — a merit-order *reshuffle*,
not a uniform lift. `carbon.merit_order_shift` reports the rank change per node.

## Validation harness
`src/validate.py` (run in CI) asserts the data invariants — positive production,
cash ≤ full-cycle, point estimate inside its band, cumulative continuity, sorted curve,
at-risk + economic = total, reconciliation with total liquids, and a carbon intensity
for every node — so a bad data edit fails loudly.

## Limitations
Publicly-anchored, simplified (23 nodes) planning inputs — not a licensed asset-level
database. No basis differentials (Brent/WTI/Urals) beyond notes, no time dynamics or
demand-elasticity feedback. Decision support, not investment advice.
