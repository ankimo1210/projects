(function () {
  'use strict';
  const math = globalThis.MathNumerical;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const raw = value => value === null ? 'null' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  const number = value => value === 0 ? '0' : Math.abs(value) < .00001 || Math.abs(value) >= 100000 ? value.toExponential(3) : Number(value.toFixed(6)).toString();
  const display = value => value === null ? '保証なし' : typeof value === 'number' ? number(value) : String(value);
  const result = (key, value, text) => `<span data-value="${escape(key)}" data-raw="${escape(raw(value))}" data-raw-value="${escape(raw(value))}"><strong>${escape(text === undefined ? display(value) : text)}</strong></span>`;
  const line = (x1, y1, x2, y2, color = '--grid', dash = '') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:2;${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const label = (x, y, text, anchor = 'middle') => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink);font-size:22px">${escape(text)}</text>`;
  const dot = (x, y, color = '--series-1') => `<circle cx="${x}" cy="${y}" r="5" style="fill:var(${color});stroke:var(${color});stroke-width:2"/>`;
  const curve = (points, color, dash = '') => `<path d="${points.map(([x, y], k) => `${k ? 'L' : 'M'}${x},${y}`).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:3;${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const figure = (id, title, desc, body, height = 360) => `<svg class="lab-svg" viewBox="0 0 360 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(desc)}</desc>${body}</svg>`;
  const range = (prefix, key, title, min, max, step, value) => `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  const select = (prefix, key, title, options) => `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}</span><select id="${prefix}-${key}" data-key="${key}">${options.map(([value, text]) => `<option value="${value}">${text}</option>`).join('')}</select></label>`;
  const panels = '<div class="lab-actions"><button type="button" data-reset data-action="reset">初期状態に戻す</button></div><p class="lab-status" role="status" aria-live="polite"></p><div data-figures></div><div class="lab-readout"></div>';
  function bind(host, defaults, render) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      const input = Object.fromEntries(controls.map(c => [c.dataset.key, ['function', 'method'].includes(c.dataset.key) ? c.value : Number(c.value)]));
      try {
        host.dataset.labError = 'false';
        host.querySelectorAll('output[data-value]').forEach(o => { const v = input[o.dataset.value]; o.textContent = display(v); o.dataset.raw = raw(v); o.dataset.rawValue = raw(v); });
        host.querySelector('.lab-status').textContent = render(input);
      } catch (error) {
        host.dataset.labError = 'true'; host.dataset.domainState = 'error';
        host.querySelector('[data-figures]').innerHTML = ''; host.querySelector('.lab-readout').textContent = '';
        host.querySelector('.lab-status').textContent = '計算できる範囲を外れました。初期状態に戻して値を調整してください。';
      }
    }
    controls.forEach(c => { c.addEventListener('input', update); if (c.tagName === 'SELECT') c.addEventListener('change', update); });
    host.querySelector('[data-reset]').addEventListener('click', () => { controls.forEach(c => { c.value = defaults[c.dataset.key]; }); update(); });
    update();
  }
  function root(host) {
    const prefix = 'numerical-root-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${select(prefix, 'function', '方程式 f(x)=0', [['square', 'x²−2（区間 [0,2]）'], ['cycle', 'x³−2x+2（区間 [−2,0]）']])}${select(prefix, 'method', '反復法', [['bisection', '二分法：区間を保証'], ['newton', 'Newton法：区間保証なし']])}${range(prefix, 'x0', 'Newton法の初期値 x₀', -2, 2, .1, 1)}${range(prefix, 'steps', '区間縮小回数／反復上限 N', 0, 12, 1, 4)}</div><p class="lab-note">二分法は表示した固定区間から始め、x₀を使いません。Newton法の反復値は初期値スライダーの範囲を出ることがあります。|次の値| &gt; 10⁶ または非有限なら表示を打ち切ります。これは発散の数学的判定ではありません。</p>${panels}`;
    bind(host, { function: 'square', method: 'bisection', x0: 1, steps: 4 }, input => {
      const s = math.rootState(input); host.dataset.domainState = s.status;
      const extent = Math.max(2, ...s.history.map(p => Math.abs(p.x))), x = k => 48 + 264 * k / 12, y = value => 195 - 90 * value / extent;
      let body = line(48, 195, 326, 195) + line(48, 90, 48, 300) + label(48, 330, '0') + label(312, 330, '12') + label(180, 345, '反復 k') + label(180, 27, '近似値 xₖ');
      body += label(180, 65, '縦の範囲 ±' + number(extent));
      body += curve(s.history.map(p => [x(p.iteration), y(p.x)]), '--series-1');
      body += s.history.map(p => dot(x(p.iteration), y(p.x))).join('');
      body += line(26, 370, 334, 370, '--rule-2');
      if (s.bracket) {
        const domain = input.function === 'cycle' ? [-2, 0] : [0, 2];
        const bx = value => 52 + 256 * (value - domain[0]) / 2;
        body += label(180, 409, '二分法の保証区間と中点');
        body += line(52, 460, 308, 460, '--rule-2');
        body += line(bx(s.bracket[0]), 460, bx(s.bracket[1]), 460, '--series-2');
        body += line(bx(s.bracket[0]), 447, bx(s.bracket[0]), 473, '--series-2');
        body += line(bx(s.bracket[1]), 447, bx(s.bracket[1]), 473, '--series-2');
        body += dot(bx(s.estimate), 460);
        body += label(52, 505, number(domain[0])) + label(308, 505, number(domain[1]));
        body += label(180, 542, '半幅 = ' + number(s.bound));
      } else {
        body += label(180, 415, 'Newton法：区間保証なし');
        body += label(180, 465, '残差や更新幅だけでは');
        body += label(180, 503, '根への距離を保証しない');
      }
      const historyDesc = '横軸は反復回数0から12、縦軸は近似値、上下の範囲は±' + number(extent) + '。' + s.iterations + '回実行し、最後の値は' + number(s.estimate) + '。' + (s.bracket ? '下段は保証区間[' + s.bracket.map(number).join(', ') + ']、点は中点。半幅' + number(s.bound) + 'が区間内の根への誤差上限。' : 'Newton法には保証区間がなく、下段で区間保証なしと示す。');
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-history', '反復履歴と、二分法だけの区間保証', historyDesc, body, 565) + '<p class="lab-note">上段の点：各段階の値。線は順序を示す補助線で、縦軸は反復値に合わせて変わります。下段は別の横軸です。二分法では固定の初期区間の中で最終区間と中点を示し、半幅が誤差上限になります。細い最終区間が一点に見えても、正確な端点は下の読取り値で確認できます。Newton法の履歴だけから収束や根への距離を保証しません。</p>';
      const descriptions = { bracket: '連続性と符号変化から、区間に少なくとも一つ根があります。', steps: '指定した有限回数に達しました。収束の保証を意味しません。', 'computed-zero': '計算された残差が0になりました。丸めを含む計算上の判定です。', 'derivative-zero': '導関数が0のため次のNewton更新を定義できません。', 'display-limit': '次のNewton値が表示範囲を超えるため打ち切りました。' };
      host.querySelector('.lab-readout').innerHTML = `<p>近似値 = ${result('estimate', s.estimate)}<br>符号付き残差 f(x) = ${result('residual', s.residual)}<br>区間 = ${result('bracket', s.bracket, s.bracket ? '[' + s.bracket.map(number).join(', ') + ']' : 'なし')}<br>中点の誤差上限 = ${result('bound', s.bound)}<br>実行回数 = ${result('iterations', s.iterations)}<br>停止状態 = ${result('status', s.status, descriptions[s.status])}</p><p>${s.method === 'newton' ? 'Newton法に中点の誤差保証は付きません。x²−2では負の初期値から負の根へ進む場合もあります。三次式を選び x₀=0 とすると0と1を往復し、根へ近づきません。' : '誤差上限は、保証した区間内の根と中点との距離の上限です。この有限の試行で、任意の関数の根の一意性まで証明したわけではありません。'}</p>`;
      return descriptions[s.status];
    });
  }
  function difference(host) {
    const prefix = 'numerical-difference-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'x', '微分する点 x', -2, 2, .1, 0)}${range(prefix, 'exponent', 'h=10⁻ᵐ の指数 m', 0, 16, 1, 4)}</div><p class="lab-note">自作の比較モデル f(x)=exp(x) を使います。解析的な導関数も exp(x) で、そのブラウザ計算値を基準に誤差を比べます。指数を増やすほど刻みは小さくなります。最終桁や誤差の細部は実行環境に依存します。</p>${panels}`;
    bind(host, { x: 0, exponent: 4 }, input => {
      const s = math.differenceState(input); host.dataset.domainState = s.inputResolved ? 'resolved' : 'rounded-input';
      const states = Array.from({ length: 17 }, (_, exponent) => math.differenceState({ x: s.x, exponent }));
      const x = k => 58 + k * 16, y = error => 293 - (Math.max(-18, Math.min(2, Math.log10(Math.max(1e-18, error)))) + 18) * 11.2;
      let body = line(58, 69, 58, 293) + line(58, 293, 322, 293) + label(58, 325, '0') + label(314, 325, '16') + label(180, 345, '刻みの指数 m') + label(180, 27, '絶対誤差の対数');
      for (const power of [-18, -12, -6, 0]) body += line(58, y(10 ** power), 322, y(10 ** power)) + label(49, y(10 ** power) + 8, String(power), 'end');
      body += curve(states.map((p, k) => [x(k), y(p.forwardError)]), '--series-1') + curve(states.map((p, k) => [x(k), y(p.centralError)]), '--series-2', '7 5');
      body += dot(x(s.exponent), y(s.forwardError)) + dot(x(s.exponent), y(s.centralError), '--series-2');
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-errors', '刻みと前進差分・中心差分の誤差', '横軸は刻みの指数0から16、縦軸は絶対誤差の常用対数。橙実線が前進差分、青破線が中心差分。値0と10のマイナス18乗以下は下端へまとめる。', body) + '<p class="lab-note">橙の実線：前進差分。青の破線：中心差分。縦軸は log₁₀(誤差) で、0や10⁻¹⁸以下は下端にまとめます。正確な値は下で確認できます。</p>';
      host.querySelector('.lab-readout').innerHTML = `<p>刻み h = ${result('h', s.h)}<br>計算された前進幅 (x+h)−x = ${result('actualForwardStep', s.actualForwardStep)}<br>計算された後退幅 x−(x−h) = ${result('actualBackwardStep', s.actualBackwardStep)}<br>解析的導関数の計算値 = ${result('exact', s.exact)}<br>前進差分 = ${result('forward', s.forward)}<br>中心差分 = ${result('central', s.central)}<br>前進差分の絶対誤差 = ${result('forwardError', s.forwardError)}<br>中心差分の絶対誤差 = ${result('centralError', s.centralError)}<br>前進の打切り誤差上界（実数演算） = ${result('forwardTruncationBound', s.forwardTruncationBound)}<br>中心の打切り誤差上界（実数演算） = ${result('centralTruncationBound', s.centralTruncationBound)}<br>前進の丸めモデル尺度 = ${result('forwardRoundingScale', s.forwardRoundingScale)}<br>中心の丸めモデル尺度 = ${result('centralRoundingScale', s.centralRoundingScale)}<br>x±h を両側で区別できるか = ${result('inputResolved', s.inputResolved, s.inputResolved ? '両方を区別' : '少なくとも一方が x に丸められた')}</p><p>丸めモデル尺度は Number.EPSILON と関数値の大きさから作る目安です。Math.exp の実装や入力 x±h の丸めを含む厳密な誤差上界ではありません。打切り上界だけを浮動小数計算の誤差保証に使うこともできません。</p>`;
      return s.inputResolved ? '実数演算の打切り誤差上界と、実際の差分の誤差を分けて表示しています。' : '刻みが小さく、少なくとも一方の入力 x±h が x と同じ計算値になりました。差分0と正しい微分値0は別です。';
    });
  }
  function ode(host) {
    const prefix = 'numerical-ode-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'lambda', '係数 λ', -4, 2, .25, -1)}${range(prefix, 'y0', '初期値 y₀', -2, 2, .25, 1)}${range(prefix, 'n', '区間 [0,2] の分割数 N', 1, 64, 1, 8)}</div><p class="lab-note">自作モデル y′=λy、y(0)=y₀ の厳密解 y₀exp(λt) と前進Euler法を比較します。λ&gt;0での非零解の絶対値の増大（0解は一定）と、λ&lt;0での数値的不安定性は区別します。</p>${panels}`;
    bind(host, { lambda: -1, y0: 1, n: 8 }, input => {
      const s = math.odeState(input); host.dataset.domainState = s.stability;
      const extent = Math.max(1, ...s.points.flatMap(p => [Math.abs(p.euler), Math.abs(p.exact)]));
      const x = t => 58 + 126 * t, y = value => 190 - 90 * value / extent;
      const exactPoints = Array.from({ length: 101 }, (_, k) => { const t = k / 50; return [x(t), y(s.y0 * Math.exp(s.lambda * t))]; });
      let body = line(58, 190, 322, 190) + line(58, 90, 58, 293) + label(58, 325, '0') + label(310, 325, '2') + label(180, 345, '時刻 t') + label(180, 27, '値 y(t)');
      body += label(180, 65, '縦の範囲 ±' + number(extent));
      body += curve(exactPoints, '--series-2', '7 4') + curve(s.points.map(p => [x(p.t), y(p.euler)]), '--series-1');
      body += s.points.map(p => dot(x(p.t), y(p.euler))).join('');
      const amplification = [1, Math.abs(s.factor), s.factor * s.factor];
      const amplificationMax = Math.max(1, ...amplification);
      body += line(26, 370, 334, 370, '--rule-2');
      body += label(180, 410, '初期の差の倍率 |q|^k');
      amplification.forEach((value, k) => {
        const row = 453 + 56 * k;
        body += label(28, row, String(k));
        body += line(58, row + 10, 58 + 205 * value / amplificationMax, row + 10, '--series-2');
        body += dot(58 + 205 * value / amplificationMax, row + 10, '--series-2');
        body += label(326, row, number(value), 'end');
      });
      body += label(180, 610, '行：k=0,1,2（同じ横縮尺）');
      const trajectoryDesc = '上段の横軸は時刻0から2、縦軸は±' + number(extent) + '。橙実線と点がEuler法、青破線が厳密解。増幅率q=' + number(s.factor) + '。下段は初期の差の絶対倍率1、|q|、|q|²を共通の横縮尺で示し、値は' + amplification.map(number).join('、') + '。y0=0の表示解が0でも、この倍率は変わらない。';
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-trajectory', 'Euler軌道と、初期摂動の増幅率', trajectoryDesc, body, 635) + '<p class="lab-note">上段の実線と点：Euler近似、破線：厳密解。縦軸は値に応じて変わり、点間の線は離散値を結ぶ補助線です。下段は別の横軸で、同じ設定に二つの異なる初期値を入れたときの差の絶対倍率1, |q|, |q|²です。y₀=0でも摂動の増幅性は残ります。棒の横縮尺は設定で変わるため、別設定の画面上の長さを直接比較せず数値を読みます。</p>';
      const classification = { decay: '絶対値が縮む |q|<1', boundary: '境界 |q|=1', growth: '絶対値が増幅 |q|>1' }[s.stability];
      host.querySelector('.lab-readout').innerHTML = `<p>刻み h = ${result('h', s.h)}<br>増幅率 q=1+hλ = ${result('factor', s.factor)}<br>反復の分類 = ${result('stability', s.stability, classification)}<br>t=2 のEuler値 = ${result('final', s.final)}<br>t=2 の厳密解の計算値 = ${result('exact', s.exact)}<br>t=2 の絶対誤差 = ${result('error', s.error)}</p><p>${s.lambda < 0 ? Math.abs(s.factor) < 1 ? '厳密解は減衰し、離散反復も減衰します。有限の刻みではまだ誤差が残ります。' : Math.abs(s.factor) === 1 ? '厳密解は減衰しますが離散反復は減衰しません。q=−1では符号を交互に変え、初期誤差の大きさも残ります。' : '厳密解は減衰するのに、離散反復の絶対値は増幅します。刻みを小さくして安定域へ入れる必要があります。' : s.lambda === 0 ? '厳密解もEuler近似も初期値のままです。q=1は境界で、減衰ではありません。' : '非零解の絶対値が増大します。0解は一定です。|q|>1だけを理由に、減衰問題の数値的不安定性と同じ結論は出せません。'}</p><p>y₀=0ならどの設定でも表示解は0です。ただし増幅率の分類は、非零の初期摂動を入れたときの性質です。この有限区間の比較だけで、一般のODE解法の収束を証明したことにはなりません。</p>`;
      return `増幅率 q=${number(s.factor)}、${classification}。厳密解と有限のEuler近似を表示しています。`;
    });
  }
  function initialize() {
    const labs = { 'numerical-root': root, 'numerical-difference': difference, 'numerical-ode': ode };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) { labs[host.dataset.lab](host); host.dataset.labInitialized = 'true'; }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
