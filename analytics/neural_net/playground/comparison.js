/* Display local, reviewed PyTorch measurements. This view performs no training. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const snapshot = JSON.parse($('scale-data').textContent);
  const pct = value => `${(value * 100).toFixed(2)}%`;
  const mean = values => values.reduce((a, b) => a + b, 0) / values.length;
  const compact = value => value >= 1e6 ? `${(value / 1e6).toFixed(2)}M` : `${(value / 1000).toFixed(2)}K`;
  const classNames = ['Tシャツ', 'ズボン', 'プルオーバー', 'ドレス', 'コート', 'サンダル', 'シャツ', 'スニーカー', 'バッグ', 'ブーツ'];
  const shortName = model => model.hidden.length ? `${model.hidden[0]}×${model.hidden.length}` : 'Linear';
  let colors, capacityMarks = [], costMarks = [], learningMarks = [], lossMarks = [], confusionView;

  function switchMode(mode) {
    for (const value of ['digits', 'playground', 'comparison']) {
      $(`mode-${value}`).setAttribute('aria-selected', String(mode === value));
      $(`${value}-view`).hidden = mode !== value;
    }
    window.dispatchEvent(new Event('lab-mode-change'));
  }
  const modes = ['digits', 'playground', 'comparison'];
  for (const mode of modes) {
    $(`mode-${mode}`).addEventListener('click', () => switchMode(mode));
    $(`mode-${mode}`).addEventListener('keydown', event => {
      if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
        const other = modes[(modes.indexOf(mode) + (event.key === 'ArrowRight' ? 1 : modes.length - 1)) % modes.length];
        switchMode(other); $(`mode-${other}`).focus(); event.preventDefault();
      }
    });
  }
  if (!snapshot) { $('scale-empty').hidden = false; $('scale-evidence').hidden = true; return; }
  const summaries = new Map(snapshot.summary.map(row => [row.model_id, row]));
  const modelIndex = id => snapshot.models.findIndex(model => model.id === id);
  const modelRuns = id => snapshot.runs.filter(run => run.model_id === id);

  function palette() {
    const style = getComputedStyle(document.documentElement), get = name => style.getPropertyValue(`--${name}`).trim();
    return {ink: get('ink'), muted: get('ink-3'), grid: get('grid'), surface: get('surface'),
      orange: get('series-1'), blue: get('series-2'), mono: get('mono'),
      models: snapshot.models.map((_, i) => get(`cat-${i + 1}`))};
  }
  function mix(a, b, amount) {
    const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
    const before = rgb(a), after = rgb(b);
    return `rgb(${before.map((v, i) => Math.round(v + (after[i] - v) * amount)).join(',')})`;
  }
  function context(id) {
    const canvas = $(id), rect = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width * dpr); canvas.height = Math.round(rect.height * dpr);
    const ctx = canvas.getContext('2d'); ctx.scale(dpr, dpr);
    ctx.font = `12px ${colors.mono}`;
    return {canvas, ctx, w: rect.width, h: rect.height, left: 50, top: 22, width: rect.width - 72, height: rect.height - 60};
  }
  function grid(view, ticks, map, format) {
    const {ctx, left, top, width, height} = view;
    ctx.strokeStyle = colors.grid; ctx.lineWidth = 0.7;
    ctx.fillStyle = colors.muted; ctx.textAlign = 'right';
    for (const value of ticks) {
      const y = map(value);
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + width, y); ctx.stroke();
      ctx.fillText(format(value), left - 8, y + 4);
    }
    ctx.strokeStyle = colors.grid; ctx.strokeRect(left, top, width, height);
  }
  function line(ctx, points, color, dash = []) {
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash(dash); ctx.beginPath();
    points.forEach((p, i) => { if (i) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); });
    ctx.stroke(); ctx.setLineDash([]);
    for (const p of points) { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }
  function tooltip(canvasId, tipId, event, text) {
    const canvas = $(canvasId), tip = $(tipId), rect = canvas.getBoundingClientRect();
    if (!text) { tip.hidden = true; return; }
    tip.textContent = text; tip.hidden = false;
    tip.style.left = `${Math.max(0, Math.min(event.clientX - rect.left + 8, rect.width - tip.offsetWidth))}px`;
    tip.style.top = `${Math.max(0, event.clientY - rect.top - tip.offsetHeight - 8)}px`;
  }
  function bindMarks(canvasId, tipId, marks) {
    $(canvasId).addEventListener('pointermove', event => {
      const rect = $(canvasId).getBoundingClientRect(), x = event.clientX - rect.left, y = event.clientY - rect.top;
      const nearest = marks().map(mark => ({mark, distance: Math.hypot(mark.x - x, mark.y - y)})).sort((a, b) => a.distance - b.distance)[0];
      tooltip(canvasId, tipId, event, nearest && nearest.distance < 28 ? nearest.mark.text : null);
    });
    $(canvasId).addEventListener('pointerleave', () => { $(tipId).hidden = true; });
  }

  function drawPreviews() {
    snapshot.data.previews.forEach((image, i) => {
      const canvas = $(`scale-image-${i}`), ctx = canvas.getContext('2d');
      canvas.width = canvas.height = 28;
      image.pixels.forEach((pixel, k) => { ctx.fillStyle = mix(colors.surface, colors.ink, pixel / 255); ctx.fillRect(k % 28, Math.floor(k / 28), 1, 1); });
    });
  }
  function drawCapacity() {
    const view = context('scale-capacity'), {ctx, w, h, left, top, width, height} = view;
    const rows = snapshot.summary, models = snapshot.models;
    const xmin = Math.floor(Math.log10(models[0].parameters) * 2) / 2;
    const xmax = Math.ceil(Math.log10(models.at(-1).parameters) * 2) / 2;
    const ymin = Math.floor(Math.min(...rows.map(r => r.test_accuracy_mean - r.test_accuracy_std)) * 20) / 20;
    const ymax = Math.max(ymin + 0.05, Math.ceil(Math.max(...rows.map(r => r.test_accuracy_mean + r.test_accuracy_std)) * 20) / 20);
    const x = p => left + (Math.log10(p) - xmin) * width / (xmax - xmin);
    const y = a => top + height - (a - ymin) * height / (ymax - ymin);
    grid(view, Array.from({length: 5}, (_, i) => ymin + i * (ymax - ymin) / 4), y, a => `${(a * 100).toFixed(1)}%`);
    ctx.textAlign = 'center';
    for (let exponent = Math.ceil(xmin); exponent <= xmax; exponent++) ctx.fillText(compact(10 ** exponent), x(10 ** exponent), h - 18);
    capacityMarks = models.map((model, i) => {
      const row = summaries.get(model.id), px = x(model.parameters), py = y(row.test_accuracy_mean);
      const lower = y(row.test_accuracy_mean - row.test_accuracy_std), upper = y(row.test_accuracy_mean + row.test_accuracy_std);
      ctx.strokeStyle = colors.models[i]; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(px, lower); ctx.lineTo(px, upper); ctx.moveTo(px - 4, lower); ctx.lineTo(px + 4, lower); ctx.moveTo(px - 4, upper); ctx.lineTo(px + 4, upper); ctx.stroke();
      ctx.fillStyle = colors.models[i]; ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = colors.ink; ctx.fillText(shortName(model), Math.max(30, Math.min(w - 38, px)), py + (i === 0 ? 23 : -14));
      return {x: px, y: py, text: `${model.label}\n${model.parameters.toLocaleString()} params\n${pct(row.test_accuracy_mean)} ± ${(row.test_accuracy_std * 100).toFixed(2)}pt`};
    });
  }
  function drawCost() {
    const view = context('scale-cost'), {ctx, h, left, top, width, height} = view;
    const times = snapshot.models.flatMap(m => m.timings.map(t => t.step_ms));
    if (!times.length) return;
    const ymin = Math.floor(Math.log10(Math.min(...times))), ymax = Math.ceil(Math.log10(Math.max(...times)) * 2) / 2;
    const y = ms => top + height - (Math.log10(ms) - ymin) * height / (ymax - ymin);
    const ticks = []; for (let exponent = ymin; exponent <= ymax; exponent++) ticks.push(10 ** exponent);
    grid(view, ticks, y, n => n < 1 ? n.toFixed(1) : String(n));
    const group = width / snapshot.models.length, bar = Math.min(17, group * 0.23);
    costMarks = [];
    snapshot.models.forEach((model, i) => {
      const cx = left + (i + 0.5) * group;
      for (const timing of model.timings) {
        const px = cx + (timing.device === 'cpu' ? -bar - 2 : 2), py = y(timing.step_ms);
        ctx.fillStyle = timing.device === 'cpu' ? colors.orange : colors.blue;
        ctx.fillRect(px, py, bar, top + height - py);
        costMarks.push({x: px + bar / 2, y: py, text: `${model.label} · ${timing.device.toUpperCase()}\n${timing.step_ms.toFixed(3)} ms / 更新\n${Math.round(timing.samples_per_second).toLocaleString()} 点/秒`});
      }
      ctx.fillStyle = colors.muted; ctx.textAlign = 'center'; ctx.fillText(shortName(model), cx, h - 18);
    });
  }

  function drawLearning() {
    const view = context('scale-learning'), {ctx, h, left, top, width, height} = view;
    const timeAxis = $('scale-xaxis').value === 'time';
    const curves = snapshot.models.map(model => {
      const runs = modelRuns(model.id);
      return runs[0].history.slice(1).map((_, j) => ({epoch: j + 1,
        seconds: mean(runs.map(run => run.history[j + 1].elapsed_seconds)),
        accuracy: mean(runs.map(run => run.history[j + 1].validation.accuracy))}));
    });
    const xmax = timeAxis ? Math.max(...curves.flat().map(row => row.seconds)) : snapshot.config.epochs;
    const ymin = Math.floor(Math.min(...curves.flat().map(row => row.accuracy)) * 20) / 20;
    const ymax = Math.max(ymin + 0.05, Math.ceil(Math.max(...curves.flat().map(row => row.accuracy)) * 20) / 20);
    const x = row => left + (timeAxis ? row.seconds : row.epoch) * width / xmax;
    const y = a => top + height - (a - ymin) * height / (ymax - ymin);
    grid(view, Array.from({length: 5}, (_, i) => ymin + i * (ymax - ymin) / 4), y, a => `${(a * 100).toFixed(1)}%`);
    ctx.textAlign = 'center';
    for (let i = 0; i <= 4; i++) { const value = xmax * i / 4; ctx.fillText(timeAxis ? `${value.toFixed(1)}s` : String(value), left + width * i / 4, h - 18); }
    learningMarks = [];
    curves.forEach((curve, i) => {
      const points = curve.map(row => ({x: x(row), y: y(row.accuracy), text: `${snapshot.models[i].label} · epoch ${row.epoch}\n検証平均 ${pct(row.accuracy)}\n経過 ${row.seconds.toFixed(3)}s`}));
      line(ctx, points, colors.models[i]); learningMarks.push(...points);
    });
  }

  function currentRun() { return snapshot.runs.find(run => run.model_id === $('scale-model').value && run.seed === Number($('scale-seed').value)); }
  function drawDetail() {
    const run = currentRun();
    if (!run) return;
    const model = snapshot.models[modelIndex(run.model_id)];
    $('scale-detail-meta').textContent = `${[784, ...model.hidden, 10].join(' → ')} · ${run.parameters.toLocaleString()} params · 検証loss最小 epoch ${run.best_epoch} · テスト ${pct(run.test.accuracy)}（${run.test.correct}/${run.test.n.toLocaleString()}）`;
    const view = context('scale-loss'), {ctx, h, left, top, width, height} = view;
    const maxLoss = Math.ceil(Math.max(...run.history.flatMap(row => [row.train.loss, row.validation.loss])) * 2) / 2;
    const x = epoch => left + epoch * width / snapshot.config.epochs;
    const y = loss => top + height - loss * height / maxLoss;
    grid(view, Array.from({length: 5}, (_, i) => i * maxLoss / 4), y, n => n.toFixed(2));
    ctx.textAlign = 'center';
    for (let i = 0; i <= 4; i++) { const epoch = snapshot.config.epochs * i / 4; ctx.fillText(String(epoch), x(epoch), h - 18); }
    lossMarks = [];
    for (const [split, color, dash] of [['train', colors.orange, []], ['validation', colors.blue, [5, 4]]]) {
      const points = run.history.map(row => ({x: x(row.epoch), y: y(row[split].loss), text: `${split === 'train' ? '学習' : '検証'} · epoch ${row.epoch}\nCE ${row[split].loss.toFixed(4)}\n正解率 ${pct(row[split].accuracy)}`}));
      line(ctx, points, color, dash); lossMarks.push(...points);
    }
    ctx.strokeStyle = colors.muted; ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(x(run.best_epoch), top); ctx.lineTo(x(run.best_epoch), top + height); ctx.stroke(); ctx.setLineDash([]);
    drawConfusion(run);
  }
  function drawConfusion(run) {
    const {ctx, w, h} = context('scale-confusion');
    const left = 33, top = 18, cell = Math.min((w - 42) / 10, (h - 48) / 10);
    const matrix = run.test.confusion;
    confusionView = {left, top, cell, matrix};
    matrix.forEach((row, i) => row.forEach((count, j) => {
      const rate = count / row.reduce((a, b) => a + b, 0);
      ctx.fillStyle = mix(colors.surface, colors.blue, rate * 0.6); ctx.fillRect(left + j * cell, top + i * cell, cell, cell);
      ctx.strokeStyle = colors.grid; ctx.lineWidth = 0.5; ctx.strokeRect(left + j * cell, top + i * cell, cell, cell);
      ctx.fillStyle = colors.ink; ctx.textAlign = 'center'; if (count) ctx.fillText(String(count), left + (j + 0.5) * cell, top + (i + 0.5) * cell + 4);
    }));
    ctx.fillStyle = colors.muted; ctx.textAlign = 'center';
    for (let i = 0; i < 10; i++) { ctx.fillText(String(i), left + (i + 0.5) * cell, top + cell * 10 + 19); ctx.fillText(String(i), left - 16, top + (i + 0.5) * cell + 4); }
  }

  function populate() {
    const d = snapshot, hw = d.hardware, values = d.summary.map(row => row.test_accuracy_mean);
    $('scale-date').textContent = new Intl.DateTimeFormat('ja-JP', {timeZone: 'Asia/Tokyo', dateStyle: 'medium'}).format(new Date(d.created_at));
    $('scale-hardware').textContent = `${hw.gpu || 'CPU'} · ${hw.gpu_total_bytes ? (hw.gpu_total_bytes / 2**30).toFixed(1) + ' GiB VRAM · ' : ''}${hw.cpu} · PyTorch ${hw.torch}`;
    $('scale-model-count').textContent = `${d.models.length} 規模`;
    $('scale-run-count').textContent = `${d.config.seeds.length} seeds × ${d.config.epochs} epoch · ${d.runs.length} 実行`;
    $('scale-parameter-range').textContent = `${compact(d.models[0].parameters)}–${compact(d.models.at(-1).parameters)}`;
    $('scale-accuracy-range').textContent = `${(Math.min(...values) * 100).toFixed(1)}–${(Math.max(...values) * 100).toFixed(1)}%`;
    const memory = Math.max(...d.summary.map(row => row.peak_allocated_bytes || 0));
    $('scale-memory').textContent = memory ? `${(memory / 2**20).toFixed(0)} MiB` : '未計測';
    $('scale-cpu-label').textContent = `CPU・${hw.cpu_threads}スレッド`;
    $('scale-gpu-label').textContent = hw.gpu || 'GPU未計測';
    $('scale-protocol').textContent = `学習 ${d.data.train.toLocaleString()} / 検証 ${d.data.validation.toLocaleString()} / テスト ${d.data.test.toLocaleString()} 枚 · batch ${d.config.batch_size} · Adam lr ${d.config.lr} · L2 ${d.config.weight_decay} · ${d.config.device === 'cuda' ? 'GPU' : 'CPU'}学習 · float32 / TF32なし`;
    for (const [i, image] of d.data.previews.entries()) {
      const figure = document.createElement('figure'); figure.className = 'scale-preview';
      const canvas = document.createElement('canvas'); canvas.id = `scale-image-${i}`; canvas.setAttribute('aria-label', `${i} ${classNames[i]}の画像`); canvas.setAttribute('role', 'img');
      const caption = document.createElement('figcaption'); caption.textContent = `${image.label} ${classNames[i]}`;
      figure.append(canvas, caption); $('scale-previews').append(figure);
    }
    d.models.forEach(model => { const option = new Option(model.label, model.id); $('scale-model').add(option); });
    d.config.seeds.forEach(seed => $('scale-seed').add(new Option(String(seed), String(seed))));
    $('scale-model').value = d.models.some(model => model.id === 'mlp-512') ? 'mlp-512' : d.models[0].id;
    $('scale-provenance').textContent = `分割SHA256: ${d.data.split_sha256}\n実験コードSHA256: ${d.source_sha256}`;
  }
  function drawTable() {
    $('scale-table-body').replaceChildren(); $('scale-model-legend').replaceChildren();
    snapshot.models.forEach((model, i) => {
      const row = summaries.get(model.id), cpu = model.timings.find(t => t.device === 'cpu'), gpu = model.timings.find(t => t.device === 'cuda');
      const tr = document.createElement('tr'), name = document.createElement('td'), button = document.createElement('button');
      button.className = 'model-button'; button.textContent = model.label;
      const dot = document.createElement('i'); dot.className = 'scale-model-dot'; dot.style.background = colors.models[i]; name.append(dot, button); tr.append(name);
      button.addEventListener('click', () => { $('scale-model').value = model.id; drawDetail(); $('scale-model').focus(); });
      const cells = [model.parameters.toLocaleString(), `${pct(row.test_accuracy_mean)} ± ${(row.test_accuracy_std * 100).toFixed(2)}pt`, `${row.fit_seconds_mean.toFixed(2)} s`, cpu && gpu ? `${(cpu.step_ms / gpu.step_ms).toFixed(2)}×` : '未計測', row.peak_allocated_bytes ? `${(row.peak_allocated_bytes / 2**20).toFixed(1)} MiB` : '未計測'];
      for (const text of cells) { const cell = document.createElement('td'); cell.textContent = text; tr.append(cell); }
      $('scale-table-body').append(tr);
      const legend = document.createElement('span'), swatch = document.createElement('i'); swatch.style.background = colors.models[i]; legend.append(swatch, document.createTextNode(model.label)); $('scale-model-legend').append(legend);
    });
    const best = snapshot.summary.reduce((a, b) => a.test_accuracy_mean > b.test_accuracy_mean ? a : b);
    const last = snapshot.summary.at(-1), bestModel = snapshot.models[modelIndex(best.model_id)];
    $('scale-findings').textContent = `この条件では ${bestModel.label} が平均 ${pct(best.test_accuracy_mean)}。最大モデルは ${pct(last.test_accuracy_mean)}。規模だけで精度は決まりません。速度比は1より大きいほどGPUが速く、転送を含まない更新1回の比較です。`;
  }
  function render() {
    if ($('comparison-view').hidden) return;
    colors = palette(); drawPreviews(); drawTable(); drawCapacity(); drawCost(); drawLearning(); drawDetail();
  }
  populate();
  for (const id of ['scale-model', 'scale-seed']) $(id).addEventListener('change', drawDetail);
  $('scale-xaxis').addEventListener('change', drawLearning);
  bindMarks('scale-capacity', 'scale-capacity-tip', () => capacityMarks);
  bindMarks('scale-cost', 'scale-cost-tip', () => costMarks);
  bindMarks('scale-learning', 'scale-learning-tip', () => learningMarks);
  bindMarks('scale-loss', 'scale-loss-tip', () => lossMarks);
  $('scale-confusion').addEventListener('pointermove', event => {
    const rect = $('scale-confusion').getBoundingClientRect(), view = confusionView;
    if (!view) return;
    const col = Math.floor((event.clientX - rect.left - view.left) / view.cell), row = Math.floor((event.clientY - rect.top - view.top) / view.cell);
    const valid = row >= 0 && row < 10 && col >= 0 && col < 10;
    tooltip('scale-confusion', 'scale-confusion-tip', event, valid ? `正解 ${row} ${classNames[row]}\n予測 ${col} ${classNames[col]}\n${view.matrix[row][col]} 点 / ${view.matrix[row].reduce((a, b) => a + b)} 点` : null);
  });
  $('scale-confusion').addEventListener('pointerleave', () => { $('scale-confusion-tip').hidden = true; });
  $('scale-export').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(snapshot, null, 2)], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = 'fashion-model-scale-results.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener('lab-theme-change', render);
  window.addEventListener('lab-mode-change', render);
  let resizeTimer; window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 100); });
  render();
})();
