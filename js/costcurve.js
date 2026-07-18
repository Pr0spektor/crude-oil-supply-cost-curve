// Crude-oil supply cost curve — JavaScript port of the core Python engine.
// Kept deliberately close to src/costcurve.py so results reconcile across languages
// (Excel + Python + JS). Zero dependencies; run the tests with `node js/costcurve.test.js`.

'use strict';

/** @typedef {{name:string, region:string, production_mmbd:number,
 *             breakeven_full:number, cash_cost:number}} Segment */

/** Sort supply cheapest-first and attach cumulative production (mmb/d). */
function buildCurve(segments, cost = 'full') {
  const key = cost === 'full' ? 'breakeven_full' : 'cash_cost';
  const rows = segments
    .map((s) => ({ name: s.name, production_mmbd: s.production_mmbd, cost: s[key] }))
    .sort((a, b) => a.cost - b.cost);
  let cum = 0;
  for (const r of rows) {
    r.cum_start = cum;
    cum += r.production_mmbd;
    r.cum_end = cum;
  }
  return rows;
}

function totalSupply(segments) {
  return segments.reduce((t, s) => t + s.production_mmbd, 0);
}

/** Cost of the last barrel needed to meet demand (the market-clearing cost). */
function marginalBarrel(curve, demandMmbd) {
  for (const r of curve) {
    if (demandMmbd <= r.cum_end + 1e-12) {
      return { demand_mmbd: demandMmbd, marginal_cost: r.cost, marginal_segment: r.name, supplied: true };
    }
  }
  const last = curve[curve.length - 1];
  return { demand_mmbd: demandMmbd, marginal_cost: last.cost, marginal_segment: last.name, supplied: false };
}

/** Production whose (chosen) cost exceeds `price`. */
function uneconomicVolume(segments, price, cost = 'full') {
  const key = cost === 'full' ? 'breakeven_full' : 'cash_cost';
  let atRisk = 0;
  let economic = 0;
  for (const s of segments) {
    if (s[key] > price) atRisk += s.production_mmbd;
    else economic += s.production_mmbd;
  }
  const tot = atRisk + economic;
  return { price, at_risk_mmbd: atRisk, economic_mmbd: economic, at_risk_share: tot ? atRisk / tot : 0 };
}

module.exports = { buildCurve, totalSupply, marginalBarrel, uneconomicVolume };
