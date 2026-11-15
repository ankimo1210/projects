const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {CNN, bytes, floats, softmax, prepareDrawing} = require('./digits-engine.js');
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, 'digit-results.json'), 'utf8'));
function close(actual, expected, tolerance = 0.00008) {
  assert.equal(actual.length, expected.length);
  const maximum = Math.max(...Array.from(actual, (value, i) => Math.abs(value - expected[i])));
  assert.ok(maximum <= tolerance, `Maximum difference ${maximum} exceeds ${tolerance}`);
}
function fixture(spec) {
  const sample = snapshot.data.examples.find(item => item.id === spec.verification.sample_id);
  const input = Float64Array.from(bytes(sample.pixels), value => value / 255);
  const cnn = new CNN(spec.channels, spec.history[spec.best_epoch].weights);
  return {cnn, input, frame: cnn.forward(input)};
}

test('independent JavaScript CNN matches PyTorch logits, every feature map, and input gradients', () => {
  for (const spec of snapshot.models) {
    const {cnn, frame} = fixture(spec), oracle = spec.verification;
    close(frame.logits, oracle.training_logits);
    close(frame.logits, oracle.logits, 1e-10);
    close(frame.probabilities, oracle.probabilities, 0.000001);
    [frame.first, frame.pooledFirst, frame.second, frame.pooledSecond].forEach((layer, i) => close(layer.a, floats(oracle.features[i])));
    close(cnn.inputGradient(frame, oracle.class), floats(oracle.input_gradient));
    assert.equal(frame.prediction, oracle.class);
  }
});

test('displayed convolution patches and full class contributions sum to the actual forward values', () => {
  for (const spec of snapshot.models) {
    const {cnn, frame} = fixture(spec);
    for (const [row, col] of [[0, 0], [10, 11], [23, 23]]) for (let c = 0; c < spec.channels[0]; c++) {
      const cell = cnn.inspect(frame, c, row, col);
      close([cell.z, cell.value], [frame.first.z[(c * 24 + row) * 24 + col], frame.first.a[(c * 24 + row) * 24 + col]], 1e-12);
    }
    for (let target = 0; target < 10; target++) {
      const result = cnn.contributions(frame, target);
      close([result.values.reduce((sum, value) => sum + value.product, result.bias)], [frame.logits[target]], 1e-11);
      assert.equal(result.values.length, spec.channels[1] * 25);
    }
  }
});

test('input sensitivities agree with finite differences away from nondifferentiable pool ties', () => {
  const {cnn, input} = fixture(snapshot.models[0]);
  input.forEach((value, i) => { input[i] = value + Math.sin(i * 17.83) * .0001; });
  const frame = cnn.forward(input);
  for (const target of [0, 3, 8]) {
    const gradient = cnn.inputGradient(frame, target);
    const ranked = Array.from(gradient, (value, index) => ({value, index})).sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    for (const {index} of ranked.slice(0, 5)) {
      const plus = input.slice(), minus = input.slice(), epsilon = 1e-6;
      plus[index] += epsilon; minus[index] -= epsilon;
      const numeric = (cnn.forward(plus).logits[target] - cnn.forward(minus).logits[target]) / (2 * epsilon);
      close([gradient[index]], [numeric], 1e-6);
    }
  }
});

test('drawing preprocessing handles blank input and centers resized ink without external libraries', () => {
  assert.ok(prepareDrawing(new Float64Array(56 ** 2), 56).every(value => value === 0));
  const ink = new Float64Array(56 ** 2);
  for (let y = 4; y < 44; y++) for (let x = 3; x < 7; x++) ink[y * 56 + x] = 1;
  const result = prepareDrawing(ink, 56);
  let mass = 0, x = 0, y = 0;
  result.forEach((value, i) => { mass += value; x += i % 28 * value; y += Math.floor(i / 28) * value; });
  assert.ok(mass > 0 && result.every(value => Number.isFinite(value) && value >= 0 && value <= 1));
  assert.ok(Math.abs(x / mass - 13.5) <= .5 && Math.abs(y / mass - 13.5) <= .5);
});

test('softmax stays normalized for extreme logits and malformed tensors are rejected', () => {
  const result = softmax(Float64Array.of(10000, 9999, -10000));
  assert.ok(result.every(Number.isFinite));
  assert.ok(Math.abs(result.reduce((a, b) => a + b) - 1) < 1e-12);
  assert.throws(() => new CNN([4, 8], {}), /Invalid CNN tensor/);
});
