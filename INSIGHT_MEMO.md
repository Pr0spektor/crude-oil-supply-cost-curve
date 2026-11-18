# Insight memo — Global crude-oil supply at risk

*Figures are produced directly from the model (`python src/analysis.py`) and reconcile with the workbook.*

## Situation
Global crude + condensate supply is ≈82.1 mmb/d
(part of ≈103.0 mmb/d total liquids). Ranking it cheapest-first
on full-cycle economic breakeven produces the supply cost curve. Demand is a separate,
price-elastic curve anchored on ≈82.3 mmb/d at
$80/bbl — EIA crude + condensate demand, with IEA's
83.2 mb/d refinery runs as the upper bound — and not on the supply build-up.

The two meet at **$83.3/bbl** (P10–P90 $78–$94).
At the central anchor, demand at the top of the curve exceeds deliverable supply by
0.33 mmb/d, so the price is set by that balance and carries a
scarcity rent of **$5.3/bbl** over the $78 cost of the last node.

## Key findings
1. **The price comes from the balance, not from the most expensive node.** The Arctic/frontier
   node sets the price in 84% of
   Monte-Carlo draws and Canadian oil sands in
   14% — the
   "marginal barrel" is a probability, not a fact. Middle East onshore still clears below $30,
   Brazil pre-salt sits near $35 and US shale at $61–63 (Dallas Fed Q1'25).
2. **Full-cycle vs cash cost are very different risks.** At $40/bbl,
   36.3 mmb/d (44%)
   cannot justify **new** investment, but only 9.1 mmb/d is
   **cash-negative** (actual shut-in risk). Capital dries up long before barrels stop flowing.
3. **Uncertainty matters at the margin.** At the $65/bbl base case the
   point estimate is 4.1 mmb/d at risk, but Monte-Carlo
   (10k draws over breakeven ranges) puts the P90 at 11.1 mmb/d — a meaningful tail.
4. **Cost inflation is a price-equivalent.** A +15% supply-chain cost shock lifts the
   clearing price to $90/bbl (from $83) and raises
   at-risk volume at $65 to 15.3 mmb/d.
5. **A carbon price re-ranks by intensity, not just level.** At $100/tCO2e the highest-
   intensity barrels (oil sands ≈+$11/bbl, extra-heavy ≈+$12/bbl) take the biggest hit,
   while low-intensity supply (Brazil pre-salt, low-flare Gulf) gains relative position —
   the merit-order shift is a transition-risk signal on top of the price view.

## Implications
- A sustained sub-$45 price threatens future supply growth far more than current output,
  so price weakness shows up first as deferred FIDs, not shut-ins.
- Whenever demand exceeds what the curve can deliver, the clearing price sits above the cost of
  the marginal barrel and the gap is a scarcity rent. That rent — not the breakeven of the last
  node — is what a disruption or a demand surprise moves first.

## Recommendation
Track the **full-cycle curve for investment/FID decisions** and the **cash-cost curve for
production resilience**, and stress both for cost inflation. Prioritise breakeven-range
(uncertainty) data collection on the marginal $55–80/bbl segments, where the P10–P90 band is
widest and the swing volume sits.

---
*Illustrative, publicly-anchored data (see SOURCES.md). Economic — not fiscal — breakevens.
Decision support, not investment advice.*
