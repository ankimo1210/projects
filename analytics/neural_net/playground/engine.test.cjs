const test = require('node:test');
const assert = require('node:assert/strict');
const { MLP, Experiment, makeData, DEFAULTS, activationGrid } = require('./engine.js');

test('seeded samples are balanced, reproducible and disjoint', () => {
  const data = makeData(DEFAULTS);
  assert.deepEqual(data, makeData(DEFAULTS));
  assert.notDeepEqual(data.train, makeData({ ...DEFAULTS, seed: 7 }).train);
  const ids = new Set();
  for (const [name, size] of [['train', 360], ['validation', 120], ['test', 120]]) {
    assert.equal(data[name].length, size);
    assert.equal(data[name].filter(p => p.y === 1).length, size / 2);
    for (const point of data[name]) {
      assert.ok(!ids.has(point.id));
      ids.add(point.id);
    }
  }
  for (let axis = 0; axis < 2; axis++) {
    const mean = data.train.reduce((s, p) => s + p.x[axis], 0) / 360;
    const variance = data.train.reduce((s, p) => s + p.x[axis] ** 2, 0) / 360;
    assert.ok(Math.abs(mean) < 1e-12);
    assert.ok(Math.abs(variance - 1) < 1e-12);
    const rawMean = data.train.reduce((s, p) => s + p.raw[axis], 0) / 360;
    assert.ok(Math.abs(data.scaler.mean[axis] - rawMean) < 1e-12);
  }
});

test('backprop agrees with finite differences including L2', () => {
  const model = new MLP([2, 3, 2, 1], 12, 'tanh');
  const points = [ {x: [0.2, -0.4], y: 1}, {x: [-0.8, 0.3], y: 0} ];
  const gradients = model.gradients(points, 0.07);
  const epsilon = 1e-5;
  model.layers.forEach((layer, l) => {
    for (const key of ['weights', 'biases']) {
      layer[key].forEach((value, i) => {
        layer[key][i] = value + epsilon;
        const plus = model.objective(points, 0.07);
        layer[key][i] = value - epsilon;
        const minus = model.objective(points, 0.07);
        layer[key][i] = value;
        assert.ok(Math.abs((plus - minus) / (2 * epsilon) - gradients[l][key][i]) < 1e-7);
      });
    }
  });
});

test('BCE stays finite for extreme logits and uses a 0.5 threshold', () => {
  const model = new MLP([2, 1], 1);
  model.layers[0].weights.set([1000, -1000]);
  model.layers[0].biases[0] = 0;
  const metrics = model.evaluate([{x: [1, -1], y: 0}, {x: [-1, 1], y: 1}, {x: [0, 0], y: 1}]);
  assert.ok(Number.isFinite(metrics.loss));
  assert.ok(metrics.loss > 1000);
  assert.deepEqual(metrics.confusion, [[0, 1], [1, 1]]);
  assert.equal(metrics.accuracy, 1 / 3);
});

test('two-moons model learns and beats the linear baseline on validation', () => {
  const run = new Experiment(DEFAULTS);
  const initial = run.history[0].train.loss;
  for (let i = 0; i < 350; i++) run.step();
  const last = run.history.at(-1);
  assert.ok(last.train.loss < initial * 0.25);
  assert.ok(last.validation.accuracy >= 0.94);
  assert.ok(last.validation.accuracy > run.baselineValidation.accuracy + 0.05);
});

test('held-out labels cannot affect weights or validation history', () => {
  const a = new Experiment(DEFAULTS);
  const b = new Experiment(DEFAULTS);
  for (const p of b.data.test) { p.y = 1 - p.y; p.x = [999, -999]; }
  for (let i = 0; i < 8; i++) { a.step(); b.step(); }
  assert.deepEqual(a.history, b.history);
  assert.deepEqual(a.model.layers, b.model.layers);
  assert.equal(a.testResult, null);
});

test('final evaluation freezes training and reports reconciled counts', () => {
  const run = new Experiment(DEFAULTS);
  assert.throws(() => run.finalize(), /train/i);
  run.step();
  const result = run.finalize();
  assert.equal(result.model.n, 120);
  assert.equal(result.model.confusion.flat().reduce((a, b) => a + b), 120);
  assert.equal(result.model.correct / 120, result.model.accuracy);
  assert.equal(run.finalize(), result);
  assert.throws(() => run.step(), /final/i);
});

test('all exposed dataset and activation choices train with finite metrics', () => {
  for (const dataset of ['moons', 'circles', 'xor']) {
    for (const activation of ['tanh', 'relu']) {
      const run = new Experiment({...DEFAULTS, dataset, activation, noise: 0.3, depth: 3, width: 16});
      for (let i = 0; i < 4; i++) run.step();
      assert.ok(Number.isFinite(run.history.at(-1).validation.loss));
    }
  }
});

test('neuron inspection reconciles every contribution with actual forward values', () => {
  const model = new MLP([2, 2, 1], 4);
  model.layers[0].weights.set([0.5, -0.25, 1, 0.2]);
  model.layers[0].biases.set([0.1, -0.3]);
  model.layers[1].weights.set([0.7, -0.4]);
  model.layers[1].biases[0] = 0.2;
  const input = [0.2, -0.5], forward = model.forward(input);
  const before = structuredClone(model.layers);
  for (let stage = 1; stage < model.sizes.length; stage++) {
    for (let unit = 0; unit < model.sizes[stage]; unit++) {
      const node = model.inspectNeuron(input, stage, unit);
      assert.ok(Math.abs(node.contributions.reduce((s, p) => s + p.product, node.bias) - node.z) < 1e-12);
      assert.equal(node.value, forward.activations[stage][unit]);
      assert.equal(node.z, forward.preactivations[stage - 1][unit]);
    }
  }
  assert.deepEqual(model.layers, before);
});

test('activation maps use the same raw coordinate orientation and actual model outputs', () => {
  const run = new Experiment(DEFAULTS);
  const domain = {xMin: -2, xMax: 2, yMin: -1, yMax: 1};
  const map = activationGrid(run.model, raw => run.transform(raw), domain, 3);
  const raws = [[-2, 1], [0, 1], [2, 1], [-2, 0], [0, 0], [2, 0], [-2, -1], [0, -1], [2, -1]];
  raws.forEach((raw, index) => {
    const values = run.model.forward(run.transform(raw)).activations;
    values.forEach((layer, stage) => layer.forEach((value, unit) => assert.equal(map.layers[stage][unit][index], value)));
  });
  assert.throws(() => activationGrid(run.model, x => x, domain, 1), /resolution/i);
});

test('recorded update is the real full-batch gradient and Adam weight change', () => {
  const run = new Experiment(DEFAULTS);
  const expected = run.model.gradients(run.data.train, run.config.l2);
  const weights = run.model.layers.map(layer => Array.from(layer.weights));
  const previousLoss = run.history[0].train.loss;
  run.step();
  assert.equal(run.lastUpdate.beforeLoss, previousLoss);
  assert.equal(run.lastUpdate.afterLoss, run.history.at(-1).train.loss);
  let squared = 0;
  expected.forEach((gradient, l) => {
    for (const key of ['weights', 'biases']) {
      gradient[key].forEach((value, i) => {
        assert.equal(run.lastUpdate.layers[l][key].gradient[i], value);
        assert.equal(run.lastUpdate.layers[l][key].after[i], run.model.layers[l][key][i]);
        squared += value * value;
      });
    }
    assert.deepEqual(Array.from(run.lastUpdate.layers[l].weights.before), weights[l]);
  });
  assert.ok(Math.abs(run.lastUpdate.gradientNorm - Math.sqrt(squared)) < 1e-12);
  const saved = structuredClone(run.lastUpdate);
  run.step();
  assert.equal(saved.layers[0].weights.after[0], run.lastUpdate.layers[0].weights.before[0]);
});
