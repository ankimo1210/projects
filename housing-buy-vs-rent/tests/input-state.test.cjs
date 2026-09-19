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

test('flat transaction amounts stay out of the price-proportional rates', () => {
  const flat = {...p, buy_cost_fixed: 1200000, sell_cost_fixed: 900000, basis_cost_fixed: 400000};
  const plain = M.saleTax(p, 300000000), withFlat = M.saleTax(flat, 300000000);
  const basisAfterDepreciation = 400000 * (1 - p.building_share * .9 * .015 * p.years);
  near(plain.taxable_gain - withFlat.taxable_gain, 900000 + basisAfterDepreciation);
  near(withFlat.basis - plain.basis, 400000 - 400000 * p.building_share * .9 * .015 * p.years);
  near(M.run(flat).initial_buy - M.run(p).initial_buy, 1200000);
});

test('break-even search reprices flat sale costs at the candidate price', () => {
  const flat = {...p, sell_cost_fixed: 900000};
  for (const mode of ['rent', 'corp']) {
    const be = M.breakSale(flat, mode);
    near(M.run({...flat, growth: be.growth})['wealth_diff_' + mode], 0, .01);
  }
  assert.ok(M.breakSale(flat).price > M.breakSale(p).price);
});

test('rent follows the captured yield until an amount is typed in', () => {
  const linked = I.setMode(I.createDefault(), 'rent', 'yield_linked');
  near(linked.rentYield, .036, 1e-12);
  near(I.resolve(linked).parameters.rent, 750000, 1e-6);
  near(I.resolve(I.scenario(linked, {price: 150000000})).parameters.rent, 450000, 1e-6);
  const typed = I.update(linked, {rent: 800000});
  assert.equal(typed.modes.rent, 'manual');
  near(I.resolve(I.scenario(typed, {price: 150000000})).parameters.rent, 800000, 1e-6);
  near(typed.rentYield, 800000 * 12 / 250000000, 1e-12);
});

test('yield-linked rent keeps the entry-price search inside the rent range', () => {
  const linked = I.setMode(I.createDefault(), 'rent', 'yield_linked');
  for (const solver of ['breakPrice', 'breakEntry']) {
    assert.doesNotThrow(() => I[solver](linked), `${solver} walked outside the rent range`);
    const price = I[solver](linked);
    if (price === null) continue;
    const rent = price * linked.rentYield / 12;
    assert.ok(rent >= 100000 && rent <= 2000000, `${solver} implied rent ${rent}`);
    assert.doesNotThrow(() => I.resolve(I.scenario(linked, {price})));
  }
  // Rent that scales with the price removes the crossing; holding the exit price keeps one.
  assert.equal(I.breakPrice(linked), null);
  assert.ok(I.breakEntry(linked) > 0);
});

test('residential relief preset sets both assumptions and yields to either edit', () => {
  const off = I.setMode(I.createDefault(), 'deduction_sale', 'non_residential');
  const resolved = I.resolve(off).parameters;
  assert.equal(resolved.deduction_sale, 0);
  assert.equal(resolved.reduced_long, false);
  assert.equal(I.update(off, {reduced_long: true}).modes.deduction_sale, 'manual');
  assert.equal(I.resolve(I.setMode(off, 'deduction_sale', 'residential')).parameters.deduction_sale, 30000000);
  assert.ok(I.evaluate(off).corp.growth > I.evaluate(I.createDefault()).corp.growth);
});

test('itemized sale costs follow the brokerage scale and the stamp bracket', () => {
  const itemized = I.setMode(I.createDefault(), 'sell_cost', 'itemized');
  const q = I.resolve(itemized).parameters;
  near(q.sell_cost, .033, 1e-12);
  // 2.5億円は「1億円超5億円以下」区分なので印紙6万円。仲介の定額6.6万円と抹消0.2万円を足す。
  near(q.sell_cost_fixed, 66000 + 60000 + 2000);
  const price = 250000000, fee = price * q.sell_cost + q.sell_cost_fixed;
  near(fee, price * .033 + 128000);
  near(fee / price, .0335, 1e-4);
  // 5億円超に届く予想売値では印紙が16万円の区分に上がる。
  const bigger = I.resolve(I.scenario(itemized, {price: 600000000})).parameters;
  near(bigger.sell_cost_fixed, 66000 + 160000 + 2000);
  // 率を手で入れると連動が外れるが、画面に出ていた定額はそのまま引き継ぐ。
  const typed = I.update(itemized, {sell_cost: .04});
  assert.equal(typed.modes.sell_cost, 'manual');
  near(I.resolve(typed).parameters.sell_cost, .04, 1e-12);
  near(I.resolve(I.scenario(typed, {price: 600000000})).parameters.sell_cost_fixed, 128000);
  // 選択欄で手入力に戻したときも同じ。
  const released = I.setMode(itemized, 'sell_cost', 'manual');
  near(I.resolve(released).parameters.sell_cost_fixed, 128000);
  near(I.resolve(released).parameters.sell_cost, .033, 1e-12);
});

test('schema 1 files load without the flat amounts or the newer links', () => {
  const saved = JSON.parse(I.serialize(I.createDefault()));
  saved.schemaVersion = 1;
  for (const key of ['buy_cost_fixed', 'sell_cost_fixed', 'basis_cost_fixed']) {
    delete saved.inputs.values[key];
    delete saved.parameters[key];
  }
  delete saved.inputs.modes.rent;
  delete saved.inputs.modes.deduction_sale;
  delete saved.inputs.rentYield;
  const loaded = I.deserialize(saved);
  assert.equal(loaded.modes.rent, 'manual');
  assert.equal(loaded.modes.deduction_sale, 'manual');
  assert.equal(I.resolve(loaded).parameters.sell_cost_fixed, 0);
  near(I.resolve(loaded).parameters.social, 1804372);
  const missingRequired = JSON.parse(I.serialize(I.createDefault()));
  delete missingRequired.inputs.modes.social;
  assert.throws(() => I.deserialize(missingRequired));
});

test('reject invalid modes and altered resolved snapshot', () => {
  const current = I.createDefault();
  assert.throws(() => I.setMode(current, 'social', 'same_as_rent'));
  const saved = JSON.parse(I.serialize(current));
  saved.parameters.social = 0;
  assert.throws(() => I.deserialize(saved));
  assert.equal(I.resolve(current).parameters.social, 1804372);
});
