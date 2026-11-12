/* Small, deterministic neural-network engine. No browser or package dependency. */
(function (root) {
  'use strict';

  const DEFAULTS = Object.freeze({
    dataset: 'moons', noise: 0.14, seed: 42, depth: 2, width: 8,
    activation: 'tanh', lr: 0.01, l2: 0.0001,
  });
  const MAX_EPOCHS = 1000;

  function random(seed) {
    let state = seed >>> 0;
    const uniform = () => {
      state = (state + 0x6D2B79F5) >>> 0;
      let n = Math.imul(state ^ (state >>> 15), 1 | state);
      n ^= n + Math.imul(n ^ (n >>> 7), 61 | n);
      return ((n ^ (n >>> 14)) >>> 0) / 4294967296;
    };
    const normal = () => Math.sqrt(-2 * Math.log(Math.max(uniform(), 1e-12)))
      * Math.cos(2 * Math.PI * uniform());
    return { uniform, normal };
  }

  function shuffle(points, rng) {
    for (let i = points.length - 1; i > 0; i--) {
      const j = Math.floor(rng.uniform() * (i + 1));
      [points[i], points[j]] = [points[j], points[i]];
    }
    return points;
  }

  function makeData(config = DEFAULTS) {
    const { dataset = 'moons', noise = 0.14, seed = 42 } = config;
    if (!['moons', 'circles', 'xor'].includes(dataset)) throw new Error('Unknown dataset');
    if (!Number.isFinite(noise) || noise < 0 || noise > 0.5) throw new Error('Invalid noise');
    const rng = random(seed);
    const splits = { train: [], validation: [], test: [] };
    for (let y = 0; y <= 1; y++) {
      const points = [];
      for (let i = 0; i < 300; i++) {
        const angle = rng.uniform() * Math.PI;
        let x1, x2;
        if (dataset === 'moons') {
          x1 = y === 0 ? Math.cos(angle) - 0.5 : 0.5 - Math.cos(angle);
          x2 = y === 0 ? Math.sin(angle) - 0.25 : 0.25 - Math.sin(angle);
        } else if (dataset === 'circles') {
          const radius = y === 0 ? 1 : 0.45;
          x1 = radius * Math.cos(2 * angle);
          x2 = radius * Math.sin(2 * angle);
        } else {
          const sign = rng.uniform() < 0.5 ? -1 : 1;
          x1 = sign * (0.15 + rng.uniform() * 0.85);
          x2 = sign * (y === 0 ? 1 : -1) * (0.15 + rng.uniform() * 0.85);
        }
        points.push({ id: `${dataset}-${y}-${i}`, raw: [x1 + noise * rng.normal(), x2 + noise * rng.normal()], y });
      }
      shuffle(points, rng);
      splits.train.push(...points.slice(0, 180));
      splits.validation.push(...points.slice(180, 240));
      splits.test.push(...points.slice(240));
    }
    const mean = [0, 1].map(k => splits.train.reduce((s, p) => s + p.raw[k], 0) / splits.train.length);
    const std = [0, 1].map(k => Math.sqrt(splits.train.reduce((s, p) => s + (p.raw[k] - mean[k]) ** 2, 0) / splits.train.length));
    const scaler = { mean, std };
    for (const split of Object.values(splits)) {
      shuffle(split, rng);
      for (const p of split) p.x = p.raw.map((v, k) => (v - mean[k]) / std[k]);
    }
    return { ...splits, scaler };
  }

  const sigmoid = z => z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z));
  const bce = (z, y) => Math.max(z, 0) - z * y + Math.log1p(Math.exp(-Math.abs(z)));

  class MLP {
    constructor(sizes, seed = 42, activation = 'tanh') {
      if (sizes.length < 2 || sizes.at(-1) !== 1 || sizes.some(s => !Number.isInteger(s) || s < 1)) {
        throw new Error('Expected positive layer sizes and one binary output');
      }
      if (!['tanh', 'relu'].includes(activation)) throw new Error('Unknown activation');
      this.sizes = sizes;
      this.activation = activation;
      this.updates = 0;
      const rng = random(seed);
      this.layers = sizes.slice(1).map((out, i) => {
        const input = sizes[i];
        const scale = Math.sqrt(activation === 'relu' && i < sizes.length - 2 ? 2 / input : 2 / (input + out));
        return { input, out,
          weights: Float64Array.from({length: input * out}, () => rng.normal() * scale),
          biases: new Float64Array(out),
          mw: new Float64Array(input * out), vw: new Float64Array(input * out),
          mb: new Float64Array(out), vb: new Float64Array(out),
        };
      });
    }

    forward(x) {
      const activations = [x];
      const preactivations = [];
      let logit = 0;
      this.layers.forEach((layer, l) => {
        const previous = activations[l];
        const next = new Float64Array(layer.out);
        const preactivation = new Float64Array(layer.out);
        for (let j = 0; j < layer.out; j++) {
          let z = layer.biases[j];
          for (let k = 0; k < layer.input; k++) z += previous[k] * layer.weights[j * layer.input + k];
          preactivation[j] = z;
          if (l === this.layers.length - 1) { logit = z; next[j] = sigmoid(z); }
          else next[j] = this.activation === 'tanh' ? Math.tanh(z) : Math.max(0, z);
        }
        activations.push(next);
        preactivations.push(preactivation);
      });
      return { activations, preactivations, logit, probability: activations.at(-1)[0] };
    }

    predict(x) { return this.forward(x).probability; }

    inspectNeuron(x, stage, unit) {
      if (!Number.isInteger(stage) || stage < 1 || stage >= this.sizes.length
          || !Number.isInteger(unit) || unit < 0 || unit >= this.sizes[stage]) throw new Error('Invalid neuron');
      const trace = this.forward(x), layer = this.layers[stage - 1];
      const contributions = Array.from(trace.activations[stage - 1], (value, index) => {
        const weight = layer.weights[unit * layer.input + index];
        return { index, value, weight, product: value * weight };
      });
      return {stage, unit, contributions, bias: layer.biases[unit],
        z: trace.preactivations[stage - 1][unit], value: trace.activations[stage][unit],
        activation: stage === this.sizes.length - 1 ? 'sigmoid' : this.activation};
    }

    evaluate(points) {
      let loss = 0, correct = 0;
      const confusion = [[0, 0], [0, 0]];
      for (const p of points) {
        const result = this.forward(p.x);
        const predicted = Number(result.probability >= 0.5);
        loss += bce(result.logit, p.y);
        correct += Number(predicted === p.y);
        confusion[p.y][predicted]++;
      }
      return { loss: loss / points.length, accuracy: correct / points.length, correct, n: points.length, confusion };
    }

    objective(points, l2 = 0) {
      return this.evaluate(points).loss + 0.5 * l2 * this.layers.reduce((s, layer) =>
        s + layer.weights.reduce((total, w) => total + w * w, 0), 0);
    }

    gradients(points, l2 = 0) {
      const gradients = this.layers.map(layer => ({weights: new Float64Array(layer.weights.length), biases: new Float64Array(layer.out)}));
      for (const p of points) {
        const { activations, probability } = this.forward(p.x);
        let delta = [probability - p.y];
        for (let l = this.layers.length - 1; l >= 0; l--) {
          const layer = this.layers[l];
          const previous = activations[l];
          const previousDelta = new Float64Array(layer.input);
          for (let j = 0; j < layer.out; j++) {
            gradients[l].biases[j] += delta[j];
            for (let k = 0; k < layer.input; k++) {
              const index = j * layer.input + k;
              gradients[l].weights[index] += delta[j] * previous[k];
              previousDelta[k] += layer.weights[index] * delta[j];
            }
          }
          if (l > 0) {
            for (let k = 0; k < layer.input; k++) previousDelta[k] *= this.activation === 'tanh'
              ? 1 - previous[k] ** 2 : Number(previous[k] > 0);
          }
          delta = previousDelta;
        }
      }
      gradients.forEach((g, l) => {
        for (let i = 0; i < g.weights.length; i++) g.weights[i] = g.weights[i] / points.length + l2 * this.layers[l].weights[i];
        for (let i = 0; i < g.biases.length; i++) g.biases[i] /= points.length;
      });
      return gradients;
    }

    train(points, lr = 0.01, l2 = 0, capture = false) {
      const gradients = this.gradients(points, l2);
      const update = capture ? {layers: this.layers.map((layer, l) => Object.fromEntries(
        ['weights', 'biases'].map(key => [key, {before: layer[key].slice(), gradient: gradients[l][key]}])
      )), gradientNorm: Math.sqrt(gradients.reduce((sum, g) => sum
        + g.weights.reduce((s, v) => s + v * v, 0) + g.biases.reduce((s, v) => s + v * v, 0), 0))} : null;
      this.updates++;
      const correction1 = 1 - 0.9 ** this.updates;
      const correction2 = 1 - 0.999 ** this.updates;
      this.layers.forEach((layer, l) => {
        for (const [key, moment, variance] of [['weights', 'mw', 'vw'], ['biases', 'mb', 'vb']]) {
          layer[key].forEach((_, i) => {
            const g = gradients[l][key][i];
            layer[moment][i] = 0.9 * layer[moment][i] + 0.1 * g;
            layer[variance][i] = 0.999 * layer[variance][i] + 0.001 * g * g;
            layer[key][i] -= lr * (layer[moment][i] / correction1) / (Math.sqrt(layer[variance][i] / correction2) + 1e-8);
          });
        }
      });
      if (update) this.layers.forEach((layer, l) => {
        for (const key of ['weights', 'biases']) update.layers[l][key].after = layer[key].slice();
      });
      return update;
    }

    parameterCount() { return this.layers.reduce((n, l) => n + l.weights.length + l.biases.length, 0); }
  }

  class Experiment {
    constructor(config = {}) {
      this.config = { ...DEFAULTS, ...config };
      const c = this.config;
      if (!Number.isInteger(c.depth) || c.depth < 0 || c.depth > 3 || ![4, 8, 16].includes(c.width)
        || !Number.isInteger(c.seed) || c.seed < 0 || c.seed > 999999
        || !Number.isFinite(c.lr) || c.lr <= 0 || c.lr > 0.1
        || !Number.isFinite(c.l2) || c.l2 < 0 || c.l2 > 0.1) throw new Error('Invalid training configuration');
      this.data = makeData(c);
      this.model = new MLP([2, ...Array(c.depth).fill(c.width), 1], c.seed + 101, c.activation);
      this.baseline = new MLP([2, 1], c.seed + 911);
      for (let i = 0; i < 400; i++) this.baseline.train(this.data.train, 0.03, 0);
      this.baselineValidation = this.baseline.evaluate(this.data.validation);
      this.epoch = 0;
      this.testResult = null;
      this.history = [this.measure()];
      this.lastUpdate = null;
    }

    measure() {
      return { epoch: this.epoch, train: this.model.evaluate(this.data.train), validation: this.model.evaluate(this.data.validation) };
    }

    step() {
      if (this.testResult) throw new Error('Experiment is finalized');
      if (this.epoch >= MAX_EPOCHS) return false;
      const beforeLoss = this.history.at(-1).train.loss;
      const update = this.model.train(this.data.train, this.config.lr, this.config.l2, true);
      this.epoch++;
      this.history.push(this.measure());
      this.lastUpdate = {...update, epoch: this.epoch, beforeLoss, afterLoss: this.history.at(-1).train.loss};
      return true;
    }

    finalize() {
      if (!this.epoch) throw new Error('Train at least one epoch first');
      if (!this.testResult) this.testResult = { epoch: this.epoch, model: this.model.evaluate(this.data.test), baseline: this.baseline.evaluate(this.data.test) };
      return this.testResult;
    }

    transform(raw) { return raw.map((v, k) => (v - this.data.scaler.mean[k]) / this.data.scaler.std[k]); }
  }

  function activationGrid(model, transform, domain, resolution = 20) {
    if (!Number.isInteger(resolution) || resolution < 2 || resolution > 128) throw new Error('Invalid resolution');
    if (!domain || ![domain.xMin, domain.xMax, domain.yMin, domain.yMax].every(Number.isFinite)
        || domain.xMax <= domain.xMin || domain.yMax <= domain.yMin) throw new Error('Invalid domain');
    const layers = model.sizes.map(size => Array.from({length: size}, () => new Float64Array(resolution ** 2)));
    for (let row = 0; row < resolution; row++) for (let col = 0; col < resolution; col++) {
      const raw = [domain.xMin + (domain.xMax - domain.xMin) * col / (resolution - 1),
        domain.yMax - (domain.yMax - domain.yMin) * row / (resolution - 1)];
      model.forward(transform(raw)).activations.forEach((values, stage) => {
        values.forEach((value, unit) => { layers[stage][unit][row * resolution + col] = value; });
      });
    }
    return {resolution, domain: {...domain}, layers};
  }

  const api = { DEFAULTS, MAX_EPOCHS, random, makeData, MLP, Experiment, activationGrid };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.NeuralLab = api;
})(globalThis);
