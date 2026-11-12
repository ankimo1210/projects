(function () {
  'use strict';
  const { Experiment, DEFAULTS, MAX_EPOCHS } = NeuralLab;
  const $ = id => document.getElementById(id);
  const percent = n => `${(100 * n).toFixed(1)}%`;
  const decimal = n => n.toFixed(4);
  const settings = ['dataset', 'noise', 'seed', 'depth', 'width', 'activation', 'lr', 'l2'];
  const datasetNames = {moons: '三日月', circles: '同心円', xor: 'XOR'};
  let experiment, running = false, frameId = 0, lastDraw = 0, lastStep = 0;
  let selectedRaw = [0, 0], boundaryView, curveViews = {}, colors;
  let selection = {stage: 3, unit: 0}, connection = 0, pointPinned = false, tracePhase = -1, traceTimer = 0;

  function updateTraceControls() {
    $('trace-play').textContent = traceTimer ? 'Ⅱ 推論を一時停止' : tracePhase >= 0 ? '▶ 推論をもう一度' : '▶ この点の推論を追う';
    $('pin-point').textContent = pointPinned ? '点の固定を解除' : '点を固定';
    $('pin-point').setAttribute('aria-pressed', String(pointPinned));
    const last = experiment ? experiment.model.sizes.length - 1 : 3;
    $('trace-phase').textContent = tracePhase < 0 ? '全層を同時に表示' : `${tracePhase + 1} / ${last + 1} · ${tracePhase === 0 ? '入力を標準化' : tracePhase === last ? '出力の確率を計算' : '隠れ層 ' + tracePhase + ' を計算'}`;
  }
  function cancelTrace(clearPhase = true) {
    clearTimeout(traceTimer); traceTimer = 0;
    if (clearPhase) tracePhase = -1;
    updateTraceControls();
  }

  function palette() {
    const style = getComputedStyle(document.documentElement);
    const get = name => style.getPropertyValue(`--${name}`).trim();
    return { surface: get('surface'), ink: get('ink'), muted: get('ink-3'), grid: get('grid'), orange: get('series-1'), blue: get('series-2'), mono: get('mono') };
  }
  function mix(a, b, fraction) {
    const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
    const first = rgb(a), second = rgb(b);
    return `rgb(${first.map((v, i) => Math.round(v + (second[i] - v) * fraction)).join(',')})`;
  }
  const probabilityColor = p => mix(colors.surface, p < 0.5 ? colors.orange : colors.blue, Math.abs(p - 0.5) * 1.12);

  function canvasContext(id) {
    const canvas = $(id), rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.font = `12px ${colors.mono}`;
    ctx.fillStyle = colors.muted;
    ctx.lineWidth = 1;
    return { canvas, ctx, w: rect.width, h: rect.height };
  }

  function status(text) { $('run-status').textContent = text; }
  function updateButtons() {
    const finished = Boolean(experiment.testResult);
    const maximum = experiment.epoch >= MAX_EPOCHS;
    $('start').disabled = finished || maximum;
    $('step').disabled = finished || maximum || running;
    $('start').textContent = running ? 'Ⅱ 一時停止' : experiment.epoch ? '▶ 学習を再開' : '▶ 学習を開始';
    $('finalize').disabled = !experiment.epoch || finished;
    $('run-status').dataset.running = String(running);
    $('width').disabled = experiment.config.depth === 0;
    $('activation').disabled = experiment.config.depth === 0;
  }
  function stop() {
    running = false;
    cancelAnimationFrame(frameId);
    updateButtons();
  }

  function reset() {
    const seed = Number($('seed').value);
    if (!$('seed').value.trim() || !Number.isInteger(seed) || seed < 0 || seed > 999999) {
      $('seed').value = String(experiment ? experiment.config.seed : DEFAULTS.seed);
      status('seedは0〜999999の整数です');
      return;
    }
    if (experiment) stop();
    cancelTrace();
    const config = Object.fromEntries(settings.map(id => [id, ['dataset', 'activation'].includes(id) ? $(id).value : Number($(id).value)]));
    experiment = new Experiment(config);
    selectedRaw = experiment.data.validation[0].raw.slice();
    selection = {stage: experiment.model.sizes.length - 1, unit: 0}; connection = 0; pointPinned = false;
    $('noise-value').textContent = config.noise.toFixed(2);
    $('test-results').hidden = true;
    $('test-accuracy').textContent = '未評価';
    $('test-accuracy').classList.add('locked');
    $('test-count').textContent = '学習を終えてから開く';
    $('test-status').textContent = '1 epoch以上学習すると評価できます。評価すると、この実行の学習は終了します。';
    $('points').querySelector('[value="test"]').disabled = true;
    if ($('points').value === 'test') $('points').value = 'validation';
    $('finalize').textContent = '学習を終えてテストを評価';
    status('準備完了');
    updateButtons();
    updateTraceControls();
    render();
  }

  function tick(timestamp) {
    if (!running) return;
    const speed = {slow: [100, 1], normal: [30, 2], fast: [30, 10]}[$('speed').value];
    if (timestamp - lastStep >= speed[0]) {
      for (let i = 0; i < speed[1]; i++) experiment.step();
      lastStep = timestamp;
    }
    if (timestamp - lastDraw >= 100 || experiment.epoch >= MAX_EPOCHS) {
      render();
      lastDraw = timestamp;
    }
    if (experiment.epoch >= MAX_EPOCHS) {
      stop(); status('1,000 epochに到達'); return;
    }
    frameId = requestAnimationFrame(tick);
  }

  function renderMetrics() {
    const current = experiment.history.at(-1);
    $('epoch').textContent = experiment.epoch.toLocaleString('en-US');
    $('progress').value = experiment.epoch;
    $('train-loss').textContent = decimal(current.train.loss);
    $('val-accuracy').textContent = percent(current.validation.accuracy);
    $('val-count').textContent = `${current.validation.correct} / 120点`;
    $('baseline-accuracy').textContent = percent(experiment.baselineValidation.accuracy);
    const difference = 100 * (current.validation.accuracy - experiment.baselineValidation.accuracy);
    $('comparison').textContent = `線形モデルとの差：${difference > 0 ? '+' : ''}${difference.toFixed(1)}ポイント（検証120点）。`;
    $('architecture').textContent = `${experiment.model.sizes.join(' → ')} · ${experiment.config.depth ? experiment.config.activation : 'sigmoid出力のみ'}`;
    $('parameters').textContent = `${experiment.model.parameterCount()} params`;
    updateButtons();
  }

  function drawPreview() {
    if (!$('settings-panel').open || $('playground-view').hidden) return;
    const {ctx, w, h} = canvasContext('dataset-preview');
    const points = experiment.data.train;
    const max = Math.max(1.5, ...points.flatMap(p => p.raw.map(Math.abs)));
    for (const p of points.slice(0, 140)) {
      ctx.fillStyle = p.y ? colors.blue : colors.orange;
      ctx.beginPath(); ctx.arc(w / 2 + p.raw[0] * (w - 12) / (2 * max), h / 2 - p.raw[1] * (h - 8) / (2 * max), 1.7, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawBoundary() {
    const { ctx, w, h } = canvasContext('boundary');
    const area = {left: 38, top: 12, width: w - 50, height: h - 46};
    const pool = [...experiment.data.train, ...experiment.data.validation];
    // A final test never influences the axes used during model selection.
    if (experiment.testResult) pool.push(...experiment.data.test);
    const maxX = Math.max(1.55, ...pool.map(p => Math.abs(p.raw[0])));
    const maxY = Math.max(1.15, ...pool.map(p => Math.abs(p.raw[1])));
    const unit = Math.max(2.16 * maxX / area.width, 2.16 * maxY / area.height);
    const xMax = unit * area.width / 2, yMax = unit * area.height / 2;
    const rawAt = (x, y) => [(x - area.left - area.width / 2) * unit, (area.top + area.height / 2 - y) * unit];
    const pos = raw => [area.left + area.width / 2 + raw[0] / unit, area.top + area.height / 2 - raw[1] / unit];
    boundaryView = { ...area, rawAt, pos, domain: {xMin: -xMax, xMax, yMin: -yMax, yMax} };
    const columns = 58, rows = 48, dx = area.width / columns, dy = area.height / rows;
    const probabilities = Array.from({length: rows + 1}, (_, y) => Array.from({length: columns + 1}, (_, x) =>
      experiment.model.predict(experiment.transform(rawAt(area.left + x * dx, area.top + y * dy)))));
    for (let y = 0; y < rows; y++) for (let x = 0; x < columns; x++) {
      const corners = [probabilities[y][x], probabilities[y][x + 1], probabilities[y + 1][x + 1], probabilities[y + 1][x]];
      ctx.fillStyle = probabilityColor(corners.reduce((a, b) => a + b, 0) / 4);
      ctx.fillRect(area.left + x * dx, area.top + y * dy, dx + 0.6, dy + 0.6);
      const vertices = [[0, 0], [1, 0], [1, 1], [0, 1]], intersections = [];
      for (let edge = 0; edge < 4; edge++) {
        const next = (edge + 1) % 4, a = corners[edge], b = corners[next];
        if ((a >= 0.5) !== (b >= 0.5)) {
          const t = (0.5 - a) / (b - a);
          intersections.push([area.left + (x + vertices[edge][0] + t * (vertices[next][0] - vertices[edge][0])) * dx,
            area.top + (y + vertices[edge][1] + t * (vertices[next][1] - vertices[edge][1])) * dy]);
        }
      }
      ctx.strokeStyle = colors.ink; ctx.lineWidth = 1.2;
      for (let i = 0; i + 1 < intersections.length; i += 2) {
        ctx.beginPath(); ctx.moveTo(...intersections[i]); ctx.lineTo(...intersections[i + 1]); ctx.stroke();
      }
    }
    ctx.strokeStyle = colors.grid; ctx.lineWidth = 0.6;
    ctx.fillStyle = colors.muted; ctx.textAlign = 'center';
    for (let value = Math.ceil(-xMax); value <= xMax; value++) {
      const x = pos([value, 0])[0];
      ctx.beginPath(); ctx.moveTo(x, area.top); ctx.lineTo(x, area.top + area.height); ctx.stroke();
      ctx.fillText(String(value), x, h - 16);
    }
    ctx.textAlign = 'right';
    for (let value = Math.ceil(-yMax); value <= yMax; value++) {
      const y = pos([0, value])[1];
      ctx.beginPath(); ctx.moveTo(area.left, y); ctx.lineTo(area.left + area.width, y); ctx.stroke();
      ctx.fillText(String(value), area.left - 8, y + 4);
    }
    ctx.fillText('x₁', w - 2, h - 16); ctx.fillText('x₂', 25, 12);
    const points = experiment.data[$('points').value];
    ctx.save(); ctx.beginPath(); ctx.rect(area.left, area.top, area.width, area.height); ctx.clip();
    for (const p of points) {
      const [x, y] = pos(p.raw), incorrect = Number(experiment.model.predict(p.x) >= 0.5) !== p.y;
      ctx.fillStyle = p.y ? colors.blue : colors.orange;
      ctx.strokeStyle = incorrect ? colors.ink : colors.surface;
      ctx.lineWidth = incorrect ? 1.8 : 0.9;
      ctx.beginPath();
      if (p.y) { ctx.moveTo(x, y - 4); ctx.lineTo(x + 4, y); ctx.lineTo(x, y + 4); ctx.lineTo(x - 4, y); ctx.closePath(); }
      else ctx.arc(x, y, 3.4, 0, 2 * Math.PI);
      ctx.fill(); ctx.stroke();
    }
    ctx.restore();
    drawProbe();
  }

  function drawProbe() {
    const rect = $('boundary').getBoundingClientRect();
    $('probe-overlay').setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
    const [x, y] = boundaryView.pos(selectedRaw);
    $('probe-marker').setAttribute('d', `M ${x - 6} ${y} h 12 M ${x} ${y - 6} v 12`);
  }

  function probeDescription(probability) {
    return `x₁ ${selectedRaw[0].toFixed(2)} · x₂ ${selectedRaw[1].toFixed(2)}\nP(クラス1) ${probability.toFixed(3)} · 予測 ${Number(probability >= 0.5)}`;
  }

  function drawNetwork() {
    if (!boundaryView) return;
    const trace = NeuralInspector.render({experiment, model: experiment.model, raw: selectedRaw,
      domain: boundaryView.domain, selection, connection, phase: tracePhase,
      onSelect: (stage, unit) => {
        const wasTracing = tracePhase >= 0;
        cancelTrace(false); if (wasTracing) tracePhase = stage;
        selection = {stage, unit}; connection = 0; updateTraceControls(); drawNetwork();
      },
      onConnection: input => { connection = input; drawNetwork(); }});
    const probability = trace.probability, last = experiment.model.sizes.length - 1;
    const revealed = tracePhase < 0 || tracePhase === last;
    $('probe-probability').textContent = revealed ? probability.toFixed(3) : '…';
    $('prediction-bar').style.width = revealed ? `${probability * 100}%` : '0%';
    const sample = experiment.data[$('points').value].find(p => p.raw.every((value, k) => Math.abs(value - selectedRaw[k]) < 1e-10));
    $('probe').textContent = `${pointPinned ? '固定' : '観察'} x₁=${selectedRaw[0].toFixed(2)} · x₂=${selectedRaw[1].toFixed(2)}${sample ? ' · 正解' + sample.y : ''}${revealed ? ' → P(1)=' + probability.toFixed(3) : ' · 層ごとに計算中'}`;
    if (!$('boundary-tip').hidden) $('boundary-tip').textContent = probeDescription(probability);
  }

  function drawCurve(id, metric) {
    const {ctx, w, h} = canvasContext(id);
    const history = experiment.history;
    const left = 44, top = 15, width = w - 58, height = h - 48;
    const maxEpoch = Math.max(100, Math.ceil(experiment.epoch / 100) * 100);
    const maxY = metric === 'loss' ? Math.max(0.2, Math.ceil(Math.max(...history.flatMap(row => [row.train.loss, row.validation.loss])) * 5) / 5) : 1;
    const x = epoch => left + epoch * width / maxEpoch;
    const y = value => top + height - value * height / maxY;
    curveViews[id] = {left, top, width, height, maxEpoch, metric};
    ctx.textAlign = 'right'; ctx.fillStyle = colors.muted; ctx.strokeStyle = colors.grid; ctx.lineWidth = 0.6;
    for (let i = 0; i <= 4; i++) {
      const value = maxY * i / 4, posY = y(value);
      ctx.beginPath(); ctx.moveTo(left, posY); ctx.lineTo(left + width, posY); ctx.stroke();
      ctx.fillText(metric === 'accuracy' ? `${Math.round(value * 100)}%` : value.toFixed(maxY < 1 ? 2 : 1), left - 8, posY + 4);
    }
    ctx.textAlign = 'center';
    for (let i = 0; i <= 4; i++) {
      const epoch = maxEpoch * i / 4;
      ctx.fillText(String(epoch), x(epoch), h - 15);
    }
    if (metric === 'accuracy') {
      ctx.strokeStyle = colors.muted; ctx.lineWidth = 1.2; ctx.setLineDash([2, 4]);
      const baseline = y(experiment.baselineValidation.accuracy);
      ctx.beginPath(); ctx.moveTo(left, baseline); ctx.lineTo(left + width, baseline); ctx.stroke();
    }
    for (const [split, color, dash] of [['train', colors.orange, []], ['validation', colors.blue, [6, 4]]]) {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash(dash); ctx.beginPath();
      history.forEach((row, i) => { const args = [x(row.epoch), y(row[split][metric])]; if (i) ctx.lineTo(...args); else ctx.moveTo(...args); });
      ctx.stroke(); ctx.setLineDash([]);
      const last = history.at(-1); ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(x(last.epoch), y(last[split][metric]), 2.5, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = colors.muted; ctx.textAlign = 'right'; ctx.fillText('epoch', w - 2, h - 1);
  }

  function render() {
    if ($('playground-view').hidden) return;
    colors = palette();
    renderMetrics(); drawPreview(); drawBoundary(); drawNetwork();
    drawCurve('loss-chart', 'loss'); drawCurve('accuracy-chart', 'accuracy');
  }

  function showTip(id, canvas, event, content) {
    const tip = $(id), rect = canvas.getBoundingClientRect();
    tip.textContent = content; tip.hidden = false;
    tip.style.left = `${Math.max(0, Math.min(event.clientX - rect.left + 10, rect.width - tip.offsetWidth - 2))}px`;
    tip.style.top = `${Math.max(0, event.clientY - rect.top - tip.offsetHeight - 10)}px`;
  }
  function selectPoint(event, pin = false) {
    if (!boundaryView) return;
    const canvas = $('boundary'), rect = canvas.getBoundingClientRect(), v = boundaryView;
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    if (x < v.left || x > v.left + v.width || y < v.top || y > v.top + v.height) { $('boundary-tip').hidden = true; return; }
    selectedRaw = v.rawAt(x, y);
    if (pin) {
      const nearby = experiment.data[$('points').value].find(p => {
        const position = v.pos(p.raw); return Math.hypot(position[0] - x, position[1] - y) < 9;
      });
      if (nearby) selectedRaw = nearby.raw.slice();
      cancelTrace(); pointPinned = true; updateTraceControls();
    }
    const p = experiment.model.predict(experiment.transform(selectedRaw));
    showTip('boundary-tip', canvas, event, probeDescription(p));
    drawProbe(); drawNetwork();
  }
  $('boundary').addEventListener('pointermove', event => { if (!pointPinned) selectPoint(event); });
  $('boundary').addEventListener('click', event => selectPoint(event, true));
  $('boundary').addEventListener('keydown', event => {
    if (event.key === ' ') { event.preventDefault(); $('pin-point').click(); return; }
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key) || !boundaryView) return;
    event.preventDefault(); cancelTrace(); pointPinned = true;
    const step = event.shiftKey ? 0.2 : 0.08, domain = boundaryView.domain;
    selectedRaw[0] = Math.max(domain.xMin, Math.min(domain.xMax, selectedRaw[0] + (event.key === 'ArrowRight' ? step : event.key === 'ArrowLeft' ? -step : 0)));
    selectedRaw[1] = Math.max(domain.yMin, Math.min(domain.yMax, selectedRaw[1] + (event.key === 'ArrowUp' ? step : event.key === 'ArrowDown' ? -step : 0)));
    updateTraceControls(); drawProbe(); drawNetwork();
  });
  $('boundary').addEventListener('pointerleave', () => { $('boundary-tip').hidden = true; });
  for (const [id, tipId] of [['loss-chart', 'loss-tip'], ['accuracy-chart', 'accuracy-tip']]) {
    $(id).addEventListener('pointermove', event => {
      const view = curveViews[id], canvas = $(id), rect = canvas.getBoundingClientRect();
      const epoch = Math.max(0, Math.min(experiment.epoch, Math.round((event.clientX - rect.left - view.left) * view.maxEpoch / view.width)));
      const row = experiment.history[epoch], format = view.metric === 'accuracy' ? percent : decimal;
      showTip(tipId, canvas, event, `epoch ${epoch}\n学習 ${format(row.train[view.metric])}\n検証 ${format(row.validation[view.metric])}`);
    });
    $(id).addEventListener('pointerleave', () => { $(tipId).hidden = true; });
  }

  settings.forEach(id => $(id).addEventListener('change', reset));
  $('noise').addEventListener('input', () => { $('noise-value').textContent = Number($('noise').value).toFixed(2); });
  $('reset').addEventListener('click', reset);
  $('points').addEventListener('change', () => {
    cancelTrace(); selectedRaw = experiment.data[$('points').value][0].raw.slice(); pointPinned = false;
    updateTraceControls(); drawBoundary(); drawNetwork();
  });
  $('start').addEventListener('click', () => {
    cancelTrace();
    if (running) { stop(); status('一時停止'); render(); }
    else { running = true; lastStep = 0; lastDraw = 0; status('学習中'); updateButtons(); frameId = requestAnimationFrame(tick); }
  });
  $('step').addEventListener('click', () => {
    cancelTrace();
    experiment.step(); status(experiment.epoch >= MAX_EPOCHS ? '1,000 epochに到達' : '1 epoch更新'); render();
  });
  $('finalize').addEventListener('click', () => {
    stop(); cancelTrace();
    const result = experiment.finalize();
    $('test-results').hidden = false;
    $('test-accuracy').textContent = percent(result.model.accuracy);
    $('test-accuracy').classList.remove('locked');
    $('test-count').textContent = `${result.model.correct} / 120点 · epoch ${result.epoch}`;
    $('test-status').textContent = `epoch ${result.epoch}の重みを固定して評価しました。新しい実験はリセットか設定変更で開始できます。`;
    $('test-comparison').textContent = `ニューラルネット ${percent(result.model.accuracy)} / 線形モデル ${percent(result.baseline.accuracy)}（同じテスト120点）`;
    $('test-loss').textContent = `テストBCE：${decimal(result.model.loss)}`;
    for (let row = 0; row < 2; row++) for (let col = 0; col < 2; col++) $(`cm-${row}${col}`).textContent = result.model.confusion[row][col];
    $('points').querySelector('[value="test"]').disabled = false;
    $('points').value = 'test';
    selectedRaw = experiment.data.test[0].raw.slice();
    $('finalize').textContent = 'テスト評価済み';
    status('最終評価済み'); render();
  });
  $('output-neuron').addEventListener('click', () => {
    const wasTracing = tracePhase >= 0; cancelTrace(false);
    selection = {stage: experiment.model.sizes.length - 1, unit: 0}; connection = 0;
    if (wasTracing) tracePhase = selection.stage;
    updateTraceControls(); drawNetwork();
  });
  $('pin-point').addEventListener('click', () => { cancelTrace(); pointPinned = !pointPinned; updateTraceControls(); drawNetwork(); });
  function advanceInference() {
    tracePhase++;
    selection = {stage: tracePhase, unit: 0}; connection = 0;
    updateTraceControls(); drawNetwork();
  }
  $('trace-next').addEventListener('click', () => {
    stop(); cancelTrace(false); pointPinned = true;
    status('推論を観察（重み固定）');
    if (tracePhase >= experiment.model.sizes.length - 1) tracePhase = -1;
    advanceInference();
    render();
  });
  $('trace-play').addEventListener('click', () => {
    if (traceTimer) { cancelTrace(false); status('推論を一時停止（重み固定）'); drawNetwork(); return; }
    stop(); cancelTrace(); pointPinned = true; tracePhase = -1;
    status('推論を観察（重み固定）');
    advanceInference();
    render();
    const advance = () => {
      if (tracePhase < experiment.model.sizes.length - 1) {
        advanceInference(); traceTimer = setTimeout(advance, 950);
      } else { traceTimer = 0; status('推論完了（重み固定）'); updateTraceControls(); }
    };
    traceTimer = setTimeout(advance, 950); updateTraceControls();
  });
  $('theme').addEventListener('click', () => {
    const dark = document.documentElement.dataset.theme !== 'dark';
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    $('theme').textContent = dark ? 'ライト表示' : 'ダーク表示';
    $('theme').setAttribute('aria-pressed', String(dark));
    render();
    window.dispatchEvent(new Event('lab-theme-change'));
  });
  $('export').addEventListener('click', () => {
    const snapshot = {schemaVersion: 1, source: 'Seeded synthetic data generated by engine.js', config: experiment.config,
      datasetName: datasetNames[experiment.config.dataset], split: {train: 360, validation: 120, test: 120}, scaler: experiment.data.scaler,
      method: {optimizer: 'Adam', batchSize: 360, threshold: 0.5, loss: 'Mean BCE excluding L2', baseline: {sizes: [2, 1], epochs: 400, lr: 0.03, l2: 0}},
      history: experiment.history, baselineValidation: experiment.baselineValidation, finalTest: experiment.testResult};
    const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url;
    link.download = `neural-lab-${experiment.config.dataset}-seed${experiment.config.seed}-epoch${experiment.epoch}.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('source-code').textContent = $('engine-source').textContent.trim();
  const narrowScreen = matchMedia('(max-width: 900px)');
  $('settings-panel').open = !narrowScreen.matches;
  narrowScreen.addEventListener('change', event => { $('settings-panel').open = !event.matches; });
  $('settings-panel').addEventListener('toggle', () => { if ($('settings-panel').open) drawPreview(); });
  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 100); });
  window.addEventListener('lab-mode-change', () => {
    if ($('playground-view').hidden && running) { stop(); status('一時停止（比較画面へ移動）'); }
    if ($('playground-view').hidden) cancelTrace();
    render();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden && (running || traceTimer)) { stop(); cancelTrace(); status('一時停止（タブが非表示）'); render(); } });
  reset();
})();
