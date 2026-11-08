(function () {
  'use strict';
  const math = globalThis.MathMultivariable;
  if (!math) return;
  let serial = 0;
  const fmt = value => {
    if (value === 0) return '0';
    return Math.abs(value) < 1e-4 || Math.abs(value) > 1e4
      ? value.toExponential(3) : value.toFixed(4).replace(/\.?0+$/, '');
  };
  const label = (x, y, text, anchor = 'middle') =>
    `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink-2);font-size:26px">${text}</text>`;
  const line = (x1, y1, x2, y2, color = '--grid', dash = '') =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:2;${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const curve = (points, color, dash = '', width = 3) => points.length < 2 ? '' :
    `<polyline points="${points.map(p => p.join(',')).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const dot = (x, y, color, open = false, radius = 6) =>
    `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${open ? '--surface' : color});stroke:var(${color});stroke-width:3"/>`;
  const square = (x, y, color) =>
    `<rect x="${x - 5}" y="${y - 5}" width="10" height="10" style="fill:var(${color})"/>`;

  function chart(xmin, xmax, ymin, ymax, xticks, yticks, xlabel, ylabel, squarePlot = false) {
    const left = squarePlot ? 112 : 82;
    const right = squarePlot ? 366 : 444;
    const x = value => left + (right - left) * (value - xmin) / (xmax - xmin);
    const y = value => 290 - 254 * (value - ymin) / (ymax - ymin);
    let svg = '';
    xticks.forEach(t => {
      svg += line(x(t), 36, x(t), 290) + label(x(t), 324, fmt(t));
    });
    yticks.forEach(t => {
      svg += line(left, y(t), right, y(t)) + label(left - 11, y(t) + 9, fmt(t), 'end');
    });
    if (xmin <= 0 && xmax >= 0) svg += line(x(0), 36, x(0), 290, '--ink-2');
    if (ymin <= 0 && ymax >= 0) svg += line(left, y(0), right, y(0), '--ink-2');
    svg += label(right, 353, xlabel, 'end') + label(left, 25, ylabel, 'start');
    return { x, y, svg };
  }

  function figure(id, title, description, body) {
    return `<svg class="lab-svg" viewBox="0 0 480 360" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${title}</title><desc id="${id}-desc">${description}</desc>${body}</svg>`;
  }

  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }

  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      const values = Object.fromEntries(controls.map(control => [control.dataset.key,
        control.tagName === 'SELECT' ? control.value : Number(control.value)]));
      host.querySelectorAll('[data-value]').forEach(output => {
        output.textContent = fmt(values[output.dataset.value]);
      });
      try {
        render(values);
      } catch (error) {
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = 'この数値範囲では計算できません。初期状態に戻すか、値を調整してください。';
      }
    }
    controls.forEach(control => control.addEventListener(control.tagName === 'SELECT' ? 'change' : 'input', update));
    host.querySelector('button').addEventListener('click', () => {
      controls.forEach(control => { control.value = defaults[control.dataset.key]; });
      update();
    });
    update();
  }

  function paths(host) {
    const prefix = 'multivariable-paths-' + (++serial);
    const names = { 'x-axis': 'x軸', 'y-axis': 'y軸', line: '直線 y = cx', parabola: '放物線 y = cx²' };
    host.innerHTML = `<div class="lab-controls"><label class="lab-control" for="${prefix}-example"><span class="lab-control-label">関数の例</span><select id="${prefix}-example" data-key="example"><option value="axis-trap">F：軸と斜めの違い</option><option value="curved-trap">H：直線と曲線の違い</option></select></label><label class="lab-control" for="${prefix}-path"><span class="lab-control-label">比較する経路</span><select id="${prefix}-path" data-key="path"><option value="x-axis">x軸：(t, 0)</option><option value="y-axis">y軸：(0, t)</option><option value="line" selected>直線：(t, ct)</option><option value="parabola">放物線：(t, ct²)</option></select></label>${range(prefix, 'c', '係数 c', -2, 2, .1, 1)}${range(prefix, 't', '原点へ近づくパラメータ t', -1, 1, .01, .5)}</div><div class="lab-actions"><button type="button">初期状態に戻す</button></div><p class="lab-note" data-coefficient-note></p><p class="lab-note">橙の実線：選んだ経路。灰色の破線：x軸。青の点線：y軸。橙の大きな塗りつぶし丸は現在位置、灰色の小さな塗りつぶし点は原点です。</p><div data-figures></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div><p class="lab-note">数値表示には丸め誤差が含まれます。</p><p class="lab-note">出力の枝は t = 0 で結ばず、白抜き丸は枝が近づく高さ、塗りつぶし点は原点での定義値0です。両者が一致すると丸と点は重なります。経路の不一致は不存在の証明に使えます。一致する有限個の図だけでは存在を証明できません。</p>`;
    bind(host, { example: 'axis-trap', path: 'line', c: 1, t: .5 }, ({ example, path, c, t }) => {
      const symbol = example === 'axis-trap' ? 'F' : 'H';
      const axisSelected = path === 'x-axis' || path === 'y-axis';
      host.querySelector('[data-key="c"]').disabled = axisSelected;
      host.querySelector('[data-coefficient-note]').textContent = axisSelected
        ? '軸では係数cを使いません。選んでいたcの値は保持しています。'
        : '係数cを変えて、直線の傾きや放物線の開き方を比べられます。';
      const plane = chart(-2.2, 2.2, -2.2, 2.2, [-2, 0, 2], [-2, 2], 'x', 'y', true);
      const output = chart(-1, 1, -.6, .6, [-1, 0, 1], [-.5, .5], 't', symbol);
      // Preserve all valid samples; only the t=0 axis is light and dashed.
      output.svg = output.svg.replace(line(output.x(0), 36, output.x(0), 290), '')
        .replace(line(output.x(0), 36, output.x(0), 290, '--ink-2'),
          line(output.x(0), 36, output.x(0), 290, '--ink-3', '3 6').replace('stroke-width:2', 'stroke-width:1'));
      const series = [
        { key: 'x-axis', color: '--ink-2', dash: '10 7', width: 6 },
        { key: 'y-axis', color: '--series-2', dash: '3 6', width: 4 },
        { key: path, color: '--series-1', dash: '', width: 3 }
      ];
      series.forEach(item => {
        const samples = Array.from({ length: 201 }, (_, i) => math.pathState(example, item.key, (i - 100) / 100, c));
        plane.svg += curve(samples.map(s => [plane.x(s.point.x), plane.y(s.point.y)]), item.color, item.dash, item.width);
        // Never join a nonzero-path value to the separately defined value at the origin.
        [-1, 1].forEach(sign => {
          const branch = samples.filter(s => sign * s.t > 0);
          output.svg += curve(branch.map(s => [output.x(s.t), output.y(s.value)]), item.color, item.dash, item.width);
        });
      });
      // Exact branch limits, separate from the function's defined origin value 0.
      series.forEach(item => {
        const exceptional = (example === 'axis-trap' && item.key === 'line')
          || (example === 'curved-trap' && item.key === 'parabola');
        const branchLimit = exceptional ? c / (1 + c * c) : 0;
        output.svg += dot(output.x(0), output.y(branchLimit), item.color, true, 7);
      });
      const current = math.pathState(example, path, t, c);
      const onX = math.pathState(example, 'x-axis', t, c);
      const onY = math.pathState(example, 'y-axis', t, c);
      plane.svg += dot(plane.x(current.point.x), plane.y(current.point.y), '--series-1', false, 8) + dot(plane.x(0), plane.y(0), '--ink-2', false, 4);
      output.svg += dot(output.x(t), output.y(current.value), '--series-1', false, 8) + dot(output.x(0), output.y(0), '--ink-2', false, 5);
      const currentText = `t = ${fmt(t)}、点 (${fmt(current.point.x)}, ${fmt(current.point.y)})、原点からの距離 ${fmt(current.distance)}、${symbol}の値 ${fmt(current.value)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">入力平面：三つの経路</p>${figure(prefix + '-plane', '原点へ近づく入力の経路', `${names[path]}と二つの座標軸。${currentText}`, plane.svg)}<p class="lab-note">出力：パラメータtと関数値</p>${figure(prefix + '-output', '経路ごとの関数値', `${currentText} t=0の細い破線上で、白抜き丸は各枝が近づく高さ、塗りつぶし点は定義値0を示す。高さが一致すると両者は重なる。t≠0の有効な標本は省略していません。`, output.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>${symbol}(x, y) = ${example === 'axis-trap' ? 'xy / (x² + y²)' : 'x²y / (x⁴ + y²)'}（原点以外）<br>${symbol}(0, 0) = 0（定義値）</p><p>選択：${names[path]}、c = ${fmt(c)}<br>t = ${fmt(t)}、(x, y) = (${fmt(current.point.x)}, ${fmt(current.point.y)})<br>原点からの距離 = ${fmt(current.distance)}<br>選んだ経路の値 = <strong>${fmt(current.value)}</strong></p><p>同じtでの比較：<br>x軸の値 = ${fmt(onX.value)}<br>y軸の値 = ${fmt(onY.value)}</p>${current.atOrigin ? '<p>現在は原点です。表示した0は関数の定義値であり、周囲からの極限が0であることを意味しません。</p>' : '<p>原点での定義値0と、経路上で近づく値を分けて比較してください。</p>'}`;
    });
  }

  function linear(host) {
    const prefix = 'multivariable-linear-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', '基準点の座標 a', -1, 1, .1, 1)}${range(prefix, 'b', '基準点の座標 b', -1, 1, .1, 1)}${range(prefix, 'h', '基本増分 h', -1, 1, .05, .1)}${range(prefix, 'k', '基本増分 k', -1, 1, .05, -.2)}${range(prefix, 'rho', '拡大率 ρ', 0, 1, .01, 1)}</div><div class="lab-actions"><button type="button">初期状態に戻す</button></div><p class="lab-note">P(x, y) = x² + xy + y²。基本増分v = (h, k)の向きを固定し、実際の増分ρvを動かします。第一図は接平面の選んだ切り口であり、接平面全体の図ではありません。</p><p class="lab-note">初期状態の差0.03は第一図の固定軸では見えにくいため、数値欄で確認し、第二図では距離で割った比として確かめてください。h = k ≠ 0の方向では、ρ > 0で余りが理論上限に等しくなり、第二図の二曲線が重なります。</p><div data-figures></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div><p class="lab-note">数値表示には丸め誤差が含まれます。</p>`;
    bind(host, { a: 1, b: 1, h: .1, k: -.2, rho: 1 }, ({ a, b, h, k, rho }) => {
      const base = { x: a, y: b };
      const basic = { x: h, y: k };
      const nonzero = math.norm2(basic) > 0;
      const stateAt = sigma => math.quadraticLinearState(base, { x: sigma * h, y: sigma * k });
      const current = stateAt(rho);
      const samples = Array.from({ length: 101 }, (_, i) => ({ sigma: i / 100, state: stateAt(i / 100) }));
      const values = chart(0, 1, -3.5, 12.5, [0, .5, 1], [0, 6, 12], 'σ', '値');
      values.svg += curve(samples.map(s => [values.x(s.sigma), values.y(s.state.value)]), '--series-1');
      values.svg += curve(samples.map(s => [values.x(s.sigma), values.y(s.state.linearValue)]), '--series-2', '9 6');
      values.svg += line(values.x(rho), 36, values.x(rho), 290, '--ink-2', '3 6');
      values.svg += dot(values.x(rho), values.y(current.value), '--series-1', false, 6) + square(values.x(rho), values.y(current.linearValue), '--series-2');
      const errors = chart(0, 1, 0, 2.2, [0, .5, 1], [1, 2], 'σ', '比');
      if (nonzero) {
        const positive = samples.filter(s => s.state.normalizedError !== null);
        errors.svg += curve(positive.map(s => [errors.x(s.sigma), errors.y(s.state.normalizedError)]), '--series-1');
        errors.svg += curve(positive.map(s => [errors.x(s.sigma), errors.y(s.state.errorBound / s.state.distance)]), '--series-2', '9 6');
        errors.svg += dot(errors.x(0), errors.y(0), '--series-1', true, 6);
      }
      errors.svg += line(errors.x(rho), 36, errors.x(rho), 290, '--ink-2', '3 6');
      if (current.normalizedError !== null) errors.svg += dot(errors.x(rho), errors.y(current.normalizedError), '--series-1', false, 6);
      const ratioText = current.normalizedError === null ? 'ずれ0のため比は未定義' : fmt(current.normalizedError);
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">選んだ切り口：橙の実線と丸は正確値、青の破線と四角は一次予測。縦の点線は現在のρです。</p>${figure(prefix + '-values', '正確値と線形近似の切り口', `基準点 (${fmt(a)}, ${fmt(b)})、基本増分 (${fmt(h)}, ${fmt(k)})。現在ρ = ${fmt(rho)}で、正確値 ${fmt(current.value)}、一次予測 ${fmt(current.linearValue)}。軸は固定です。`, values.svg)}<p class="lab-note">橙の実線：|R(σv)| / ‖σv‖。青の破線：上限 (3/2)σ‖v‖。${nonzero ? 'σ = 0の比は未定義です。白抜き点は本文の評価から分かる極限0を示します。' : '基本増分が0なので、比の曲線は描きません。hまたはkを0以外にして増分を選んでください。'}</p>${figure(prefix + '-errors', '距離で割った余りと理論上限', `現在ρ = ${fmt(rho)}で、正規化誤差は${ratioText}。${nonzero ? 'σが0の比は未定義で、白抜き点は極限0を示します。' : '基本増分が0のため全てのσで比は未定義です。'}`, errors.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>基準点 p = (${fmt(a)}, ${fmt(b)})<br>基本増分 v = (${fmt(h)}, ${fmt(k)})、ρ = ${fmt(rho)}<br>実際の増分 ρv = (${fmt(current.delta.x)}, ${fmt(current.delta.y)})<br>評価点 p + ρv = (${fmt(current.point.x)}, ${fmt(current.point.y)})</p><p>一次式の係数：(${fmt(current.coefficients.x)}, ${fmt(current.coefficients.y)})<br>P(p) = ${fmt(current.baseValue)}<br>正確値 = <strong>${fmt(current.value)}</strong><br>一次予測 = <strong>${fmt(current.linearValue)}</strong><br>余り R = ${fmt(current.remainder)}<br>距離 ‖ρv‖ = ${fmt(current.distance)}<br>正規化誤差 |R| / ‖ρv‖ = ${ratioText}<br>余りの理論上限 (3/2)‖ρv‖² = ${fmt(current.errorBound)}</p>${current.normalizedError === null ? '<p>余り（分子）は0ですが、比は0/0なので定義しません。</p>' : `<p>正規化誤差の理論上限 (3/2)‖ρv‖ = ${fmt(current.errorBound / current.distance)}</p>`}`;
    });
  }

  function initialize() {
    const labs = { 'multivariable-paths': paths, 'multivariable-linear': linear };
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
