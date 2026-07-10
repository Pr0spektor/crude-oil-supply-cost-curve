# crude-oil-supply-cost-curve

**Global crude-oil supply cost curve — breakeven benchmarking.** A compact,
Energy-Solutions-style analytical tool that ranks oil supply by breakeven ($/bbl),
builds the cumulative supply cost curve, finds the marginal barrel needed to meet
demand, and quantifies how much production is uneconomic at a given oil price.
Implemented as an **interactive Excel workbook** (live SUMIF logic) and an
**auditable, unit-tested Python engine** that agree exactly.

Author: **Pr0spektor** · Bonn, Germany · [github.com/Pr0spektor](https://github.com/Pr0spektor)

---

## The question it answers

*"Oil just fell to $40/bbl. How much of world supply is now underwater, which
segment sets the marginal price, and where does new investment stop making sense?"*

This is a staple of energy-market intelligence: producers, investors and trading
desks read the supply cost curve to judge price floors, capital discipline and
which barrels clear the market. The method — rank supply cheapest-first, read the
clearing cost off the curve — follows the public cost-curve work of the IEA, EIA
and Rystad Energy.

## Headline results (illustrative dataset, ~98.5 mmb/d)

| Oil price | New-investment at risk (full-cycle) | Shut-in risk (cash cost) |
|---|---|---|
| **$40/bbl** | 51.5 mmb/d (52%) | 6.5 mmb/d |
| **$60/bbl** | 6.5 mmb/d (7%) | 0 |
| **$80/bbl** | 1.5 mmb/d (2%) | 0 |

*Two cost views matter: **full-cycle** breakeven governs whether NEW investment is
sanctioned; **cash cost** governs whether EXISTING output is shut in. High-cost
supply stops attracting capital long before it is actually curtailed.*

![Supply cost curve](results/supply_cost_curve.png)
![Supply at risk vs price](results/price_sensitivity.png)

## What's in the model

- **Cost curve** — segments sorted cheapest-first with cumulative production.
- **Marginal barrel** — the clearing cost to meet a demand scenario (flags a
  shortfall when demand exceeds supply).
- **At-risk volume** — production above the oil price, on both full-cycle and
  cash-cost views, with the at-risk share of supply.
- **Price sensitivity** — how at-risk volume changes across $30–90/bbl.

## Repository layout

```
src/costcurve.py     # engine: build_curve, marginal_barrel, uneconomic_volume … (stdlib only)
src/assets.py        # supply-segment dataset (production, full-cycle & cash breakeven)
src/build_workbook.py# writes model.xlsx (live SUMIF) + charts + summary.json
tests/test_costcurve.py # 13 unit tests (hand-checked fixture)
model.xlsx           # interactive workbook: Assets → CostCurve → Outputs
results/             # cost-curve & sensitivity charts + summary.json
```

## Run it

```bash
python src/build_workbook.py     # (re)build model.xlsx + charts  (needs openpyxl, matplotlib)
python tests/test_costcurve.py   # 13/13 tests, standalone …
pytest -q                        # … or under pytest (CI)
```

Open **`model.xlsx`**, change the oil-price cell on the **Outputs** sheet, and the
at-risk volumes recompute natively via `SUMIF` (no macros). Verified by recalculating
the workbook headless in LibreOffice — Excel and Python match.

## Data & caveats

Segment production and breakeven figures follow the **shape** of public supply cost
curves (IEA WEO, EIA, Rystad Energy UCube) but are **illustrative planning inputs**,
not audited asset economics, and are deliberately simplified (nine global segments).
This is a method demonstrator for decision support, not investment advice; use a
licensed asset-level database for commercial work.

## License

MIT — see [LICENSE](LICENSE).
