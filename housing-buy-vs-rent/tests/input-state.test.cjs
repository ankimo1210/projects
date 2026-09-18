const test = require('node:test');
const assert = require('node:assert/strict');
const {M, p, I} = require('./load-model.cjs')();

const near = (actual, expected, tolerance=0.01) =>
  assert.ok(Math.abs(actual-expected) <= tolerance, `${actual} != ${expected}`);

test('legacy manual state reproduces the original baseline', () => {
  const state = I.create(p);
  const result = I.evaluate(state);
  assert.equal(result.error, undefined);
  near(result.corp.growth, M.breakSale(p).growth, 1e-12);
  assert.equal(I.resolve(state).parameters.social, 1500000);
});

test('default social estimates use monthly caps and employment insurance', () => {
  const state = I.createDefault();
  const resolved = I.resolve(state).parameters;
  near(resolved.social, 1804372);
  near(resolved.social_corp, 1759372);
  near(resolved.owner_cost, 2500000);
  near(I.resolve(I.setAgeBand(state, '40-64')).parameters.social, 1939480);
  assert.equal(state.ageBand, 'under40');
});

test('salary, rent and corporate rules recalculate estimated social premiums', () => {
  const state = I.createDefault();
  const changed = I.update(state, {salary: 40000000, rent: 900000});
  const q = I.resolve(changed).parameters;
  near(q.social, 1754372);
  near(q.social_corp, 1700372);
  assert.equal(I.resolve(state).parameters.salary, 50000000);
});

test('property cost tracks price until the user supplies an annual amount', () => {
  const base = I.createDefault();
  const changed = I.update(base, {price: 300000000});
  near(I.resolve(changed).parameters.owner_cost, 3000000);
  const fixed = I.update(changed, {owner_cost: 2400000});
  near(I.resolve(I.update(fixed, {price: 200000000})).parameters.owner_cost, 2400000);
  near(I.resolve(I.setMode(fixed, 'owner_cost', 'estimate')).parameters.owner_cost, 3000000);
});

test('social manual override and explicit equal-to-normal mode', () => {
  const base = I.createDefault();
  const manual = I.update(base, {social_corp: 1500000});
  near(I.resolve(I.update(manual, {salary: 40000000})).parameters.social_corp, 1500000);
  const equal = I.setMode(manual, 'social_corp', 'same_as_normal');
  near(I.resolve(I.update(equal, {salary: 40000000})).parameters.social_corp, 1754372);
  assert.equal(I.resolve(manual).parameters.social_corp, 1500000);
});

test('full residence follows duration; independent heatmap preserves original period', () => {
  const base = I.setMode(I.createDefault(), 'corp_years', 'full_residence');
  const linked = I.evaluate(I.scenario(base, {years: 15}));
  const independent = I.evaluate(I.scenario(base, {years: 15}, 'independent'));
  assert.equal(linked.p.corp_years, 15);
  assert.equal(independent.p.corp_years, 10);
  assert.ok(linked.corp.growth > independent.corp.growth);
  assert.equal(I.resolve(base).parameters.years, 10);
});

test('setting an increasing cost rate can follow rent or retain an override', () => {
  const base = I.setMode(I.createDefault(), 'owner_growth', 'same_as_rent');
  near(I.resolve(I.update(base, {rent_growth: .03})).parameters.owner_growth, .03, 1e-12);
  const manual = I.update(base, {owner_growth: .01});
  near(I.resolve(I.update(manual, {rent_growth: .04})).parameters.owner_growth, .01, 1e-12);
});

test('entry-price break-even recalculates price-linked ownership costs', () => {
  const state = I.createDefault();
  for (const fixedExit of [false, true]) {
    const price = fixedExit ? I.breakEntry(state) : I.breakPrice(state);
    assert.ok(price > 0);
    const initial = I.resolve(state).parameters;
    const scenario = I.scenario(state, {
      price,
      ...(fixedExit ? {growth: Math.pow(initial.price * Math.pow(1 + initial.growth, initial.years) / price, 1 / initial.years) - 1} : {})
    });
    const resolved = I.resolve(scenario).parameters;
    near(resolved.owner_cost, price * .01, 1e-6);
    near(M.run(resolved).wealth_diff_corp, 0, 1);
  }
});

test('manual inverse prices preserve legacy results', () => {
  const manual = I.create(p);
  near(I.breakPrice(manual), M.breakPrice(p), 1);
  near(I.breakEntry(manual), M.breakEntry(p), 1);
});

test('old JSON stays manual and new JSON restores active estimates and links', () => {
  const old = I.deserialize({model: 'housing-tax-comparison-v2-2026-09-17', parameters: p});
  near(I.evaluate(old).corp.growth, M.breakSale(p).growth, 1e-12);
  near(I.resolve(I.update(old, {price: 300000000})).parameters.owner_cost, 2500000);
  const current = I.setMode(I.createDefault(), 'corp_years', 'full_residence');
  const loaded = I.deserialize(JSON.parse(I.serialize(current)));
  assert.equal(I.resolve(I.update(loaded, {years: 15})).parameters.corp_years, 15);
  near(I.resolve(loaded).parameters.social, 1804372);
});

test('reject invalid modes and altered resolved snapshot', () => {
  const current = I.createDefault();
  assert.throws(() => I.setMode(current, 'social', 'same_as_rent'));
  const saved = JSON.parse(I.serialize(current));
  saved.parameters.social = 0;
  assert.throws(() => I.deserialize(saved));
  assert.equal(I.resolve(current).parameters.social, 1804372);
});
