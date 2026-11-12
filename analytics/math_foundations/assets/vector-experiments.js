(function () {
  'use strict';
  const math = globalThis.MathVector;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const raw = value => JSON.stringify(value);
  const number = value => value === 0 ? '0' : Math.abs(value) < .00001 ? value.toExponential(2) : Number(value.toFixed(5)).toString();
  const display = value => Array.isArray(value) ? '(' + value.map(number).join(', ') + ')' : number(value);
  const result = (key, value, text) => `<span data-value="${escape(key)}" data-raw="${escape(raw(value))}" data-raw-value="${escape(raw(value))}"><strong>${escape(text === undefined ? display(value) : text)}</strong></span>`;
  const label = (x, y, text, color = '--ink') => `<text x="${x}" y="${y}" text-anchor="middle" style="fill:var(${color});font-size:22px">${escape(text)}</text>`;
  const line = (x1, y1, x2, y2, color = '--ink-3', width = 2, dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const circle = (x, y, radius, color, filled = true) => `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${filled ? color : '--surface'});stroke:var(${color});stroke-width:3"/>`;
  function arrow(x1, y1, x2, y2, color = '--series-1', dash = '') {
    const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy);
    if (length < .001) return circle(x2, y2, 4, color, false);
    const ux = dx / length, uy = dy / length, head = Math.min(10, length * .4);
    // Each arrowhead has exactly one subpath, including when several arrows
    // share a figure. There is no multi-M path with a single final marker.
    return line(x1, y1, x2, y2, color, 3, dash) + `<path d="M${x2 - head * ux - head * .5 * uy},${y2 - head * uy + head * .5 * ux} L${x2},${y2} L${x2 - head * ux + head * .5 * uy},${y2 - head * uy - head * .5 * ux}" style="fill:none;stroke:var(${color});stroke-width:3"/>`;
  }
  const path = (points, color = '--series-1', width = 3, dash = '') => `<path d="${points.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const figure = (id, title, description, body, height = 360) => `<svg class="lab-svg" viewBox="0 0 360 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(description)}</desc>${body}</svg>`;
  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }
  function select(prefix, key, title, options) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}</span><select id="${prefix}-${key}" data-key="${key}">${options.map(([value, name]) => `<option value="${value}">${name}</option>`).join('')}</select></label>`;
  }
  const orientation = (prefix, title) => select(prefix, 'orientation', title, [[1, '正向き（+1）'], [-1, '逆向き（−1）']]);
  const reset = '<div class="lab-actions"><button type="button" data-action="reset" data-reset>初期状態に戻す</button></div>';
  const panels = '<p class="lab-status" role="status" aria-live="polite"></p><div data-figures></div><div class="lab-readout"></div>';
  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      try {
        const input = Object.fromEntries(controls.map(control => [control.dataset.key, ['field', 'path'].includes(control.dataset.key) ? control.value : Number(control.value)]));
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
  function workPoint(name, t) {
    if (name === 'straight') return [t, t];
    if (name === 'parabola') return [t, t * t];
    if (name === 'x-first') return t <= .5 ? [2 * t, 0] : [1, 2 * t - 1];
    return t <= .5 ? [0, 2 * t] : [2 * t - 1, 1];
  }
  function work(host) {
    const prefix = 'vector-work-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${select(prefix, 'field', 'ベクトル場 F', [['gradient', '勾配場 F=(y,x)=∇(xy)'], ['rotation', '回転場 F=(−y,x)']])}${select(prefix, 'path', 'A=(0,0) と B=(1,1) を結ぶ経路', [['parabola', '放物線 (t,t²)'], ['straight', '線分 (t,t)'], ['x-first', '先に x 方向、次に y 方向'], ['y-first', '先に y 方向、次に x 方向']])}${orientation(prefix, '経路をたどる向き：正は A→B')}${range(prefix, 'n', '各滑らかな部分の中点分割数 n', 16, 128, 16, 32)}</div>${reset}<p class="lab-note">折線は二つの線分をそれぞれ n 分割し、標本数は 2n です。逆向きでは経路も積分の符号も反転します。矢印は場と経路の向きを別々に示します。</p>${panels}`;
    bind(host, { field: 'gradient', path: 'parabola', orientation: 1, n: 32 }, input => {
      const s = math.workState(input), xy = ([x, y]) => [64 + 210 * x, 286 - 210 * y];
      let body = line(42, 286, 330, 286) + line(64, 312, 64, 36) + label(326, 313, 'x') + label(38, 48, 'y');
      for (const x of [.2, .4, .6, .8]) for (const y of [.2, .4, .6, .8]) {
        const fx = s.field === 'gradient' ? y : -y, from = xy([x, y]), to = xy([x + .13 * fx, y + .13 * x]);
        body += arrow(...from, ...to, '--series-2');
      }
      const points = Array.from({ length: 65 }, (_, k) => xy(workPoint(s.path, s.orientation === 1 ? k / 64 : 1 - k / 64)));
      body += path(points, '--series-1', 5);
      for (const t of [.2, .7]) {
        const from = xy(workPoint(s.path, t - s.orientation * .035)), to = xy(workPoint(s.path, t + s.orientation * .035));
        body += arrow(...from, ...to, '--series-1');
      }
      body += circle(...xy(s.start), 8, '--ink', false) + circle(...xy(s.end), 6, '--series-1');
      body += label(101, 333, 'A=(0,0)') + label(266, 53, 'B=(1,1)');
      const comparisons = [['straight', '線分', 0], ['parabola', '放物線', 1/3], ['x-first', 'x先', 1], ['y-first', 'y先', -1]];
      body += label(180, 382, '同じ端点の四経路を比較')
        + line(190, 402, 190, 570, '--ink-3', 1, '4 4');
      comparisons.forEach(([key, name, rotationValue], i) => {
        const yy = 421 + 43 * i, value = s.orientation * (s.field === 'gradient' ? 1 : rotationValue), xx = 190 + 75 * value;
        body += label(57, yy + 7, name)
          + line(190, yy, xx, yy, '--series-2', 5, key === s.path ? '' : '5 4')
          + circle(xx, yy, key === s.path ? 6 : 4, key === s.path ? '--series-1' : '--series-2', key === s.path)
          + label(352, yy + 7, number(value)).replace('text-anchor="middle"', 'text-anchor="end"');
      });
      body += label(190, 591, '0') + label(180, 628, '選択中は塗点。他は白抜き点');
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-plane', 'ベクトル場と向き付き経路', `横と縦は同じ縮尺。青い短い矢印は${s.field === 'gradient' ? '勾配場(y,x)' : '回転場(−y,x)'}。橙の曲線と矢印は${s.orientation === 1 ? 'AからB' : 'BからA'}への経路。白抜きの輪は出発点、塗った点は到着点。下段では同じ場と向きの四経路の厳密な仕事を同時比較する。四例の一致だけで全経路の独立性を証明したわけではない。`, body, 655) + '<p class="lab-note">青い短い矢印：場 F。橙の太い線と矢印：選んだ経路と向き。白抜きの輪：出発点。塗った点：到着点。横・縦は同じ縮尺です。</p>';
      host.querySelector('.lab-readout').innerHTML = `<p>出発点 = ${result('start', s.start)}<br>到着点 = ${result('end', s.end)}<br>向き = ${result('orientation', s.orientation)}<br>滑らかな部分の数 = ${result('pieces', s.pieces)}<br>中点標本の総数 = ${result('samples', s.samples)}<br>厳密な仕事積分 = ${result('exact', s.exact)}<br>中点則の数値和 = ${result('numeric', s.numeric)}<br>絶対誤差 = ${result('error', s.error)}</p><p>${s.field === 'gradient' ? 'F=∇(xy) なので、A→B の厳密値は xy(B)−xy(A)=1。ここにある四経路すべてで同じです。' : '回転場では端点が同じでも値が変わります。A→B の厳密値は、線分0、放物線1/3、xを先に進む折線1、yを先に進む折線−1です。'}</p><p>数値和は各中点で F(γ(t))·γ′(t) を評価しています。有限の標本による一致は、経路独立性や収束の証明ではありません。</p>`;
      return `${s.orientation === 1 ? 'AからB' : 'BからA'}へ進み、${s.samples}個の中点標本と厳密値を比較しています。積分値0も定義された値です。`;
    });
  }
  // Rows of this orthographic projection are orthonormal: the same world
  // scale applies to x,y,z. Foreshortening is projection, not axis rescaling.
  const project = ([x, y, z]) => [180 + 66 * (y - x) / Math.SQRT2, 190 + 66 * ((x + y) / Math.sqrt(6) - z * Math.sqrt(2 / 3))];
  function axes3d() {
    let body = '';
    for (const [point, name, offset] of [[[1.7, 0, 0], 'x', [-12, 15]], [[0, 1.7, 0], 'y', [12, 15]], [[0, 0, 1.7], 'z', [18, 0]]]) {
      const to = project(point); body += line(...project([0, 0, 0]), ...to) + label(to[0] + offset[0], to[1] + offset[1], name);
    }
    return body;
  }
  function flux(host) {
    const prefix = 'vector-flux-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', 'x 方向の傾き a', -1, 1, .25, .5)}${range(prefix, 'b', 'y 方向の傾き b', -1, 1, .25, .25)}${range(prefix, 'c', '鉛直な場 F=(0,0,c) の c', -2, 2, .25, 1)}${orientation(prefix, '面の向き：正は上向き法線')}</div>${reset}<p class="lab-note">面は r(u,v)=(u,v,au+bv)、−1≤u,v≤1。面積、単位法線、流束はすべて解析値です。図は三軸に同じ縮尺を用いた直交投影で、奥行きによる見かけの短縮があります。</p>${panels}`;
    bind(host, { a: .5, b: .25, c: 1, orientation: 1 }, input => {
      const s = math.fluxState(input), corners = [[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]];
      const projected = corners.map(([u, v]) => project([u, v, 0])), surface = corners.map(([u, v]) => project([u, v, s.a * u + s.b * v]));
      const yAxisEnd = project([0, 1.7, 0]), yLabelX = yAxisEnd[0] + 30, yLabelY = yAxisEnd[1] + 15;
      const yAxisLabel = label(yLabelX, yLabelY, 'y');
      let body = axes3d().replace(label(yAxisEnd[0] + 12, yLabelY, 'y'), '') + path(projected, '--ink-3', 3, '7 5');
      for (const [u, v] of corners.slice(0, 4)) body += line(...project([u, v, 0]), ...project([u, v, s.a * u + s.b * v]), '--ink-3', 1, '3 4');
      body += `<polygon points="${surface.slice(0, 4).map(p => p.join(',')).join(' ')}" style="fill:var(--series-2);fill-opacity:.12;stroke:var(--series-2);stroke-width:3"/>`;
      for (const t of [-.5, 0, .5]) {
        body += path([project([t, -1, s.a * t - s.b]), project([t, 1, s.a * t + s.b])], '--series-2', 1);
        body += path([project([-1, t, -s.a + s.b * t]), project([1, t, s.a + s.b * t])], '--series-2', 1);
      }
      const normalEnd = project(s.unitNormal.map(v => 1.05 * v));
      body += arrow(...project([0, 0, 0]), ...normalEnd, '--series-1');
      // The normal is named in the legend below the scene, away from projected grid edges.
      const fieldFrom = project([1.25, -1.25, -.4 * s.c]), fieldTo = project([1.25, -1.25, .4 * s.c]);
      body += arrow(...fieldFrom, ...fieldTo, '--ink', '6 4') + label(fieldFrom[0] - 14, (fieldFrom[1] + fieldTo[1]) / 2 + 7, s.c === 0 ? 'F=0' : 'F').replace('text-anchor="middle"', 'text-anchor="end"');
      // Keep the y-axis name outside every surface/guide footprint, without masking geometry.
      body += yAxisLabel;
      body += label(180, 380, '格子は面S、破線枠はxy投影') + label(180, 415, Math.hypot(normalEnd[0]-180,normalEnd[1]-190)<.001 ? 'nは視線方向（点に投影）' : '実線矢印n ／ 破線矢印F');
      const areaFactor = Math.sqrt(1 + s.a * s.a + s.b * s.b), verticalFactor = s.orientation / areaFactor;
      body += label(180, 450, '矢印の長さは比べない')
        + label(180, 495, '下の二本の棒は同じ目盛') + label(180, 529, '縦の破線は0')
        + line(115, 550, 115, 577, '--ink-3', 1, '4 4') + line(115, 622, 115, 642, '--ink-3', 1, '4 4')
        + line(115, 567, 115 + 95 * areaFactor, 567, '--series-2', 6)
        + circle(115 + 95 * areaFactor, 567, 5, '--series-2')
        + label(180, 604, 'k = ' + number(areaFactor))
        + line(115, 632, 115 + 95 * verticalFactor, 632, '--series-1', 6)
        + circle(115 + 95 * verticalFactor, 632, 5, '--series-1')
        + label(180, 669, 'e_z·n = 向き/k = ' + number(verticalFactor))
        + label(180, 713, '流束 = 4k × c × (向き/k)')
        + label(180, 751, '= 4c×向き = ' + number(s.flux));
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-surface', '傾いた面、投影正方形、向き付き法線', `青い面z=${s.a}x+${s.b}y。灰色の破線はz=0への投影で面積4。橙の矢印nは${s.orientation === 1 ? '上向き' : '下向き'}単位法線。破線矢印Fは鉛直な場でc=${s.c}。三軸は共通の世界座標の縮尺から直交投影したもの。下段の二本は無次元の面積倍率kと鉛直単位方向の法線射影を示す。どちらも同じ単位目盛で、向きだけの反転で後者は負になる。`, body, 784) + '<p class="lab-note">青い実線・格子：面 S。灰色の破線：xy 平面への投影。橙の実線矢印 n：選んだ法線。破線矢印 F：場。F=0 では白抜きの点で示します。a=b=0 では面と投影が重なります。</p>';
      host.querySelector('.lab-readout').innerHTML = `<p>接ベクトル rᵤ = ${result('tangentU', s.tangentU)}<br>接ベクトル rᵥ = ${result('tangentV', s.tangentV)}<br>向き付き面積ベクトル密度 = ${result('normalArea', s.normalArea)}<br>単位法線 n = ${result('unitNormal', s.unitNormal)}<br>曲面の面積 = ${result('area', s.area)}<br>xy 平面への投影面積 = ${result('projectedArea', s.projectedArea)}<br>単位面積あたり F·n = ${result('normalDensity', s.normalDensity)}<br>流束 ∫ F·n dS = ${result('flux', s.flux)}<br>向き = ${result('orientation', s.orientation)}</p><p>rᵤ×rᵥ=(−a,−b,1)。面積は 4√(1+a²+b²) と常に正で、流束は向き×4c です。傾くと面積が増える一方、鉛直場の単位面積あたりの流束が減り、この族では積が一定になります。</p><p>${s.flux === 0 ? '現在の流束は0です。面積が0なのではなく、c=0 なので場が0です。' : s.flux < 0 ? '現在の流束は負です。場は選んだ法線の反対側へ流れています。' : '現在の流束は正です。場は選んだ法線の側へ流れています。'} これらは解析式で求めた値で、数値求積の結果ではありません。</p>`;
      return `面積は正の${number(s.area)}、向き付き流束は${number(s.flux)}です。法線を反転すると流束だけが符号反転します。`;
    });
  }
  function stokes(host) {
    const prefix = 'vector-stokes-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'height', '曲面の高さ h', -1.5, 1.5, .25, .75)}${range(prefix, 'alpha', '場の係数 α', -1, 1, .25, .5)}${orientation(prefix, '曲面と境界の向き：正は上向き・反時計回り')}${range(prefix, 'n', '半径の中点分割数 n', 8, 128, 8, 32)}</div>${reset}<p class="lab-note">曲面は単位円板上の Cartesian グラフ z=h(1−x²−y²)。F=(−y(1+αr²)/2, x(1+αr²)/2, 0)、r²=x²+y² です。高さを変えても境界は z=0 の同じ単位円です。</p>${panels}`;
    bind(host, { height: .75, alpha: .5, orientation: 1, n: 32 }, input => {
      const s = math.stokesState(input), graph = (x, y) => project([x, y, s.height * (1 - x * x - y * y)]);
      let body = axes3d();
      for (const fixed of [-.8, -.4, 0, .4, .8]) {
        const extent = Math.sqrt(1 - fixed * fixed);
        body += path(Array.from({ length: 33 }, (_, k) => graph(fixed, -extent + 2 * extent * k / 32)), '--series-2', 2);
        body += path(Array.from({ length: 33 }, (_, k) => graph(-extent + 2 * extent * k / 32, fixed)), '--series-2', 2);
      }
      const boundary = Array.from({ length: 97 }, (_, k) => project([Math.cos(2 * Math.PI * k / 96), Math.sin(2 * Math.PI * k / 96), 0]));
      body += path(boundary, '--series-1', 4);
      for (const t of [.4, 2.6, 4.6]) {
        const from = project([Math.cos(t - .12 * s.orientation), Math.sin(t - .12 * s.orientation), 0]);
        const to = project([Math.cos(t + .12 * s.orientation), Math.sin(t + .12 * s.orientation), 0]);
        body += arrow(...from, ...to, '--series-1');
      }
      const center = graph(0, 0), normalEnd = project([0, 0, s.height + .65 * s.orientation]);
      body += line(...project([0, 0, 0]), ...center, '--ink-3', 2, '5 4') + circle(...center, 5, '--series-2');
      body += arrow(...center, ...normalEnd, '--series-2');
      body += label(180, 32, s.height > 0 ? 'h>0：上へ膨らむ' : s.height < 0 ? 'h<0：下へ膨らむ' : 'h=0：平らな円板', '--series-2') + label(180, 339, '橙の境界：z=0 の同じ円', '--series-1');
      body += label(180, 378, '青い矢印n：選んだ法線', '--series-2');
      let density = line(54, 190, 326, 190) + line(54, 46, 54, 292) + label(180, 28, 'curl F の z 成分') + label(316, 221, 'r') + label(54, 317, '0') + label(306, 317, '1');
      for (const value of [-1, 0, 1, 2, 3]) density += line(49, 190 - 42 * value, 59, 190 - 42 * value) + label(28, 198 - 42 * value, String(value));
      const densityPoints = Array.from({ length: 65 }, (_, k) => { const r = k / 64; return [54 + 252 * r, 190 - 42 * (1 + 2 * s.alpha * r * r)]; });
      density += path(densityPoints, '--series-2', 4);
      const weighted = r => 2 * r * (1 + 2 * s.alpha * r * r), wx = r => 54 + 252 * r, wy = value => 595 - 26 * value;
      const split = s.alpha < -.5 ? Math.sqrt(-1 / (2 * s.alpha)) : 1;
      const positive = s.alpha < -.5 ? -1 / (4 * s.alpha) : 1 + s.alpha, negative = 1 + s.alpha - positive;
      const band = (a, b, color) => {
        if (b <= a) return '';
        const points = [[wx(a),wy(0)], ...Array.from({length:65},(_,k)=>{const r=a+(b-a)*k/64;return[wx(r),wy(weighted(r))];}), [wx(b),wy(0)]];
        return `<polygon points="${points.map(p=>p.join(',')).join(' ')}" style="fill:var(${color});fill-opacity:.16;stroke:none"/>`;
      };
      density += label(180, 379, 'リングの重み2rを掛ける')
        + label(180, 413, '2r×curl_z F（πは外へ）')
        + band(0, split, '--series-1') + band(split, 1, '--series-2')
        + line(54,wy(0),326,wy(0),'--ink-3',2) + line(54,435,54,654,'--ink-3',2);
      for(const v of[-2,0,3,6]) density += label(28,wy(v)+7,String(v));
      density += path(Array.from({length:97},(_,k)=>{const r=k/96;return[wx(r),wy(weighted(r))];}),'--series-2',3)
        + label(54,682,'0') + label(306,682,'1') + label(330,624,'r')
        + label(180,727,'正側 ' + number(positive) + 'π / 負側 ' + number(negative) + 'π')
        + label(180,771,'向きの負号は、この合計に掛ける');
      host.querySelector('[data-figures]').innerHTML = `<h3>同じ境界をもつ曲面</h3>${figure(prefix + '-surface', '同じ単位円を境界とする高さの異なる曲面', `h=${s.height}。青い格子はCartesianグラフ、橙の曲線は常にz=0の単位円。正向きは上向き法線と上から見て反時計回りの境界、逆向きはその両方を反転。原点でもグラフは正則。三軸の縮尺は共通の直交投影。`, body, 405)}<p class="lab-note">青い格子：曲面。橙の線と矢印：境界と向き。青い矢印 n：中心の法線。正向きの境界は上から見て反時計回りです。三軸は同じ縮尺を直交投影しています。</p><h3>半径と回転の密度</h3>${figure(prefix + '-density', '半径によるcurlの鉛直成分', `横軸rは0から1、縦軸はcurl Fのz成分1+2αr²。この成分は高さと向きの選択では変わらず、向き付き面積ベクトルとの内積は向きに応じて符号反転する。軸の縮尺は異なる。下段はリング面積の重みを入れた2r(1+2αr²)。ゼロ線の上下の符号付き面積をπ倍すると、向きの符号を掛ける前の曲面積分となる。α=-1では正負の面積が各1/4で相殺する。有限の描画が積分の証明ではない。`, density, 800)}<p class="lab-note">curl F=(0,0,1+2αr²)。このグラフの値は高さや面の向きによらず、面積ベクトルとの内積で向きの符号が付きます。横軸は半径、縦軸は密度で、両軸の単位と縮尺は異なります。</p>`;
      host.querySelector('.lab-readout').innerHTML = `<p>境界の半径 = ${result('boundaryRadius', s.boundaryRadius)}<br>境界の高さ = ${result('boundaryHeight', s.boundaryHeight)}<br>中心の向き付き面積ベクトル密度 = ${result('centerNormalArea', s.centerNormalArea)}<br>境界の線積分（厳密値）= ${result('circulationExact', s.circulationExact)}<br>曲面積分（厳密値）= ${result('surfaceExact', s.surfaceExact)}<br>半径 n 分割の中点則 = ${result('surfaceNumeric', s.surfaceNumeric)}<br>絶対誤差 = ${result('error', s.error)}<br>向き = ${result('orientation', s.orientation)}</p><p>上向きの面積ベクトルは (2hx,2hy,1) dxdy で、原点でも0になりません。グラフのパラメータは (x,y) です。求積に用いる極座標の原点を正則なパラメータ点と扱ってはいません。</p><p>両方の厳密値は 向き×π(1+α)。角度の積分 2π は解析的に済ませ、半径の積分だけを有限の中点則で近似します。${s.alpha === -1 ? 'α=−1 では厳密値は0ですが、正負の密度を有限に足した数値和には誤差が残ります。' : '高さを変えても境界と積分値は変わりません。'} 図や有限の数値求積は Stokes の定理の証明ではありません。</p>`;
      return `高さ h=${s.height}でも境界は同じ円です。${s.orientation === 1 ? '上向き法線と反時計回り' : '下向き法線と時計回り'}を同時に選び、厳密値と半径${s.n}分割の有限和を比較しています。`;
    });
  }
  function initialize() {
    const labs = { 'vector-work': work, 'vector-flux': flux, 'vector-stokes': stokes };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) { labs[host.dataset.lab](host); host.dataset.labInitialized = 'true'; }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
