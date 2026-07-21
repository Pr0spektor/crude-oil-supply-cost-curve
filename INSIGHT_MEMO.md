# Insight memo — Global crude-oil supply at risk

*Figures are produced directly from the model (`python src/analysis.py`) and reconcile with the workbook.*

## Situation
Global crude + condensate supply is ≈82.1 mmb/d
(part of ≈103.0 mmb/d total liquids). Ranking it cheapest-first
on full-cycle economic breakeven produces the supply cost curve. To clear demand of
≈82 mmb/d the marginal barrel costs about
$78/bbl (Arctic / frontier).

## Key findings
1. **The market is cost-segmented.** Middle East onshore clears well below $30/bbl,
   Brazil pre-salt is a low-cost deepwater outlier (≈$35), US shale sits mid-curve
   (≈$61–63, Dallas Fed Q1'25), and oil sands / Arctic anchor the high end ($70–78).
2. **Full-cycle vs cash cost are very different risks.** At $40/bbl,
   36.3 mmb/d (44%)
   cannot justify **new** investment, but only 9.1 mmb/d is
   **cash-negative** (actual shut-in risk). Capital dries up long before barrels stop flowing.
3. **Uncertainty matters at the margin.** At the $65/bbl base case the
   point estimate is 4.1 mmb/d at risk, but Monte-Carlo
   (10k draws over breakeven ranges) puts the P90 at 11.1 mmb/d — a meaningful tail.
4. **Cost inflation is a price-equivalent.** A +15% supply-chain cost shock lifts the
   marginal barrel to $90/bbl and raises at-risk volume
   at $65 to 15.3 mmb/d.
5. **A carbon price re-ranks by intensity, not just level.** At $100/tCO2e the highest-
   intensity barrels (oil sands ≈+$11/bbl, extra-heavy ≈+$12/bbl) take the biggest hit,
   while low-intensity supply (Brazil pre-salt, low-flare Gulf) gains relative position —
   the merit-order shift is a transition-risk signal on top of the price view.

## Implications
- A sustained sub-$45 price threatens future supply growth far more than current output,
  so price weakness shows up first as deferred FIDs, not shut-ins.
- The clearing price is set by high-cost marginal supply (oil sands, Arctic, mature offshore);
  those segments are the swing factor for both price and investment.

## Recommendation
Track the **full-cycle curve for investment/FID decisions** and the **cash-cost curve for
production resilience**, and stress both for cost inflation. Prioritise breakeven-range
(uncertainty) data collection on the marginal $55–80/bbl segments, where the P10–P90 band is
widest and the swing volume sits.

---
*Illustrative, publicly-anchored data (see SOURCES.md). Economic — not fiscal — breakevens.
Decision support, not investment advice.*
