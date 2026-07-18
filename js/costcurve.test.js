// Dependency-free tests for the JS engine. Run: node js/costcurve.test.js
'use strict';
const assert = require('assert');
const { buildCurve, totalSupply, marginalBarrel, uneconomicVolume } = require('./costcurve');

const fix = [
  { name: 'A', region: 'R', production_mmbd: 10, breakeven_full: 20, cash_cost: 10 },
  { name: 'B', region: 'R', production_mmbd: 5, breakeven_full: 50, cash_cost: 30 },
  { name: 'C', region: 'R', production_mmbd: 5, breakeven_full: 35, cash_cost: 25 },
];

let passed = 0;
const test = (name, fn) => { fn(); console.log('  PASS  ' + name); passed++; };

test('total supply', () => assert.strictEqual(totalSupply(fix), 20));

test('sorted cheapest-first with cumulative', () => {
  const c = buildCurve(fix);
  assert.deepStrictEqual(c.map((r) => r.name), ['A', 'C', 'B']);
  assert.strictEqual(c[2].cum_end, 20);
  for (let i = 1; i < c.length; i++) assert.strictEqual(c[i].cum_start, c[i - 1].cum_end);
});

test('marginal barrel within supply', () => {
  const r = marginalBarrel(buildCurve(fix), 12);
  assert.strictEqual(r.marginal_segment, 'C');
  assert.strictEqual(r.marginal_cost, 35);
  assert.strictEqual(r.supplied, true);
});

test('marginal barrel exceeding supply', () => {
  assert.strictEqual(marginalBarrel(buildCurve(fix), 25).supplied, false);
});

test('uneconomic volume conserves total', () => {
  for (const p of [10, 25, 40, 60]) {
    const u = uneconomicVolume(fix, p);
    assert.strictEqual(u.at_risk_mmbd + u.economic_mmbd, 20);
  }
  assert.strictEqual(uneconomicVolume(fix, 15).at_risk_mmbd, 20); // all above $15
  assert.strictEqual(uneconomicVolume(fix, 60).at_risk_mmbd, 0);  // none above $60
});

console.log(`\n${passed}/5 JS tests passed.`);
