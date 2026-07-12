"""Run the full analysis: charts, summary.json, and a model-driven insight memo that
stays in sync with the data. Numbers in the memo are computed here so they match the engine.

Run:  python src/analysis.py
"""
from __future__ import annotations
import json, os
from data import (SEGMENTS, DEMAND_MMBD, PRICE_SCENARIOS, COST_INFLATION_SCENARIOS,
                  TOTAL_LIQUIDS_2024)
from costcurve import (build_curve, total_supply, marginal_barrel, uneconomic_volume,
                       price_sensitivity, monte_carlo_at_risk, apply_cost_inflation,
                       average_cost_to_meet)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)


def compute():
    curve = build_curve(SEGMENTS, "full")
    supply = total_supply(SEGMENTS)
    out = {
        "supply_crude_condensate_mmbd": round(supply, 1),
        "total_liquids_ref_mmbd": TOTAL_LIQUIDS_2024,
        "demand_mmbd": DEMAND_MMBD,
        "marginal_barrel": marginal_barrel(curve, DEMAND_MMBD),
        "avg_cost_to_meet_demand": round(average_cost_to_meet(curve, DEMAND_MMBD), 1),
        "price_scenarios": {}, "monte_carlo": {}, "cost_inflation": {},
    }
    for name, p in PRICE_SCENARIOS.items():
        out["price_scenarios"][name] = {
            "price": p,
            "full_cycle": uneconomic_volume(SEGMENTS, p, "full"),
            "cash": uneconomic_volume(SEGMENTS, p, "cash"),
        }
        out["monte_carlo"][name] = monte_carlo_at_risk(SEGMENTS, p, n=10000, seed=42)
    for name, infl in COST_INFLATION_SCENARIOS.items():
        segs = apply_cost_inflation(SEGMENTS, infl)
        out["cost_inflation"][name] = {
            "inflation": infl,
            "marginal_barrel_at_demand": marginal_barrel(build_curve(segs, "full"), DEMAND_MMBD)["marginal_cost"],
            "at_risk_at_65_full": uneconomic_volume(segs, 65, "full")["at_risk_mmbd"],
        }
    return out


def charts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    curve = build_curve(SEGMENTS, "full")

    # 1) supply cost curve with uncertainty whiskers
    fig, ax = plt.subplots(figsize=(10, 5))
    for r in curve:
        ax.bar(r["cum_start"], r["cost"], width=r["production_mmbd"], align="edge",
               color="#3B6EA5", edgecolor="white", linewidth=0.6)
        xc = r["cum_start"] + r["production_mmbd"] / 2
        ax.plot([xc, xc], [r["low"], r["high"]], color="#20344a", lw=1.1)
        ax.plot([xc], [r["cost"]], marker="_", color="#20344a", ms=6)
    for label, price in PRICE_SCENARIOS.items():
        ax.axhline(price, ls="--", lw=1, color="#C0504D")
        ax.text(0.3, price + 0.7, f"${price:.0f}", color="#C0504D", fontsize=8)
    ax.set_xlabel("Cumulative crude + condensate (million barrels/day)")
    ax.set_ylabel("Full-cycle economic breakeven ($/bbl)")
    ax.set_title("Global crude-oil supply cost curve with breakeven uncertainty")
    ax.set_xlim(0, total_supply(SEGMENTS)); ax.set_ylim(0, 100)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "supply_cost_curve.png"), dpi=120)
    plt.close(fig)

    # 2) price sensitivity, full & cash, with MC band on the full-cycle line
    prices = list(range(30, 96, 5))
    full = [uneconomic_volume(SEGMENTS, p, "full")["at_risk_mmbd"] for p in prices]
    cash = [uneconomic_volume(SEGMENTS, p, "cash")["at_risk_mmbd"] for p in prices]
    mc = [monte_carlo_at_risk(SEGMENTS, p, n=4000, seed=1) for p in prices]
    p10 = [m["p10"] for m in mc]; p90 = [m["p90"] for m in mc]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.fill_between(prices, p10, p90, color="#3B6EA5", alpha=0.18, label="Full-cycle P10–P90 (Monte-Carlo)")
    ax.plot(prices, full, "-o", color="#3B6EA5", label="New-investment at risk (full-cycle)")
    ax.plot(prices, cash, "-o", color="#C0504D", label="Shut-in risk (cash cost)")
    ax.set_xlabel("Oil price ($/bbl)"); ax.set_ylabel("Volume at risk (mmb/d)")
    ax.set_title("Supply at risk vs oil price (with uncertainty band)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "price_sensitivity.png"), dpi=120)
    plt.close(fig)

    # 3b) carbon-cost overlay: base breakeven + carbon cost, ranked by carbon-adjusted cost
    from carbon import carbon_adjusted_curve
    cp = 100.0
    cadj = carbon_adjusted_curve(SEGMENTS, cp)
    names = [r["name"] for r in cadj]
    base_c = [r["base"] for r in cadj]
    carb = [r["carbon_cost"] for r in cadj]
    figc, axc = plt.subplots(figsize=(10, 5))
    y = range(len(cadj))
    axc.barh(list(y), base_c, color="#3B6EA5", label="Full-cycle breakeven")
    axc.barh(list(y), carb, left=base_c, color="#4F9D69", label=f"Carbon cost @ ${cp:.0f}/tCO2e")
    axc.set_yticks(list(y)); axc.set_yticklabels(names, fontsize=7)
    axc.invert_yaxis(); axc.set_xlabel("$/bbl"); axc.legend(loc="lower right", fontsize=8)
    axc.set_title("Carbon-adjusted supply cost (upstream intensity), ranked")
    figc.tight_layout(); figc.savefig(os.path.join(RESULTS, "carbon_overlay.png"), dpi=120)
    plt.close(figc)

    # 3) Monte-Carlo distribution of at-risk volume at the base price
    base = PRICE_SCENARIOS["base_65"]
    import random
    rng = random.Random(42)
    from costcurve import _triangular
    bands = [(s.production_mmbd, *s.band(), s.breakeven_full) for s in SEGMENTS]
    draws = []
    for _ in range(10000):
        v = sum(prod for prod, lo, hi, mode in bands if _triangular(lo, mode, hi, rng) > base)
        draws.append(v)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.hist(draws, bins=40, color="#3B6EA5", edgecolor="white")
    ax.set_xlabel(f"At-risk volume at ${base:.0f}/bbl (mmb/d)")
    ax.set_ylabel("Frequency"); ax.set_title("Monte-Carlo: at-risk volume distribution (10,000 draws)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "monte_carlo.png"), dpi=120)
    plt.close(fig)


def write_memo(s):
    base = s["price_scenarios"]["base_65"]
    stress = s["price_scenarios"]["stress_40"]
    mc65 = s["monte_carlo"]["base_65"]
    infl = s["cost_inflation"]["supply_chain_+15%"]
    memo = f"""# Insight memo — Global crude-oil supply at risk

*Figures are produced directly from the model (`python src/analysis.py`) and reconcile with the workbook.*

## Situation
Global crude + condensate supply is ~{s['supply_crude_condensate_mmbd']} mmb/d
(part of ~{s['total_liquids_ref_mmbd']} mmb/d total liquids). Ranking it cheapest-first
on full-cycle economic breakeven produces the supply cost curve. To clear demand of
~{s['demand_mmbd']:.0f} mmb/d the marginal barrel costs about
${s['marginal_barrel']['marginal_cost']:.0f}/bbl ({s['marginal_barrel']['marginal_segment']}).

## Key findings
1. **The market is cost-segmented.** Middle East onshore clears well below $30/bbl,
   Brazil pre-salt is a low-cost deepwater outlier (~$35), US shale sits mid-curve
   (~$61–63, Dallas Fed Q1'25), and oil sands / Arctic anchor the high end ($70–78).
2. **Full-cycle vs cash cost are very different risks.** At ${stress['price']:.0f}/bbl,
   {stress['full_cycle']['at_risk_mmbd']:.1f} mmb/d ({stress['full_cycle']['at_risk_share']*100:.0f}%)
   cannot justify **new** investment, but only {stress['cash']['at_risk_mmbd']:.1f} mmb/d is
   **cash-negative** (actual shut-in risk). Capital dries up long before barrels stop flowing.
3. **Uncertainty matters at the margin.** At the ${base['price']:.0f}/bbl base case the
   point estimate is {base['full_cycle']['at_risk_mmbd']:.1f} mmb/d at risk, but Monte-Carlo
   (10k draws over breakeven ranges) puts the P90 at {mc65['p90']:.1f} mmb/d — a meaningful tail.
4. **Cost inflation is a price-equivalent.** A +15% supply-chain cost shock lifts the
   marginal barrel to ${infl['marginal_barrel_at_demand']:.0f}/bbl and raises at-risk volume
   at $65 to {infl['at_risk_at_65_full']:.1f} mmb/d.
5. **A carbon price re-ranks by intensity, not just level.** At $100/tCO2e the highest-
   intensity barrels (oil sands ~+$11/bbl, extra-heavy ~+$12/bbl) take the biggest hit,
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
"""
    with open(os.path.join(ROOT, "INSIGHT_MEMO.md"), "w") as f:
        f.write(memo)


def main():
    s = compute()
    with open(os.path.join(RESULTS, "summary.json"), "w") as f:
        json.dump(s, f, indent=2)
    charts()
    write_memo(s)
    print("Analysis complete. Supply %.1f mmb/d | marginal barrel $%.0f | base at-risk P50 %.1f mmb/d"
          % (s["supply_crude_condensate_mmbd"], s["marginal_barrel"]["marginal_cost"],
             s["monte_carlo"]["base_65"]["p50"]))


if __name__ == "__main__":
    main()
