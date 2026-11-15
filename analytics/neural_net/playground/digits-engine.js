/* Independent, dependency-free CNN forward/backward math for the MNIST lab. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DigitMath = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  function bytes(encoded) {
    if (typeof Buffer !== 'undefined') return Uint8Array.from(Buffer.from(encoded, 'base64'));
    return Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
  }
  function floats(encoded) {
    const data = bytes(encoded), view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    if (data.length % 4) throw new Error('Invalid float32 byte length');
    return Float64Array.from({length: data.length / 4}, (_, i) => view.getFloat32(i * 4, true));
  }
  function convolve(input, size, inChannels, outChannels, kernel, weights, biases) {
    const side = size - kernel + 1, z = new Float64Array(outChannels * side * side), a = new Float64Array(z.length);
    for (let c = 0; c < outChannels; c++) for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) {
      let value = biases[c];
      for (let p = 0; p < inChannels; p++) for (let ky = 0; ky < kernel; ky++) for (let kx = 0; kx < kernel; kx++)
        value += input[(p * size + y + ky) * size + x + kx] * weights[((c * inChannels + p) * kernel + ky) * kernel + kx];
      const index = (c * side + y) * side + x; z[index] = value; a[index] = Math.max(0, value);
    }
    return {z, a, side};
  }
  function pool(input, size, channels) {
    const side = Math.floor(size / 2), a = new Float64Array(channels * side * side), switches = new Int32Array(a.length);
    for (let c = 0; c < channels; c++) for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) {
      let winner = (c * size + y * 2) * size + x * 2;
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
        const i = (c * size + y * 2 + dy) * size + x * 2 + dx;
        if (input[i] > input[winner]) winner = i;
      }
      const index = (c * side + y) * side + x; a[index] = input[winner]; switches[index] = winner;
    }
    return {a, switches, side};
  }
  function softmax(logits) {
    const top = Math.max(...logits), exponential = logits.map(value => Math.exp(value - top));
    const denominator = exponential.reduce((a, b) => a + b, 0);
    return exponential.map(value => value / denominator);
  }
  function unpool(gradient, pooled, length) {
    const result = new Float64Array(length);
    gradient.forEach((value, i) => { result[pooled.switches[i]] += value; });
    return result;
  }
  function convolutionGradient(gradient, activation, inputSize, inChannels, outChannels, kernel, weights) {
    const side = inputSize - kernel + 1, result = new Float64Array(inputSize * inputSize * inChannels);
    for (let c = 0; c < outChannels; c++) for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) {
      const index = (c * side + y) * side + x;
      if (activation.z[index] <= 0 || gradient[index] === 0) continue;
      for (let p = 0; p < inChannels; p++) for (let ky = 0; ky < kernel; ky++) for (let kx = 0; kx < kernel; kx++)
        result[(p * inputSize + y + ky) * inputSize + x + kx] += gradient[index] * weights[((c * inChannels + p) * kernel + ky) * kernel + kx];
    }
    return result;
  }
  class CNN {
    constructor(channels, packed) {
      this.channels = channels.slice(); this.weights = {};
      for (const [key, value] of Object.entries(packed)) this.weights[key] = floats(value);
      const [c1, c2] = channels;
      const lengths = {'conv1.weight': c1 * 25, 'conv1.bias': c1, 'conv2.weight': c2 * c1 * 9, 'conv2.bias': c2, 'head.weight': 10 * c2 * 25, 'head.bias': 10};
      for (const [key, length] of Object.entries(lengths))
        if (!this.weights[key] || this.weights[key].length !== length) throw new Error(`Invalid CNN tensor: ${key}`);
    }
    forward(pixels) {
      if (pixels.length !== 784 || Array.from(pixels).some(value => !Number.isFinite(value))) throw new Error('Expected 28 × 28 finite pixels');
      const [c1, c2] = this.channels, w = this.weights;
      const first = convolve(pixels, 28, 1, c1, 5, w['conv1.weight'], w['conv1.bias']);
      const pooledFirst = pool(first.a, 24, c1);
      const second = convolve(pooledFirst.a, 12, c1, c2, 3, w['conv2.weight'], w['conv2.bias']);
      const pooledSecond = pool(second.a, 10, c2), features = pooledSecond.a;
      const logits = new Float64Array(10);
      for (let c = 0; c < 10; c++) {
        logits[c] = w['head.bias'][c];
        for (let i = 0; i < features.length; i++) logits[c] += features[i] * w['head.weight'][c * features.length + i];
      }
      const probabilities = softmax(logits), prediction = probabilities.indexOf(Math.max(...probabilities));
      return {input: Float64Array.from(pixels), first, pooledFirst, second, pooledSecond, logits, probabilities, prediction};
    }
    inputGradient(frame, target) {
      if (!Number.isInteger(target) || target < 0 || target > 9) throw new Error('Expected a digit class');
      const [c1, c2] = this.channels, w = this.weights, length = frame.pooledSecond.a.length;
      const head = w['head.weight'].slice(target * length, (target + 1) * length);
      const secondGradient = unpool(head, frame.pooledSecond, frame.second.a.length);
      const pooledFirstGradient = convolutionGradient(secondGradient, frame.second, 12, c1, c2, 3, w['conv2.weight']);
      const firstGradient = unpool(pooledFirstGradient, frame.pooledFirst, frame.first.a.length);
      return convolutionGradient(firstGradient, frame.first, 28, 1, c1, 5, w['conv1.weight']);
    }
    inspect(frame, channel, row, col) {
      if (!Number.isInteger(channel) || channel < 0 || channel >= this.channels[0] || !Number.isInteger(row) || !Number.isInteger(col) || row < 0 || row > 23 || col < 0 || col > 23) throw new Error('Invalid convolution cell');
      const terms = [];
      for (let y = 0; y < 5; y++) for (let x = 0; x < 5; x++) {
        const value = frame.input[(row + y) * 28 + col + x], weight = this.weights['conv1.weight'][channel * 25 + y * 5 + x];
        terms.push({value, weight, product: value * weight});
      }
      const bias = this.weights['conv1.bias'][channel], z = terms.reduce((sum, term) => sum + term.product, bias);
      return {terms, bias, z, value: Math.max(0, z)};
    }
    contributions(frame, target) {
      const features = frame.pooledSecond.a, weights = this.weights['head.weight'];
      const values = Array.from(features, (value, index) => ({index, channel: Math.floor(index / 25), row: Math.floor(index % 25 / 5), col: index % 5, value, weight: weights[target * features.length + index], product: value * weights[target * features.length + index]}));
      return {values, bias: this.weights['head.bias'][target], logit: frame.logits[target]};
    }
  }
  function prepareDrawing(pixels, side) {
    if (pixels.length !== side * side || !Number.isInteger(side) || side < 2) throw new Error('Invalid drawing');
    let left = side, top = side, right = -1, bottom = -1;
    for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) if (pixels[y * side + x] > 0.05) {
      left = Math.min(left, x); right = Math.max(right, x); top = Math.min(top, y); bottom = Math.max(bottom, y);
    }
    const result = new Float64Array(784);
    if (right < left) return result;
    const width = right - left + 1, height = bottom - top + 1, scale = 20 / Math.max(width, height);
    const targetWidth = Math.max(1, Math.round(width * scale)), targetHeight = Math.max(1, Math.round(height * scale));
    const offsetX = Math.floor((28 - targetWidth) / 2), offsetY = Math.floor((28 - targetHeight) / 2);
    // Area sampling preserves thin pen strokes when shrinking the drawing.
    for (let y = 0; y < targetHeight; y++) for (let x = 0; x < targetWidth; x++) {
      const x0 = left + x * width / targetWidth, x1 = left + (x + 1) * width / targetWidth;
      const y0 = top + y * height / targetHeight, y1 = top + (y + 1) * height / targetHeight;
      let sum = 0;
      for (let py = Math.floor(y0); py < Math.ceil(y1); py++) for (let px = Math.floor(x0); px < Math.ceil(x1); px++)
        sum += pixels[py * side + px] * Math.max(0, Math.min(x1, px + 1) - Math.max(x0, px)) * Math.max(0, Math.min(y1, py + 1) - Math.max(y0, py));
      result[(offsetY + y) * 28 + offsetX + x] = sum / ((x1 - x0) * (y1 - y0));
    }
    let mass = 0, centerX = 0, centerY = 0;
    result.forEach((value, i) => { mass += value; centerX += i % 28 * value; centerY += Math.floor(i / 28) * value; });
    if (mass === 0) return result;
    const dx = Math.round(13.5 - centerX / mass), dy = Math.round(13.5 - centerY / mass), centered = new Float64Array(784);
    for (let y = 0; y < 28; y++) for (let x = 0; x < 28; x++) if (y + dy >= 0 && y + dy < 28 && x + dx >= 0 && x + dx < 28)
      centered[(y + dy) * 28 + x + dx] = result[y * 28 + x];
    return centered;
  }
  return {CNN, bytes, floats, softmax, prepareDrawing};
});
