/* Real MNIST checkpoint replay; every new image is inferred locally. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id), math = DigitMath;
  const data = JSON.parse($('digit-data').textContent);
  if (!data) return;
  const pct = value => `${(value * 100).toFixed(2)}%`, number = value => value.toFixed(4);
  const phases = ['画素を0〜1へ', '5×5の線・曲がりを拾う', '2×2の最大値を残す', '特徴を組み合わせる', 'もう一度、最大値を残す', '10候補の確率に変換'];
  const examples = new Map(data.data.examples.map(example => [example.id, {...example, values: Float64Array.from(math.bytes(example.pixels), value => value / 255)}]));
  let spec = data.models.at(-1), epoch = spec.best_epoch, cnn, frame, selectedExample = examples.get(spec.verification.sample_id);
  let input = selectedExample.values.slice(), inspectedClass = null, filter = 0, row = 10, col = 10, weightCell = 12;
  let colors, learningTimer = 0, traceTimer = 0, phase = -1, drawing = false, lastPoint = null, pendingDrawing = 0;
  const ink = new Float64Array(280 * 280);

  function palette() {
    const styles = getComputedStyle(document.documentElement), get = key => styles.getPropertyValue(`--${key}`).trim();
    return {surface: get('surface'), dark: get('ink'), muted: get('ink-3'), grid: get('grid'), orange: get('series-1'), blue: get('series-2'), mono: get('mono')};
  }
  function rgb(color) { return [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16)); }
  function mix(a, b, fraction) {
    const before = rgb(a), after = rgb(b), value = Math.max(0, Math.min(1, fraction));
    return `rgb(${before.map((v, i) => Math.round(v + (after[i] - v) * value)).join(',')})`;
  }
  function raster(canvas, values, side, {signed = false, max = 1, image = false, marker = null} = {}) {
    canvas.width = side; canvas.height = side;
    const ctx = canvas.getContext('2d'), pixels = ctx.createImageData(side, side), surface = rgb(colors.surface);
    const zero = image ? rgb(colors.dark) : surface, positive = rgb(image ? colors.surface : colors.blue), negative = rgb(colors.orange);
    for (let i = 0; i < values.length; i++) {
      const fraction = Math.min(1, Math.abs(values[i]) / (max || 1)), target = signed && values[i] < 0 ? negative : positive;
      for (let c = 0; c < 3; c++) pixels.data[i * 4 + c] = Math.round(zero[c] + (target[c] - zero[c]) * fraction);
      pixels.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(pixels, 0, 0);
    if (marker) { ctx.strokeStyle = colors.orange; ctx.lineWidth = .7; const size = marker.size || 1; ctx.strokeRect(marker.col + .1, marker.row + .1, size - .2, size - .2); }
  }
  function stopLearning() { clearTimeout(learningTimer); learningTimer = 0; $('digit-learn').textContent = '▶ 学習を最初から再生'; }
  function stopTrace(clear = true) { clearTimeout(traceTimer); traceTimer = 0; if (clear) phase = -1; $('digit-trace').textContent = '▶ 推論を追う'; }
  function infer() { frame = cnn.forward(input); if (inspectedClass === null) inspectedClass = frame.prediction; }
  function loadEpoch(value) {
    epoch = Math.max(0, Math.min(data.config.epochs, value));
    cnn = new math.CNN(spec.channels, spec.history[epoch].weights);
    inspectedClass = null; infer(); render();
  }
  function chooseExample(id) {
    stopTrace(); selectedExample = examples.get(id); input = selectedExample.values.slice(); inspectedClass = null;
    infer(); render();
  }
  function renderGallery() {
    const errors = $('digit-gallery-kind').value === 'errors';
    let candidates = errors ? spec.error_ids.map(id => examples.get(id)) : data.data.examples.slice(0, 30).map(example => examples.get(example.id));
    if (!errors) candidates = Array.from({length: 3}, (_, round) => Array.from({length: 10}, (_, label) => candidates.filter(example => example.label === label)[round])).flat().filter(Boolean);
    const gallery = $('digit-gallery'); gallery.replaceChildren();
    for (const example of candidates) {
      const button = document.createElement('button'), canvas = document.createElement('canvas');
      button.dataset.digitFocus = `sample-${example.id}`;
      button.type = 'button'; button.setAttribute('aria-label', `正解 ${example.label}、検証画像 ${example.id}`);
      button.setAttribute('aria-pressed', String(selectedExample?.id === example.id));
      button.append(canvas, document.createTextNode(String(example.label)));
      button.addEventListener('click', () => chooseExample(example.id)); gallery.append(button);
      raster(canvas, example.values, 28, {image: true});
    }
    $('digit-gallery-note').textContent = errors ? `検証で選んだepoch ${spec.best_epoch}で誤分類した画像を、検証集合の順に最大12枚。表示中のepochでは正解する場合もあります。` : '検証集合の各数字から先頭3枚を固定。下の数字は正解ラベルです。テスト画像は使っていません。';
  }
  function renderPrediction() {
    const hasInk = input.some(value => value > .05), reveal = phase < 0 || phase === 5;
    $('digit-result').textContent = !hasInk ? '数字を描いてください' : !reveal ? '推論を進めています…' : `予測 ${frame.prediction} · ${pct(frame.probabilities[frame.prediction])}`;
    $('digit-correctness').textContent = !hasInk ? '入力待ち' : !reveal ? '計算中' : selectedExample ? `正解 ${selectedExample.label} / ${frame.prediction === selectedExample.label ? '一致' : '取り違え'}` : '手描き · 正解ラベルなし';
    $('digit-image-source').textContent = selectedExample ? `検証画像 ${selectedExample.id} · 正解 ${selectedExample.label}` : 'あなたが描いた画像 · 学習には使いません';
    const target = $('digit-probabilities');
    if (!target.children.length) for (let c = 0; c < 10; c++) {
      const button = document.createElement('button'); button.type = 'button';
      button.innerHTML = `<b>${c}</b><span class="digit-bar"><i></i></span><span></span>`;
      button.addEventListener('click', () => { stopTrace(); inspectedClass = c; render(); }); target.append(button);
    }
    Array.from(target.children).forEach((button, c) => {
      const probability = frame.probabilities[c]; button.classList.toggle('predicted', c === frame.prediction && reveal && hasInk);
      button.setAttribute('aria-pressed', String(c === inspectedClass)); button.setAttribute('aria-label', `数字 ${c} の寄与を選択${reveal && hasInk ? '、確率 '+pct(probability) : ''}`);
      button.querySelector('i').style.width = `${reveal && hasInk ? probability * 100 : 0}%`;
      button.lastElementChild.textContent = reveal && hasInk ? pct(probability) : '—';
    });
    raster($('digit-normalized'), input, 28, {image: true});
    raster($('digit-draw'), selectedExample ? input : ink, selectedExample ? 28 : 280, {image: true});
  }
  function stage(title, subtitle, index) {
    const section = document.createElement('div'); section.className = 'digit-stage';
    section.classList.toggle('active', phase === index); section.classList.toggle('future', phase >= 0 && phase < index);
    const h = document.createElement('h3'), p = document.createElement('p'); h.textContent = title; p.textContent = subtitle; section.append(h, p); return section;
  }
  function renderFlow() {
    const flow = $('digit-flow'); flow.replaceChildren();
    const first = stage('① 入力', '28 × 28 × 1', 0), canvas = document.createElement('canvas');
    first.append(canvas); raster(canvas, input, 28, {image: true, marker: {row, col, size: 5}}); flow.append(first);
    const groups = [
      ['② 畳み込み + ReLU', frame.first, spec.channels[0]],
      ['③ 最大値pool', frame.pooledFirst, spec.channels[0]],
      ['④ 畳み込み + ReLU', frame.second, spec.channels[1]],
      ['⑤ 最大値pool', frame.pooledSecond, spec.channels[1]],
    ];
    groups.forEach(([label, layer, count], group) => {
      const section = stage(label, `${layer.side} × ${layer.side} × ${count}`, group + 1), maps = document.createElement('div'); maps.className = 'digit-map-grid';
      let maximum = 0; for (const value of layer.a) maximum = Math.max(maximum, value);
      for (let channel = 0; channel < count; channel++) {
        const button = document.createElement(group === 0 ? 'button' : 'div'), plot = document.createElement('canvas'); button.className = 'digit-feature';
        if (group === 0) { button.type = 'button'; button.dataset.digitFocus = `filter-${channel}`; }
        else button.setAttribute('role', 'img');
        button.setAttribute('aria-label', `${label} フィルタ ${channel + 1}${group === 0 ? '、クリックしたマスの積和を調べる' : ''}`);
        if (group === 0) button.setAttribute('aria-pressed', String(filter === channel));
        const offset = channel * layer.side ** 2;
        raster(plot, layer.a.subarray(offset, offset + layer.side ** 2), layer.side, {max: maximum, marker: group === 0 && filter === channel ? {row, col} : null});
        button.append(plot, document.createTextNode(String(channel + 1)));
        if (group === 0) button.addEventListener('click', event => {
          stopTrace();
          if (group === 0) {
            filter = channel;
            if (event.detail > 0 && event.target === plot) {
              const rect = plot.getBoundingClientRect(); row = Math.max(0, Math.min(23, Math.floor((event.clientY - rect.top) / rect.height * 24))); col = Math.max(0, Math.min(23, Math.floor((event.clientX - rect.left) / rect.width * 24)));
            }
          }
          render();
        });
        maps.append(button);
      }
      section.append(maps); flow.append(section);
    });
    const output = stage('⑥ 10クラス', '全結合 → softmax', 5), result = document.createElement('div'); result.className = 'digit-flow-result';
    const digit = document.createElement('b'), probability = document.createElement('span'); digit.textContent = input.some(value => value > .05) ? String(frame.prediction) : '—'; probability.textContent = input.some(value => value > .05) ? pct(frame.probabilities[frame.prediction]) : '—'; result.append(digit, probability); output.append(result); flow.append(output);
    $('digit-phase').textContent = phase < 0 ? '全段階を表示 · 重みを固定した1枚の順伝播' : `${phase + 1} / 6 · ${phases[phase]}`;
  }
  function cells(id, values, signed, interactive = false) {
    const container = $(id), maximum = signed ? Math.max(...values.map(Math.abs), 0.001) : 1;
    if (container.children.length !== 25) {
      container.replaceChildren();
      for (let i = 0; i < 25; i++) {
        const element = document.createElement(interactive ? 'button' : 'span');
        if (interactive) { element.type = 'button'; element.addEventListener('click', () => { weightCell = i; renderFilter(); renderUpdate(); }); }
        container.append(element);
      }
    }
    values.forEach((value, i) => {
      const element = container.children[i]; element.textContent = Math.abs(value) < .005 ? '0' : value.toFixed(2);
      element.style.background = mix(colors.surface, signed && value < 0 ? colors.orange : colors.blue, Math.abs(value) / maximum * .22);
      if (interactive) { element.setAttribute('aria-pressed', String(weightCell === i)); element.setAttribute('aria-label', `フィルタ${filter + 1}の重み、行${Math.floor(i / 5) + 1} 列${i % 5 + 1}、${value.toFixed(5)}`); }
    });
  }
  function renderFilter() {
    $('digit-filter').value = String(filter); $('digit-cell-row').value = row; $('digit-cell-col').value = col;
    const inspected = cnn.inspect(frame, filter, row, col), sum = inspected.terms.reduce((total, term) => total + term.product, 0);
    cells('digit-patch', inspected.terms.map(term => term.value), false);
    cells('digit-kernel', inspected.terms.map(term => term.weight), true, true);
    cells('digit-products', inspected.terms.map(term => term.product), true);
    $('digit-filter-location').textContent = `フィルタ ${filter + 1} · 地図の行 ${row + 1}、列 ${col + 1}（1始まり）`;
    $('digit-filter-result').textContent = `反応 ${number(inspected.value)}`;
    $('digit-filter-equation').textContent = `Σ(画素 × 重み) ${number(sum)} + bias ${number(inspected.bias)} = ${number(inspected.z)} → ReLU = ${number(inspected.value)}`;
    const poolRow = Math.floor(row / 2), poolCol = Math.floor(col / 2), values = [];
    for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) values.push(frame.first.a[(filter * 24 + poolRow * 2 + dy) * 24 + poolCol * 2 + dx]);
    $('digit-pool-equation').textContent = `この位置を含む2×2 → max(${values.map(value => value.toFixed(3)).join(', ')}) = ${Math.max(...values).toFixed(3)}。pool地図の行${poolRow + 1}、列${poolCol + 1}に残ります。`;
  }
  function renderEvidence() {
    const evidence = cnn.contributions(frame, inspectedClass), total = evidence.values.reduce((sum, value) => sum + value.product, 0);
    $('digit-evidence-title').textContent = `「${inspectedClass}」の判定への寄与`;
    $('digit-output-equation').textContent = `全${evidence.values.length}特徴の寄与 ${number(total)} + bias ${number(evidence.bias)} = logit ${number(evidence.logit)}`;
    const strongest = evidence.values.slice().sort((a, b) => Math.abs(b.product) - Math.abs(a.product)).slice(0, 6), body = $('digit-contributions'); body.replaceChildren();
    for (const item of strongest) {
      const tr = document.createElement('tr'); tr.dataset.sign = item.product >= 0 ? 'positive' : 'negative';
      for (const text of [`F${item.channel + 1} / ${item.row + 1},${item.col + 1}`, number(item.value), number(item.weight), number(item.product)]) { const td = document.createElement('td'); td.textContent = text; tr.append(td); } body.append(tr);
    }
    const remainder = total - strongest.reduce((sum, value) => sum + value.product, 0);
    $('digit-contribution-note').textContent = `絶対値が大きい6特徴を表示。残る${evidence.values.length - 6}特徴の寄与合計 ${number(remainder)}。青は選択クラスのlogitを上げ、橙は下げる寄与です。`;
    const gradient = cnn.inputGradient(frame, inspectedClass), maximum = Math.max(...gradient.map(Math.abs));
    raster($('digit-sensitivity'), gradient, 28, {signed: true, max: maximum});
    $('digit-sensitivity-note').textContent = `「${inspectedClass}」のlogitの入力感度 ∂logit/∂画素。青の画素を少し明るくすると値が上がり、橙では下がる局所勾配です。最大絶対値 ${number(maximum)}。`;
  }
  function renderUpdate() {
    const update = spec.history[epoch].update, index = filter * 25 + weightCell;
    $('digit-update-weight-name').textContent = `第1層 F${filter + 1} · 重みの行${Math.floor(weightCell / 5) + 1}、列${weightCell % 5 + 1}`;
    if (!update) {
      $('digit-update-context').textContent = 'epoch 0は未学習。スライダーを進めると実際の更新を表示します。';
      for (const id of ['digit-update-loss', 'digit-update-gradient', 'digit-update-weight']) $(id).textContent = '—';
      $('digit-update-delta').textContent = 'Adam · 学習率0.001'; return;
    }
    const before = math.floats(update.before)[index], after = math.floats(update.after)[index], gradient = math.floats(update.gradient)[index];
    $('digit-update-context').textContent = `epoch ${epoch} 最後の学習${update.batch_size}枚 · Adam更新 ${update.optimizer_step}回目`;
    $('digit-update-loss').textContent = `${number(update.loss_before)} → ${number(update.loss_after)}`;
    $('digit-update-gradient').textContent = `${gradient < 0 ? '−' : '+'}${Math.abs(gradient).toExponential(3)}`;
    $('digit-update-weight').textContent = `${number(before)} → ${number(after)}`;
    $('digit-update-delta').textContent = `差分 ${(after - before).toExponential(3)} · Adamは勾配の移動平均も使います。`;
  }
  function renderLearning() {
    const canvas = $('digit-learning'), rect = canvas.getBoundingClientRect();
    if (!rect.width) return;
    const ratio = Math.min(devicePixelRatio || 1, 2), width = rect.width, height = rect.height;
    canvas.width = width * ratio; canvas.height = height * ratio;
    const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.font = `12px ${colors.mono}`;
    const left = 44, top = 22, w = width - 64, h = height - 60, x = e => left + e / data.config.epochs * w, y = value => top + (1 - value) * h;
    ctx.textAlign = 'right';
    for (const value of [0, .25, .5, .75, 1]) { ctx.strokeStyle = colors.grid; ctx.beginPath(); ctx.moveTo(left, y(value)); ctx.lineTo(left + w, y(value)); ctx.stroke(); ctx.fillStyle = colors.muted; ctx.fillText(`${value * 100}%`, left - 7, y(value) + 4); }
    ctx.textAlign = 'center';
    for (let e = 0; e <= data.config.epochs; e += 2) ctx.fillText(String(e), x(e), top + h + 21);
    ctx.fillText('epoch', left + w / 2, height - 3);
    for (const [history, field, color, dashed] of [[spec.history, 'train', colors.orange, false], [spec.history, 'validation', colors.blue, false], [data.baseline.history, 'validation', colors.muted, true]]) {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash(dashed ? [4, 4] : []); ctx.beginPath();
      history.forEach((entry, i) => { if (i) ctx.lineTo(x(entry.epoch), y(entry[field].accuracy)); else ctx.moveTo(x(entry.epoch), y(entry[field].accuracy)); }); ctx.stroke();
    }
    ctx.setLineDash([3, 3]); ctx.strokeStyle = colors.muted; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x(epoch), top); ctx.lineTo(x(epoch), top + h); ctx.stroke(); ctx.setLineDash([]);
    const entry = spec.history[epoch];
    $('digit-learning-note').textContent = `epoch ${epoch} · 学習CE ${number(entry.train.loss)} / 検証CE ${number(entry.validation.loss)}。学習画像の暗記だけでなく、検証正解率も追います。`;
  }
  function renderConfusion() {
    const matrix = spec.history[epoch].validation.confusion, container = $('digit-confusion'); container.replaceChildren();
    const table = document.createElement('table'), caption = document.createElement('caption'); caption.textContent = '検証集合の混同行列'; table.append(caption);
    const head = document.createElement('thead'), tr = document.createElement('tr');
    for (const value of ['正解＼予測', ...Array.from({length: 10}, (_, i) => i)]) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = String(value); tr.append(th); } head.append(tr); table.append(head);
    const body = document.createElement('tbody');
    for (let row = 0; row < 10; row++) {
      const line = document.createElement('tr'), th = document.createElement('th'); th.scope = 'row'; th.textContent = row; line.append(th);
      const total = matrix[row].reduce((a, b) => a + b, 0);
      for (let col = 0; col < 10; col++) { const td = document.createElement('td'); td.textContent = matrix[row][col]; td.style.background = mix(colors.surface, row === col ? colors.blue : colors.orange, matrix[row][col] / total * .32); td.title = `正解 ${row} → 予測 ${col}：${matrix[row][col]} / ${total}枚`; line.append(td); } body.append(line);
    }
    table.append(body); container.append(table);
  }
  function render() {
    if ($('digits-view').hidden) return;
    const focusKey = document.activeElement?.dataset.digitFocus;
    colors = palette(); const entry = spec.history[epoch];
    $('digit-model').value = spec.id; $('digit-epoch').value = epoch; $('digit-epoch-label').textContent = `epoch ${epoch} / ${data.config.epochs}`;
    $('digit-checkpoint-note').textContent = epoch === 0 ? '初期重み' : epoch === spec.best_epoch ? '検証損失で選んだ重み' : '保存した実際の重み';
    $('digit-val').textContent = pct(entry.validation.accuracy); $('digit-val-count').textContent = `${entry.validation.correct.toLocaleString()} / 10,000枚`;
    $('digit-baseline').textContent = pct(data.baseline.history[epoch].validation.accuracy); $('digit-parameters').textContent = spec.parameters.toLocaleString();
    $('digit-fit-time').textContent = `${spec.channels.join(' → ')} filters · GPU学習・評価 ${spec.fit_seconds.toFixed(2)}秒`;
    $('digit-test').textContent = epoch === spec.best_epoch ? pct(spec.test.accuracy) : '—';
    $('digit-test-note').textContent = epoch === spec.best_epoch ? `選択epoch ${spec.best_epoch} · ${spec.test.correct.toLocaleString()} / 10,000枚` : `最終テストは選択epoch ${spec.best_epoch}だけで評価`;
    renderPrediction(); renderGallery(); renderFlow(); renderFilter(); renderEvidence(); renderUpdate(); renderLearning(); renderConfusion();
    if (focusKey) document.querySelector(`[data-digit-focus="${focusKey}"]`)?.focus({preventScroll: true});
  }
  function buildFilters() {
    $('digit-filter').replaceChildren();
    for (let i = 0; i < spec.channels[0]; i++) { const option = document.createElement('option'); option.value = i; option.textContent = `F${i + 1}`; $('digit-filter').append(option); }
  }
  for (const model of data.models) { const option = document.createElement('option'); option.value = model.id; option.textContent = `${model.label} · ${model.parameters.toLocaleString()} params`; $('digit-model').append(option); }
  $('digit-model').addEventListener('change', () => { stopLearning(); stopTrace(); spec = data.models.find(model => model.id === $('digit-model').value); filter = 0; buildFilters(); loadEpoch(spec.best_epoch); });
  $('digit-epoch').max = data.config.epochs;
  $('digit-epoch').addEventListener('input', () => { stopLearning(); stopTrace(); loadEpoch(Number($('digit-epoch').value)); });
  $('digit-best').addEventListener('click', () => { stopLearning(); stopTrace(); loadEpoch(spec.best_epoch); });
  $('digit-learn').addEventListener('click', () => {
    if (learningTimer) { stopLearning(); return; }
    stopTrace(); loadEpoch(0);
    const advance = () => { loadEpoch(epoch + 1); if (epoch < data.config.epochs) learningTimer = setTimeout(advance, 1100); else stopLearning(); };
    learningTimer = setTimeout(advance, 1100); $('digit-learn').textContent = 'Ⅱ 学習の再生を一時停止';
  });
  $('digit-gallery-kind').addEventListener('change', renderGallery);
  $('digit-filter').addEventListener('change', () => { stopTrace(); filter = Number($('digit-filter').value); render(); });
  for (const [id, setter] of [['digit-cell-row', value => { row = value; }], ['digit-cell-col', value => { col = value; }]]) $(id).addEventListener('input', () => { stopTrace(); setter(Number($(id).value)); renderFlow(); renderFilter(); });
  function advanceTrace() { phase = (phase + 1) % 6; render(); }
  $('digit-next').addEventListener('click', () => { stopLearning(); stopTrace(false); advanceTrace(); });
  $('digit-trace').addEventListener('click', () => {
    if (traceTimer) { stopTrace(false); return; }
    stopLearning(); stopTrace(); advanceTrace();
    const advance = () => { if (phase < 5) { advanceTrace(); traceTimer = setTimeout(advance, 950); } else stopTrace(false); };
    traceTimer = setTimeout(advance, 950); $('digit-trace').textContent = 'Ⅱ 推論を一時停止';
  });
  function clearDrawing() {
    cancelAnimationFrame(pendingDrawing); pendingDrawing = 0;
    stopTrace(); selectedExample = null; ink.fill(0); input.fill(0); inspectedClass = null; infer(); render();
  }
  $('digit-clear').addEventListener('click', clearDrawing);
  const draw = $('digit-draw');
  function dab(x, y) {
    const radius = 8.5;
    for (let row = Math.max(0, Math.floor(y - radius)); row <= Math.min(279, Math.ceil(y + radius)); row++) for (let col = Math.max(0, Math.floor(x - radius)); col <= Math.min(279, Math.ceil(x + radius)); col++) {
      const amount = Math.max(0, Math.min(1, radius - Math.hypot(row - y, col - x)));
      ink[row * 280 + col] = Math.max(ink[row * 280 + col], amount);
    }
  }
  function drawAt(event) {
    const rect = draw.getBoundingClientRect(), point = [(event.clientX - rect.left) / rect.width * 280, (event.clientY - rect.top) / rect.height * 280];
    if (lastPoint) { const steps = Math.max(1, Math.ceil(Math.hypot(point[0] - lastPoint[0], point[1] - lastPoint[1]) / 2)); for (let i = 0; i <= steps; i++) dab(lastPoint[0] + (point[0] - lastPoint[0]) * i / steps, lastPoint[1] + (point[1] - lastPoint[1]) * i / steps); } else dab(...point);
    lastPoint = point;
    if (!pendingDrawing) pendingDrawing = requestAnimationFrame(() => { pendingDrawing = 0; input = math.prepareDrawing(ink, 280); inspectedClass = null; infer(); render(); });
  }
  draw.addEventListener('pointerdown', event => { if (event.button !== 0) return; stopTrace(); if (selectedExample) { selectedExample = null; ink.fill(0); } drawing = true; lastPoint = null; draw.setPointerCapture(event.pointerId); drawAt(event); });
  draw.addEventListener('pointermove', event => { if (drawing) drawAt(event); });
  const endDrawing = () => { drawing = false; lastPoint = null; };
  draw.addEventListener('pointerup', endDrawing); draw.addEventListener('pointercancel', endDrawing);
  draw.addEventListener('keydown', event => { if (['Delete', 'Backspace'].includes(event.key)) { event.preventDefault(); clearDrawing(); } });
  $('digit-methods').innerHTML = `<p>MNIST公式学習60,000枚からseed42で層化分割し、学習50,000 / 検証10,000枚。公式テスト10,000枚は、各モデルで検証交差エントロピー最小のepochを選んだ後に1回だけ評価。テストでモデルやepochを選んでいません。</p><p>全モデル：seed11、${data.config.epochs} epoch、batch256、Adam、学習率0.001、正則化なし、float32、TF32なし。入力は画素/255で、統計量の推定はありません。CNNは5×5 conv → ReLU → 2×2 maxpool → 3×3 conv → ReLU → 2×2 maxpool → 全結合10 → softmax。線形分類器は784 → 10です。</p><p><span id="digit-hardware-info"></span>。時間は初期評価を除く学習・全学習/検証集合の評価・再生用記録を含みます。2規模とも同じ学習画像順ですが、単一seed・8 epochでの比較です。手描きはMNISTとの見た目の違いで間違う場合があります。</p><p>既存キャッシュを読み、追加ダウンロードなし。保存画像は各数字の先頭3検証例と各モデルの最初の12誤分類例。再現コード：<code>nn_textbook.digit_experiment</code>。入力と分割、コードのSHA256もJSONに記録。入力勾配は選択クラスのlogitの局所微分です。</p><p>データ：<a href="https://yann.lecun.org/exdb/mnist/" target="_blank" rel="noopener noreferrer">MNIST / LeCun・Cortes・Burges</a>。実装：<a href="https://docs.pytorch.org/vision/stable/generated/torchvision.datasets.MNIST.html" target="_blank" rel="noopener noreferrer">torchvision MNIST</a>。</p>`;
  $('digit-hardware-info').textContent = `GPU：${data.hardware.gpu} / PyTorch ${data.hardware.torch}`;
  window.addEventListener('lab-mode-change', () => { if ($('digits-view').hidden) { stopLearning(); stopTrace(); } else render(); });
  window.addEventListener('lab-theme-change', render);
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stopLearning(); stopTrace(); } });
  let resizeTimer; window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 100); });
  buildFilters(); loadEpoch(epoch);
})();
