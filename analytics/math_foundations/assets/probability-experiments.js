(function () {
  'use strict';
  const math = globalThis.MathProbability;
  if (!math) return;
  let serial = 0;
  const fmt = value => {
    if (value === 0) return '0';
    if (Math.abs(value) <= 1e-12) return '約0';
    return Math.abs(value) < 1e-4 ? value.toExponential(3) : value.toFixed(4).replace(/\.?0+$/, '');
  };
  const percent = value => fmt(100 * value) + '%';
  const tickPercent = value => (100 * value).toFixed(1).replace(/\.0$/, '') + '%';
  const result = (key, value, text) => `<span data-value="${key}" data-raw="${value === null ? 'null' : value}"><strong>${text === undefined ? (value === null ? '条件付け不可' : fmt(value)) : text}</strong></span>`;
  const label = (x, y, text, anchor = 'middle') => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink-2);font-size:28px">${text}</text>`;
  const line = (x1, y1, x2, y2, color = '--grid', dash = '', width = 2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const curve = (points, color, dash = '') => `<polyline points="${points.map(p => p.join(',')).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:3;${dash ? `stroke-dasharray:${dash};` : ''}"/>`;
  const dot = (x, y, color = '--series-1') => `<circle cx="${x}" cy="${y}" r="6" style="fill:var(${color});stroke:var(--surface);stroke-width:2"/>`;
  function figure(id, title, description, body, height = 360) {
    return `<svg class="lab-svg" viewBox="0 0 480 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${title}</title><desc id="${id}-desc">${description}</desc>${body}</svg>`;
  }
  function chart(xmax, ymax, xticks, yticks, xlabel, ylabel) {
    const left = 96, right = 438, top = 40, bottom = 278;
    const x = v => left + (right - left) * v / xmax;
    const y = v => bottom - (bottom - top) * v / ymax;
    let svg = '';
    for (const tick of xticks) {
      const [v, text] = Array.isArray(tick) ? tick : [tick, fmt(tick)];
      svg += line(x(v), top, x(v), bottom) + label(x(v), 316, text);
    }
    for (const tick of yticks) {
      const [v, text] = Array.isArray(tick) ? tick : [tick, fmt(tick)];
      svg += line(left, y(v), right, y(v)) + label(left - 12, y(v) + 9, text, 'end');
    }
    svg += line(left, top, left, bottom, '--ink-2') + line(left, bottom, right, bottom, '--ink-2');
    svg += label(right, 352, xlabel, 'end') + label(left, 27, ylabel, 'start');
    return { x, y, left, right, top, bottom, svg };
  }
  function range(prefix, key, title, min, max, step, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="${step}" value="${value}"></label>`;
  }
  const reset = '<div class="lab-actions"><button type="button" data-action="reset" data-reset>初期状態に戻す</button></div>';
  const panels = '<div data-figures></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div>';
  const rounding = '<p class="lab-note">表示は浮動小数点の近似を丸めています。非零でも絶対値10⁻¹²以下は「約0」と表示します。表示が同じでも、数学的な等号とは限りません。</p>';
  function bind(host, defaults, render, normalize) {
    const controls = [...host.querySelectorAll('input[data-key]')];
    function update() {
      const values = Object.fromEntries(controls.map(c => [c.dataset.key, Number(c.value)]));
      try {
        if (normalize) normalize(values);
        host.querySelectorAll('output[data-value]').forEach(o => { o.textContent = fmt(values[o.dataset.value]); });
        render(values);
      } catch (error) {
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = 'この数値範囲では計算できません。初期状態に戻すか、値を調整してください。';
      }
    }
    controls.forEach(c => c.addEventListener('input', update));
    host.querySelector('[data-reset]').addEventListener('click', () => {
      // A prior marginal change may have restricted the joint slider beyond its initial value.
      const joint = controls.find(c => c.dataset.key === 'joint');
      if (joint) { joint.min = 0; joint.max = 1; }
      controls.forEach(c => { c.value = defaults[c.dataset.key]; });
      update();
    });
    update();
  }
  function tableFigure(prefix, cells, rows, columns, title, description, comparison) {
    let svg = label(207, 45, columns[0]) + label(378, 45, columns[1]);
    rows.forEach((text, i) => { svg += label(70, 124 + 95 * i, text); });
    cells.forEach((probability, i) => {
      const x = 122 + (i % 2) * 171, y = 65 + Math.floor(i / 2) * 95;
      const color = i === 0 ? '--series-1' : i === 2 ? '--series-2' : '--surface-2';
      svg += '<rect x="' + x + '" y="' + y + '" width="171" height="95" style="fill:var(' + color + ');fill-opacity:' + (i === 0 || i === 2 ? '.2' : '1') + ';stroke:var(--rule-2);stroke-width:2"/>';
      svg += label(x + 85.5, y + 59, percent(probability));
    });
    for (const [value, text] of [[0, '0'], [.5, '50%'], [1, '100%']]) {
      const x = 160 + 280 * value;
      svg += line(x, 315, x, 450, '--grid', '4 5') + label(x, 482, text);
    }
    svg += label(90, 310, 'P(A∩B)') + label(90, 347, percent(comparison.joint));
    svg += label(90, 385, 'P(A)P(B)') + label(90, 422, percent(comparison.product));
    svg += '<rect x="160" y="326" width="' + (280 * comparison.joint) + '" height="20" style="fill:var(--series-1);fill-opacity:.4;stroke:var(--series-1);stroke-width:2"/>';
    svg += '<rect x="160" y="401" width="' + (280 * comparison.product) + '" height="20" style="fill:var(--series-2);fill-opacity:.2;stroke:var(--series-2);stroke-width:2;stroke-dasharray:6 4"/>';
    svg += line(160, 450, 440, 450, '--ink-2');
    svg += label(240, 535, '差＝' + fmt(comparison.difference));
    return figure(prefix + '-table', title, description + '下の二本の棒は同じ0から100%の尺度。実線枠は共通確率、破線枠は周辺確率の積で、長さが一致することが独立の等式に対応する。', svg, 565);
  }
  function bayesNormalizationFigure(prefix, s, description) {
    const pattern = prefix + '-striped';
    let body = '<defs><pattern id="' + pattern + '" patternUnits="userSpaceOnUse" width="10" height="10"><path d="M0 10 L10 0" style="fill:none;stroke:var(--ink-3);stroke-width:1.5"/></pattern></defs>';
    body += label(207, 45, '+') + label(378, 45, '−') + label(70, 124, 'D') + label(70, 219, 'Dᶜ');
    s.cells.forEach((mass, i) => {
      const x = 122 + (i % 2) * 171, y = 65 + Math.floor(i / 2) * 95;
      const color = i === 0 ? '--series-1' : i === 2 ? '--series-2' : '--surface-2';
      body += '<rect x="' + x + '" y="' + y + '" width="171" height="95" style="fill:var(' + color + ');fill-opacity:' + (i === 0 || i === 2 ? '.2' : '1') + ';stroke:var(--rule-2);stroke-width:2"/>';
      if (i === 2) {
        body += '<rect x="' + x + '" y="' + y + '" width="171" height="95" style="fill:url(#' + pattern + ');fill-opacity:.4"/>';
        body += '<rect x="' + (x + 17) + '" y="' + (y + 28) + '" width="137" height="39" rx="3" style="fill:var(--surface);stroke:none"/>';
      }
      body += label(x + 85.5, y + 59, percent(mass));
    });
    if (s.posterior === null) {
      body += label(240, 294, 'P(+)=0 では割れない');
      body += '<rect x="100" y="340" width="340" height="46" style="fill:none;stroke:var(--ink-2);stroke-width:2;stroke-dasharray:6 5"/>';
      body += label(270, 371, '条件付け不可');
      body += label(240, 437, '0%の分布ではありません');
    } else {
      const first = 340 * s.posterior, second = 340 - first;
      body += label(240, 294, 'P(+)=' + percent(s.positive) + ' で割る');
      body += '<rect x="100" y="340" width="' + first + '" height="46" style="fill:var(--series-1);fill-opacity:.3"/>';
      body += '<rect x="' + (100 + first) + '" y="340" width="' + second + '" height="46" style="fill:var(--series-2);fill-opacity:.3"/>';
      body += '<rect x="' + (100 + first) + '" y="340" width="' + second + '" height="46" style="fill:url(#' + pattern + ');fill-opacity:.4"/>';
      body += '<rect x="100" y="340" width="340" height="46" style="fill:none;stroke:var(--ink-2);stroke-width:2"/>';
      body += line(100 + first, 340, 100 + first, 386, '--ink-2', '5 4', 2);
      body += label(240, 435, 'D（無地）：' + percent(s.posterior));
      body += label(240, 480, 'Dᶜ（斜線）：' + percent(1 - s.posterior));
    }
    const title = '同時確率の警報列を事後確率へ正規化する';
    const desc = 'Dは不良品、Dᶜは良品、+は警報、−は警報なし。上の四セルは全製品に対する同時確率。' + description + (s.posterior === null
      ? '警報全体が0なので正規化する分布は定義しない。バーは空の破線枠で条件付け不可と示し、0%へ置き換えない。'
      : '上の左列が警報全体。その二セルを合計で割った下の長方形は合計100%。無地の不良割合は' + percent(s.posterior) + '、斜線の良品割合は' + percent(1 - s.posterior) + '。上のセルは面積比例ではなく数字を読む表、下の帯の長さは条件付き確率に比例する。');
    return figure(prefix + '-normalization', title, desc, body, 510);
  }
  function bayes(host) {
    const prefix = 'probability-bayes-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'prior', '不良率 P(D)', .01, .99, .01, .01)}${range(prefix, 'sensitivity', '検出率 P(+ | D)', 0, 1, .01, .9)}${range(prefix, 'falsePositive', '誤警報率 P(+ | Dᶜ)', 0, 1, .01, .05)}</div>${reset}<p class="lab-note">仮想の工場検査モデルです。Dは不良品、Dᶜは良品、+は警報、−は警報なしを表します。表の4セルは全製品に対する同時確率です。左列の二セルを合わせたものが警報全体です。上の表のセル面積は確率を表しません。下の帯では、その列を合計100%に正規化します。不良Dは無地、良品Dᶜは斜線で、長さが条件付き確率に比例します。</p>${panels}${rounding}`;
    bind(host, { prior: .01, sensitivity: .9, falsePositive: .05 }, input => {
      const s = math.bayesState(input);
      const description = `不良かつ警報 ${percent(s.cells[0])}、不良かつ警報なし ${percent(s.cells[1])}、良品かつ警報 ${percent(s.cells[2])}、良品かつ警報なし ${percent(s.cells[3])}。`;
      host.querySelector('[data-figures]').innerHTML = bayesNormalizationFigure(prefix, s, description);
      host.querySelector('.lab-readout').innerHTML = `<p>不良かつ警報 P(D ∩ +) = ${result('truePositive', s.truePositive, percent(s.truePositive))}<br>良品かつ警報 P(Dᶜ ∩ +) = ${result('falsePositiveMass', s.falsePositiveMass, percent(s.falsePositiveMass))}<br>警報 P(+) = ${result('positive', s.positive, percent(s.positive))}<br>警報が出た後の不良確率 P(D | +) = ${result('posterior', s.posterior, s.posterior === null ? '条件付け不可' : percent(s.posterior))}</p><p>${s.posterior === null ? 'P(+) = 0なので、警報を条件にした確率はこの式では定義できません。0%という意味ではありません。' : '分母は警報全体、分子はそのうちの不良品です。検出率と、警報が出た後の不良確率は別の条件付き確率です。'}</p>`;
    });
  }
  function independence(host) {
    const prefix = 'probability-independence-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'a', '周辺確率 P(A)', .1, .9, .05, .5)}${range(prefix, 'b', '周辺確率 P(B)', .1, .9, .05, .5)}${range(prefix, 'joint', '同時確率 P(A ∩ B)', 0, .5, .01, .25)}</div>${reset}<p class="lab-note">行がA・Aᶜ、列がB・Bᶜです。4セルは同時確率で、合計は1です。橙の左上はP(A ∩ B)。下段の実線枠はP(A ∩ B)、破線枠はP(A)P(B)を同じ0〜100%の尺度で表します。独立は二本の長さが等しいか、排反は左上セルが0かという別の検査です。セルの面積は確率を表しません。同じ長さに見えるだけで厳密な等号を認定せず、数値と定義も確かめます。</p>${panels}${rounding}`;
    bind(host, { a: .5, b: .5, joint: .25 }, input => {
      const s = math.independenceState(input);
      const description = `P(A)=${fmt(s.a)}、P(B)=${fmt(s.b)}、P(A ∩ B)=${fmt(s.joint)}。同時確率と周辺確率の積の差は${fmt(s.difference)}。`;
      host.querySelector('[data-figures]').innerHTML = tableFigure(prefix, s.cells, ['A', 'Aᶜ'], ['B', 'Bᶜ'], '同時確率と周辺確率の積を同じ尺度で比べる', description, s);
      host.querySelector('.lab-readout').innerHTML = `<p>同時確率 P(A ∩ B) = ${result('joint', s.joint)}<br>周辺確率の積 P(A)P(B) = ${result('product', s.product)}<br>差 P(A ∩ B) − P(A)P(B) = ${result('difference', s.difference)}<br>条件付き確率 P(A | B) = ${result('conditional', s.conditional)}</p><p>実現可能な同時確率の範囲：${fmt(input.minimum)} ≤ P(A ∩ B) ≤ ${fmt(input.maximum)}。${input.clamped ? '周辺確率の変更に合わせ、同時確率をこの範囲の端へ調整しました。' : 'この範囲なら4セルは非負です。'}</p><p>差の丸め表示が0や「約0」でも、厳密な独立の証明にはなりません。独立の定義はP(A ∩ B) = P(A)P(B)です。</p>`;
    }, input => {
      // Marginal controls use hundredths; round their derived endpoint to the same decimal grid.
      const minimum = Math.max(0, Math.round((input.a + input.b - 1) * 100) / 100), maximum = Math.min(input.a, input.b);
      const joint = host.querySelector('input[data-key="joint"]');
      const clamped = input.joint < minimum || input.joint > maximum;
      joint.min = minimum; joint.max = maximum;
      joint.value = Math.max(minimum, Math.min(maximum, input.joint));
      Object.assign(input, { joint: Number(joint.value), minimum, maximum, clamped });
    });
  }
  function binomial(host) {
    const prefix = 'probability-binomial-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'n', '独立な試行回数 n', 1, 40, 1, 10)}${range(prefix, 'p', '1回の成功確率 p', 0, 1, .01, .5)}</div>${reset}<p class="lab-note">各回が独立で成功確率pのBernoulli試行をn回行い、成功回数Sを数えるモデルです。第一図の橙の棒の高さがP(S = k)です。棒の高さの合計は1で、連続密度の面積とは区別します。第二図の青線は累積分布関数F(x) = P(S ≤ x)です。</p>${panels}${rounding}`;
    bind(host, { n: 10, p: .5 }, input => {
      const s = math.binomialState(input), ymax = Math.max(...s.pmf);
      const xticks = s.n === 1 ? [0, 1] : [0, Math.floor(s.n / 2), s.n];
      const plane = chart(s.n, ymax, xticks, [0, [ymax / 2, tickPercent(ymax / 2)], [ymax, tickPercent(ymax)]], '成功回数 k', '確率');
      // Offset endpoint bars inside the plot, keeping their full width visible.
      const barWidth = Math.min(34, (plane.right - plane.left) / (s.n + 1) * .8);
      const center = k => plane.left + barWidth / 2 + (plane.right - plane.left - barWidth) * k / s.n;
      // Tick positions follow these discrete bar centres, including k=0 and k=n.
      let body = '';
      for (const tick of xticks) body += line(center(tick), plane.top, center(tick), plane.bottom) + label(center(tick), 316, tick);
      for (const [height, text] of [[0, '0'], [ymax / 2, tickPercent(ymax / 2)], [ymax, tickPercent(ymax)]]) body += line(plane.left, plane.y(height), plane.right, plane.y(height)) + label(plane.left - 12, plane.y(height) + 9, text, 'end');
      body += line(plane.left, plane.top, plane.left, plane.bottom, '--ink-2') + line(plane.left, plane.bottom, plane.right, plane.bottom, '--ink-2') + label(plane.right, 352, '成功回数 k', 'end') + label(plane.left, 27, '確率', 'start');
      s.pmf.forEach((mass, k) => {
        body += `<rect x="${center(k) - barWidth / 2}" y="${plane.y(mass)}" width="${barWidth}" height="${plane.bottom - plane.y(mass)}" style="fill:var(--series-1);fill-opacity:.72;stroke:var(--series-1);stroke-width:1"/>`;
      });
      const description = `n=${s.n}、p=${fmt(s.p)}。平均${fmt(s.mean)}、分散${fmt(s.variance)}。${s.p === 0 ? '成功回数0の確率が1。' : s.p === 1 ? `成功回数${s.n}の確率が1。` : '棒は各整数での確率を表します。'}`;
      const cumulative = chart(s.n, 1, xticks, [0, .5, 1], 'x', '累積確率 F(x)');
      const radius = 5;
      const markerStep = Math.ceil(s.n / 20);
      const marked = k => k % markerStep === 0 || k === s.n;
      for (let k = 0; k < s.n; k++) {
        cumulative.svg += line(cumulative.x(k), cumulative.y(s.cdf[k]), cumulative.x(k + 1), cumulative.y(s.cdf[k]), '--series-2', '', 3);
      }
      // Draw the excluded right endpoint before the included integer points. When
      // adjacent CDF values coincide there is no jump and no open point is needed.
      for (let k = 0; k < s.n; k++) if (marked(k + 1) && s.cdf[k] < s.cdf[k + 1]) {
        cumulative.svg += `<circle cx="${cumulative.x(k + 1)}" cy="${cumulative.y(s.cdf[k])}" r="${radius}" style="fill:var(--surface);stroke:var(--series-2);stroke-width:2"/>`;
      }
      s.cdf.forEach((probability, k) => {
        if (!marked(k)) return;
        cumulative.svg += `<circle cx="${cumulative.x(k)}" cy="${cumulative.y(probability)}" r="${radius}" style="fill:var(--series-2);stroke:var(--surface);stroke-width:1"/>`;
      });
      const cumulativeDescription = `n=${s.n}、p=${fmt(s.p)}。整数kの塗りつぶし点はF(k)=P(S≤k)で、F(0)=${fmt(s.cdf[0])}、F(n)=1。k以上k+1未満ではF(k)の一定値をとる右連続の階段です。跳び上がる箇所の右端の白抜き点はその低い値を含みません。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">第1図：確率質量関数（PMF）</p>${figure(prefix + '-pmf', '二項分布の確率質量関数', description, body)}<p class="lab-note">第2図：累積分布関数（CDF）</p><p class="lab-note">整数kの塗りつぶし点がF(k)です。k ≤ x &lt; k + 1では水平に一定で、跳び上がる箇所の右端の白抜き点はその低い値を含みません。実数の間を斜めに補間しません。nが20を超えると点は一部の整数位置に間引き、横線は全区間に描きます。とても小さい跳びでは二点が重なることがあります。図の外ではx &lt; 0で0、x ≥ nで1です。</p>${figure(prefix + '-cdf', '二項分布の右連続な累積分布関数', cumulativeDescription, cumulative.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>平均 E[S] = np = ${result('mean', s.mean)}<br>分散 Var(S) = np(1 − p) = ${result('variance', s.variance)}<br>全確率の和 = ${result('total', s.pmf.reduce((sum, v) => sum + v, 0))}<br>P(S = 0) = ${result('zeroMass', s.pmf[0], percent(s.pmf[0]))}<br>P(S = n) = ${result('allMass', s.pmf[s.n], percent(s.pmf[s.n]))}</p><p>${s.p === 0 || s.p === 1 ? '端点のpでは、成功回数が一つの値に確定する退化分布です。分散は0です。' : 'nとpは分布のモデルを定めます。この図は乱数による実測頻度ではありません。'}</p>`;
    });
  }
  function density(host) {
    const prefix = 'probability-density-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'b', '区間の右端 b', 0, 1, .01, .5)}</div>${reset}<p class="lab-note">密度f(x) = 2x（0 ≤ x ≤ 1、区間外は0）を考えます。第一図の橙の塗りが0からbまでの面積、青の破線がその右端です。第二図の曲線は累積分布関数F(b) = b²で、橙の点の高さが同じ確率です。</p>${panels}${rounding}`;
    bind(host, { b: .5 }, ({ b }) => {
      const s = math.densityState(b), densityPlot = chart(1, 2, [0, .5, 1], [0, 1, 2], 'x', '密度 f(x)');
      densityPlot.svg += `<polygon points="${[[densityPlot.x(0), densityPlot.y(0)], [densityPlot.x(b), densityPlot.y(2 * b)], [densityPlot.x(b), densityPlot.y(0)]].map(p => p.join(',')).join(' ')}" style="fill:var(--series-1);fill-opacity:.25"/>`;
      densityPlot.svg += curve([[densityPlot.x(0), densityPlot.y(0)], [densityPlot.x(1), densityPlot.y(2)]], '--series-1');
      densityPlot.svg += line(densityPlot.x(b), densityPlot.y(0), densityPlot.x(b), densityPlot.y(2 * b), '--series-2', '8 5', 3) + dot(densityPlot.x(b), densityPlot.y(2 * b), '--series-2');
      const cdfPlot = chart(1, 1, [0, .5, 1], [0, .5, 1], 'b', '累積確率 F(b)');
      cdfPlot.svg += curve(Array.from({ length: 65 }, (_, i) => [cdfPlot.x(i / 64), cdfPlot.y((i / 64) ** 2)]), '--series-2');
      cdfPlot.svg += line(cdfPlot.x(b), cdfPlot.y(0), cdfPlot.x(b), cdfPlot.y(s.probability), '--ink-2', '4 5') + dot(cdfPlot.x(b), cdfPlot.y(s.probability));
      const description = `b=${fmt(b)}、密度の高さf(b)=${fmt(s.density)}、0からbまでの確率は${fmt(s.probability)}。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">密度：確率は橙の面積</p>${figure(prefix + '-density', '密度と区間の確率', description, densityPlot.svg)}<p class="lab-note">累積分布関数：確率は点の高さ</p>${figure(prefix + '-cdf', '密度を積分した累積分布関数', description, cdfPlot.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>密度の高さ f(b) = 2b = ${result('density', s.density)}<br>区間の確率 P(0 ≤ X ≤ b) = b² = ${result('probability', s.probability, percent(s.probability))}<br>一点の確率 P(X = b) = ${result('pointProbability', 0)}</p><p>密度の高さは確率そのものではないので1を超えても構いません。一点は幅が0なので、密度が正でも面積は0です。確率0というだけで、その点が標本空間にないとはいえません。</p>`;
    });
  }
  function lln(host) {
    const prefix = 'probability-lln-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'n', '試行回数 n', 10, 200, 10, 100)}${range(prefix, 'p', '成功確率・母平均 p', .1, .9, .05, .5)}${range(prefix, 'epsilon', 'ずれの閾値 ε', .05, .5, .05, .1)}</div>${reset}<p class="lab-note">主図は独立Bernoulliモデルの理論値です。橙の実線と丸が逸脱確率、青の破線と四角がChebyshev上界。灰色の縦点線と二つの印が、選んだnでの値を示します。曲線は整数nの値をつなぐ補助線です。</p>${panels}${rounding}`;
    let cachedParameters = '', probabilities = [];
    bind(host, { n: 100, p: .5, epsilon: .1 }, input => {
      const s = math.llnState({ ...input, seed: 42 });
      const key = s.p + ':' + s.epsilon;
      if (key !== cachedParameters) {
        // Retain only 200 scalar triples and replace the cache when p or epsilon changes.
        // The n slider reuses the same theoretical curves without 200 repeated calls.
        probabilities = Array.from({ length: 200 }, (_, index) => {
          const state = math.llnState({ n: index + 1, p: s.p, epsilon: s.epsilon, seed: 42 });
          return { n: state.n, exactTail: state.exactTail, bound: state.bound };
        });
        cachedParameters = key;
      }
      const theory = chart(200, 1, [1, 100, 200], [0, .5, 1], '試行回数 n', '逸脱確率・上界');
      theory.svg += curve(probabilities.map(point => [theory.x(point.n), theory.y(point.bound)]), '--series-2', '9 6');
      theory.svg += curve(probabilities.map(point => [theory.x(point.n), theory.y(point.exactTail)]), '--series-1');
      theory.svg += line(theory.x(s.n), theory.top, theory.x(s.n), theory.bottom, '--ink-2', '3 6');
      theory.svg += `<rect x="${theory.x(s.n) - 6}" y="${theory.y(s.bound) - 6}" width="12" height="12" style="fill:var(--series-2);stroke:var(--surface);stroke-width:2"/>`;
      theory.svg += dot(theory.x(s.n), theory.y(s.exactTail));
      const theoryDescription = `p=${fmt(s.p)}、epsilon=${fmt(s.epsilon)}を固定したn=1から200の理論値。選んだn=${s.n}では逸脱確率${fmt(s.exactTail)}、Chebyshev上界${fmt(s.bound)}。逸脱確率は格子の影響で単調に下がるとは限りません。`;
      const plane = chart(s.n, 1, [0, s.n / 2, s.n], [0, .5, 1], '試行回数', '標本平均');
      const low = Math.max(0, s.p - s.epsilon), high = Math.min(1, s.p + s.epsilon);
      plane.svg += `<rect x="${plane.left}" y="${plane.y(high)}" width="${plane.right - plane.left}" height="${plane.y(low) - plane.y(high)}" style="fill:var(--series-2);fill-opacity:.09"/>`;
      for (const value of [s.p - s.epsilon, s.p + s.epsilon]) if (value >= 0 && value <= 1) plane.svg += line(plane.left, plane.y(value), plane.right, plane.y(value), '--ink-2', '7 6', 2);
      plane.svg += line(plane.left, plane.y(s.p), plane.right, plane.y(s.p), '--series-2', '', 3);
      plane.svg += curve(s.trajectory.map((value, i) => [plane.x(i + 1), plane.y(value)]), '--series-1') + dot(plane.x(s.n), plane.y(s.mean));
      const pathDescription = `一本の経路の例。n=${s.n}、p=${fmt(s.p)}、epsilon=${fmt(s.epsilon)}、seed=42。今回の標本平均は${fmt(s.mean)}。この経路は主図の理論確率を実測したものではありません。`;
      host.querySelector('[data-figures]').innerHTML = `<p class="lab-note">主図：逸脱確率とその上界</p>${figure(prefix + '-theory', '標本平均が閾値以上ずれる理論確率とChebyshev上界', theoryDescription, theory.svg)}<p class="lab-note">補助図：一本の経路の例（固定seed = 42）</p><p class="lab-note">橙の実線は疑似乱数列から作った標本平均、青の水平実線は母平均p、灰色の破線はp ± εです（0〜1の図内のみ）。淡い帯は|標本平均 − p| &lt; εの範囲で、経路が常に帯内に留まる保証ではありません。</p>${figure(prefix + '-trajectory', '補助図：再現可能な一本のBernoulli標本平均の経路', pathDescription, plane.svg)}`;
      host.querySelector('.lab-readout').innerHTML = `<p>理論の逸脱確率 P(|X̄ₙ − p| ≥ ε) = ${result('exactTail', s.exactTail, percent(s.exactTail))}<br>Chebyshev上界 min(1, p(1 − p)/(nε²)) = ${result('bound', s.bound, percent(s.bound))}<br>母平均 p = ${result('populationMean', s.p)}</p><p>補助図の標本平均 = ${result('mean', s.mean)}<br>補助図のずれ |標本平均 − p| = ${result('deviation', Math.abs(s.mean - s.p))}</p><p>主図の逸脱確率は二項分布を足した理論値です。pとεを固定すると上界はnとともに下がるか一定ですが、逸脱確率は整数の格子と閾値の位置によって途中で増えることもあります。弱大数は逸脱確率が0へ近づく主張であり、各段階で単調に減ることは要求しません。</p><p>上界は同じnでの確率の評価で、一本の経路全体を保証しません。補助図の標本平均は上下に動き、毎回母平均へ近づくとは限りません。seed固定の有限疑似乱数列は再現可能な観察用で、独立性や弱大数の証明にはなりません。nを変えても同じ列の先頭を使います。</p><p>≥の境界判定では、入力値の最短十進表現を整数比として比較し、等号の丸め落ちを避けています。</p>`;
    });
  }
  function initialize() {
    const labs = { 'probability-bayes': bayes, 'probability-independence': independence, 'probability-binomial': binomial, 'probability-density': density, 'probability-lln': lln };
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
