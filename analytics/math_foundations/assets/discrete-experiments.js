(function () {
  'use strict';
  const math = globalThis.MathDiscrete;
  if (!math) return;
  let serial = 0;
  const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const display = value => value === Infinity ? '∞' : value === null ? 'なし' : String(value);
  const raw = value => value === Infinity ? 'unreachable' : value === null ? 'null' : String(value);
  const result = (key, value, text) => `<span data-value="${escape(key)}" data-raw="${escape(raw(value))}" data-raw-value="${escape(raw(value))}"><strong>${escape(text === undefined ? display(value) : text)}</strong></span>`;
  const label = (x, y, text, color = '--ink', size = 24) => `<text x="${x}" y="${y}" text-anchor="middle" style="fill:var(${color});font-size:${size}px">${escape(text)}</text>`;
  const line = (x1, y1, x2, y2, color = '--rule-2', width = 2, dashed = false) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" style="stroke:var(${color});stroke-width:${width};${dashed ? 'stroke-dasharray:6 4;' : ''}"/>`;
  function figure(id, title, description, body, height = 330) {
    return `<svg class="lab-svg" viewBox="0 0 360 ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${escape(title)}</title><desc id="${id}-desc">${escape(description)}</desc>${body}</svg>`;
  }
  function range(prefix, key, title, min, max, value) {
    return `<label class="lab-control" for="${prefix}-${key}"><span class="lab-control-label">${title}：<output data-value="${key}" for="${prefix}-${key}"></output></span><input type="range" id="${prefix}-${key}" data-key="${key}" min="${min}" max="${max}" step="1" value="${value}"></label>`;
  }
  const reset = '<div class="lab-actions"><button type="button" data-action="reset" data-reset>初期状態に戻す</button></div>';
  const panels = '<p class="lab-status" role="status" aria-live="polite"></p><div data-figures></div><div class="lab-readout"></div>';
  function table(caption, headings, rows) {
    return `<div class="concept-table-wrap" tabindex="0" role="region" aria-label="${escape(caption)}"><table class="concept-table"><caption>${escape(caption)}</caption><thead><tr>${headings.map(heading => `<th scope="col">${escape(heading)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }
  function bind(host, defaults, render, normalize, resetLimits) {
    const controls = [...host.querySelectorAll('[data-key]')];
    function update() {
      const values = Object.fromEntries(controls.map(control => [control.dataset.key, control.tagName === 'SELECT' ? control.value : Number(control.value)]));
      try {
        if (normalize) normalize(values);
        host.querySelectorAll('output[data-value]').forEach(output => {
          const value = values[output.dataset.value];
          output.textContent = display(value); output.dataset.raw = raw(value); output.dataset.rawValue = raw(value);
        });
        host.querySelector('.lab-status').textContent = render(values);
      } catch (error) {
        host.querySelector('[data-figures]').innerHTML = '';
        host.querySelector('.lab-readout').textContent = '';
        host.querySelector('.lab-status').textContent = 'この値では計算できません。初期状態に戻して値を調整してください。';
      }
    }
    controls.forEach(control => {
      control.addEventListener('input', update);
      if (control.tagName === 'SELECT') control.addEventListener('change', update);
    });
    host.querySelector('[data-reset]').addEventListener('click', () => {
      if (resetLimits) resetLimits();
      controls.forEach(control => { control.value = defaults[control.dataset.key]; });
      update();
    });
    update();
  }
  function modular(host) {
    const prefix = 'discrete-modular-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'm', '法 m', 2, 12, 7)}${range(prefix, 'a', '乗数 a', 0, 6, 3)}${range(prefix, 'x', '入力 x', 0, 6, 2)}</div>${reset}<p class="lab-note">円周上に0からm−1の余りを順に並べます。数字の下の小さい●印が、写像x ↦ ax mod mの像に属する余りです。淡い塗りも同じ所属を示します。橙の大きな破線の輪が入力x、青の小さな実線の輪が出力です。同じ点になることもあります。</p>${panels}<details><summary>すべての入力と出力を表で見る</summary><div data-table></div></details>`;
    bind(host, { m: 7, a: 3, x: 2 }, input => {
      const s = math.modularState(input);
      let body = '<circle cx="180" cy="165" r="115" style="fill:none;stroke:var(--rule-2);stroke-width:2;stroke-dasharray:4 5"/>';
      for (let residue = 0; residue < s.m; residue++) {
        const angle = -Math.PI / 2 + 2 * Math.PI * residue / s.m;
        const x = 180 + 115 * Math.cos(angle), y = 165 + 115 * Math.sin(angle);
        body += `<circle cx="${x}" cy="${y}" r="19" style="fill:var(--surface);stroke:var(--rule-2);stroke-width:2"/>`;
        if (s.image.includes(residue)) body += `<circle cx="${x}" cy="${y}" r="19" style="fill:var(--series-2);fill-opacity:.18;stroke:none"/>`;
        if (s.image.includes(residue)) body += `<circle cx="${x}" cy="${y + 31}" r="3" data-image-residue="${residue}" style="fill:var(--ink);stroke:none"/>`;
        if (residue === s.x) body += `<circle cx="${x}" cy="${y}" r="26" style="fill:none;stroke:var(--series-1);stroke-width:3;stroke-dasharray:5 3"/>`;
        if (residue === s.value) body += `<circle cx="${x}" cy="${y}" r="20" style="fill:none;stroke:var(--series-2);stroke-width:4"/>`;
        body += label(x, y + 8, residue, '--ink', 22);
      }
      const description = `法${s.m}、乗数${s.a}、入力${s.x}、出力${s.value}。数字の下の小さい点が像への所属を表し、像は${s.image.join('、')}。最大公約数は${s.gcd}、逆元は${s.inverse === null ? '存在しません' : s.inverse}。`;
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-circle', '余りの円：数字下の点が乗算の像', description, body, 320);
      host.querySelector('.lab-readout').innerHTML = `<p>${s.a} × ${s.x} mod ${s.m} = ${result('value', s.value)}<br>gcd(${s.a}, ${s.m}) = ${result('gcd', s.gcd)}<br>乗数${s.a}の逆元 = ${result('inverse', s.inverse, s.inverse === null ? '存在しない' : s.inverse)}<br>像 = {${s.image.join(', ')}}<br>像の要素数 = ${result('imageSize', s.image.length)}</p><p>${s.inverse === null ? '異なる入力が同じ出力に重なります。逆元がないことと、ある入力の出力が0であることは別です。' : `${s.a} × ${s.inverse} ≡ 1 (mod ${s.m})。すべての余りがちょうど1回ずつ出力に現れます。`}</p>`;
      host.querySelector('[data-table]').innerHTML = table('各入力の乗算結果', ['入力 x', 'ax mod m'], s.residues.map((value, index) => `<tr><th scope="row">${index}${index === s.x ? ' ← 選択' : ''}</th><td>${value}</td></tr>`));
      return input.clamped ? `法を${s.m}に変更したため、乗数と入力を0から${s.m - 1}の範囲に調整しました。` : `入力${s.x}の出力は${s.value}。像は${s.image.length}種類です。`;
    }, input => {
      input.clamped = false;
      for (const key of ['a', 'x']) {
        const control = host.querySelector(`[data-key="${key}"]`);
        const next = Math.min(input[key], input.m - 1);
        input.clamped = input.clamped || next !== input[key];
        control.max = input.m - 1; control.value = next; input[key] = Number(control.value);
      }
    }, () => {
      for (const key of ['a', 'x']) host.querySelector(`[data-key="${key}"]`).max = 11;
    });
  }
  function recurrence(host) {
    const prefix = 'discrete-recurrence-' + (++serial);
    host.innerHTML = `<div class="lab-controls">${range(prefix, 'n', '盤の長さ n', 0, 20, 5)}</div>${reset}<p class="lab-note">長さ1と長さ2のタイルで、横一列の盤を隙間なく埋めます。最後のタイルを外すと、長さn−1またはn−2の部分問題に分かれます。空の盤にも「何も置かない」1通りがあります。</p>${panels}<details><summary>小さい盤から計算した表を見る</summary><div data-table></div></details>`;
    bind(host, { n: 5 }, ({ n }) => {
      const s = math.recurrenceState({ n });
      function box(x, y, index, value, color, width = 144) {
        return `<rect x="${x}" y="${y}" width="${width}" height="78" rx="8" style="fill:var(--surface-2);stroke:var(${color});stroke-width:3"/>${label(x + width / 2, y + 30, `T(${index})`, '--ink', 24)}${label(x + width / 2, y + 61, value, color, 26)}`;
      }
      let body = '';
      if (n < 2) {
        body += box(108, 30, n, s.value, '--series-1');
        body += label(180, 158, '初期値', '--ink', 24);
        body += label(180, 203, n === 0 ? '空の盤は1通り' : '1マスの盤は1通り', '--ink-2', 22);
      } else {
        body += line(160, 96, 87, 159) + line(200, 96, 273, 159);
        body += label(80, 131, '1マス', '--ink-2', 22) + label(280, 131, '2マス', '--ink-2', 22);
        body += box(108, 18, n, s.value, '--series-1');
        body += box(15, 159, n - 1, s.subproblems[0].value, '--series-2');
        body += box(201, 159, n - 2, s.subproblems[1].value, '--series-2');
        body += label(180, 210, '+', '--ink', 26);
      }
      const description = n < 2 ? `n=${n}は初期値で、並べ方は1通りです。加算は不要です。` : `T(${n})=${s.value}は、T(${n - 1})=${s.subproblems[0].value}とT(${n - 2})=${s.subproblems[1].value}の和です。`;
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-split', '最後のタイルで分ける部分問題', description, body, 260);
      host.querySelector('.lab-readout').innerHTML = `<p>並べ方 T(${n}) = ${result('value', s.value)}<br>表を小さい順に埋める加算回数 = ${result('additions', s.additions)}</p>${n < 2 ? '<p>初期値をそのまま使うので、部分問題への分割も加算も行いません。</p>' : `<p>最後が1マス：T(${n - 1}) = ${result('left', s.subproblems[0].value)}<br>最後が2マス：T(${n - 2}) = ${result('right', s.subproblems[1].value)}<br>${s.subproblems[0].value} + ${s.subproblems[1].value} = ${s.value}</p>`}<p>加算回数はT(2)からT(n)を各1回計算する回数です。画面描画や代入などは数えていません。重複する部分問題を何度も呼ぶ再帰は実行していません。</p>`;
      host.querySelector('[data-table]').innerHTML = table('一度ずつ計算して再利用する値', ['長さ i', '並べ方 T(i)'], s.values.map((value, index) => `<tr><th scope="row">${index}</th><td>${value}</td></tr>`));
      return description + ` 表を埋める加算は${s.additions}回です。`;
    });
  }
  function shortest(host) {
    const prefix = 'discrete-shortest-' + (++serial);
    host.innerHTML = `<div class="lab-controls"><label class="lab-control" for="${prefix}-preset"><span class="lab-control-label">グラフの条件</span><select id="${prefix}-preset" data-key="preset"><option value="normal">通常の重み</option><option value="zeroTie">0重みと同距離</option><option value="disconnected">Fへ到達不能</option></select></label>${range(prefix, 'step', '確定した頂点の数（0は初期状態）', 0, 6, 0)}</div>${reset}<p class="lab-note">始点Aから終点Fを探します。辺は無向で、数字が重みです。●の頂点は距離が確定、○は未確定。二重の輪はこのステップで確定した頂点です。太い青線は現在見つかっているA→Fの道で、Fが未確定なら暫定の道です。距離と親は下の表で読みます。</p>${panels}<div data-table></div>`;
    let previousPreset = 'normal', state = math.shortestPathState({ graph: math.shortestPresets.normal, source: 'A', target: 'F' });
    bind(host, { preset: 'normal', step: 0 }, input => {
      const s = state.steps[input.step], final = input.step === state.steps.length - 1;
      const targetSettled = s.settled.includes('F');
      const vertices = new Map(state.graph.vertices.map(vertex => [vertex.id, vertex]));
      const routeEdges = new Set();
      if (s.route) for (let i = 1; i < s.route.length; i++) routeEdges.add([s.route[i - 1], s.route[i]].sort().join(''));
      let body = '';
      const offsets = { AB: [0, -13], BC: [0, -13], AD: [-17, 0], BE: [20, 0], CF: [19, 0], DE: [-4, 24], EF: [7, 24] };
      state.graph.edges.forEach(edge => {
        const a = vertices.get(edge.from), b = vertices.get(edge.to), key = [edge.from, edge.to].sort().join('');
        const onRoute = routeEdges.has(key);
        body += line(a.x, a.y, b.x, b.y, onRoute ? '--series-2' : '--rule-2', onRoute ? 6 : 3);
        const [dx, dy] = offsets[key] || [0, 0], x = (a.x + b.x) / 2 + dx, y = (a.y + b.y) / 2 + dy;
        body += `<rect x="${x - 14}" y="${y - 19}" width="28" height="30" rx="4" style="fill:var(--surface);stroke:none"/>`;
        body += label(x, y + 4, edge.weight, '--ink', 24);
      });
      state.graph.vertices.forEach(vertex => {
        const settled = s.settled.includes(vertex.id);
        body += `<circle cx="${vertex.x}" cy="${vertex.y}" r="22" style="fill:var(--surface);stroke:var(${settled ? '--series-1' : '--ink-2'});stroke-width:${settled ? 4 : 2};${settled ? '' : 'stroke-dasharray:5 3;'}"/>`;
        if (settled) body += `<circle cx="${vertex.x}" cy="${vertex.y}" r="20" style="fill:var(--series-1);fill-opacity:.18;stroke:none"/>`;
        if (vertex.id === s.current) body += `<circle cx="${vertex.x}" cy="${vertex.y}" r="28" style="fill:none;stroke:var(--series-1);stroke-width:2"/>`;
        body += label(vertex.x, vertex.y + 8, vertex.id, '--ink', 24);
      });
      const routeText = s.route ? s.route.join(' → ') : final ? '到達不能' : 'まだ道が見つかっていない';
      const distanceLabel = targetSettled ? 'Fまでの確定距離' : final ? 'Fまでの距離' : 'Fまでの暫定距離';
      const description = `ステップ${input.step}。確定頂点は${s.settled.length ? s.settled.join('、') : 'なし'}。${distanceLabel}は${display(s.distance)}。${routeText}。`;
      host.querySelector('[data-figures]').innerHTML = figure(prefix + '-graph', 'Dijkstra法の確定頂点と現在の道', description, body);
      host.querySelector('.lab-readout').innerHTML = `<p>ステップ = ${result('step', input.step)}<br>確定頂点数 = ${result('settled', s.settled.length, `${s.settled.length} / 6`)}<br>${distanceLabel} = ${result('distance', s.distance)}<br>${targetSettled ? '最短の道' : s.route ? '暫定の道' : 'A→Fの道'}：${result('route', s.route ? s.route.join('-') : null, routeText)}</p><p>${s.current === null ? '初期状態：Aだけを0、残りを∞とし、まだどの頂点も確定していません。' : `${s.current}を確定。${s.relaxations.length ? '距離を改善：' + s.relaxations.map(r => `${r.to}を${display(r.previous)}から${r.distance}へ`).join('、') + '。' : '未確定頂点の距離の改善はありません。'}`}</p><p>${final && !targetSettled ? '未確定頂点に有限の距離が残っていないので終了です。Fへ到達する道はありません。∞は0ではありません。' : final ? `Aから到達するすべての頂点を確定して終了です。A→Fの最短距離は${s.distance}です。` : '次は未確定頂点のうち暫定距離が最小の頂点を確定します。同距離ならAからFの順で選び、同じ距離の候補では親を変更しません。'}</p>`;
      host.querySelector('[data-table]').innerHTML = table('各頂点の距離と親（●確定・○未確定）', ['頂点', '距離', '親', '状態'], state.graph.vertices.map(vertex => {
        const id = vertex.id, isSettled = s.settled.includes(id), distance = s.distances[id];
        const status = isSettled ? '● 確定' : distance === Infinity ? final ? '○ 到達不能' : '○ 未発見' : '○ 暫定';
        return `<tr><th scope="row">${id}</th><td>${result('distance-' + id, distance)}</td><td>${result('parent-' + id, s.parents[id], s.parents[id] === null ? '—' : s.parents[id])}</td><td>${status}</td></tr>`;
      }));
      return description;
    }, input => {
      if (input.preset !== previousPreset) {
        state = math.shortestPathState({ graph: math.shortestPresets[input.preset], source: 'A', target: 'F' });
        previousPreset = input.preset; input.step = 0;
      }
      const control = host.querySelector('[data-key="step"]');
      control.max = state.steps.length - 1; control.value = Math.min(input.step, state.steps.length - 1); input.step = Number(control.value);
    });
  }
  function initialize() {
    const labs = { 'discrete-modular': modular, 'discrete-recurrence': recurrence, 'discrete-shortest': shortest };
    document.querySelectorAll('[data-lab]').forEach(host => {
      if (!host.dataset.labInitialized && labs[host.dataset.lab]) {
        labs[host.dataset.lab](host); host.dataset.labInitialized = 'true';
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once: true });
  else initialize();
}());
