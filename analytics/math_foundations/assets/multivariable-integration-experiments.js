(function () {
  'use strict';
  const math = globalThis.MathMultivariableIntegration;
  if (!math) return;
  let serial = 0;
  const rad = degrees => degrees * Math.PI / 180;
  const fmt = value => {
    if (value === 0) return '0';
    if (Math.abs(value) <= 1e-12) return '約0';
    return Math.abs(value) < 1e-4 ? value.toExponential(3) : value.toFixed(4).replace(/\.?0+$/, '');
  };
  const label = (x, y, text, anchor = 'middle', size = 28) => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink-2);font-size:${size}px">${text}</text>`;
  const line = (x1, y1, x2, y2, color = '--grid', dash = '', width = 2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const curve = (points, color, dash = '', width = 3) => `<polyline points="${points.map(p => p.join(',')).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const dot = (x, y, color, radius = 5) => `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${color});stroke:var(${color});stroke-width:1"/>`;
  function chart(xmin, xmax, ymin, ymax, xticks, yticks, xlabel, ylabel, plane = false) {
    const left = plane ? 112 : 82, right = plane ? 366 : 444;
    const x = v => left + (right - left) * (v - xmin) / (xmax - xmin);
    const y = v => 290 - 254 * (v - ymin) / (ymax - ymin);
    let svg = '';
    xticks.forEach(tick => {
      const [v, text] = Array.isArray(tick) ? tick : [tick, fmt(tick)];
      svg += line(x(v), 36, x(v), 290) + label(x(v), 325, text);
    });
    yticks.forEach(tick => {
      const [v, text] = Array.isArray(tick) ? tick : [tick, fmt(tick)];
      svg += line(left, y(v), right, y(v)) + label(left - 11, y(v) + 9, text, 'end');
    });
    if (xmin <= 0 && xmax >= 0) svg += line(x(0), 36, x(0), 290, '--ink-2');
    if (ymin <= 0 && ymax >= 0) svg += line(left, y(0), right, y(0), '--ink-2');
    svg += label(right, 360, xlabel, 'end') + label(left, 26, ylabel, 'start');
    return { x, y, svg };
  }
  function figure(id, title, description, body, height = 374) {
    return `<svg class="lab-svg" viewBox="0 0 480 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${title}</title><desc id="${id}-desc">${description}</desc>${body}</svg>`;
  }
  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }
  const reset = '<div class="lab-actions"><button type="button" data-action="reset">初期状態に戻す</button></div>';
  const panels = '<div data-figures></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div><p class="lab-note">数値は浮動小数点の近似です。絶対値が10⁻¹²以下の非零値を「約0」と表示します。図の観察と本文の証明を区別してください。</p>';
  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      const values = Object.fromEntries(controls.map(c => [c.dataset.key, c.tagName === 'SELECT' ? c.value : Number(c.value)]));
      host.querySelectorAll('[data-value]').forEach(o => { o.textContent = fmt(values[o.dataset.value]) + (['angle', 'angularWidth'].includes(o.dataset.value) ? '°' : ''); });
      try { render(values); }
      catch (error) {
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = 'この数値範囲では計算できません。初期状態に戻すか、値を調整してください。';
      }
    }
    controls.forEach(c => c.addEventListener(c.tagName === 'SELECT' ? 'change' : 'input', update));
    host.querySelector('[data-action="reset"]').addEventListener('click', () => {
      controls.forEach(c => { c.value = defaults[c.dataset.key]; });
      update();
    });
    update();
  }
  function rectangles(host) {
    const prefix = 'multivariable-double-integral-' + (++serial);
    const names = { lower: '下和（左下）', upper: '上和（右上）', midpoint: '中点和' };
    const colors = { lower: '--series-1', upper: '--series-2', midpoint: '--ink-2' };
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'n', '各軸の分割数 n', 1, 32, 1, 4)}<label class="lab-control" for="${prefix}-rule"><span class="lab-control-label">セルの代表点</span><select id="${prefix}-rule" data-key="rule"><option value="lower">下和：左下</option><option value="upper">上和：右上</option><option value="midpoint" selected>中点和：中心</option></select></label></div>${reset}<p class="lab-note">単位正方形の密度f(x, y) = x² + y²を足し合わせます。第一図は両軸が同じ縮尺です。橙の色が濃いセルほど選んだ代表点の密度が大きく、塗りつぶし点が代表点です。図が表すのは密度であり、セルの寄与は密度×セル面積です。</p><p class="lab-note">第二図は橙の実線が下和、青の破線が上和、灰色の点線の曲線が中点和、灰色の水平線が真値2/3です。大きな丸は現在選んだ和を示します。縦の点線は現在のnです。nは整数なので曲線は整数の点をつないだ補助線です。</p>${panels}`;
    // At most 32² cells per state; only the scalar convergence values are retained.
    const convergence = Array.from({ length: 32 }, (_, i) => {
      const s = math.rectangleSumState(i + 1, 'midpoint');
      return { n: s.n, lower: s.lower, upper: s.upper, midpoint: s.midpoint };
    });
    bind(host, { n: 4, rule: 'midpoint' }, ({ n, rule }) => {
      const state = math.rectangleSumState(n, rule);
      const plane = chart(-.08, 1.08, -.08, 1.08, [0, .5, 1], [.5, 1], 'x', 'y', true);
      state.cells.forEach(cell => {
        const x1 = plane.x(cell.i / n), x2 = plane.x((cell.i + 1) / n);
        const y1 = plane.y((cell.j + 1) / n), y2 = plane.y(cell.j / n);
        plane.svg += `<rect x="${x1}" y="${y1}" width="${x2 - x1}" height="${y2 - y1}" style="fill:var(--series-1);fill-opacity:${.06 + .84 * cell.density / 2};stroke:var(--grid);stroke-width:.7"/>`;
      });
      state.cells.forEach(cell => { plane.svg += dot(plane.x(cell.x), plane.y(cell.y), '--ink-2', Math.min(4, 30 / n)); });
      const selected = state.cells.find(cell => cell.i === n - 1 && cell.j === n - 1);
      const cellLeft = plane.x((n - 1) / n), cellRight = plane.x(1);
      const cellTop = plane.y(1), cellBottom = plane.y((n - 1) / n);
      plane.svg += `<rect x="${cellLeft}" y="${cellTop}" width="${cellRight-cellLeft}" height="${cellBottom-cellTop}" style="fill:none;stroke:var(--ink-2);stroke-width:3;stroke-dasharray:5 3"/>`
        + label(240, 398, '破線の右上セルを取り出す', 'middle', 24)
        + label(240, 440, `密度 ${fmt(selected.density)} × 面積 ${fmt(state.cellArea)}`)
        + label(240, 482, `このセルの寄与 = ${fmt(selected.density*state.cellArea)}`);
      const sums = chart(1, 32, 0, 2.2, [1, 16, 32], [0, 1, 2], 'n', '和');
      sums.svg += line(sums.x(1), sums.y(state.integral), sums.x(32), sums.y(state.integral), '--ink-2');
      for (const [key, dash] of [['lower', ''], ['upper', '9 6'], ['midpoint', '3 6']]) sums.svg += curve(convergence.map(s => [sums.x(s.n), sums.y(s[key])]), colors[key], dash);
      sums.svg += line(sums.x(n), 36, sums.x(n), 290, '--ink-2', '3 6') + dot(sums.x(n), sums.y(state.sum), colors[rule], 7);
      const description = `n = ${n}、${n * n}セル、${names[rule]} = ${fmt(state.sum)}、上下和の差 ${fmt(state.gap)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">入力平面：密度と代表点</p>${figure(prefix + '-cells', '密度をセル面積で重み付けする', description + '右上の破線セルの密度と面積を下段で掛け、この一セルの寄与を示す。色の濃さ自体は面積や寄与ではない。', plane.svg, 510)}<p class="lab-note">分割数と三つの和</p>${figure(prefix + '-sums', '上下和と中点和の収束', description + '真値は2/3です。', sums.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>分割数 n = ${state.n}、セル数 = ${state.cells.length}<br>規則：${names[rule]}<br>各セルの面積 = ${fmt(state.cellArea)}<br>選んだ和 = <strong>${fmt(state.sum)}</strong><br>下和 L = ${fmt(state.lower)}<br>上和 U = ${fmt(state.upper)}<br>中点和 M = ${fmt(state.midpoint)}<br>真値 I = 2/3 ≈ ${fmt(state.integral)}<br>上下和の差 U − L = ${fmt(state.gap)}<br>選んだ和 − I = ${fmt(state.sum - state.integral)}</p><p>下和と上和はこの単調な密度のセル最小・最大から得ています。中点和が常に上下和の中点になるとは限りません。図の収束は観察用で、積分可能性は本文の議論によります。</p>`;
    });
  }
  function polar(host) {
    const prefix = 'multivariable-polar-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'innerRadius', '内半径 r₀', 0, 1.5, .1, .5)}${range(prefix, 'radialWidth', '半径方向の幅 Δr', .1, .5, .1, .5)}${range(prefix, 'angle', '開始角 θ₀', -180, 180, 5, 0)}${range(prefix, 'angularWidth', '角幅 Δθ', 5, 90, 5, 90)}</div>${reset}<p class="lab-note">第一図はxy平面の環状扇形で、両軸は同じ縮尺です。橙の境界と塗りが選んだセル、塗りつぶし点が四隅の像です。内半径0では二つの隅が原点で重なります。</p><p class="lab-note">第二図は座標領域の矩形です。縦軸は開始角からの差φ = θ − θ₀（rad）、横軸は半径rで、両軸の単位と縮尺は異なります。操作角は度表示ですが、面積の計算にはradを用います。二つの図の見た目の大きさから面積を比較しないでください。</p>${panels}`;
    bind(host, { innerRadius: .5, radialWidth: .5, angle: 0, angularWidth: 90 }, values => {
      const state = math.polarCellState({ innerRadius: values.innerRadius, radialWidth: values.radialWidth, angleRad: rad(values.angle), angularWidth: rad(values.angularWidth) });
      const plane = chart(-2.2, 2.2, -2.2, 2.2, [-2, 0, 2], [-2, 2], 'x', 'y', true);
      const arc = (radius, backwards = false) => Array.from({ length: 65 }, (_, i) => {
        const a = state.angleRad + state.angularWidth * (backwards ? 64 - i : i) / 64;
        return [plane.x(radius * Math.cos(a)), plane.y(radius * Math.sin(a))];
      });
      const boundary = [...arc(state.outerRadius), ...arc(state.innerRadius, true)];
      plane.svg += `<polygon points="${boundary.map(p => p.join(',')).join(' ')}" style="fill:var(--series-1);fill-opacity:.22;stroke:var(--series-1);stroke-width:3"/>`;
      state.corners.forEach(p => { plane.svg += dot(plane.x(p.x), plane.y(p.y), '--series-1', 5); });
      plane.svg += curve(arc(state.midpointRadius), '--series-2', '6 4', 3);
      const middleAngle = state.angleRad + state.angularWidth / 2;
      plane.svg += line(plane.x(state.innerRadius*Math.cos(middleAngle)), plane.y(state.innerRadius*Math.sin(middleAngle)),
        plane.x(state.outerRadius*Math.cos(middleAngle)), plane.y(state.outerRadius*Math.sin(middleAngle)), '--ink-2', '3 3', 3)
        + label(240, 398, `中点の弧 rₘΔθ = ${fmt(state.midpointRadius*state.angularWidth)}`, 'middle', 24)
        + label(240, 440, `Δr × 弧長 = ${fmt(state.exactArea)}`, 'middle', 24)
        + label(240, 482, '環状扇形の厳密式。一般変換は極限', 'middle', 24);
      const coordinates = chart(-.1, 2.1, -.12, 1.7, [0, 1, 2], [[0, '0'], [Math.PI / 4, 'π/4'], [Math.PI / 2, 'π/2']], 'r', 'φ (rad)');
      const left = coordinates.x(state.innerRadius), right = coordinates.x(state.outerRadius);
      const top = coordinates.y(state.angularWidth), bottom = coordinates.y(0);
      coordinates.svg += `<rect x="${left}" y="${top}" width="${right - left}" height="${bottom - top}" style="fill:var(--series-2);fill-opacity:.22;stroke:var(--series-2);stroke-width:3"/>`;
      [[left, bottom], [right, bottom], [right, top], [left, top]].forEach(([x, y]) => { coordinates.svg += dot(x, y, '--series-2'); });
      const description = `内半径 ${fmt(state.innerRadius)}、外半径 ${fmt(state.outerRadius)}、開始角 ${fmt(values.angle)}度、角幅 ${fmt(values.angularWidth)}度。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">xy平面：環状扇形の実際の面積</p>${figure(prefix + '-plane', '環状扇形の面積を幅と中間の弧で読む', description + `破線は中点半径の円弧、点線は半径方向の幅。同じ幅でも半径が大きければ弧が長い。厳密な面積は ${fmt(state.exactArea)}。一般の有限セルで中点Jacobianが厳密になることは示さない。`, plane.svg, 510)}<p class="lab-note">座標領域：半径と開始角からの角度差</p>${figure(prefix + '-coordinates', '極座標領域の矩形', description + `ΔrΔθは ${fmt(state.coordinateProduct)}。これはxy平面の面積ではありません。`, coordinates.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>内半径 r₀ = ${fmt(state.innerRadius)}<br>外半径 r₁ = ${fmt(state.outerRadius)}<br>半径方向の幅 Δr = ${fmt(state.radialWidth)}<br>開始角 θ₀ = ${fmt(values.angle)}°（${fmt(state.angleRad)} rad）<br>角幅 Δθ = ${fmt(values.angularWidth)}°（${fmt(state.angularWidth)} rad）</p><p>xy平面の面積 (r₁² − r₀²)Δθ/2 = <strong>${fmt(state.exactArea)}</strong><br>座標領域の積 ΔrΔθ = <strong>${fmt(state.coordinateProduct)}</strong><br>面積と座標積の比 = ${fmt(state.areaRatio)}<br>中点半径 (r₀ + r₁)/2 = ${fmt(state.midpointRadius)}<br>中点でのJacobian |det DT| = ${fmt(state.jacobianAtMidpoint)}</p><p>環状扇形では面積÷座標積が中点半径と正確に一致します。これはこのセルの扇形公式による等式です。一般の変換で有限セルの面積が中点Jacobian×座標積と必ず一致するわけではありません。</p><p>描画の円弧は有限個の線分による近似です。数値欄の面積は本文の扇形公式で計算しています。</p><p>内半径0の原点ではJacobianが0です。この場合の面積公式は、本文で原点付近の除外誤差を0へ近づける議論によって拡張しています。</p>`;
    });
  }
  function initialize() {
    const labs = { 'multivariable-double-integral': rectangles, 'multivariable-polar': polar };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) {
        labs[host.dataset.lab](host);
        host.dataset.labInitialized = 'true';
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
