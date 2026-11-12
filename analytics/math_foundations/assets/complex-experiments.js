(function () {
  'use strict';
  const math = globalThis.MathComplex;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const raw = value => value === null ? 'null' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  const number = value => value === 0 ? '0' : Math.abs(value) < .00001 ? value.toExponential(2) : Number(value.toFixed(5)).toString();
  function display(value) {
    if (value === null) return '未定義';
    if (typeof value === 'number') return number(value);
    if (typeof value !== 'object') return String(value);
    if (Math.abs(value.im) < .0000005) return number(value.re);
    if (Math.abs(value.re) < .0000005) return `${number(value.im)}i`;
    return `${number(value.re)} ${value.im < 0 ? '−' : '+'} ${number(Math.abs(value.im))}i`;
  }
  const result = (key, value, text) => `<span data-value="${escape(key)}" data-raw="${escape(raw(value))}" data-raw-value="${escape(raw(value))}"><strong>${escape(text === undefined ? display(value) : text)}</strong></span>`;
  const label = (x, y, text, color = '--ink', size = 22) => `<text x="${x}" y="${y}" text-anchor="middle" style="fill:var(${color});font-size:${size}px">${escape(text)}</text>`;
  const line = (x1, y1, x2, y2, color = '--ink-3', width = 2, dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const circle = (x, y, radius, color, filled = true) => `<circle cx="${x}" cy="${y}" r="${radius}" style="fill:var(${filled ? color : '--surface'});stroke:var(${color});stroke-width:3"/>`;
  function arrow(x1, y1, x2, y2, color = '--series-1', dash = '') {
    const dx = x2 - x1, dy = y2 - y1, length = Math.hypot(dx, dy);
    if (length < .001) return circle(x2, y2, 5, color, false);
    const ux = dx / length, uy = dy / length, head = Math.min(11, length * .45);
    return line(x1, y1, x2, y2, color, 3, dash) + `<path d="M${x2 - head * ux - head * .5 * uy},${y2 - head * uy + head * .5 * ux} L${x2},${y2} L${x2 - head * ux + head * .5 * uy},${y2 - head * uy - head * .5 * ux}" style="fill:none;stroke:var(${color});stroke-width:3"/>`;
  }
  function figure(id, title, description, body, height = 360) {
    return `<svg class="lab-svg" viewBox="0 0 360 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(description)}</desc>${body}</svg>`;
  }
  function plane(extent) {
    const scale = 126 / extent;
    const xy = z => [180 + scale * z.re, 190 - scale * z.im];
    const axes = line(24, 190, 336, 190) + line(180, 40, 180, 340)
      + line(54, 184, 54, 196) + line(306, 184, 306, 196)
      + label(325, 176, 'Re') + label(203, 50, 'Im') + label(160, 219, '0')
      + label(54, 219, '−' + number(extent)) + label(306, 219, number(extent));
    return { xy, axes, scale };
  }
  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }
  const reset = '<div class="lab-actions"><button type="button" data-action="reset" data-reset>初期状態に戻す</button></div>';
  const panels = '<p class="lab-status" role="status" aria-live="polite"></p><div data-figures></div><div class="lab-readout"></div>';
  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      const input = Object.fromEntries(controls.map(control => [control.dataset.key, control.dataset.key === 'function' ? control.value : Number(control.value)]));
      try {
        host.dataset.labError = 'false';
        host.querySelectorAll('output[data-value]').forEach(output => {
          const value = input[output.dataset.value]; output.textContent = display(value); output.dataset.raw = raw(value); output.dataset.rawValue = raw(value);
        });
        host.querySelector('.lab-status').textContent = render(input);
      } catch (error) {
        host.dataset.labError = 'true'; host.dataset.domainState = 'error';
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = '';
        host.querySelector('.lab-status').textContent = '計算中に問題が起きました。初期状態に戻して値を調整してください。';
      }
    }
    controls.forEach(control => { control.addEventListener('input', update); if (control.tagName === 'SELECT') control.addEventListener('change', update); });
    host.querySelector('[data-reset]').addEventListener('click', () => { controls.forEach(control => { control.value = defaults[control.dataset.key]; }); update(); });
    update();
  }
  function difference(host) {
    const prefix = 'complex-difference-' + (++serial);
    host.innerHTML = `<div class="lab-controls"><label class="lab-control" for="${prefix}-function"><span class="lab-control-label">調べる関数 f(z)</span><select id="${prefix}-function" data-key="function"><option value="square">z²</option><option value="conjugate">共役 z̄</option><option value="absSquare">絶対値の2乗 |z|²</option></select></label>${range(prefix, 'x', '点の実部 x', -1.5, 1.5, .05, .5)}${range(prefix, 'y', '点の虚部 y', -1.5, 1.5, .05, .5)}${range(prefix, 'h', '刻みの大きさ h', .05, 1, .05, .25)}${range(prefix, 'theta', '近づく方向 θ（度）', 0, 360, 5, 0)}</div>${reset}<p class="lab-note">δ = h(cos θ + i sin θ) として Q = {f(z+δ)−f(z)}/δ を計算します。h は正の有限値です。各平面は横・縦が同じ縮尺で、図ごとに値に応じて縮尺が変わります。</p>${panels}`;
    bind(host, { function: 'square', x: .5, y: .5, h: .25, theta: 0 }, input => {
      const s = math.differenceState(input); host.dataset.domainState = 'defined';
      const source = plane(Math.max(1, Math.ceil(Math.max(...[s.point, s.nextPoint].flatMap(z => [Math.abs(z.re), Math.abs(z.im)])))));
      const [zx, zy] = source.xy(s.point), [nx, ny] = source.xy(s.nextPoint);
      const sourceBody = source.axes + arrow(zx, zy, nx, ny) + circle(zx, zy, 7, '--ink', false) + circle(nx, ny, 5, '--series-1');
      const values = [s.orthogonal0, s.orthogonal90, s.selected, ...(s.derivative ? [s.derivative] : [])];
      const extent = Math.max(1, Math.ceil(Math.max(...values.flatMap(z => [Math.abs(z.re), Math.abs(z.im)]))));
      const target = plane(extent);
      const [ax, ay] = target.xy(s.orthogonal0), [bx, by] = target.xy(s.orthogonal90), [qx, qy] = target.xy(s.selected);
      let targetBody = target.axes + arrow(180, 190, ax, ay, '--series-2', '8 5') + arrow(180, 190, bx, by, '--series-2', '2 5');
      targetBody += `<rect x="${ax - 7}" y="${ay - 7}" width="14" height="14" style="fill:var(--surface);stroke:var(--series-2);stroke-width:3"/>`;
      targetBody += `<path d="M${bx},${by - 9} L${bx + 8},${by + 7} L${bx - 8},${by + 7} Z" style="fill:var(--surface);stroke:var(--series-2);stroke-width:3"/>`;
      targetBody += arrow(180, 190, qx, qy) + circle(qx, qy, 5, '--series-1');
      if (s.derivative) { const [dx, dy] = target.xy(s.derivative); targetBody += circle(dx, dy, 10, '--ink', false); }
      host.querySelector('[data-figures]').innerHTML = `<h3>入力平面：点と増分</h3>${figure(prefix + '-input', '入力点と有限の増分', `白抜きの点z=${display(s.point)}から、橙の点z+δ=${display(s.nextPoint)}へ向かう矢印。δ=${display(s.delta)}。`, sourceBody)}<p class="lab-note">白抜き点が z、橙の点が z+δ。矢印が増分 δ です。</p><h3>差商 Q の平面</h3>${figure(prefix + '-quotients', '三方向の有限差商と微分極限', `橙の丸は選択方向${s.theta}度。青の四角は0度、青の三角は90度の有限差商。${s.derivative ? '大きい白抜きの輪は複素微分の値。' : '複素微分の値は存在しません。'}`, targetBody)}<p class="lab-note">● 橙の実線：選択方向。□ 青の破線：0°。△ 青の点線：90°。大きい白抜きの輪：存在するときの f′(z)。重なる点もあります。</p>`;
      const explanation = s.function === 'square' ? 'z² は全平面で正則です。有限差商は 2z+δ なので、微分極限 2z との距離は h です。' : s.function === 'conjugate' ? '共役の差商は e^(−2iθ)。h を小さくしても方向による違いが残り、どの点でも複素微分できません。' : s.differentiable ? '|z|² は原点だけで複素微分でき、微分値は0です。有限差商 h e^(−iθ) は h→0 で0へ近づきます。ただし原点のどの開近傍でも正則ではありません。' : '|z|² はこの点では複素微分できません。原点では微分できますが、そのどの開近傍でも正則ではありません。';
      host.querySelector('.lab-readout').innerHTML = `<p>選択方向 ${s.theta}° の有限差商 = ${result('selected', s.selected)}<br>0° の有限差商 = ${result('orthogonal0', s.orthogonal0)}<br>90° の有限差商 = ${result('orthogonal90', s.orthogonal90)}<br>微分極限 f′(z) = ${result('derivative', s.derivative, s.derivative === null ? '存在しない' : undefined)}<br>有限差商と微分値の距離 = ${result('error', s.error, s.error === null ? '比較する微分値なし' : undefined)}<br>微分の回転角（rad） = ${result('derivativeRotation', s.derivativeRotation, s.derivativeRotation === null ? '未定義（非存在または微分値0）' : undefined)}</p><p>${explanation}</p><p>微分値0は拡大率0です。向きを保つ非零の矢印が残らないため、その回転角は定めません。三方向の観察だけでは、全方向での極限の証明にはなりません。</p>`;
      return `有限の刻み h=${s.h}、方向${s.theta}°の差商を表示しています。${s.differentiable ? 'この点の微分極限とは別に表示しています。' : 'この点には複素微分の値が存在しません。'}`;
    });
  }
  function logarithm(host) {
    const prefix = 'complex-log-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'radius', '半径 r', .5, 2, .05, 1)}${range(prefix, 'theta', '経路に沿う角度 θ（度）', -360, 360, 5, 0)}</div>${reset}<p class="lab-note">出発点 r から角度 θ まで円をたどります。経路に沿って追跡した値 log r+iθ と、切断を除いた平面で定義する主値 Log を比較します。角度の式の θ はラジアンです。</p>${panels}`;
    bind(host, { radius: 1, theta: 0 }, input => {
      const s = math.logarithmState(input); host.dataset.domainState = s.onCut ? 'cut' : 'defined';
      const p = plane(2), [zx, zy] = p.xy(s.point), radius = p.scale * s.radius;
      let path = '';
      const steps = Math.max(1, Math.ceil(Math.abs(s.theta) / 4));
      for (let k = 0; k <= steps; k++) {
        const v = math.logarithmState({ radius: s.radius, theta: s.theta * k / steps }), [x, y] = p.xy(v.point);
        path += `${k ? 'L' : 'M'}${x},${y} `;
      }
      let body = p.axes + line(24, 190, 180, 190, '--series-1', 6, '8 5');
      body += `<circle cx="180" cy="190" r="${radius}" style="fill:none;stroke:var(--ink-3);stroke-width:2"/><path d="${path}" style="fill:none;stroke:var(--series-2);stroke-width:4"/>`;
      body += circle(180 + radius, 190, 9, '--ink', false) + circle(zx, zy, 6, '--series-2');
      const x = angle => 54 + (angle + 360) * 252 / 720, y = angle => 180 - angle * 126 / 360;
      let chart = line(42, 180, 332, 180) + line(180, 42, 180, 318);
      chart += label(54, 342, '−360°') + label(306, 342, '360°') + label(191, 342, 'θ');
      chart += label(28, 60, '2π') + label(28, 313, '−2π') + label(25, 188, '0');
      chart += label(212, 27, '虚部');
      chart += line(x(-180), 46, x(-180), 314, '--ink-3', 1, '4 5') + line(x(180), 46, x(180), 314, '--ink-3', 1, '4 5');
      chart += `<path data-curve="tracked" d="M${x(0)},${y(0)} L${x(s.theta)},${y(s.theta)}" style="fill:none;stroke:var(--series-1);stroke-width:5;stroke-dasharray:8 4"/>`;
      // Separate M commands at each cut: never connect the sawtooth jump.
      const principalPath = `M${x(-360)},${y(0)} L${x(-180)},${y(180)} M${x(-180)},${y(-180)} L${x(180)},${y(180)} M${x(180)},${y(-180)} L${x(360)},${y(0)}`;
      chart += `<path data-curve="principal" d="${principalPath}" style="fill:none;stroke:var(--series-2);stroke-width:3"/>`;
      for (const cut of [-180, 180]) for (const limit of [-180, 180]) chart += circle(x(cut), y(limit), 5, '--series-2', false);
      chart += circle(x(s.theta), y(s.theta), 8, '--series-1', false);
      if (s.principal !== null) chart += circle(x(s.theta), y(s.principalAngle * 180 / Math.PI), 4, '--series-2');
      host.querySelector('[data-figures]').innerHTML = `<h3>入力平面：円をたどる</h3>${figure(prefix + '-plane', '円上の点と対数の切断', `半径${s.radius}の円を${s.theta}度までたどった点は${display(s.point)}。橙の破線は主値Logから除く負の実軸。青い線はたどった経路。`, body)}<p class="lab-note">白抜きの輪が出発点 r、青い丸が現在地 z。橙の破線は切断で、負の実軸上では主値 Log を定義しません。</p><h3>角度を追う：二つの虚部</h3>${figure(prefix + '-branches', '経路に沿う値と主値の虚部', '横軸は経路角度−360度から360度、縦軸は虚部−2πから2π。橙の破線は0から現在角度まで連続に追跡した虚部。青い線は主値の虚部で、±180度の切断で線が分かれる。白抜き端点は値を含まない。', chart)}<p class="lab-note">橙の破線と輪：経路に沿う値。青い実線と丸：主値。青い白抜き端点は未定義です。±180°の縦線では主値の線をつなぎません。</p>`;
      host.querySelector('.lab-readout').innerHTML = `<p>点 z = ${result('point', s.point)}<br>経路に沿う値 log r+iθ = ${result('tracked', s.tracked)}<br>主値 Log z = ${result('principal', s.principal, s.onCut ? '未定義（切断上）' : undefined)}<br>主偏角 Arg z（rad） = ${result('principalAngle', s.principalAngle, s.onCut ? '未定義（切断上）' : undefined)}</p><p>${s.onCut ? '現在の点は負の実軸上です。主値の定義域から外れるので、±πを主値として代入しません。経路に沿う値は引き続き追跡できます。' : Math.abs(s.theta) === 360 ? '一周して点 z は出発点 r に戻りました。主値の虚部は0ですが、経路に沿う値の虚部は±2πだけ変わりました。' : '主値の虚部は −π より大きく π より小さい範囲です。経路に沿う値は、どの向きへ何周したかを保持します。'}</p><p>追跡した値はこのパラメータ付き経路に沿う連続な値です。円全体の各点にただ一つの連続な対数を定めたものではありません。</p>`;
      return s.onCut ? '切断上なので主値 Log は未定義です。これは意図した定義域の表示です。経路に沿う値と図は表示を続けます。' : `角度${s.theta}°。同じ点へ戻っても、経路に沿う値には回転の履歴が残ります。`;
    });
  }
  function residue(host) {
    const prefix = 'complex-residue-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', '実軸上の極 a', -2, 2, .01, .5)}<label class="lab-control" for="${prefix}-orientation"><span class="lab-control-label">円をたどる向き</span><select id="${prefix}-orientation" data-key="orientation"><option value="1">反時計回り（正向き +1）</option><option value="-1">時計回り（負向き −1）</option></select></label>${range(prefix, 'n', '中点則の分割数 N', 16, 256, 16, 64)}</div>${reset}<p class="lab-note">単位円 |z|=1 に沿って f(z)=1/(z−a) を積分します。厳密値と、円のパラメータを等分して各区間の中点で求める有限和を比較します。</p>${panels}`;
    bind(host, { a: .5, orientation: 1, n: 64 }, input => {
      const s = math.residueState(input); host.dataset.domainState = s.region === 'boundary' ? 'boundary' : 'defined';
      const p = plane(2), r = p.scale, [ax, ay] = p.xy({ re: s.a, im: 0 });
      let body = p.axes + `<circle cx="180" cy="190" r="${r}" style="fill:var(--series-2);fill-opacity:.08;stroke:var(--series-2);stroke-width:3"/>`;
      // Three tangent arrows carry direction without relying on color.
      for (const angle of [45, 165, 285]) {
        const t = angle * Math.PI / 180, x = 180 + r * Math.cos(t), y = 190 - r * Math.sin(t);
        const dx = -Math.sin(t) * s.orientation * 13, dy = -Math.cos(t) * s.orientation * 13;
        body += arrow(x - dx, y - dy, x + dx, y + dy, '--series-2');
      }
      body += line(ax - 8, ay - 8, ax + 8, ay + 8, '--series-1', 4) + line(ax - 8, ay + 8, ax + 8, ay - 8, '--series-1', 4);
      body += label(180, 295, '|z| = 1', '--series-2', 24);
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-contour', '単位円と実軸上の極', `円は${s.orientation === 1 ? '反時計回りの正向き' : '時計回りの負向き'}。橙の十字は実軸上a=${s.a}の極。極は円の${s.region === 'boundary' ? '上にあります。この積分は未定義です' : s.region === 'inside' ? '内側にあります' : '外側にあります'}。横・縦は同じ縮尺。`, body) + '<p class="lab-note">青い円と矢印：積分経路と向き。橙の ×：極 a。円の内外は、十字の中心で判定します。</p>';
      const regionText = { inside: '円の内側', outside: '円の外側', boundary: '円周上（積分は未定義）' }[s.region];
      host.querySelector('.lab-readout').innerHTML = `<p>極の位置 = ${result('region', s.region, regionText)}<br>向き = ${result('orientation', s.orientation, s.orientation === 1 ? '反時計回り（+1）' : '時計回り（−1）')}<br>厳密な積分値 = ${result('exact', s.exact, s.region === 'boundary' ? '未定義（輪郭上に極）' : undefined)}<br>中点則 N=${s.n} の数値和 = ${result('numeric', s.numeric, s.region === 'boundary' ? '表示しない（積分が未定義）' : undefined)}<br>数値和と厳密値の距離 = ${result('error', s.error, s.error === null ? '未定義' : undefined)}</p><p>${s.region === 'boundary' ? 'a=±1 では極が積分経路上にあります。中点のサンプルが極を避けて有限和になっても、通常の輪郭積分の値とは呼べません。厳密値・数値和ともに表示しません。' : s.region === 'inside' ? '極の留数は1なので、正向きの厳密値は 2πi。向きを逆にすると符号が変わります。' : '極が円の外にあるので、厳密値は0です。有限の中点則には誤差が残ることがあります。'}</p><p>極が円に近いと細かい分割が必要です。N を増やした観察は収束の証明ではなく、有限の数値計算です。円周のすぐ近くでも、極が経路上になければ通常の積分は定義されます。</p>`;
      return s.region === 'boundary' ? '輪郭上に極があるため積分は未定義です。これは意図した定義域の表示です。極と円の図は表示を続けます。' : `極は${regionText}。${s.orientation === 1 ? '正' : '負'}向きの厳密値と${s.n}分割の有限和を比較しています。`;
    });
  }
  function initialize() {
    const labs = { 'complex-difference': difference, 'complex-log': logarithm, 'complex-residue': residue };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) { labs[host.dataset.lab](host); host.dataset.labInitialized = 'true'; }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
