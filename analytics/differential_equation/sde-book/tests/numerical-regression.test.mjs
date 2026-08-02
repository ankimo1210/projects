import assert from "node:assert/strict";
import test from "node:test";

import { memoizedDiagnostics } from "../app/diagnostics-cache.mjs";
import { normalCdf, normalQuantile } from "../app/numerical-functions.mjs";
import { binomial, mulberry32 } from "../app/random-distributions.mjs";

test("diagnostics are reused only for the same immutable settings and key", () => {
  const settings = { seed: 42 };
  let calculations = 0;
  const calculate = () => ({ value: ++calculations });

  const first = memoizedDiagnostics(settings, "lab-a", calculate);
  const repeated = memoizedDiagnostics(settings, "lab-a", calculate);
  const anotherLab = memoizedDiagnostics(settings, "lab-b", calculate);
  const changedSettings = memoizedDiagnostics({ seed: 43 }, "lab-a", calculate);

  assert.strictEqual(repeated, first);
  assert.equal(anotherLab.value, 2);
  assert.equal(changedSettings.value, 3);
  assert.equal(calculations, 3);
});

test("normal CDF and quantile remain numerical inverses", () => {
  for (const probability of [0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999]) {
    assert.ok(Math.abs(normalCdf(normalQuantile(probability)) - probability) < 2e-7);
  }
  assert.ok(Math.abs(normalCdf(0) - 0.5) < 1e-7);
  assert.ok(Math.abs(normalCdf(-1.25) - (1 - normalCdf(1.25))) < 1e-12);
});

test("binomial preserves rare SIR infection probabilities", () => {
  const population = 120;
  const infected = 4;
  const susceptible = population - infected;
  const beta = 1.6;
  const dt = 10 / 300;
  const probability = 1 - Math.exp((-beta * infected * dt) / population);
  const exactAtLeastOne = 1 - (1 - probability) ** susceptible;
  const random = mulberry32(4201);
  const draws = 120_000;
  let atLeastOne = 0;
  let total = 0;

  for (let index = 0; index < draws; index += 1) {
    const value = binomial(random, susceptible, probability);
    total += value;
    if (value > 0) atLeastOne += 1;
  }

  assert.ok(Math.abs(atLeastOne / draws - exactAtLeastOne) < 0.004);
  assert.ok(Math.abs(total / draws - susceptible * probability) < 0.008);
});

test("binomial handles rare failures without leaving its support", () => {
  const random = mulberry32(4001);
  const trials = 100;
  const probability = 0.992;
  const draws = 80_000;
  let total = 0;

  for (let index = 0; index < draws; index += 1) {
    const value = binomial(random, trials, probability);
    assert.ok(value >= 0 && value <= trials);
    total += value;
  }

  assert.ok(Math.abs(total / draws - trials * probability) < 0.03);
  assert.equal(binomial(random, trials, 0), 0);
  assert.equal(binomial(random, trials, 1), trials);
});
