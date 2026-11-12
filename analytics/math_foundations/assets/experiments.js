(function () {
  'use strict';
  const math = typeof globalThis !== 'undefined' ? globalThis.MathFoundations : null;
  if (!math || typeof document === 'undefined') return;
  let nextId = 0;

  function number(value, digits = 3) {
    if (value === null || !Number.isFinite(value)) return '未定義';
    if (Math.abs(value) >= 10000) return value.toExponential(3);
    const rounded = Math.abs(value) < 0.5 * (10 ** -digits) ? 0 : value;
    return rounded.toFixed(digits);
  }

  function complex(value) {
    return number(value.re) + (value.im < -0.0005 ? ' − ' : ' + ') + number(Math.abs(value.im)) + 'i';
  }

  function escapeText(value) {
    return String(value).replace(/[&<>\"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[character]));
  }

  function svg(prefix, title, description, body, height = 350) {
    return '<svg class="lab-svg" viewBox="0 0 480 ' + height + '" role="img" aria-labelledby="' + prefix + '-title ' + prefix + '-desc" style="display:block;width:100%;max-width:480px;height:auto;margin-inline:auto">' +
      '<title id="' + prefix + '-title">' + escapeText(title) + '</title>' +
      '<desc id="' + prefix + '-desc">' + escapeText(description) + '</desc>' + body + '</svg>';
  }

  function text(x, y, label, anchor = 'middle', fill = '--ink-2') {
    return '<text x="' + x + '" y="' + y + '" text-anchor="' + anchor + '" style="fill:var(' + fill + ');font-size:var(--lab-label-size,20px);font-family:inherit">' + escapeText(label) + '</text>';
  }

  function line(x1, y1, x2, y2, color, width = 1.5, dash = '') {
    return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" style="stroke:var(' + color + ');stroke-width:' + width + (dash ? ';stroke-dasharray:' + dash : '') + '" />';
  }

  function circle(x, y, radius, color, filled = true, width = 2) {
    return '<circle cx="' + x + '" cy="' + y + '" r="' + radius + '" style="fill:' + (filled ? 'var(' + color + ')' : 'none') + ';stroke:var(' + color + ');stroke-width:' + width + '" />';
  }

  function plane() {
    return line(65, 170, 415, 170, '--grid') + line(240, 32, 240, 307, '--grid') +
      text(423, 176, '実部', 'start', '--ink-2') + text(249, 28, '虚部', 'start', '--ink-2') +
      text(230, 190, '0', 'end', '--ink-2');
  }

  function arc(start, degrees, radius, color) {
    if (degrees === 0) return '';
    const points = [];
    const count = Math.max(2, Math.ceil(Math.abs(degrees) / 5));
    for (let i = 0; i <= count; i += 1) {
      const angle = (start + degrees * i / count) * Math.PI / 180;
      points.push((240 + radius * Math.cos(angle)).toFixed(2) + ',' + (170 - radius * Math.sin(angle)).toFixed(2));
    }
    return '<polyline points="' + points.join(' ') + '" style="fill:none;stroke:var(' + color + ');stroke-width:2.5;stroke-dasharray:5 4" />';
  }

  function initializeNumbers(host, prefix) {
    host.innerHTML = '<div class="lab-controls"><label class="lab-control" for="' + prefix + '-turns">' +
      '<span class="lab-control-label">i を掛ける回数 n</span> <output for="' + prefix + '-turns" data-role="angle"></output>' +
      '<input id="' + prefix + '-turns" type="range" min="0" max="4" step="1" value="0" aria-describedby="' + prefix + '-note"></label>' +
      '<div class="lab-actions"><button type="button" data-role="reset">初期状態に戻す</button></div></div>' +
      '<p class="lab-note" id="' + prefix + '-note">右に1目盛り進むたびに、点を反時計回りに90°回します。矢印キーでも操作できます。</p>' +
      '<div data-role="figure"></div><div class="lab-readout" aria-live="polite" aria-atomic="true" data-role="readout"></div>';
    const control = host.querySelector('input');
    const update = function () {
      const n = Number(control.value);
      const point = math.quarterTurn(n);
      const names = ['1', 'i', '−1', '−i', '1'];
      const prior = n > 0 ? math.quarterTurn(n - 1) : null;
      const priorFigure = prior ? line(240, 170, 240 + prior.re * 112, 170 - prior.im * 112, '--ink-3', 2, '4 4') +
        circle(240 + prior.re * 112, 170 - prior.im * 112, 7, '--ink-3', false, 2.5) : '';
      const lastQuarter = n > 0 ? arc((n - 1) * 90, 90, 67, '--series-2')
        .replace('stroke-dasharray:5 4', 'stroke-dasharray:none')
        .replace('<polyline ', '<polyline marker-end="url(#' + prefix + '-quarter-arrow)" ') : '';
      const quarterMarker = '<defs><marker id="' + prefix + '-quarter-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0 0 L10 5 L0 10 Z" style="fill:var(--series-2)" /></marker></defs>';
      host.querySelector('[data-role="angle"]').textContent = n + ' 回 / ' + (90 * n) + '°';
      const body = quarterMarker + plane() + circle(240, 170, 112, '--grid', false, 1) + arc(0, n * 90, 92, '--ink-3') + priorFigure + lastQuarter +
        text(365, 163, '1', 'start') + text(253, 51, 'i', 'start') + text(115, 163, '−1', 'end') + text(253, 300, '−i', 'start') +
        line(240, 170, 240 + point.re * 112, 170 - point.im * 112, '--series-1', 3.5) +
        circle(240 + point.re * 112, 170 - point.im * 112, 7, '--series-1') +
        text(240, 335, '1 → i → −1 → −i → 1', 'middle', '--ink-2') +
        text(240, 372, n === 0 ? '出発点1。まだ i を掛けていない' : '灰輪：前　橙点：今　青弧：90°', 'middle', '--ink-2');
      host.querySelector('[data-role="figure"]').innerHTML = svg(prefix, 'iの一回の作用と、四回で戻る周期を比べる',
        '出発点1からiを' + n + '回掛けた現在点は' + names[n] + '、座標は実部' + point.re + '、虚部' + point.im + '。' +
        (prior ? '灰の白抜き点は直前の点。青い矢印付きの弧は最後の1回の90度回転で、原点距離1は変わらない。' : 'まだ回転せず、現在点は1。') +
        'これは1から始める有限の4段階の図で、任意の複素数への作用は本文の積の定義で説明する。',
        body.replaceAll('--lab-label-size,20px', '--lab-label-size,24px'), 405);
      host.querySelector('[data-role="readout"]').innerHTML = '<p><strong>i' + (n === 0 ? '⁰' : '<sup>' + n + '</sup>') + ' = ' + names[n] + '</strong>　座標 (' + point.re + ', ' + point.im + ')</p>' +
        '<p>' + (n === 0 ? '出発点は1。まだ i を掛けていません。' : n === 4 ? '4回で元の1へ戻ります。ここから同じ4点を繰り返します。' : '直前の点に i を掛けると、さらに90°回転します。') + '</p>';
    };
    control.addEventListener('input', update);
    host.querySelector('[data-role="reset"]').addEventListener('click', function () { control.value = '0'; update(); });
    update();
  }

  function continuityPlot(kind, state, prefix) {
    const x = value => 64 + value * 188;
    const y = value => 170 - value * 36;
    let body = '';
    for (const tick of [-2, -1, 0, 1, 2]) {
      body += line(64, y(tick), 440, y(tick), '--grid', tick === 0 ? 1.7 : 1);
      body += text(52, y(tick) + 5, String(tick), 'end', '--ink-2');
    }
    body += line(64, 52, 64, 278, '--grid');
    for (const tick of [0, 0.5, 1, 1.5, 2]) {
      body += line(x(tick), 167, x(tick), 174, '--ink-2', 1);
      body += text(x(tick), 297, String(tick), 'middle', '--ink-2');
    }
    body += text(448, 176, 'x', 'start', '--ink-2') + text(51, 39, 'f(x)', 'middle', '--ink-2');
    body += '<rect x="' + x(state.a) + '" y="52" width="' + Math.max(0.8, x(state.b) - x(state.a)) + '" height="226" style="fill:var(--series-2);opacity:0.12" />';
    if (kind !== 'sqrt') body += line(x(1.3), 52, x(1.3), 278, '--ink-2', 1.5, '4 4') + text(x(1.3), 31, '1.3', 'middle', '--ink-2');
    const paths = [];
    let points = [];
    let previousSide = null;
    for (let i = 0; i <= 400; i += 1) {
      const currentX = i / 200;
      const value = math.evaluateExample(kind, currentX);
      const side = currentX < 1.3 ? 'left' : 'right';
      if (value === null || Math.abs(value) > 3 || (kind !== 'sqrt' && previousSide !== null && side !== previousSide)) {
        if (points.length) paths.push(points);
        points = [];
      }
      if (value !== null && Math.abs(value) <= 3) points.push(x(currentX).toFixed(2) + ',' + y(value).toFixed(2));
      previousSide = side;
    }
    if (points.length) paths.push(points);
    paths.forEach(path => { body += '<polyline points="' + path.join(' ') + '" style="fill:none;stroke:var(--series-1);stroke-width:3" />'; });
    if (kind === 'step') {
      body += circle(x(1.3), y(1), 5, '--series-1');
    }
    body += line(x(state.a), 52, x(state.a), 278, '--series-2', 1.7, '3 3') + line(x(state.b), 52, x(state.b), 278, '--series-2', 1.7, '3 3');
    body += circle(x(state.midpoint), 170, 4.5, '--series-2');
    if (state.value !== null && Math.abs(state.value) <= 3) body += circle(x(state.midpoint), y(state.value), 5, '--series-1');
    if (kind === 'step') body += circle(x(1.3), y(-1), 5, '--series-1', false, 2.5).replace('fill:none', 'fill:var(--surface)');
    body += text(240, 331, '帯と破線：残した区間 [a, b]', 'middle', '--ink-2');
    body += text(240, 360, 'f(a)<0<f(b)（0.000は丸めた表示）', 'middle', '--ink-2');
    body += text(240, 389, kind === 'sqrt' ? '連続＋実数の完備性 ⇒ 根がある' : '符号だけでは根を保証しない', 'middle', '--ink-2');
    const description = '横軸は0から2。' + (kind === 'sqrt' ? '連続な放物線が横軸を横切る。' : kind === 'step' ? '1.3で負から正へ跳ぶが、0にはならない。白抜き点は値を含まず、塗った点は値を含む。' : '1.3で関数が未定義。左右の曲線はつながらず、横軸を横切らない。縦方向は−3から3で表示を切っている。') +
      '現在の区間は' + number(state.a, 6) + 'から' + number(state.b, 6) + '。左端負・右端正という符号を保って残す。有限の幅や丸めた表示だけでは根の存在を証明しない。実数の完備性は共通する入力の存在、連続性はその出力が0になることを保証する。';
    return svg(prefix, '異符号の区間を残す手順と、根の存在保証を区別する', description, body, 410);
  }

  function initializeContinuity(host, prefix) {
    host.innerHTML = '<div class="lab-controls"><label class="lab-control" for="' + prefix + '-function"><span class="lab-control-label">調べる関数</span>' +
      '<select id="' + prefix + '-function"><option value="sqrt">連続：x² − 2</option><option value="step">不連続：1.3 で跳ぶ階段</option><option value="pole">未定義の点：1 / (x − 1.3)</option></select></label>' +
      '<label class="lab-control" for="' + prefix + '-iterations"><span class="lab-control-label">二分する回数 n</span> <output for="' + prefix + '-iterations" data-role="count"></output>' +
      '<input id="' + prefix + '-iterations" type="range" min="0" max="10" step="1" value="0" aria-describedby="' + prefix + '-note"></label>' +
      '<div class="lab-actions"><button type="button" data-role="reset">初期状態に戻す</button></div></div>' +
      '<p class="lab-note" id="' + prefix + '-note">端点の符号が異なる側を残します。区間が狭まる様子と、根があるという保証を分けて観察してください。</p>' +
      '<p class="lab-note" data-role="definition"></p><div data-role="figure"></div><div class="lab-readout" aria-live="polite" aria-atomic="true" data-role="readout"></div>';
    const selection = host.querySelector('select');
    const control = host.querySelector('input');
    const update = function () {
      const kind = selection.value;
      const state = math.bisectionState(kind, Number(control.value));
      host.querySelector('[data-role="count"]').textContent = state.iterations + ' 回';
      host.querySelector('[data-role="definition"]').textContent = kind === 'sqrt' ? 'f(x) = x² − 2、初期区間 [0, 2]。' : kind === 'step' ? 'f(x) = −1（x < 1.3）、f(x) = 1（x ≥ 1.3）。0になる点はありません。' : 'f(x) = 1 / (x − 1.3)。x = 1.3 では未定義で、定義された点でも0にはなりません。縦軸は −3 から3の範囲です。';
      host.querySelector('[data-role="figure"]').innerHTML = continuityPlot(kind, state, prefix);
      const guarantee = kind === 'sqrt' ? '<p class="lab-status"><strong>根の存在が保証されます。</strong> [0, 2] で連続で、端点の値が負と正だからです。</p>' +
        '<p>中点と根 √2 の距離 ≤ <strong>' + number(state.errorBound, 6) + '</strong>（区間幅の半分）。</p>' :
        '<p class="lab-status"><strong>根はありません。中間値の定理は適用できません。</strong> ' + (kind === 'step' ? 'x = 1.3 で不連続です。符号が変わっても値0を飛び越えています。' : 'x = 1.3 で未定義なので、区間全体で連続ではありません。区間は根のない特異点へ近づきます。') + '</p>' +
        '<p>区間幅は小さくなりますが、根の近似値や根の誤差上限としては使えません。</p>';
      host.querySelector('[data-role="readout"]').innerHTML = '<p>[a, b] = [' + number(state.a, 6) + ', ' + number(state.b, 6) + ']　幅 = ' + number(state.width, 6) + '</p>' +
        '<p>f(a) = ' + number(state.fa) + '、f(b) = ' + number(state.fb) + '<br>中点 m = ' + number(state.midpoint, 6) + '、f(m) = ' + number(state.value) + '</p>' + guarantee;
    };
    selection.addEventListener('change', update);
    control.addEventListener('input', update);
    host.querySelector('[data-role="reset"]').addEventListener('click', function () { selection.value = 'sqrt'; control.value = '0'; update(); });
    update();
  }

  function initializeRotation(host, prefix) {
    host.innerHTML = '<div class="lab-controls"><label class="lab-control" for="' + prefix + '-beta"><span class="lab-control-label">最初の回転 β</span> <output for="' + prefix + '-beta" data-role="beta-value"></output>' +
      '<input id="' + prefix + '-beta" type="range" min="-180" max="180" step="5" value="60" aria-describedby="' + prefix + '-note"></label>' +
      '<label class="lab-control" for="' + prefix + '-alpha"><span class="lab-control-label">後の回転 α</span> <output for="' + prefix + '-alpha" data-role="alpha-value"></output>' +
      '<input id="' + prefix + '-alpha" type="range" min="-180" max="180" step="5" value="30" aria-describedby="' + prefix + '-note"></label>' +
      '<div class="lab-actions"><button type="button" data-role="reset">初期状態に戻す</button></div></div>' +
      '<p class="lab-note" id="' + prefix + '-note">出発点は (1, 0.5)。先に β、後に α を回すので、行列は R(α)R(β) の順に書きます。正の角は反時計回り、負の角は時計回りです。点と輪が重なれば、2通りの結果が一致しています。</p>' +
      '<div data-role="figure"></div><div class="lab-readout" aria-live="polite" aria-atomic="true" data-role="readout"></div>';
    const alphaControl = host.querySelector('#' + prefix + '-alpha');
    const betaControl = host.querySelector('#' + prefix + '-beta');
    const update = function () {
      const alpha = Number(alphaControl.value);
      const beta = Number(betaControl.value);
      const original = { x: 1, y: 0.5 };
      const first = math.rotateVector(original, beta);
      const successive = math.rotateVector(first, alpha);
      const sum = math.rotateVector(original, alpha + beta);
      const alphaUnit = math.rotateVector({ x: 1, y: 0 }, alpha);
      const betaUnit = math.rotateVector({ x: 1, y: 0 }, beta);
      const coefficient = math.complexMultiply({ re: alphaUnit.x, im: alphaUnit.y }, { re: betaUnit.x, im: betaUnit.y });
      const result = math.complexMultiply(coefficient, { re: original.x, im: original.y });
      const matrix = math.rotationMatrix(alpha + beta);
      const px = point => 240 + point.x * 112;
      const py = point => 170 - point.y * 112;
      const startAngle = Math.atan2(original.y, original.x) * 180 / Math.PI;
      host.querySelector('[data-role="alpha-value"]').textContent = alpha + '°';
      host.querySelector('[data-role="beta-value"]').textContent = beta + '°';
      const body = plane() + circle(240, 170, Math.hypot(original.x, original.y) * 112, '--grid', false, 1) +
        line(240, 170, px(original), py(original), '--ink-2', 1.5) + circle(px(original), py(original), 4, '--ink-2', false) +
        arc(startAngle, beta, 72, '--series-1') + arc(startAngle + beta, alpha, 91, '--series-2') +
        line(240, 170, px(first), py(first), '--series-1', 3, '6 4') + circle(px(first), py(first), 4, '--series-1') +
        line(240, 170, px(sum), py(sum), '--series-2', 4) + circle(px(sum), py(sum), 11, '--series-2', false, 2.5) +
        circle(px(successive), py(successive), 5, '--series-2') +
        text(240, 334, '点：β の後に α　輪：α + β を一度') +
        text(240, 360, '破線：β の後の点　細線：出発点');
      host.querySelector('[data-role="figure"]').innerHTML = svg(prefix, '2回の回転と角の和による回転',
        '出発点は1、0.5。最初にβの' + beta + '度、次にαの' + alpha + '度。合計' + (alpha + beta) + '度の回転と同じ点、座標' + number(sum.x) + '、' + number(sum.y) + 'へ移る。原点からの長さは√1.25のまま。', body, 390);
      host.querySelector('[data-role="readout"]').innerHTML = '<p><strong>α + β = ' + (alpha + beta) + '°</strong><br>β の後に α：(' + number(successive.x) + ', ' + number(successive.y) + ')<br>角を足して一度：(' + number(sum.x) + ', ' + number(sum.y) + ')</p>' +
        '<p>複素数の積 zα zβ：(' + complex({ re: alphaUnit.x, im: alphaUnit.y }) + ') × (' + complex({ re: betaUnit.x, im: betaUnit.y }) + ')<br>= ' + complex(coefficient) + '<br>これを出発点 1 + 0.5i に掛けると <strong>' + complex(result) + '</strong></p>' +
        '<p>R(α + β) の行列（角の和から計算）：<br>［' + number(matrix[0][0]) + '　' + number(matrix[0][1]) + '］<br>［' + number(matrix[1][0]) + '　' + number(matrix[1][1]) + '］</p>' +
        '<p>原点からの長さ = ' + number(Math.hypot(successive.x, successive.y)) + '（出発時も √1.25 ≈ ' + number(Math.hypot(original.x, original.y)) + '）。数値は小数第3位までの丸めです。</p>';
    };
    alphaControl.addEventListener('input', update);
    betaControl.addEventListener('input', update);
    host.querySelector('[data-role="reset"]').addEventListener('click', function () { alphaControl.value = '30'; betaControl.value = '60'; update(); });
    update();
  }

  function initialize() {
    const labs = { numbers: initializeNumbers, continuity: initializeContinuity, rotation: initializeRotation };
    document.querySelectorAll('[data-lab]').forEach(function (host) {
      if (host.dataset.labInitialized || !labs[host.dataset.lab]) return;
      const prefix = 'math-lab-' + (++nextId);
      labs[host.dataset.lab](host, prefix);
      host.dataset.labInitialized = 'true';
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
