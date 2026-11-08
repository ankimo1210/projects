(function () {
  'use strict';
  const math = globalThis.MathOptimization;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const raw = value => JSON.stringify(value);
  const number = value => value === 0 ? '0' : Math.abs(value) < .00001 || Math.abs(value) >= 100000 ? value.toExponential(4) : Number(value.toFixed(6)).toString();
  const display = value => value === null ? '未定義' : Array.isArray(value) ? '(' + value.map(number).join(', ') + ')' : typeof value === 'number' ? number(value) : String(value);
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
  const figure = (id, title, description, body) => `<svg class="lab-svg" data-visual="optimization-lab" viewBox="0 0 360 360" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(description)}</desc>${body}</svg>`;
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
  function gradient(host) {
    const prefix = 'opt-gradient-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'kappa', '曲率比 κ', 1, 16, 1, 4)}${range(prefix, 'alpha', 'ステップ幅 α', 0, .5, .025, .15)}${range(prefix, 'n', '更新回数 n', 0, 40, 1, 12)}${range(prefix, 'x0', '初期値 x₀', -2, 2, .25, 1)}${range(prefix, 'y0', '初期値 y₀', -2, 2, .25, 1)}</div><p class="lab-note">f(x,y)=(x²+κy²)/2、∇f=(x,κy)。各点を (x,y)←(x,y)−α∇f で逐次計算します。原点が唯一の最小点です。有限回の表示と、無限反復が原点へ収束する条件を分けて読みます。</p>${panels}`;
    bind(host, { kappa: 4, alpha: .15, n: 12, x0: 1, y0: 1 }, input => {
      const s = math.gradientState(input);
      const extent = Math.max(1, ...s.points.flatMap(p => [Math.abs(p.x), Math.abs(p.y)])) * 1.1;
      const xy = ([x, y]) => [180 + 120 * x / extent, 180 - 120 * y / extent];
      let orbit = line(60, 180, 300, 180) + line(180, 60, 180, 300);
      orbit += label(60, 329, '−1') + label(300, 329, '1') + label(180, 352, 'x / S') + label(180, 29, 'y / S');
      orbit += label(40, 68, '1') + label(36, 307, '−1');
      for (const r of [36, 72, 108]) orbit += `<ellipse cx="180" cy="180" rx="${r}" ry="${r / Math.sqrt(s.kappa)}" style="fill:none;stroke:var(--series-2);stroke-width:2;stroke-dasharray:5 5"/>`;
      orbit += path(s.points.map(p => xy([p.x, p.y])), '--series-1');
      orbit += s.points.map(p => dot(...xy([p.x, p.y]), 3)).join('');
      orbit += dot(...xy([s.x0, s.y0]), 8, '--series-1', false) + dot(...xy(s.final), 5, '--series-1');
      const positives = s.points.filter(p => p.logObjective !== null);
      const lower = Math.floor(Math.min(0, ...positives.map(p => p.logObjective))) - .5, upper = Math.ceil(Math.max(0, ...positives.map(p => p.logObjective))) + .5;
      const lx = k => 88 + 228 * k / Math.max(1, s.n), ly = v => 285 - 220 * (v - lower) / (upper - lower);
      let logs = line(88, 65, 88, 285) + line(88, 285, 316, 285) + label(180, 28, 'log₁₀ f(xₖ,yₖ)');
      logs += label(78, 73, number(Number(upper.toFixed(1))), '--ink', 'end') + label(78, 293, number(Number(lower.toFixed(1))), '--ink', 'end');
      logs += label(88, 320, '0') + (s.n ? label(316, 320, s.n) : '') + label(180, 349, '更新回数 k');
      if (positives.length) logs += path(positives.map(p => [lx(p.iteration), ly(p.logObjective)]), '--series-1') + positives.map(p => dot(lx(p.iteration), ly(p.logObjective), 4)).join('');
      else logs += label(195, 180, '全点で f=0');
      const omitted = s.points.length - positives.length;
      host.querySelector('[data-figures]').innerHTML = `<h3>同じ縮尺で見る有限軌道</h3>${figure(prefix + '-orbit', '対角二次関数の等高線と有限回の勾配更新', `横と縦は同じ縮尺S=${number(extent)}。青い破線はこの関数の等高線、橙の点と線は0回目から${s.n}回目までの更新。輪は初期値、塗った点は最終値。`, orbit)}<p class="lab-note">青い破線：f の等高線。橙の点と線：計算した有限軌道。大きな輪：初期値。塗った終点：n 回後。両軸の共通尺度 S=${number(extent)} で座標を割っています。S は値に合わせて変わり、極端に大きな軌道では小さい座標が重なって見えます。</p><h3>目的関数の大きさ</h3>${figure(prefix + '-objective', '更新回数と目的関数の常用対数', `横軸は更新回数0から${s.n}、縦軸は正の目的関数値の常用対数。f=0の${omitted}点は対数未定義のため描かない。両軸の単位と縮尺は異なる。`, logs)}<p class="lab-note">正の f のみ log₁₀ f を描きます。f=0 の${omitted}点は対数が未定義なので省略し、0を代わりの高さに置きません。線は点の順序を示す補助線で、横軸と縦軸の単位・縮尺は異なります。</p>`;
      const globalText = { contracting: '全初期値で原点への厳密な収縮', boundary: '収縮条件の境界（全初期値の収束保証なし）', unstable: '全初期値の収縮条件外（増幅方向あり）' }[s.allInitialState];
      const orbitText = { 'fixed-origin': '原点なので全ステップ幅で不動', contracting: 'この初期値では原点へ収束する条件を満たす', boundary: 'この非零初期値は原点へ収束しない', unstable: 'この初期値は増幅する方向を含む' }[s.trajectoryState];
      host.querySelector('.lab-readout').innerHTML = `<p>倍率 (q₁,q₂) = ${result('factors', s.factors)}<br>全方向の最大増幅率 ρ = ${result('rho', s.rho)}<br>上側の境界 2/κ = ${result('criticalAlpha', s.criticalAlpha)}<br>全初期値の条件 0&lt;α&lt;2/κ = ${result('contractsAll', s.contractsAll, s.contractsAll ? '満たす' : '満たさない')}<br>全初期値について = ${result('allInitialState', s.allInitialState, globalText)}<br>この初期値について = ${result('trajectoryState', s.trajectoryState, orbitText)}<br>この初期値が原点へ収束する条件 = ${result('trajectoryConverges', s.trajectoryConverges, s.trajectoryConverges ? '満たす（無限反復の解析条件）' : '満たさない')}<br>実行した更新回数 = ${result('iterations', s.n)}<br>n 回後の (xₙ,yₙ) = ${result('final', s.final)}<br>初期目的関数 f₀ = ${result('initialObjective', s.initialObjective)}<br>n 回後の目的関数 fₙ = ${result('objective', s.objective)}<br>比 fₙ/f₀ = ${result('objectiveRatio', s.objectiveRatio, s.objectiveRatio === null ? '未定義：f₀=0 のため 0/0' : display(s.objectiveRatio))}</p><p>${s.n === 0 ? 'n=0 は未反復です。初期値を表示しているだけで、停止を収束の観測とは呼びません。' : '表示したのは指定回数だけの計算値です。有限の軌道や目的関数の減少を、一般の関数に対する収束の証明とは呼びません。'} y₀=0 なら y 方向の不安定性は現れず、全初期値の条件外でも原点へ収束する場合があります。α=0 の非原点の定数列は、原点へは収束しません。</p>`;
      return `${s.n === 0 ? '更新はまだ行っていません。' : `${s.n}回の有限更新を表示しています。`} ${globalText}。${orbitText}。`;
    });
  }
  function projection(host) {
    const prefix = 'opt-projection-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${select(prefix, 'kind', '閉凸集合 C', [['disk', '円板：中心0、半径 r'], ['box', '正方形：中心0、半辺長 r']])}${range(prefix, 'x', '点 p の x 座標', -2, 2, .25, 1.5)}${range(prefix, 'y', '点 p の y 座標', -2, 2, .25, 1)}${range(prefix, 'radius', '半径／半辺長 r', .5, 1.5, .25, 1)}</div><p class="lab-note">q=P<sub>C</sub>(p) は C で p に最も近い点です。円板の外では q=rp/‖p‖、正方形では各座標を [−r,r] へ切り詰めます。集合内の p はそのまま q になります。</p>${panels}`;
    bind(host, { kind: 'disk', x: 1.5, y: 1, radius: 1 }, input => {
      const s = math.projectionState(input), xy = ([x, y]) => [180 + 50 * x, 180 - 50 * y];
      const p = xy([s.x, s.y]), q = xy(s.projected), r = 50 * s.radius;
      let body = line(60, 180, 300, 180) + line(180, 60, 180, 300);
      body += label(80, 329, '−2') + label(280, 329, '2') + label(180, 352, 'x') + label(180, 29, 'y') + label(39, 88, '2') + label(34, 288, '−2');
      body += s.kind === 'disk'
        ? `<circle cx="180" cy="180" r="${r}" style="fill:var(--series-2);fill-opacity:.1;stroke:var(--series-2);stroke-width:3"/>`
        : `<rect x="${180 - r}" y="${180 - r}" width="${2 * r}" height="${2 * r}" style="fill:var(--series-2);fill-opacity:.1;stroke:var(--series-2);stroke-width:3"/>`;
      body += arrow(...q, ...p, '--series-1') + dot(...q, 6, '--series-2') + dot(...p, 8, '--series-1', false);
      // Nearby points have one combined label; it never asserts equality
      // unless the computed distance actually vanishes.
      const pointLabel = s.distance === 0 ? 'p=q' : s.distance < .8 ? 'p・q' : 'p';
      let labelX = p[0] + (s.distance > 0 && s.residual[0] < 0 ? -25 : 25);
      let labelY = p[1] + (s.distance > 0 && s.residual[1] < 0 ? 32 : -18);
      if (Math.abs(labelX - 180) < 20) labelX += p[0] >= 180 ? 25 : -25;
      if (labelY > 174 && labelY < 210) labelY = p[1] <= 180 ? 215 : 160;
      if (labelY > 300) labelY = 325;
      body += s.distance === 0 ? label(285, 45, pointLabel) : label(labelX, labelY, pointLabel);
      if (s.distance >= .8) {
        const ux = s.residual[0] / s.distance, uy = -s.residual[1] / s.distance;
        // Offset both outward and across the residual, then avoid either coordinate axis.
        let qLabelX = q[0] + 30 * (ux + uy), qLabelY = q[1] + 30 * (uy - ux) + 8;
        if (Math.abs(qLabelX - 180) < 20) qLabelX = qLabelX >= 180 ? 205 : 155;
        if (qLabelY > 174 && qLabelY < 210) qLabelY = q[1] <= 180 ? 215 : 165;
        body += label(Math.max(45, Math.min(315, qLabelX)), Math.max(55, Math.min(305, qLabelY)), 'q', '--series-2');
      }
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-set', '閉凸集合へのEuclid射影と残差', `横と縦は同じ縮尺。青い${s.kind === 'disk' ? '円板' : '正方形'}がC。橙の白抜き点はp、青い点は射影q。橙の矢印はqからpへの残差p−q。距離0なら点は重なり、p=qの一つのラベルで表す。`, body) + '<p class="lab-note">橙の輪：p。青い点：q。橙の矢印：q から p への残差 p−q。残差0では矢印の向きを作らず、重なった点に p=q と表示します。両軸は同じ縮尺です。</p>';
      const location = { inside: '集合の内部', boundary: '集合の境界上', outside: '集合の外部' }[s.inputLocation];
      host.querySelector('.lab-readout').innerHTML = `<p>射影 q = ${result('projected', s.projected)}<br>残差 p−q = ${result('residual', s.residual)}<br>距離 ‖p−q‖ = ${result('distance', s.distance)}<br>最小の二乗距離 /2 = ${result('objective', s.objective)}<br>残差の単位方向 = ${result('residualUnit', s.residualUnit, s.residualUnit === null ? '未定義：残差0を単位化できない' : display(s.residualUnit))}<br>入力 p の位置 = ${result('inputLocation', s.inputLocation, location)}</p><p>この射影は、すべての z∈C に対して (p−q)·(z−q)≤0 を満たします。一般には直交の等号ではありません。${s.distance === 0 ? '現在は p=q なので左辺はすべて0です。残差方向を単位化できないことと、境界の幾何学的法線が存在しないことは別です。' : s.kind === 'box' ? '正方形の角では、この不等式を満たす外向きの方向が複数あります。描く残差はその一つです。' : '円板の外からの残差は、射影点の外向き半径方向です。'}</p><p>図は計算された射影を示します。有限個の点を眺めることは、すべての z に対する不等式の証明ではありません。</p>`;
      return `${location}の p を射影しました。${s.distance === 0 ? '距離は0で、残差の単位方向は未定義です。' : `距離は${number(s.distance)}です。`}`;
    });
  }
  function kkt(host) {
    const prefix = 'opt-kkt-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', '目的関数の中心 a', -2, 2, .1, 0)}${range(prefix, 'b', '制約の境界 b', -1.5, 1.5, .1, 1)}${range(prefix, 'lambda', '試す双対乗数 λ', 0, 4, .1, 0)}</div><p class="lab-note">min (x−a)²/2、制約 x≥b。g(x)=b−x≤0、L(x,λ)=(x−a)²/2+λ(b−x) の符号で統一します。最小点 x*=max(a,b) は解析式で求め、入力した λ と最適乗数 λ*=max(b−a,0) を比べます。</p>${panels}`;
    bind(host, { a: 0, b: 1, lambda: 0 }, input => {
      const s = math.kktState(input), px = x => 60 + 42 * (x + 3), py = f => 285 - 230 * f / 13;
      let primal = `<rect x="${px(s.b)}" y="55" width="${312 - px(s.b)}" height="230" style="fill:var(--series-2);fill-opacity:.12"/>`;
      primal += line(60, 285, 312, 285) + line(60, 55, 60, 285) + line(px(s.b), 55, px(s.b), 285, '--series-2', 2, '6 5');
      primal += path(Array.from({ length: 97 }, (_, i) => { const x = -3 + i / 16; return [px(x), py((x - s.a) ** 2 / 2)]; }));
      primal += dot(px(s.xStar), py(s.primalOptimal), 6, '--series-2') + label(px(s.xStar) + (s.active ? -22 : 22), py(s.primalOptimal) - 17, 'x*', '--series-2');
      primal += label(180, 28, 'f(x)=(x−a)²/2') + label(60, 320, '−3') + label(312, 320, '3') + label(px(s.b), 320, 'b', '--series-2') + label(180, 349, 'x');
      primal += label(47, 293, '0', '--ink', 'end') + label(47, 63, '13', '--ink', 'end');
      const dualLower = Math.floor(Math.min(0, 4 * (s.b - s.a) - 8) * 2) / 2 - .5;
      const dualUpper = Math.ceil(Math.max(.5, s.primalOptimal) * 2) / 2 + .5;
      const dx = lambda => 88 + 57 * lambda, dy = value => 285 - 230 * (value - dualLower) / (dualUpper - dualLower);
      const top = dy(s.primalOptimal), bottom = dy(s.dualValue), currentX = dx(s.lambda);
      let dual = line(88, 55, 88, 285) + line(88, dy(0), 316, dy(0));
      dual += path(Array.from({ length: 97 }, (_, i) => { const lambda = i / 24; return [dx(lambda), dy(lambda * (s.b - s.a) - lambda * lambda / 2)]; }), '--series-2');
      dual += line(88, top, 316, top, '--ink-3', 2, '6 5') + label(296, top - 18, 'p*');
      dual += dot(dx(s.lambdaStar), top, 7, '--series-2', false);
      if (s.dualGap > 0) dual += line(currentX, top, currentX, bottom, '--series-1', 3) + line(currentX - 6, top, currentX + 6, top, '--series-1', 3);
      dual += dot(currentX, bottom, 5, '--series-1');
      dual += label(180, 28, '双対下界 d(λ) と p*') + label(88, 320, '0') + label(316, 320, '4') + label(180, 349, 'λ≥0');
      dual += label(78, 63, number(dualUpper), '--ink', 'end') + label(78, 293, number(dualLower), '--ink', 'end');
      host.querySelector('[data-figures]').innerHTML = `<h3>主問題：実行可能な場所で最小化</h3>${figure(prefix + '-primal', '二次目的関数と半直線制約の最小点', `横軸xは−3から3、縦軸fは0から13。青い領域はx≥b=${number(s.b)}、破線は境界、青い点が最小点x*=${number(s.xStar)}。横軸と縦軸の単位と縮尺は異なる。`, primal)}<p class="lab-note">橙：目的関数。青い領域：実行可能な x≥b。青い点：x*。横軸 x は [−3,3]、縦軸 f は [0,13] で、単位と縮尺は異なります。</p><h3>双対問題：下界と最適値の差</h3>${figure(prefix + '-dual', '双対関数の値と主最適値との非負の差', `横軸λは0から4、縦軸は${number(dualLower)}から${number(dualUpper)}。青い曲線d(λ)、灰色の破線p*、青い輪は最適乗数λ*、橙の点は入力λでの双対値。橙の縦線は同じ縦尺度のp*とd(λ)の差。主問題の図とは軸の単位と縮尺が異なる。`, dual)}<p class="lab-note">青い曲線：d(λ)=λ(b−a)−λ²/2。灰色の破線：p*。青い輪：λ*。橙の点：入力 λ の下界。橙の縦線：同じ縦尺度で測る gap。差0では点が重なります。横軸 λ は [0,4]、縦軸は [${number(dualLower)},${number(dualUpper)}] で値に応じて変わります。上の主問題の図とは軸の単位・縮尺が異なります。</p>`;
      host.querySelector('.lab-readout').innerHTML = `<p>主最小点 x* = ${result('xStar', s.xStar)}<br>最適乗数 λ* = ${result('lambdaStar', s.lambdaStar)}<br>主最適値 p* = ${result('primalOptimal', s.primalOptimal)}<br>入力 λ の双対下界 d(λ) = ${result('dualValue', s.dualValue)}<br>双対 gap p*−d(λ) = ${result('dualGap', s.dualGap)}<br>停留条件の残差 x*−a−λ = ${result('stationarity', s.stationarity)}<br>制約値 g(x*)=b−x* = ${result('gValue', s.gValue)}<br>余裕 x*−b = ${result('slack', s.slack)}<br>相補性の積 λg(x*) = ${result('complementarity', s.complementarity)}<br>制約が active か = ${result('active', s.active, s.active ? '境界上（active）' : '正の余裕あり')}<br>入力 λ の双対実行可能性 = ${result('dualFeasible', s.dualFeasible, 'λ≥0 を満たす')}<br>KKT 残差が計算値でともに0か = ${result('kktSatisfied', s.kktSatisfied, s.kktSatisfied ? 'ともに0' : '少なくとも一つは非零')}</p><p>入力 λ は常に双対実行可能ですが、任意の λ で停留条件と相補性が成立するわけではありません。a=b では制約は active でも λ*=0 です。λg(x*) の符号で相補性を表示しており、λ×余裕ではありません。</p><p>gap は桁落ちを抑える等価な式で計算します。δ=b−a≥0 なら (λ−δ)²/2、δ&lt;0 なら λ²/2−δλ です。表示値はブラウザの浮動小数計算で、微小な非零の残差も0へ置き換えません。丸め表示で λ と λ* が同じに見えても残差が非零の場合があります。「残差0」はこの計算値の判定で、一般の最適性の証明ではありません。</p>`;
      // The native controls represent exact tenths; binary residuals remain visible.
      const exactMultiplierTicks = Math.max(Math.round(s.b * 10) - Math.round(s.a * 10), 0);
      const gridOptimal = Math.round(s.lambda * 10) === exactMultiplierTicks;
      const residualText = s.kktSatisfied ? 'KKT残差は計算値でともに0です。'
        : gridOptimal ? '0.1刻みの厳密な値では最適乗数です。表示された微小なKKT残差とgapは、b−aなどの浮動小数計算の丸めによるものです。'
        : 'この入力は0.1刻みの厳密な値でも最適乗数と異なり、KKT残差が残っています。';
      return `主最適値は${number(s.primalOptimal)}、入力した双対乗数の下界は${number(s.dualValue)}、gapは${number(s.dualGap)}です。${residualText}`;
    });
  }
  function initialize() {
    const labs = { 'opt-gradient': gradient, 'opt-projection': projection, 'opt-kkt': kkt };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) { labs[host.dataset.lab](host); host.dataset.labInitialized = 'true'; }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
