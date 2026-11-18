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

## Demand and the clearing price
`marginal_barrel(curve, demand)` walks the sorted curve and returns the cost of the last
barrel *needed* — but only if demand is supplied exogenously. Feeding it a demand figure that
was itself set equal to modelled supply makes the most expensive node marginal by construction,
which is what the earlier version did (82.0 vs 82.1 mmb/d).

`src/demand.py` replaces that with a price-elastic curve:

```
Q(p) = anchor * (p / anchor_price) ** -elasticity
anchor        = 82.3 mmb/d   world crude + condensate demand, 2024 (EIA STEO)
anchor_price  = 80 $/bbl
elasticity    = 0.06         short-run, literature range 0.03-0.10
```

`clearing(curve, demand)` then solves the balance and returns one of three states:

| State | Meaning | Price |
|---|---|---|
| `interior` | demand is met inside the curve | cost of the marginal node |
| `demand_capped` | the cheapest node already covers demand | cost of the cheapest node |
| `supply_capped` | demand exceeds everything the curve can deliver | scarcity price above marginal cost |

In the `supply_capped` case the price is *not* a cost of production: it is the price at which
demand falls to the deliverable volume, and the difference from the top of the curve is reported
as `scarcity_rent`. `extrapolated` flags cases where the constant-elasticity form is being
stretched beyond a 50% rent.

`clearing_distribution()` draws the demand anchor (normal, sd 0.45 mmb/d), the elasticity
(uniform 0.03-0.10) and every breakeven band (triangular) to produce a price distribution and,
more usefully, the probability that each node is the marginal one — the question a single
"marginal barrel" number cannot answer.

Limitation: the curve has no OPEC+ spare capacity, so when demand exceeds 82.1 mmb/d the model
prices rationing rather than a swing producer. That is stated in the output rather than hidden.

## Validation
- Modelled crude + condensate (≈82 mmb/d) reconciles with total liquids (≈103 mmb/d,
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
