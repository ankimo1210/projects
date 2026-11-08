(function () {
  'use strict';
  const math = globalThis.MathMultivariableMiddle;
  if (!math) return;
  let serial = 0;
  const rad = degrees => degrees * Math.PI / 180;
  const fmt = value => {
    if (value === 0) return '0';
    if (Math.abs(value) <= 1e-12) return '約0';
    return Math.abs(value) < 1e-4 ? value.toExponential(3)
      : value.toFixed(4).replace(/\.?0+$/, '');
  };
  const vectorText = v => `(${fmt(v.x)}, ${fmt(v.y)})`;
  const label = (x, y, text, anchor = 'middle') =>
    `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink-2);font-size:26px">${text}</text>`;
  const line = (x1, y1, x2, y2, color = '--grid', dash = '', width = 2) =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const curve = (points, color, dash = '', width = 3) =>
    `<polyline points="${points.map(p => p.join(',')).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const dot = (x, y, color, radius = 6) =>
    `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${color});stroke:var(${color});stroke-width:2"/>`;
  const square = (x, y, color, radius = 5) =>
    `<rect x="${x - radius}" y="${y - radius}" width="${2 * radius}" height="${2 * radius}" style="fill:var(${color})"/>`;

  function chart(xmin, xmax, ymin, ymax, xticks, yticks, xlabel, ylabel, plane = false) {
    const left = plane ? 112 : 82;
    const right = plane ? 366 : 444;
    const x = value => left + (right - left) * (value - xmin) / (xmax - xmin);
    const y = value => 290 - 254 * (value - ymin) / (ymax - ymin);
    let svg = '';
    xticks.forEach(t => { svg += line(x(t), 36, x(t), 290) + label(x(t), 324, fmt(t)); });
    yticks.forEach(t => { svg += line(left, y(t), right, y(t)) + label(left - 11, y(t) + 9, fmt(t), 'end'); });
    if (xmin <= 0 && xmax >= 0) svg += line(x(0), 36, x(0), 290, '--ink-2');
    if (ymin <= 0 && ymax >= 0) svg += line(left, y(0), right, y(0), '--ink-2');
    svg += label(right, 353, xlabel, 'end') + label(left, 25, ylabel, 'start');
    return { x, y, svg };
  }

  function arrow(plot, start, v, color, scale = 1, dash = '', width = 3) {
    const x1 = plot.x(start.x), y1 = plot.y(start.y);
    const x2 = plot.x(start.x + scale * v.x), y2 = plot.y(start.y + scale * v.y);
    const length = Math.hypot(x2 - x1, y2 - y1);
    if (length < 1e-10) return '';
    const dx = (x2 - x1) / length, dy = (y2 - y1) / length;
    const size = Math.min(9, length * .45);
    return line(x1, y1, x2, y2, color, dash, width)
      + `<polygon points="${x2},${y2} ${x2 - size * dx + size * .5 * dy},${y2 - size * dy - size * .5 * dx} ${x2 - size * dx - size * .5 * dy},${y2 - size * dy + size * .5 * dx}" style="fill:var(${color})"/>`;
  }

  function circle(plot, radius, color = '--grid', dash = '') {
    return `<circle cx="${plot.x(0)}" cy="${plot.y(0)}" r="${plot.x(radius) - plot.x(0)}" style="fill:none;stroke:var(${color});stroke-width:2;${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  }

  function figure(id, title, description, body, height = 360) {
    return `<svg class="lab-svg" viewBox="0 0 480 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${title}</title><desc id="${id}-desc">${description}</desc>${body}</svg>`;
  }
  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }
  const reset = '<div class="lab-actions"><button type="button" data-action="reset">初期状態に戻す</button></div>';
  const panels = '<div data-figures></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div><p class="lab-note">図は有限個の点を結んだ観察用です。数値には丸め誤差があり、絶対値が10⁻¹²以下の非零値を「約0」と表示します。丸め表示から等号や極値を判定しません。</p>';

  function bind(host, defaults, render, analyticAngles = null) {
    const controls = [...host.querySelectorAll('[data-key]')];
    let analytic = null;
    function update() {
      const values = Object.fromEntries(controls.map(c => [c.dataset.key, c.tagName === 'SELECT' ? c.value : Number(c.value)]));
      host.querySelectorAll('[data-value]').forEach(output => {
        output.textContent = output.dataset.value === 'angle' && analytic
          ? fmt(analytic.angle * 180 / Math.PI) + '°（解析的な角度）'
          : fmt(values[output.dataset.value]) + (output.dataset.value === 'angle' ? '°' : '');
      });
      try {
        render(values, analytic);
      } catch (error) {
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = 'この数値範囲では計算できません。初期状態に戻すか、値を調整してください。';
      }
    }
    controls.forEach(c => c.addEventListener(c.tagName === 'SELECT' ? 'change' : 'input', () => {
      analytic = null;
      update();
    }));
    host.querySelector('[data-action="reset"]').addEventListener('click', () => {
      controls.forEach(c => { c.value = defaults[c.dataset.key]; });
      analytic = null;
      update();
    });
    if (analyticAngles) Object.entries(analyticAngles).forEach(([kind, angle]) => {
      host.querySelector(`[data-action="${kind}"]`).addEventListener('click', () => {
        analytic = { kind, angle };
        host.querySelector('[data-key="angle"]').value = Math.round(angle * 180 / Math.PI);
        update();
      });
    });
    update();
  }

  function compass(host) {
    const prefix = 'multivariable-compass-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', '基準点の座標 a', -1, 1, .1, 1)}${range(prefix, 'b', '基準点の座標 b', -1, 1, .1, 0)}${range(prefix, 'angle', '方向の角度 θ', -180, 180, 1, 0)}</div>${reset}<p class="lab-note">P(x, y) = x² + xy + y²。第一図は基準点pでの方向ベクトルを原点から描きます。基準点pの位置を描いた図ではありません。横軸と縦軸は同じ縮尺です。</p><p class="lab-note">橙の実線矢印：単位方向u。青の破線矢印：勾配∇P（実際の長さ）。灰色の点線矢印：最急単位方向。灰色の円は単位円。黒い四角は勾配からuの直線へ下ろした垂線の足で、原点からの符号付き長さが方向微分です。勾配0なら足も原点です。第二図の橙の丸は現在の方向微分、灰色の破線は理論上の最大・最小変化率です。</p>${panels}`;
    bind(host, { a: 1, b: 0, angle: 0 }, ({ a, b, angle }) => {
      const base = { x: a, y: b };
      const state = math.gradientCompassState(base, rad(angle));
      const plane = chart(-4.6, 4.6, -4.6, 4.6, [-4, 0, 4], [-4, 4], 'x方向', 'y方向', true);
      plane.svg += circle(plane, 1, '--ink-2');
      const origin = { x: 0, y: 0 };
      plane.svg += arrow(plane, origin, state.gradient, '--series-2', 1, '9 6', 4);
      if (state.steepest) plane.svg += arrow(plane, origin, state.steepest, '--ink-2', 1, '3 5', 5);
      plane.svg += arrow(plane, origin, state.direction, '--series-1');
      plane.svg += dot(plane.x(state.direction.x), plane.y(state.direction.y), '--series-1', 5)
        + dot(plane.x(0), plane.y(0), '--ink-2', 4);
      const foot = { x: state.slope * state.direction.x, y: state.slope * state.direction.y };
      plane.svg += line(plane.x(state.gradient.x), plane.y(state.gradient.y), plane.x(foot.x), plane.y(foot.y), '--ink-2', '4 4')
        + line(plane.x(0), plane.y(0), plane.x(foot.x), plane.y(foot.y), '--ink-2', '', 2)
        + square(plane.x(foot.x), plane.y(foot.y), '--ink-2', 5);
      const slopes = chart(-180, 180, -4.5, 4.5, [-180, 0, 180], [-4, 4], '角度 θ (°)', '方向微分');
      const samples = Array.from({ length: 361 }, (_, i) => ({ degrees: i - 180, state: math.gradientCompassState(base, rad(i - 180)) }));
      slopes.svg += line(slopes.x(-180), slopes.y(state.maxSlope), slopes.x(180), slopes.y(state.maxSlope), '--ink-2', '9 6')
        + line(slopes.x(-180), slopes.y(state.minSlope), slopes.x(180), slopes.y(state.minSlope), '--ink-2', '9 6')
        + curve(samples.map(s => [slopes.x(s.degrees), slopes.y(s.state.slope)]), '--series-1')
        + line(slopes.x(angle), 36, slopes.x(angle), 290, '--ink-2', '3 6')
        + dot(slopes.x(angle), slopes.y(state.slope), '--series-1', 7);
      const description = `基準点p = ${vectorText(state.base)}、θ = ${fmt(angle)}度、方向微分 ${fmt(state.slope)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">基準点pでの方向：原点を共通の始点に表示</p>${figure(prefix + '-plane', '方向微分は勾配の符号付き射影', description + '黒い四角は垂線の足。点線で勾配の先端と結び、uへの射影を示す。有限サンプルは全方向の最大値の証明ではない。' + (state.steepest ? '最急単位方向は勾配を正規化した向きです。' : '勾配が0のため最急単位方向は一意に定まりません。'), plane.svg)}<p class="lab-note">角度と方向微分：最大・最小は本文の不等式による値</p>${figure(prefix + '-slopes', '各方向の一次変化率', description + `最大変化率 ${fmt(state.maxSlope)}、最小変化率 ${fmt(state.minSlope)}。`, slopes.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>p = ${vectorText(state.base)}<br>θ = ${fmt(angle)}°<br>単位方向 u = ${vectorText(state.direction)}<br>勾配 ∇P = ${vectorText(state.gradient)}<br>方向微分 DᵤP = <strong>${fmt(state.slope)}</strong><br>最大変化率 = ${fmt(state.maxSlope)}<br>最小変化率 = ${fmt(state.minSlope)}<br>最急単位方向 = ${state.steepest ? vectorText(state.steepest) : '一意に定まらない（勾配0）'}</p>${state.steepest ? '<p>この固定多項式は全微分可能です。最大・最小変化率は曲線のサンプル探索ではなく、本文の内積の評価から得ています。</p>' : '<p>一次の傾きは全方向0です。この事実だけから極値かどうかは決められません。</p>'}`;
    });
  }

  function curvature(host) {
    const prefix = 'multivariable-curvature-' + (++serial);
    const names = { bowl: 'P = x² + xy + y²', saddle: 'x² − y²', 'flat-min': 'x⁴ + y⁴', 'flat-saddle': 'x⁴ − y⁴' };
    const verdicts = { 'strict-min': '厳密局所最小', saddle: '鞍点', inconclusive: '判定不能（D = 0）' };
    const actual = { bowl: '厳密局所最小', saddle: '鞍点', 'flat-min': '厳密局所最小', 'flat-saddle': '鞍点' };
    host.innerHTML = `<div class="lab-controls"><label class="lab-control" for="${prefix}-example"><span class="lab-control-label">関数の例（基準点は原点）</span><select id="${prefix}-example" data-key="example">${Object.entries(names).map(([key, name]) => `<option value="${key}">${name}</option>`).join('')}</select></label>${range(prefix, 'angle', '切り口の角度 θ', -180, 180, 1, 0)}${range(prefix, 't', '現在位置のパラメータ t', -1, 1, .01, .5)}</div>${reset}<p class="lab-note">第一図の橙の線は原点を通る切り口、塗りつぶし丸は現在位置tuです。平面の両軸は同じ縮尺です。第二図の橙の実線と丸は正確値f(su)、青の破線と四角は二次近似、縦の点線は現在のtです。二次式の例では両曲線が重なります。第一図の下段では選択方向と別に、同じ距離1/2のx軸・y軸の値を0の左右で比べます。二方向だけでは極小を保証しません。</p>${panels}`;
    bind(host, { example: 'bowl', angle: 0, t: .5 }, ({ example, angle, t }) => {
      const state = math.curvatureState(example, rad(angle), t);
      const samples = Array.from({ length: 201 }, (_, i) => math.curvatureState(example, rad(angle), (i - 100) / 100));
      const plane = chart(-1.15, 1.15, -1.15, 1.15, [-1, 0, 1], [-1, 1], 'x', 'y', true);
      plane.svg += circle(plane, 1)
        + curve(samples.map(s => [plane.x(s.point.x), plane.y(s.point.y)]), '--series-1')
        + dot(plane.x(0), plane.y(0), '--ink-2', 4)
        + dot(plane.x(state.point.x), plane.y(state.point.y), '--series-1', 7);
      const axisValues = [math.curvatureState(example, 0, .5).value, math.curvatureState(example, Math.PI / 2, .5).value];
      plane.svg += label(240, 398, '同じ距離t=1/2で二つの軸を比較')
        + line(240, 420, 240, 530, '--ink-2', '4 4');
      axisValues.forEach((value, i) => {
        const yy = 448 + i * 60, end = 240 + 320 * value;
        plane.svg += label(150, yy + 8, i === 0 ? 'f(1/2,0)' : 'f(0,1/2)', 'end')
          + line(240, yy, end, yy, i === 0 ? '--series-1' : '--series-2', i === 0 ? '' : '5 3', 6)
          + (i === 0 ? dot(end, yy, '--series-1') : square(end, yy, '--series-2', 6))
          + label(395, yy + 8, fmt(value), 'end');
      });
      plane.svg += label(240, 556, '0') + label(240, 598, '異符号なら原点の近くに上と下');
      const values = chart(-1, 1, -1.7, 1.7, [-1, 0, 1], [-1.5, 1.5], 's', '値');
      values.svg += curve(samples.map(s => [values.x(s.t), values.y(s.value)]), '--series-1', '', 4)
        + curve(samples.map(s => [values.x(s.t), values.y(s.quadraticValue)]), '--series-2', '9 6')
        + line(values.x(t), 36, values.x(t), 290, '--ink-2', '3 6')
        + dot(values.x(t), values.y(state.value), '--series-1', 7)
        + square(values.x(t), values.y(state.quadraticValue), '--series-2');
      const description = `${names[example]}。θ = ${fmt(angle)}度、t = ${fmt(t)}、正確値 ${fmt(state.value)}、二次近似 ${fmt(state.quadraticValue)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">原点を通る選択中の切り口と現在位置</p>${figure(prefix + '-plane', '切り口と二方向の符号比較', description + '下段は固定距離1/2のx軸・y軸の値。丸と四角の左右で符号を比較する。二方向とも正でも全方向の最小性は図だけでは保証しない。', plane.svg, 625)}<p class="lab-note">選んだ切り口の関数値と二次近似</p>${figure(prefix + '-values', '正確値と二次近似の比較', description + `Hessianによる判定は${verdicts[state.hessianVerdict]}です。`, values.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>f = ${names[example]}<br>Hf(0) = [[${fmt(state.hessian.xx)}, ${fmt(state.hessian.xy)}], [${fmt(state.hessian.xy)}, ${fmt(state.hessian.yy)}]]<br>方向 u = ${vectorText(state.direction)}<br>uᵀHu = ${fmt(state.directionalSecond)}<br>t = ${fmt(t)}、tu = ${vectorText(state.point)}<br>正確値 f(tu) = <strong>${fmt(state.value)}</strong><br>二次近似 (1/2)t²uᵀHu = ${fmt(state.quadraticValue)}<br>余り = ${fmt(state.remainder)}</p><p>Hessianによる判定：<strong>${verdicts[state.hessianVerdict]}</strong><br>本文で確かめた実際の形：<strong>${actual[example]}</strong></p><p>いずれも原点は内点・停留点で、関数はC²です。${state.hessianVerdict === 'inconclusive' ? 'Hessianが0でも関数が一定とは限りません。高次項の符号を本文で調べています。' : 'この条件のもとで本文の二階判定を適用しています。'}有限個の切り口だけから全方向の結論は出しません。<a href="#hessian-extrema-classification">本文の二階判定</a>と<a href="#hessian-extrema-degenerate">退化例</a>を確認してください。</p>`;
    });
  }

  function constraint(host) {
    const prefix = 'multivariable-constraint-' + (++serial);
    const maxAngle = Math.atan2(2, 1);
    const angles = { maximum: maxAngle, minimum: maxAngle - Math.PI };
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'angle', '円周上の角度 θ', -180, 180, 1, 0)}</div><div class="lab-actions"><button type="button" data-action="maximum">解析的な最大点へ</button> <button type="button" data-action="minimum">解析的な最小点へ</button></div>${reset}<p class="lab-note" data-angle-note></p><p class="lab-note">目的f = x + 2y、制約x² + y² = 1。第一図の塗りつぶし丸は現在位置p。橙の実線矢印は∇f、青の破線矢印は∇g、灰色の点線矢印は単位接線τで、すべてpを始点に矢印を0.5倍で描きます。黒い四角は∇fの法線成分の終点。そこから∇fの先端へ向かう青い実線は接線成分（残差）です。同じ0.5倍なので成分を足すと∇fに戻ります。平面の両軸は同じ縮尺です。</p><p class="lab-note">第二図の橙の実線は目的関数の値、橙の丸は現在値。青の四角は本文で求めた解析的な最大点・最小点です。接線方向変化率は数値欄に分けて表示します。</p>${panels}`;
    const extrema = Object.entries(angles).map(([kind, angle]) => ({ kind, degrees: angle * 180 / Math.PI, state: math.circleConstraintState(angle) }));
    const samples = Array.from({ length: 361 }, (_, i) => ({ degrees: i - 180, state: math.circleConstraintState(rad(i - 180)) }));
    bind(host, { angle: 0 }, ({ angle }, analytic) => {
      const angleRad = analytic ? analytic.angle : rad(angle);
      const degrees = angleRad * 180 / Math.PI;
      const state = math.circleConstraintState(angleRad);
      host.querySelector('[data-angle-note]').textContent = analytic
        ? `解析的な角度 ${fmt(degrees)}°を表示中です。スライダーのつまみは最寄りの${angle}°です。次にスライダーを動かすと整数度の操作へ戻ります。`
        : '角度は整数度で操作します。最大点・最小点ボタンでは、本文で求めた角度を丸めずに保持します。';
      const plane = chart(-2.4, 2.4, -2.4, 2.4, [-2, 0, 2], [-2, 2], 'x', 'y', true);
      plane.svg += circle(plane, 1, '--ink-2')
        + arrow(plane, state.point, state.constraintGradient, '--series-2', .5, '9 6', 4)
        + arrow(plane, state.point, state.tangent, '--ink-2', .5, '3 5', 4)
        + arrow(plane, state.point, state.objectiveGradient, '--series-1', .5)
        + dot(plane.x(state.point.x), plane.y(state.point.y), '--series-1', 7);
      const normal = { x: state.lambdaProjection * state.constraintGradient.x, y: state.lambdaProjection * state.constraintGradient.y };
      const normalEnd = { x: state.point.x + .5 * normal.x, y: state.point.y + .5 * normal.y };
      plane.svg += arrow(plane, state.point, normal, '--ink-2', .5, '6 4', 2)
        + square(plane.x(normalEnd.x), plane.y(normalEnd.y), '--ink-2', 4)
        + arrow(plane, normalEnd, state.normalResidual, '--series-2', .5, '', 3);
      const values = chart(-180, 180, -2.5, 2.5, [-180, 0, 180], [-2, 2], '角度 θ (°)', 'fの値');
      values.svg += curve(samples.map(s => [values.x(s.degrees), values.y(s.state.value)]), '--series-1')
        + line(values.x(degrees), 36, values.x(degrees), 290, '--ink-2', '3 6');
      extrema.forEach(s => { values.svg += square(values.x(s.degrees), values.y(s.state.value), '--series-2', 9); });
      values.svg += dot(values.x(degrees), values.y(state.value), '--series-1', 7);
      const description = `θ = ${fmt(degrees)}度、p = ${vectorText(state.point)}、目的関数の値 ${fmt(state.value)}、接線方向変化率 ${fmt(state.tangentRate)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">円周上の位置と三つの方向（各矢印は0.5倍）</p>${figure(prefix + '-plane', '目的勾配を法線成分と接線成分へ分ける', description + '黒い四角を経由して青い実線をたどると目的勾配に戻る。接線成分が0は必要条件で、最大性は本文で保証する。', plane.svg)}<p class="lab-note">円周上の目的関数と解析的な候補</p>${figure(prefix + '-values', '円周上の目的関数の値', description + '青い四角は本文の方程式と不等式から求めた全体の最大・最小です。', values.svg)}`;
      const candidate = analytic ? `<p>本文の解法による${analytic.kind === 'maximum' ? '最大点' : '最小点'}を表示中。ここでは解の λ = ${fmt(state.lambdaProjection)}（理論値 ${analytic.kind === 'maximum' ? '√5/2' : '−√5/2'}）です。</p>` : '';
      host.querySelector('.lab-readout').innerHTML = `<p>θ = ${fmt(degrees)}°<br>p = ${vectorText(state.point)}<br>f(p) = <strong>${fmt(state.value)}</strong><br>単位接線 τ = ${vectorText(state.tangent)}<br>接線方向変化率 ∇f・τ = <strong>${fmt(state.tangentRate)}</strong><br>∇f = ${vectorText(state.objectiveGradient)}<br>∇g = ${vectorText(state.constraintGradient)}<br>法線への射影係数 = ${fmt(state.lambdaProjection)}<br>残差 ∇f −（射影係数）∇g = ${vectorText(state.normalResidual)}</p>${candidate}<p>射影係数は任意の角度で計算できます。乗数方程式の解のλとは区別します。残差は接線方向変化率×τです。値が「約0」でも極値確定の判定には使いません。最大・最小の保証は本文の不等式によります。</p>`;
    }, angles);
  }

  function initialize() {
    const labs = { 'multivariable-compass': compass, 'multivariable-curvature': curvature, 'multivariable-constraint': constraint };
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
