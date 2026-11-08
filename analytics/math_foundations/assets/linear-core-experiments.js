(function () {
  'use strict';
  const math = globalThis.MathLinearCore;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const raw = value => JSON.stringify(value);
  const number = value => value === 0 ? '0' : Math.abs(value) < .00001 || Math.abs(value) >= 100000 ? value.toExponential(4) : Number(value.toFixed(6)).toString();
  const display = value => value === null ? '未定義' : Array.isArray(value) ? '(' + value.map(display).join(', ') + ')' : typeof value === 'number' ? number(value) : String(value);
  const result = (key, value, text) => `<span data-value="${escape(key)}" data-raw="${escape(raw(value))}" data-raw-value="${escape(raw(value))}"><strong>${escape(text === undefined ? display(value) : text)}</strong></span>`;
  const label = (x, y, text, color = '--ink', anchor = 'middle') => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(${color});font-size:22px">${escape(text)}</text>`;
  const line = (x1, y1, x2, y2, color = '--ink-3', width = 2, dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const dot = (x, y, radius = 5, color = '--series-1', filled = true) => `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${filled ? color : '--surface'});stroke:var(${color});stroke-width:3"/>`;
  const path = (points, color = '--series-1', width = 3, dash = '') => `<path d="${points.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  function arrow(x1, y1, x2, y2, color = '--series-1') {
    const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy);
    if (length < .001) return dot(x2, y2, 5, color, false);
    const ux = dx / length, uy = dy / length, head = Math.min(10, length * .4);
    return line(x1, y1, x2, y2, color, 3) + `<path d="M${x2 - head * ux - head * .5 * uy},${y2 - head * uy + head * .5 * ux} L${x2},${y2} L${x2 - head * ux + head * .5 * uy},${y2 - head * uy - head * .5 * ux}" style="fill:none;stroke:var(${color});stroke-width:3"/>`;
  }
  const figure = (id, title, description, body) => `<svg class="lab-svg" data-visual="linear-core-lab" viewBox="0 0 360 360" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(description)}</desc>${body}</svg>`;
  const range = (prefix, key, title, min, max, step, value) => `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  const select = (prefix, key, title, options) => `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}</span><select id="${prefix}-${key}" data-key="${key}">${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join('')}</select></label>`;
  const panels = '<div class="lab-actions"><button type="button" data-reset data-action="reset">初期状態に戻す</button></div><p class="lab-status" role="status" aria-live="polite"></p><div data-figures></div><div class="lab-readout"></div>';
  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      try {
        const input = Object.fromEntries(controls.map(control => [control.dataset.key, control.dataset.key === 'kind' ? control.value : Number(control.value)]));
        host.querySelectorAll('output[data-value]').forEach(output => {
          const value = input[output.dataset.value]; output.textContent = display(value); output.dataset.raw = raw(value); output.dataset.rawValue = raw(value);
        });
        host.querySelector('.lab-status').textContent = render(input);
        host.dataset.labError = 'false'; host.dataset.domainState = 'defined';
      } catch (error) {
        host.dataset.labError = 'true'; host.dataset.domainState = 'error';
        host.querySelector('[data-figures]').innerHTML = ''; host.querySelector('.lab-readout').textContent = '';
        host.querySelector('.lab-status').textContent = '計算中に問題が起きました。初期状態に戻して値を調整してください。';
      }
    }
    controls.forEach(control => { control.addEventListener('input', update); if (control.tagName === 'SELECT') control.addEventListener('change', update); });
    host.querySelector('[data-reset]').addEventListener('click', () => { controls.forEach(control => { control.value = defaults[control.dataset.key]; }); update(); });
    update();
  }

  const row = (title, key, value, text) => escape(title) + ' = ' + result(key, value, text) + '<br>';
  function plane(extent) {
    const xy = vector => [180 + 115 * vector[0] / extent, 180 - 115 * vector[1] / extent];
    const axes = line(45, 180, 315, 180) + line(180, 55, 180, 305)
      + label(65, 330, '−1') + label(295, 330, '1') + label(180, 354, 'x / S') + label(180, 28, 'y / S')
      + label(44, 73, '1') + label(36, 303, '−1');
    return { xy, axes };
  }
  function mapLab(host) {
    const prefix = 'linear-core-map-' + (++serial), defaults = { s: .5, t: 1, x: 1, y: 1, b1: 1, b2: 1 };
    host.innerHTML = '<div class="lab-controls">'
      + range(prefix, 's', '行列の s', -2, 2, .25, defaults.s) + range(prefix, 't', '行列の t', -2, 2, .25, defaults.t)
      + range(prefix, 'x', '入力 v の第1成分', -2, 2, .25, defaults.x) + range(prefix, 'y', '入力 v の第2成分', -2, 2, .25, defaults.y)
      + range(prefix, 'b1', '目標 b の第1成分', -2, 2, .25, defaults.b1) + range(prefix, 'b2', '目標 b の第2成分', -2, 2, .25, defaults.b2)
      + '</div><p class="lab-note">A=((1,t),(s,1)) の二つの列を動かします。入力 v の像 Av と、方程式 Az=b の目標 b は別のものです。対角成分を1に固定した族なので rank 0 は現れません。</p>' + panels;
    bind(host, defaults, input => {
      const s = math.mapState(input), c1 = s.columns[0], c2 = s.columns[1], sum = c1.map((v, i) => v + c2[i]);
      const extent = 1.2 * Math.max(1, ...c1.map(Math.abs), ...c2.map(Math.abs), ...sum.map(Math.abs));
      const p = plane(extent), vertices = [[0, 0], c1, sum, c2].map(p.xy);
      let geometry = p.axes + '<polygon points="' + vertices.map(v => v.join(',')).join(' ')
        + '" style="fill:var(--series-2);fill-opacity:.12;stroke:var(--series-2);stroke-width:2"/>';
      geometry += arrow(...p.xy([0, 0]), ...p.xy(c1), '--series-1') + arrow(...p.xy([0, 0]), ...p.xy(c2), '--series-2');
      geometry += dot(...p.xy(c1), 7, '--series-1', false) + dot(...p.xy(c2), 3, '--series-2');
      const extent2 = 1.2 * Math.max(1, Math.abs(s.x), Math.abs(s.y), Math.abs(s.b1), Math.abs(s.b2), ...s.transformed.map(Math.abs));
      const q = plane(extent2);
      let vectors = q.axes + path([q.xy([0, 0]), q.xy([s.x, s.y])], '--ink-3', 2, '5 4');
      vectors += dot(...q.xy([s.x, s.y]), 7, '--ink-3', false)
        + arrow(...q.xy([0, 0]), ...q.xy(s.transformed), '--series-1') + arrow(...q.xy([0, 0]), ...q.xy([s.b1, s.b2]), '--series-2');
      vectors += dot(...q.xy(s.transformed), 7, '--series-1', false) + dot(...q.xy([s.b1, s.b2]), 3, '--series-2');
      host.querySelector('[data-figures]').innerHTML = '<h3>二列と、単位正方形の像</h3>'
        + figure(prefix + '-columns', '二列が張る平行四辺形と符号付き面積', '橙の第1列と青の第2列から平行四辺形を描く。両軸共通尺度S=' + number(extent) + '。rank1では面積0に潰れ、同方向の列は重なる。', geometry)
        + '<p class="lab-note">橙：第1列 c₁=(1,s)。青：第2列 c₂=(t,1)。薄い面：単位正方形の像。両軸共通尺度 S=' + number(extent) + '。符号付き面積は det A、面積は |det A| です。列が同方向なら矢印が重なります。橙の輪と青の塗点でも端点を示します。</p><h3>入力の像と、目標を分ける</h3>'
        + figure(prefix + '-vectors', '入力の像と方程式の目標', '灰の破線と輪は入力v、橙はその像Av、青は目標b。原点からの座標を両軸共通尺度S=' + number(extent2) + 'で表示。各図の尺度は異なる。', vectors)
        + '<p class="lab-note">灰の破線と輪：入力 v。橙の矢印と輪：Av。青の矢印と塗点：目標 b。両軸共通尺度 S=' + number(extent2) + '。この図と上の図の S は別です。0ベクトルは原点の点で示し、重なる値は数値欄で確かめます。</p>';
      const kind = { unique: '一意解', infinite: '無限個の解', none: '解なし' }[s.solutionKind];
      host.querySelector('.lab-readout').innerHTML = '<p>' + row('行列 A（行ごと）', 'matrix', s.matrix)
        + row('二列 c₁,c₂', 'columns', s.columns) + row('入力の像 Av', 'transformed', s.transformed)
        + row('符号付き面積 det A', 'determinant', s.determinant) + row('rank A', 'rank', s.rank)
        + row('Az=b の分類', 'solutionKind', s.solutionKind, kind)
        + row('解の代表 zₚ', 'representativeSolution', s.representativeSolution, s.representativeSolution === null ? '存在しない（null）' : undefined)
        + row('核の非零方向', 'kernelDirection', s.kernelDirection, s.kernelDirection === null ? '核は{0}、非零方向なし（null）' : undefined)
        + '</p><p>' + (s.solutionKind === 'infinite' ? '全解は z=zₚ+u(−t,1)、u は任意の実数です。表示した代表は一つの特殊解です。'
          : s.solutionKind === 'none' ? 'b が像の直線上にないため解はありません。核の方向は存在しても、特殊解は存在しません。'
            : '核が{0}なので、表示した解だけが目標へ写ります。')
        + '</p><p>全入力を1/4刻みに限定しているため、det A と b₂−s b₁ の0判定はこのモデルでは二進浮動小数で正確です。一般の測定行列を閾値なしでrank判定できるという意味ではありません。</p>';
      return 'rankは' + s.rank + '、符号付き面積は' + number(s.determinant) + '、目標への方程式は' + kind + 'です。';
    });
  }
  function leastSquaresLab(host) {
    const prefix = 'linear-core-ls-' + (++serial), defaults = { y0: 1, y1: 0, y2: 2, deltaA: 0, deltaB: 0 };
    host.innerHTML = '<div class="lab-controls">'
      + range(prefix, 'y0', 'x=−1 の観測 y₀', -2, 2, .25, defaults.y0) + range(prefix, 'y1', 'x=0 の観測 y₁', -2, 2, .25, defaults.y1)
      + range(prefix, 'y2', 'x=1 の観測 y₂', -2, 2, .25, defaults.y2) + range(prefix, 'deltaA', '候補の切片差 δa', -1, 1, .25, 0)
      + range(prefix, 'deltaB', '候補の傾き差 δb', -1, 1, .25, 0)
      + '</div><p class="lab-note">x=−1,0,1 に対する三つの観測へ a+bx を当てはめます。最適係数に δa,δb を加えた候補も比べます。最小にするのは縦の残差三成分の二乗和です。</p>' + panels;
    bind(host, defaults, input => {
      const s = math.leastSquaresState(input);
      const extent = 1.2 * Math.max(2, ...s.observed.map(Math.abs), Math.abs(s.a - 1.25 * s.b), Math.abs(s.a + 1.25 * s.b),
        Math.abs(s.candidateA - 1.25 * s.candidateB), Math.abs(s.candidateA + 1.25 * s.candidateB));
      const gx = x => 180 + 90 * x, gy = y => 180 - 115 * y / extent;
      let scatter = line(60, 180, 300, 180) + line(180, 60, 180, 300)
        + label(180, 28, 'y / S') + label(180, 351, '観測の位置 x') + label(42, 73, '1') + label(34, 303, '−1');
      [-1, 0, 1].forEach(x => { scatter += label(gx(x), 330, x); });
      scatter += path([[-1.25, s.candidateA - 1.25 * s.candidateB], [1.25, s.candidateA + 1.25 * s.candidateB]].map(([x, y]) => [gx(x), gy(y)]), '--ink-3', 2, '6 5');
      scatter += path([[-1.25, s.a - 1.25 * s.b], [1.25, s.a + 1.25 * s.b]].map(([x, y]) => [gx(x), gy(y)]), '--series-2');
      s.observed.forEach((value, i) => {
        scatter += line(gx(i - 1), gy(value), gx(i - 1), gy(s.fitted[i]), '--series-1', 3)
          + dot(gx(i - 1), gy(s.fitted[i]), 6, '--series-2', false) + dot(gx(i - 1), gy(value), 4, '--series-1');
      });
      const residualExtent = 1.2 * Math.max(.5, ...s.residual.map(Math.abs)), by = value => 180 - 115 * value / residualExtent;
      let bars = line(60, 180, 300, 180) + label(180, 28, '最適残差 r / S')
        + label(42, 73, '1') + label(34, 303, '−1') + label(180, 351, '成分の位置 x');
      s.residual.forEach((value, i) => {
        const x = 90 + 90 * i, y = by(value);
        bars += '<rect x="' + (x - 17) + '" y="' + Math.min(180, y) + '" width="34" height="' + Math.abs(y - 180)
          + '" style="fill:var(--series-1);fill-opacity:.65"/>' + dot(x, y, 4, '--series-1') + label(x, 330, i - 1);
      });
      host.querySelector('[data-figures]').innerHTML = '<h3>縦の差を最小にする</h3>'
        + figure(prefix + '-fit', '三つの観測と最適な直線、係数をずらした候補', '橙の点が観測、青の直線と輪が最小二乗予測、灰の破線が候補。橙の縦線は観測から最適予測まで。横は観測x、縦はyをS=' + number(extent) + 'で割った値で、両軸の縮尺は異なる。', scatter)
        + '<p class="lab-note">橙の点：観測。青の線と輪：最適予測。灰の破線：係数をずらした候補。橙の縦線：最適予測への残差。縦の尺度 S=' + number(extent) + ' は値に応じて変わります。横の x と縦の y は単位・縮尺が異なります。候補と最適が一致すると線は重なります。</p><h3>残差を三成分で読む</h3>'
        + figure(prefix + '-residual', '三成分の最適残差', 'xがマイナス1、0、1の順に最適残差三成分を棒で表す。正なら上、負なら下、0なら中心線上の点。縦の共通尺度S=' + number(residualExtent) + '。', bars)
        + '<p class="lab-note">縦の共通尺度 S=' + number(residualExtent) + '。0は中心線上の点です。上の図の縦線は平面内の直線に垂直な距離ではありません。直交するのは三成分データ空間での残差 r と、(1,1,1)・(−1,0,1) が張る予測の部分空間です。</p>';
      host.querySelector('.lab-readout').innerHTML = '<p>'
        + row('観測三成分', 'observed', s.observed) + row('最適切片 a', 'a', s.a) + row('最適傾き b', 'b', s.b)
        + row('最適予測', 'fitted', s.fitted) + row('最適残差 r', 'residual', s.residual)
        + row('内積 Σr, −r₀+r₂', 'normalResiduals', s.normalResiduals) + row('最適な二乗和 SSE', 'sse', s.sse)
        + row('観測のノルム二乗', 'observedNormSquared', s.observedNormSquared) + row('予測のノルム二乗', 'fitNormSquared', s.fitNormSquared)
        + row('Pythagoras式の計算残差', 'pythagoreanResidual', s.pythagoreanResidual)
        + row('候補の切片', 'candidateA', s.candidateA) + row('候補の傾き', 'candidateB', s.candidateB)
        + row('候補の予測', 'candidateFitted', s.candidateFitted) + row('候補の二乗和', 'candidateSSE', s.candidateSSE)
        + row('恒等式による増加量', 'excess', s.excess)
        + '</p><p>実数の計算では、最適残差の二つの内積は0で、観測のノルム二乗＝予測のノルム二乗＋SSEです。候補の増加量は 3δa²+2δb²。上の内積・Pythagoras残差はブラウザで実際に計算した値で、微小な非零を0へ置き換えません。候補SSEの直接計算と、恒等式から安定計算した増加量も最終桁が異なる場合があります。</p>';
      const integerSecondDifference = 4 * s.y0 - 2 * (4 * s.y1) + 4 * s.y2;
      return '1/4格子の整数判定では3点は' + (integerSecondDifference === 0 ? '共線です。' : '共線ではありません。')
        + 'Pythagorasの恒等式は理論上つねに成り立ち、表示の微小非零は浮動小数の計算残差です。'
        + '最適な二乗和は' + number(s.sse) + '、候補をずらした増加量は' + number(s.excess) + 'です。'
        + (s.deltaA === 0 && s.deltaB === 0 ? '候補係数はこのモデルの最適係数と一致します。' : '候補係数は最適係数と異なります。');
    });
  }
  function spectralLab(host) {
    const prefix = 'linear-core-spectral-' + (++serial), defaults = { lambda1: 2, lambda2: .5, theta: 30, x: 1, y: 1 };
    host.innerHTML = '<div class="lab-controls">'
      + range(prefix, 'lambda1', '構成に使う固有値 λ₁', -2, 3, .25, defaults.lambda1) + range(prefix, 'lambda2', '構成に使う固有値 λ₂', -2, 3, .25, defaults.lambda2)
      + range(prefix, 'theta', '基底の回転 θ（度）', 0, 180, 15, defaults.theta) + range(prefix, 'x', '入力 v の第1成分', -2, 2, .25, defaults.x)
      + range(prefix, 'y', '入力 v の第2成分', -2, 2, .25, defaults.y)
      + '</div><p class="lab-note">Q を角度 θ の回転とし、A=Q diag(λ₁,λ₂) Qᵀ で実対称行列を作ります。λ₁,λ₂ は構成のラベル順で、大きさ順に並べ替えません。下の数値欄の長さの倍率と軸の一意性は、次章で定義する特異値・特異方向の予告です。この実対称行列の族では、特異値は |λ₁|,|λ₂| を大きさ順に並べた値です（一般の行列では違い、次章で扱います）。</p>' + panels;
    bind(host, defaults, input => {
      const s = math.spectralState(input), extent = 1.2 * Math.max(1, Math.abs(s.lambda1), Math.abs(s.lambda2)), p = plane(extent);
      const circle = Array.from({ length: 97 }, (_, i) => [Math.cos(2 * Math.PI * i / 96), Math.sin(2 * Math.PI * i / 96)]);
      const transformedCircle = circle.map(([x, y]) => [s.matrix[0][0] * x + s.matrix[0][1] * y, s.matrix[1][0] * x + s.matrix[1][1] * y]);
      let geometry = p.axes + path(circle.map(p.xy), '--ink-3', 2, '5 5') + path(transformedCircle.map(p.xy), '--series-2', 3);
      s.directions.forEach((q, i) => {
        const color = i === 0 ? '--series-1' : '--series-2', image = q.map(v => v * s.eigenvalues[i]);
        geometry += path([p.xy([0, 0]), p.xy(q)], color, 2, '4 4')
          + arrow(...p.xy([0, 0]), ...p.xy(image), color) + dot(...p.xy(q), 8, color, false) + dot(...p.xy(image), 4, color);
      });
      const extent2 = 1.2 * Math.max(1, Math.abs(s.x), Math.abs(s.y), ...s.transformed.map(Math.abs)), q = plane(extent2);
      let vectors = q.axes + path([q.xy([0, 0]), q.xy([s.x, s.y])], '--ink-3', 2, '5 5')
        + dot(...q.xy([s.x, s.y]), 8, '--ink-3', false) + arrow(...q.xy([0, 0]), ...q.xy(s.transformed), '--series-1')
        + dot(...q.xy(s.transformed), 4, '--series-1');
      const names = { 'positive-definite': '正定値', 'negative-definite': '負定値', indefinite: '不定値',
        'positive-semidefinite': '半正定値（正定値ではない）', 'negative-semidefinite': '半負定値（負定値ではない）', zero: '零行列' };
      host.querySelector('[data-figures]').innerHTML = '<h3>固有方向に沿って、伸ばす・反転する</h3>'
        + figure(prefix + '-circle', '単位円の像と構成に使った固有方向', '灰の破線は単位円、青い曲線はその像。橙がq1、青がq2で、輪は元の単位ベクトル、塗点と矢印はその像lambda倍。負なら反対向き、0なら原点へ潰れる。両軸共通尺度S=' + number(extent) + '。', geometry)
        + '<p class="lab-note">灰の破線：単位円。青の曲線：A による像。橙：q₁、青：q₂。輪と破線は元の単位ベクトル、塗点と矢印は λᵢqᵢ。負なら反転、0なら原点です。両軸共通尺度 S=' + number(extent) + '。円の像は97点を結んだ有限の近似線で示しています。重なる値は数値でも確かめます。</p><h3>任意の入力と、その像</h3>'
        + figure(prefix + '-vector', '入力と実対称行列による像', '灰の破線と輪が入力v、橙の矢印と点がAv。両軸共通尺度S=' + number(extent2) + '。', vectors)
        + '<p class="lab-note">灰：v。橙：Av。両軸共通尺度 S=' + number(extent2) + '。上の図とは S が異なります。二次形式 vᵀAv は二つのベクトルの内積で、下の数値欄に示します。例として θ=0、λ₁=2、λ₂=1/2 を選び、v=(1,0) と v=(1,1) を比べてください。前者では v と Av=(2,0) が平行ですが、後者の Av=(2,1/2) は v と向きが変わります。同じ行列で比べると、上の固有方向が特別な理由を確かめられます。一つの入力で vᵀAv が正でも、全ての非零方向で正とは限りません。</p>';
      host.querySelector('.lab-readout').innerHTML = '<p>' + row('行列 A（行ごと）', 'matrix', s.matrix)
        + row('固有値（構成ラベル順）', 'eigenvalues', s.eigenvalues) + row('構成した q₁,q₂', 'directions', s.directions)
        + row('入力の像 Av', 'transformed', s.transformed) + row('二次形式 vᵀAv', 'quadraticForm', s.quadraticForm)
        + row('trace A', 'trace', s.trace) + row('det A（モデルの値）', 'determinant', s.determinant)
        + row('rank A（モデルの値）', 'rank', s.rank) + row('二次形式の分類', 'formKind', s.formKind, names[s.formKind])
        + row('固有値が重複するか', 'repeatedEigenvalue', s.repeatedEigenvalue, s.repeatedEigenvalue ? '重複する' : '異なる')
        + row('固有方向が直線として一意か', 'eigenDirectionsUnique', s.eigenDirectionsUnique, s.eigenDirectionsUnique ? '一意（符号を除く）' : '一意ではない')
        + row('特異値（降順）', 'singularValues', s.singularValues)
        + row('右特異方向が直線として一意か', 'singularDirectionsUnique', s.singularDirectionsUnique, s.singularDirectionsUnique ? '一意（符号を除く）' : '一意ではない')
        + '</p><p>' + (s.repeatedEigenvalue ? 'λ₁=λ₂ では A=λI で、描いた直交基底は無数の選び方の一例です。'
          : '固有値が異なるため固有方向はそれぞれ一本の直線に定まります。単位ベクトルの符号は選べます。')
        + (s.singularDirectionsUnique ? ' 特異値の大きさも異なります。' : ' 特異値が重複するため、右特異方向の直交基底は一意ではありません。')
        + ' λ₁=−λ₂≠0 では固有方向は区別できても、特異方向は一意になりません。</p><p>rank・det・符号の分類は1/4刻みの λ から得たモデルの数学的値です。浮動小数で作った行列の det に閾値を当ててrankを決めていません。図と Av は通常の浮動小数計算です。この対称行列の族でのみ特異値は |λᵢ| となり、一般の非対称行列の公式ではありません。</p>';
      return '二次形式は' + names[s.formKind] + '、rankは' + s.rank + 'です。'
        + (s.eigenDirectionsUnique ? '固有方向は符号を除いて定まります。' : '描いた固有基底は一例です。');
    });
  }
  function initialize() {
    const labs = { 'linear-core-map': mapLab, 'linear-core-least-squares': leastSquaresLab, 'linear-core-spectral': spectralLab };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) { labs[host.dataset.lab](host); host.dataset.labInitialized = 'true'; }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
