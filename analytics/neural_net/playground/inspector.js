/* Linked neuron maps, exact forward contributions and real optimizer telemetry. */
(function (root) {
  'use strict';
  const $ = id => document.getElementById(id);
  const SVG = 'http://www.w3.org/2000/svg';
  const number = value => Math.abs(value) > 0 && Math.abs(value) < 0.001 ? value.toExponential(2) : value.toFixed(3);
  const name = (stage, unit, last) => stage === 0 ? `x${unit + 1}` : stage === last ? '出力' : `H${stage}.${unit + 1}`;
  let signature = '', tiles = [], layers = [], callbacks = {}, cachedMap, cachedModel, mapKey = '', rows = [];

  function colors() {
    const css = getComputedStyle(document.documentElement), get = token => css.getPropertyValue(`--${token}`).trim();
    return {surface: get('surface'), orange: get('series-1'), blue: get('series-2'), ink: get('ink')};
  }
  function mix(a, b, t) {
    const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
    const x = rgb(a), y = rgb(b);
    return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(',')})`;
  }
  function ensureStructure(sizes) {
    if (signature === sizes.join(',')) return;
    signature = sizes.join(','); tiles = []; layers = [];
    $('network').replaceChildren();
    sizes.slice(0, -1).forEach((size, stage) => {
      const layer = document.createElement('div'); layer.className = 'neural-layer'; layer.dataset.stage = stage;
      const title = document.createElement('h3'); title.textContent = stage ? `隠れ層 ${stage} · ${size}個` : '入力 · 2個';
      const board = document.createElement('div'); board.className = 'neuron-board';
      for (let unit = 0; unit < size; unit++) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'neuron-tile';
        button.dataset.stage = stage; button.dataset.unit = unit;
        const canvas = document.createElement('canvas'); canvas.setAttribute('aria-hidden', 'true');
        const label = document.createElement('span'); label.className = 'neuron-label'; label.textContent = name(stage, unit, sizes.length - 1);
        const value = document.createElement('span'); value.className = 'neuron-value';
        button.append(canvas, label, value); board.append(button);
        button.addEventListener('click', () => callbacks.select(stage, unit));
        tiles.push({stage, unit, button, canvas, value});
      }
      layer.append(title, board); $('network').append(layer); layers.push(layer);
    });
  }
  function drawMaps(state, palette, trace) {
    const key = `${state.model.updates}:${Object.values(state.domain).join(',')}`;
    if (cachedModel !== state.model || mapKey !== key) {
      cachedMap = NeuralLab.activationGrid(state.model, raw => state.experiment.transform(raw), state.domain, 20);
      cachedModel = state.model; mapKey = key;
    }
    const size = cachedMap.resolution, domain = state.domain;
    const marker = [(state.raw[0] - domain.xMin) / (domain.xMax - domain.xMin) * (size - 1),
      (domain.yMax - state.raw[1]) / (domain.yMax - domain.yMin) * (size - 1)];
    for (const tile of tiles) {
      tile.canvas.width = tile.canvas.height = size;
      const ctx = tile.canvas.getContext('2d'), values = cachedMap.layers[tile.stage][tile.unit];
      values.forEach((v, i) => {
        ctx.fillStyle = mix(palette.surface, v < 0 ? palette.orange : palette.blue, Math.min(1, Math.abs(v)) * 0.75);
        ctx.fillRect(i % size, Math.floor(i / size), 1, 1);
      });
      ctx.strokeStyle = palette.ink; ctx.lineWidth = 0.7;
      ctx.beginPath(); ctx.moveTo(marker[0] - 1.7, marker[1]); ctx.lineTo(marker[0] + 1.7, marker[1]);
      ctx.moveTo(marker[0], marker[1] - 1.7); ctx.lineTo(marker[0], marker[1] + 1.7); ctx.stroke();
      const future = state.phase >= 0 && tile.stage > state.phase;
      const value = trace.activations[tile.stage][tile.unit];
      tile.value.textContent = future ? '…' : number(value);
      tile.button.setAttribute('aria-label', `${tile.stage ? '隠れ層' + tile.stage : '入力'} ニューロン${tile.unit + 1} · ${future ? '計算待ち' : '値 ' + number(value)}`);
      tile.button.setAttribute('aria-pressed', String(state.selection.stage === tile.stage && state.selection.unit === tile.unit));
      tile.button.title = `${name(tile.stage, tile.unit, state.model.sizes.length - 1)} · 活性値 ${value.toFixed(6)}。選択して計算を見る`;
    }
    layers.forEach((layer, stage) => {
      layer.classList.toggle('phase-active', state.phase === stage);
      layer.classList.toggle('phase-future', state.phase >= 0 && stage > state.phase);
    });
    const last = state.model.sizes.length - 1;
    $('output-neuron').setAttribute('aria-pressed', String(state.selection.stage === last));
    $('output-neuron').classList.toggle('phase-active', state.phase === last);
  }
  function drawConnections(state, palette) {
    const flow = $('model-flow'), origin = flow.getBoundingClientRect(), svg = $('network-links');
    svg.setAttribute('viewBox', `0 0 ${flow.scrollWidth} ${flow.scrollHeight}`);
    const positions = new Map(tiles.map(tile => [`${tile.stage}:${tile.unit}`, tile.button.getBoundingClientRect()]));
    positions.set(`${state.model.sizes.length - 1}:0`, $('output-neuron').getBoundingClientRect());
    const fragment = document.createDocumentFragment();
    state.model.layers.forEach((layer, l) => {
      for (let unit = 0; unit < layer.out; unit++) for (let input = 0; input < layer.input; input++) {
        const source = positions.get(`${l}:${input}`), dest = positions.get(`${l + 1}:${unit}`);
        const x1 = source.right - origin.left, y1 = source.top + source.height / 2 - origin.top;
        const x2 = dest.left - origin.left, y2 = dest.top + dest.height / 2 - origin.top;
        const weight = layer.weights[unit * layer.input + input];
        const incoming = state.selection.stage === l + 1 && state.selection.unit === unit;
        const selected = incoming && input === state.connection;
        const active = state.phase === l + 1;
        const path = document.createElementNS(SVG, 'path');
        path.setAttribute('d', `M${x1},${y1} C${x1 + 28},${y1} ${x2 - 28},${y2} ${x2},${y2}`);
        path.setAttribute('fill', 'none'); path.setAttribute('stroke', weight >= 0 ? palette.blue : palette.orange);
        path.setAttribute('stroke-width', String(Math.min(3.1, 0.45 + Math.abs(weight) * 0.65 + (selected ? 1 : 0))));
        path.setAttribute('stroke-opacity', selected ? '1' : incoming || active ? '0.65' : '0.11');
        path.dataset.stage = l + 1; path.dataset.unit = unit; path.dataset.input = input;
        path.dataset.selected = String(selected);
        if (active) path.classList.add('signal-active');
        fragment.append(path);
      }
    });
    svg.replaceChildren(fragment);
  }
  function ensureRows(count) {
    if (rows.length === count) return;
    rows = []; $('contribution-body').replaceChildren();
    for (let i = 0; i < count; i++) {
      const tr = document.createElement('tr'), cells = Array.from({length: 4}, () => document.createElement('td'));
      const button = document.createElement('button'); button.type = 'button';
      button.addEventListener('click', () => callbacks.connection(i)); cells[0].append(button);
      const wrap = document.createElement('span'); wrap.className = 'contribution-value';
      const bar = document.createElement('i'), value = document.createElement('span'); wrap.append(bar, value); cells[3].append(wrap);
      tr.append(...cells); $('contribution-body').append(tr); rows.push({tr, cells, button, bar, value});
    }
  }
  function drawComputation(state, palette, trace) {
    const {stage, unit} = state.selection, last = state.model.sizes.length - 1;
    const headers = $('contribution-body').closest('table').querySelectorAll('thead th');
    const label = name(stage, unit, last);
    $('neuron-title').textContent = `${label} の計算`;
    $('neuron-value').textContent = `a = ${number(trace.activations[stage][unit])}`;
    if (stage === 0) {
      const {mean, std} = state.experiment.data.scaler;
      $('neuron-equation').textContent = `a = (x − μ) / σ = (${number(state.raw[unit])} − ${number(mean[unit])}) / ${number(std[unit])} = ${number(trace.activations[0][unit])}`;
      ['入力', '元の値 x', '平均 μ', '標準化後 a'].forEach((text, i) => { headers[i].textContent = text; });
      ensureRows(1);
      rows[0].button.textContent = label; rows[0].cells[1].textContent = number(state.raw[unit]);
      rows[0].cells[2].textContent = number(mean[unit]); rows[0].value.textContent = number(trace.activations[0][unit]); rows[0].bar.style.width = '0';
      rows[0].tr.classList.remove('is-selected');
      return;
    }
    ['前の層の入力', '値 a', '重み w', '寄与 a × w'].forEach((text, i) => { headers[i].textContent = text; });
    const node = state.model.inspectNeuron(state.experiment.transform(state.raw), stage, unit);
    const sum = node.contributions.reduce((s, row) => s + row.product, 0);
    $('neuron-equation').textContent = `Σ(a × w) = ${number(sum)}  +  b = ${number(node.bias)}  →  z = ${number(node.z)}  →  ${node.activation}(z) = ${number(node.value)}`;
    ensureRows(node.contributions.length);
    const maximum = Math.max(1e-12, ...node.contributions.map(row => Math.abs(row.product)));
    node.contributions.forEach((row, i) => {
      const item = rows[i]; item.button.textContent = `${name(stage - 1, i, last)} → ${label}`;
      item.cells[1].textContent = number(row.value); item.cells[2].textContent = number(row.weight); item.value.textContent = number(row.product);
      item.bar.style.width = `${Math.abs(row.product) / maximum * 64}px`;
      item.bar.style.background = row.product >= 0 ? palette.blue : palette.orange;
      item.tr.classList.toggle('is-selected', state.connection === i);
      item.button.setAttribute('aria-pressed', String(state.connection === i));
    });
  }
  function drawUpdate(state) {
    const update = state.experiment.lastUpdate, {stage, unit} = state.selection;
    if (!update) {
      $('update-context').textContent = '「1 epoch」で学習360点を使った実際の更新を表示します。';
      for (const id of ['update-loss', 'update-gradient', 'update-weight']) $(id).textContent = '—';
      $('update-gradient-note').textContent = '選んだ重みの勾配（L2込み）';
      $('update-weight-note').textContent = '更新前 → 更新後の重み';
      return;
    }
    const last = state.model.sizes.length - 1, config = state.experiment.config;
    $('update-loss').textContent = `${number(update.beforeLoss)} → ${number(update.afterLoss)}`;
    $('update-context').textContent = `epoch ${update.epoch} · 学習360点の平均勾配 + L2 ${config.l2} · Adam lr ${config.lr} · 全勾配ノルム ${number(update.gradientNorm)}`;
    if (!stage) {
      $('update-gradient').textContent = '入力は固定'; $('update-weight').textContent = '—';
      $('update-gradient-note').textContent = '標準化した入力には学習する重みはありません。';
      $('update-weight-note').textContent = '隠れ層か出力のニューロンを選択すると確認できます。';
      return;
    }
    const parameter = unit * state.model.layers[stage - 1].input + state.connection;
    const values = update.layers[stage - 1].weights;
    $('update-gradient').textContent = `∂J/∂w = ${number(values.gradient[parameter])}`;
    $('update-gradient-note').textContent = `${name(stage - 1, state.connection, last)} → ${name(stage, unit, last)} · L2込みの勾配`;
    $('update-weight').textContent = `${number(values.before[parameter])} → ${number(values.after[parameter])}`;
    $('update-weight-note').textContent = `Δw = ${number(values.after[parameter] - values.before[parameter])} · Adamは勾配の履歴で更新幅を調整`;
  }
  function render(state) {
    callbacks = {select: state.onSelect, connection: state.onConnection};
    ensureStructure(state.model.sizes);
    const palette = colors(), trace = state.model.forward(state.experiment.transform(state.raw));
    drawMaps(state, palette, trace); drawConnections(state, palette); drawComputation(state, palette, trace); drawUpdate(state);
    return trace;
  }
  root.NeuralInspector = {render};
})(globalThis);
