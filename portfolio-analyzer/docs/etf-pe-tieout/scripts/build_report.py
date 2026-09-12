# ruff: noqa  -- archived working script, kept as run on 2026-09-12
"""Assemble the five-ETF replication report (claude-report template) from rep_*_chart.json."""
import os
import json, re
S = os.environ.get('ETF_PE_WORKDIR', './work/')
old = open(S + 'smh_report.html').read()
css = old[old.index('<style>'):old.index('</style>') + 8]
head = old[:old.index('<style>')].replace('<title>SMH バスケット再現</title>', '<title>ETF バスケット再現</title>')
css = css.replace('</style>', """
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px 22px;margin-top:6px}
.grid .cell{min-width:0}
.cell .lab{display:flex;justify-content:space-between;align-items:baseline;font-family:var(--mono);font-size:11.5px;color:var(--ink-2);margin:0 0 2px}
.cell .lab b{font-family:var(--sans);font-size:14px;color:var(--ink);font-weight:700}
.cell .lab span{color:var(--ink-3)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:30px 0 0}
.cards>div{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r-card);padding:20px 22px 22px}
.cards .t{font-weight:700;font-size:15.5px;margin:0 0 4px;display:flex;gap:10px;align-items:baseline}
.cards .t small{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;color:var(--accent);font-weight:600;text-transform:uppercase}
.cards p{font-size:14px;line-height:1.85;margin:10px 0 0;color:var(--ink-2)}
.cards p strong{color:var(--ink)}
td.jp,th.jp{background:var(--surface-3)}
</style>""")

ETFS = [('SMH', 'smh', 'VanEck Semiconductor', 'SEC N-PORT · 四半期', 25, 0.35, '$'),
        ('QQQ', 'qqq', 'Invesco QQQ Trust', 'SEC N-PORT · 四半期', 101, 0.20, '$'),
        ('XLE', 'xle', 'Energy Select Sector SPDR', 'SEC N-PORT · 四半期', 22, 0.08, '$'),
        ('1329', '1329_q', 'iShares Core 日経225 ETF', 'iShares JP 保有明細 · 四半期末', 225, 0.0495, '¥'),
        ('1475', '1475_q', 'iShares Core TOPIX ETF', 'iShares JP 保有明細 · 四半期末', 1682, 0.0495, '¥')]
D = {}
for code, key, name, src, n, fee, cur in ETFS:
    c = json.load(open(S + f'rep_{key}_chart.json'))
    D[code] = dict(name=name, src=src, names=n, fee=fee, cur=cur, dates=c['dates'], etf=c['etf_level'], rep=c['rep'], diff=c['diff'], cum=c['cum'],
                   switches=c['switches'], stats=c['stats'], intervals=c['intervals'], worst=c['worst'])
M = {k: json.load(open(S + f'rep_{k}_chart.json'))['stats'] for k in ('1329_m', '1475_m')}
diag = json.load(open(S + 'diag_jp.json'))

def num(v, d=2, sign=False):
    s = f'{v:+.{d}f}' if sign else f'{v:.{d}f}'
    return s.replace('-', '−')

rows = ''
for code, key, name, src, n, fee, cur in ETFS:
    s = D[code]['stats']; jp = ' class="jp"' if cur == '¥' else ''
    rows += f"""      <tr><td{jp}><strong>{code}</strong> <span style="color:var(--ink-3);font-size:12px">{name}</span></td><td class="num{' jp' if jp else ''}">{n}</td><td class="num{' jp' if jp else ''}">{s['corr']:.4f}</td><td class="num{' jp' if jp else ''}">{s['std_bp']:.1f}</td><td class="num{' jp' if jp else ''}">{s['te']:.2f}%</td><td class="num{' jp' if jp else ''}">{s['over20']}</td><td class="num{' jp' if jp else ''}">{num(s['cum_end'], 2, True)}%</td><td class="num{' jp' if jp else ''}">{s['cum_max']:.2f}%</td><td class="num{' jp' if jp else ''}">{s['maxday'][5:]} {num(s['maxbp'] * (1 if D[code]['diff'][D[code]['dates'].index(s['maxday'])] > 0 else -1), 0, True)}bp</td></tr>\n"""

# per-quarter sigma table: columns = ETFs, rows = 5 intervals (US bounded by rebalance dates, JP by quarter-ends)
qlab = ['2025-07 → 09', '2025-09 → 12', '2025-12 → 2026-03', '2026-03 → 06', '2026-06 → 09']
qrows = ''
for i, lab in enumerate(qlab):
    cells = ''
    for code, *_ in ETFS:
        iv = D[code]['intervals'][i]
        cells += f'<td class="num">{iv["std"]:.1f} <span style="color:var(--ink-3)">/ {num(iv["cum"], 2, True)}</span></td>'
    qrows += f'      <tr><td>{lab}</td>{cells}</tr>\n'
cells = ''.join(f'<td class="num">{D[c]["stats"]["std_bp"]:.1f} <span style="color:var(--ink-3)">/ {num(D[c]["stats"]["cum_end"], 2, True)}</span></td>' for c, *_ in ETFS)
qrows += f'      <tr class="hl"><td>全期間</td>{cells}</tr>\n'

s_smh, s_qqq, s_xle, s_1329, s_1475 = (D[c]['stats'] for c in ('SMH', 'QQQ', 'XLE', '1329', '1475'))
body = f"""
<div class="wrap">
<header class="mast">
  <div class="eyebrow">
    <span>SMH · QQQ · XLE · 1329 · 1475</span><span>2025-07-01 → 2026-09-10</span><span>米国 301 / 日本 292 営業日</span><b>portfolio-analyzer</b>
  </div>
  <h1>ETF は中身から再現できるか<span class="sub">四半期に一度の保有開示を固定して、5 本の ETF の日次レベルを組み直す</span></h1>
  <p class="lede">米国 3 本（SMH・QQQ・XLE）は<strong>日次相関 {s_qqq['corr']:.4f}〜{s_smh['corr']:.4f}、年率トラッキングエラー {s_xle['te']:.2f}〜{s_smh['te']:.2f}%</strong>。日本 2 本（1329・1475）は TE {s_1475['te']:.2f}〜{s_1329['te']:.2f}% と 2 倍緩いが、バスケット自体は日経平均に σ {diag['1329']['idx_std_ex_divdays']}bp で一致しており、<strong>残差は ETF の終値そのものが持つノイズ</strong>。5 本とも 14.5 か月の累積乖離は ±1% に収まる。</p>
  <div class="strip">
    <div><span class="k">累積乖離が ±1% 以内</span><span class="v a">5<small style="font-size:19px">/5 本</small></span><span class="n">最大は SMH の {num(s_smh['cum_end'], 2, True)}%。うち −0.4pt は信託報酬</span></div>
    <div><span class="k">米国 3 本の TE</span><span class="v b">{s_xle['te']:.2f}<small style="font-size:19px">〜{s_smh['te']:.2f}%</small></span><span class="n">XLE が最良（22 銘柄・入れ替えなし）、SMH が最悪（半導体の分散度）</span></div>
    <div><span class="k">日本 2 本の TE</span><span class="v b">{s_1475['te']:.2f}<small style="font-size:19px">〜{s_1329['te']:.2f}%</small></span><span class="n">日次差の自己相関 −0.5 ＝ 翌日に戻る。月次の保有に替えても改善しない</span></div>
    <div><span class="k">20bp を超えた日</span><span class="v a">{s_xle['over20']}<small style="font-size:19px">〜{s_1329['over20']} 日</small></span><span class="n">XLE {s_xle['over20']} · QQQ {s_qqq['over20']} · SMH {s_smh['over20']} · 1475 {s_1475['over20']} · 1329 {s_1329['over20']}</span></div>
  </div>
</header>

<section>
  <div class="head"><span class="step">01</span><h2>5 本とも、四半期の開示だけで日次レベルが追える</h2></div>
  <div class="col">
    <p>作り方は 1 つ。四半期末の保有明細（米国は SEC <code>NPORT-P</code>、日本は iShares の保有銘柄 CSV）から各銘柄の時価を取り、<em>次の入れ替えまで株数を固定</em>して調整後終値で毎日評価する。ETF 側は市場の調整後終値。米国 3 本は指数リバランス日（3・6・9・12 月第 3 金曜の翌営業日）で構成を切り替え、日本 2 本は四半期末で切り替える（日経平均の定期見直しが 4 月・10 月初に効くため、3 月末・9 月末の明細がそのまま新構成になる）。</p>
    <p>時価 × 調整後終値の比で評価するので、分割はもう罠にならない。SMH のときに踏んだ「N-PORT の株数は申告時点の株数」問題は、株数を使わないことで消えた。</p>
  </div>

  <div class="tw"><table>
    <caption>2025-07-01 → 2026-09-10 · 日次収益率ベース。累積乖離 ＝ ETF ÷ 再現 − 1</caption>
    <thead><tr><th>ETF</th><th>銘柄数</th><th>日次相関</th><th>差の σ (bp)</th><th>TE /年</th><th>20bp 超</th><th>累積乖離</th><th>最大乖離</th><th>最悪の日</th></tr></thead>
    <tbody>
{rows}    </tbody>
  </table></div>

  <figure>
    <p class="figtitle">ETF の値動きと、バスケットから組んだ値動き</p>
    <p class="figsub">2025-06-30 ＝ 100。細い線が ETF の実際、太い線が再現バスケット。破線はバスケットを入れ替えた日</p>
    <div class="legend">
      <span><i style="background:var(--series-2)"></i>ETF 実際</span>
      <span><i style="background:var(--series-1)"></i>再現バスケット</span>
      <span><i class="sq" style="background:var(--ink-3);height:2px;width:14px;border-radius:1px"></i>入れ替え日</span>
    </div>
    <div class="grid" id="g-levels"></div>
    <figcaption><b>Fig 1</b>5 本とも 2 本の線は目視で分離しない。SMH の倍増、1329 の +66%、XLE の +57% を、四半期に一度の明細だけで追えている。差は次の図でしか見えない。</figcaption>
  </figure>

  <figure>
    <p class="figtitle">では、どこで離れていったのか</p>
    <p class="figsub">累積乖離（ETF ÷ 再現 − 1、%）。灰の破線は信託報酬をそのまま引いた場合。縦軸は 5 本共通</p>
    <div class="legend">
      <span><i style="background:var(--series-1)"></i>実際の累積乖離</span>
      <span><i class="sq" style="background:var(--ink-3);height:2px;width:14px;border-radius:1px"></i>信託報酬だけで説明される分</span>
    </div>
    <div class="grid" id="g-cum"></div>
    <figcaption><b>Fig 2</b>SMH と XLE は報酬の線に沿って沈む。QQQ だけが 2026 年 4 月から<strong>上に</strong>離れる ── 4 月 20 日に Sandisk が Atlassian と入れ替わり、四半期末の明細にはまだ無い銘柄を ETF が持っていた。日本 2 本は報酬が 0.05% と薄いぶん、ゼロの周りを ±0.5% で往復する。</figcaption>
  </figure>
</section>

<svg class="burst" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1"/></svg>

<section>
  <div class="head"><span class="step">02</span><h2>日次のずれは、米国と日本で性質が違う</h2></div>
  <figure>
    <p class="figtitle">日次の差（ETF − 再現）</p>
    <p class="figsub">ベーシスポイント。帯は ±20bp、縦軸は 5 本共通の ±60bp。縦の破線は入れ替え日</p>
    <div class="legend">
      <span><i class="sq" style="background:var(--series-2)"></i>±20bp 以内</span>
      <span><i class="sq" style="background:var(--series-1)"></i>±20bp 超</span>
    </div>
    <div class="grid" id="g-diff"></div>
    <figcaption><b>Fig 3</b>米国 3 本は大半が帯の中に収まり、外れる日はリバランス週に集まる（SMH 06-22 の −40bp、QQQ 06-26 の −28bp）。日本 2 本は帯を毎週のように超えるが、<strong>翌日に符号を変えて戻る</strong>のが特徴（1329 05-07 +55bp → 05-08 −51bp、1475 07-09 −54bp → 07-10 +50bp）。日次差の 1 階自己相関は 1329 −0.51、1475 −0.49。</figcaption>
  </figure>

  <div class="tw"><table>
    <caption>区間ごとの日次差 σ (bp) / 区間の累積乖離 (%)。米国はリバランス日、日本は四半期末で区切る</caption>
    <thead><tr><th>区間</th><th>SMH</th><th>QQQ</th><th>XLE</th><th class="jp">1329</th><th class="jp">1475</th></tr></thead>
    <tbody>
{qrows}    </tbody>
  </table></div>

  <h3>日本の残差はバスケットの誤差ではなく、ETF の終値のノイズ</h3>
  <div class="col">
    <p>同じ 1329 のバスケットを、ETF ではなく<strong>日経平均株価そのもの</strong>と比べると、日次差の σ は {diag['1329']['idx_std_ex_divdays']}bp（配当落ち日を除く）、最大 {diag['1329']['idx_max']}bp、20bp 超は {diag['1329']['idx_over20']} 日。バスケットは指数を事実上完全に再現している。一方、同じ日経平均に連動する野村の 1321 を同じバスケットと比べても σ {diag['1329']['alt_std']}bp で、1329 の {diag['1329']['own_std']}bp と同程度。つまり残差は<em>ETF の終値が NAV からずれる分</em>で、どの保有データを使っても消えない。</p>
    <p>裏付けとして、iShares Japan は <code>asOfDate</code> を付けると過去の任意日の保有明細を返すので、四半期末ではなく<strong>月末の明細</strong>に替えて同じ計算をした。TE は 1329 が {s_1329['te']:.2f}% → {M['1329_m']['te']:.2f}%、1475 が {s_1475['te']:.2f}% → {M['1475_m']['te']:.2f}% と、小数第 2 位まで動かない。</p>
  </div>

  <div class="modes">
    <div class="win">
      <p class="t">1329 · 四半期末の明細</p>
      <p class="s">6・9・12・3 月末の 5 枚</p>
      <dl><dt>日次相関</dt><dd>{s_1329['corr']:.5f}</dd><dt>日次差の σ</dt><dd>{s_1329['std_bp']:.1f}bp</dd><dt>トラッキングエラー</dt><dd>{s_1329['te']:.2f}%/年</dd><dt>累積乖離</dt><dd>{num(s_1329['cum_end'], 2, True)}%</dd></dl>
    </div>
    <div>
      <p class="t">1329 · 月末の明細</p>
      <p class="s">2025-06 〜 2026-08 の 15 枚</p>
      <dl><dt>日次相関</dt><dd>{M['1329_m']['corr']:.5f}</dd><dt>日次差の σ</dt><dd>{M['1329_m']['std_bp']:.1f}bp</dd><dt>トラッキングエラー</dt><dd>{M['1329_m']['te']:.2f}%/年</dd><dt>累積乖離</dt><dd>{num(M['1329_m']['cum_end'], 2, True)}%</dd></dl>
    </div>
    <div class="win">
      <p class="t">1475 · 四半期末の明細</p>
      <p class="s">約 1,680 銘柄 × 5 枚</p>
      <dl><dt>日次相関</dt><dd>{s_1475['corr']:.5f}</dd><dt>日次差の σ</dt><dd>{s_1475['std_bp']:.1f}bp</dd><dt>トラッキングエラー</dt><dd>{s_1475['te']:.2f}%/年</dd><dt>累積乖離</dt><dd>{num(s_1475['cum_end'], 2, True)}%</dd></dl>
    </div>
    <div>
      <p class="t">1475 · 月末の明細</p>
      <p class="s">約 1,680 銘柄 × 15 枚</p>
      <dl><dt>日次相関</dt><dd>{M['1475_m']['corr']:.5f}</dd><dt>日次差の σ</dt><dd>{M['1475_m']['std_bp']:.1f}bp</dd><dt>トラッキングエラー</dt><dd>{M['1475_m']['te']:.2f}%/年</dd><dt>累積乖離</dt><dd>{num(M['1475_m']['cum_end'], 2, True)}%</dd></dl>
    </div>
  </div>
</section>

<svg class="burst" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1"/></svg>

<section>
  <div class="head"><span class="step">03</span><h2>外れ方は銘柄ごとに違う</h2></div>
  <div class="cards">
    <div>
      <p class="t">SMH <small>rebalance week</small></p>
      <p>20bp を超えた {s_smh['over20']} 日のうち 4 日がリバランス実効日とその直後。最大は 2026-06-22 の −40bp で、MU +6.8%・INTC +5.2%・AVGO −4.5% が同時に動いた日に旧構成と新構成の差がそのまま出た。切り替えを四半期末に置くと TE は 1.14% → 1.32% に悪化する。</p>
    </div>
    <div>
      <p class="t">QQQ <small>mid-quarter change</small></p>
      <p>101 銘柄でも TE {s_qqq['te']:.2f}%。ただし 2026-03 → 06 の区間だけ ETF が再現を <strong>+0.67%</strong> 上回る。Nasdaq が 4 月 20 日に Sandisk を Atlassian と入れ替え、6 月末まで Sandisk の比率が 1.5% に膨らんだ。四半期末の明細では原理的に追えず、指数の入れ替え告知を読む以外に手がない。</p>
    </div>
    <div>
      <p class="t">XLE <small>purged tickers</small></p>
      <p>22 銘柄・入れ替えなしで TE {s_xle['te']:.2f}%、20bp 超は 0 日。落とし穴は買収消滅した Hess（2025-07-18、→ Chevron）と Coterra（2026-05-07、→ Devon）で、Yahoo からは株価履歴ごと消えている。買収側の総収益で代理すると累積 −0.37% → −0.61% と信託報酬側に寄る。</p>
    </div>
    <div>
      <p class="t">1329 · 1475 <small>etf price noise</small></p>
      <p>バスケットは指数に σ 1.8bp で一致するのに ETF との差は 14〜16bp。Yahoo の JP ETF は分配金の日付が 2 営業日遅く記録されており（08-09 と書かれた分配の落ち日は 08-07）、そのままでは −112bp / +108bp の対が 3 組出る。落ち日を探し当てて分配金を足し戻し、抜けている 2025-10-24 の終値をまたいで比べると、上の表の値になる。</p>
    </div>
  </div>

  <div class="note">
    <span class="lab">踏んだ罠</span>
    <p>SMH 単独のときは N-PORT の株数を分割で掛け直していた。今回は<strong>時価 × 調整後終値の比</strong>で評価する形に変え、株数を使わない。KLAC 10 分割・BKNG 25 分割・NFLX 10 分割・日本の 190 件超の分割が、すべて何もせずに通る。代わりに、上場廃止で Yahoo から履歴ごと消えた銘柄（HES・CTRA・9613 NTTデータ・1475 の小型 66 銘柄）は別扱いが要る。</p>
  </div>
</section>

<svg class="burst" viewBox="0 0 24 24" aria-hidden="true">
  <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9L4.9 19.1"/></svg>

<section>
  <div class="head"><span class="step">04</span><h2>ここから先は無料データでは届かない</h2></div>
  <ul>
    <li><strong>NAV ではなく市場価格と比べている。</strong>日本 2 本の残差はほぼこれ。iShares Japan は保有明細は日付指定で返すが、基準価額の履歴は CSV で出さない。米国側も VanEck・Invesco・SSGA とも日次 PCF と NAV の自動取得を塞いでいる。</li>
    <li><strong>四半期の間に起きる指数の入れ替えは追えない。</strong>QQQ の Sandisk が実例。告知は Nasdaq のプレスリリースにしか無く、機械的に拾うなら別の入力が要る。</li>
    <li><strong>上場廃止銘柄は Yahoo から履歴ごと消える。</strong>買収側の総収益で代理するか（HES→CVX、CTRA→DVN）、TOB で値が張り付いた銘柄は現金扱い（9613）。1475 の小型 66 銘柄は合計 1.3% 以下なので落として正規化した。</li>
    <li><strong>配当の扱いは yfinance の調整済み終値に委ねている。</strong>ETF 側の分配金の日付は自前で直したが、構成銘柄側の配当落ち日が 1 日ずれていれば 3 月末・9 月末の前後に数十 bp の対が残る（1329 の 09-29 −35bp、03-31 +47bp）。</li>
  </ul>
</section>

<footer>
  データ: /home/kazumasa/projects/portfolio-analyzer/docs/etf-pe-tieout/data/rep_&lt;etf&gt;_levels.csv · rep_&lt;etf&gt;_tieout.csv<br>
  スクリプト: /home/kazumasa/projects/portfolio-analyzer/docs/etf-pe-tieout/scripts/etf_daily2.py · snap_prep.py · diag_jp.py<br>
  保有: SEC NPORT-P (SMH CIK 1137360 / QQQ CIK 1067839 / XLE CIK 1064641) 2025-06-30 〜 2026-06-30 の 5 四半期 · iShares Japan 1329 / 1475 保有明細 (asOfDate 指定) 2025-06-30 〜 2026-08-31 の 15 月末<br>
  株価: yfinance 調整後終値 · 2025-07-01 〜 2026-09-10 · 米国 301 / 日本 292 営業日<br>
  作成 2026-09-12（初版 SMH のみ 2026-09-11）
</footer>
</div>

<div id="tip" role="status"></div>

<script id="data" type="application/json">{json.dumps(D, ensure_ascii=False, separators=(',', ':'))}</script>
"""

js = r"""<script>
const SVGNS="http://www.w3.org/2000/svg";
const CSSATTR=new Set(["fill","stroke","font-family"]);
const el=(t,a={})=>{const e=document.createElementNS(SVGNS,t);
  for(const k in a){const v=String(a[k]);
    if(CSSATTR.has(k)&&v.indexOf("var(")>=0)e.style.setProperty(k,v);else e.setAttribute(k,a[k]);}
  return e;};
const tip=document.getElementById("tip");
function bind(node,text){
  node.addEventListener("pointerenter",()=>{tip.textContent=text;tip.style.opacity=1;});
  node.addEventListener("pointermove",e=>{
    const w=tip.offsetWidth,h=tip.offsetHeight;
    let x=e.clientX+14,y=e.clientY-h-12;
    if(x+w>innerWidth-8)x=e.clientX-w-14;
    if(y<8)y=e.clientY+18;
    tip.style.left=x+"px";tip.style.top=y+"px";
  });
  node.addEventListener("pointerleave",()=>{tip.style.opacity=0;});
  node.classList.add("hit");
}
const ALL=JSON.parse(document.getElementById("data").textContent);
const ORDER=["SMH","QQQ","XLE","1329","1475"];
const jd=s=>{const[y,m,d]=s.split("-");return `${y}/${m}/${d}`;};
const bp=v=>(v>0?"+":"")+v.toFixed(1)+"bp";
const pc=(v,n=2)=>(v>0?"+":"")+v.toFixed(n)+"%";
const W=370,H=200;

function panel(container,code,sub){
  const cell=document.createElement("div");cell.className="cell";
  const lab=document.createElement("p");lab.className="lab";
  lab.innerHTML=`<b>${code}</b><span>${sub}</span>`;cell.appendChild(lab);
  const sc=document.createElement("div");sc.className="scroll";
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img"});sc.appendChild(svg);cell.appendChild(sc);
  container.appendChild(cell);return svg;
}
function ticksFor(D){const out=[];let seen="";
  D.dates.forEach((d,i)=>{const m=d.slice(0,7);if(m!==seen){seen=m;const mm=+m.slice(5);if((mm-1)%3===0)out.push([i,m]);}});
  return out;}
function frame(svg,D,M,yTicks,yFmt,ySc,xSc){
  const g=el("g");svg.appendChild(g);
  yTicks.forEach(v=>{const y=ySc(v);
    g.appendChild(el("line",{x1:M.l,x2:W-M.r,y1:y,y2:y,class:"gridline"}));
    const t=el("text",{x:M.l-6,y:y+3.5,"text-anchor":"end","font-size":9.5});t.textContent=yFmt(v);g.appendChild(t);});
  ticksFor(D).forEach(([i,m])=>{const t=el("text",{x:xSc(i),y:H-M.b+14,"text-anchor":"middle","font-size":9.5});
    t.textContent=m.slice(2).replace("-","/");g.appendChild(t);});
  return g;
}
function switches(g,D,M,xSc){
  D.switches.forEach(s=>{const i=D.dates.indexOf(s);if(i<0)return;
    g.appendChild(el("line",{x1:xSc(i),x2:xSc(i),y1:M.t,y2:H-M.b,class:"sw"}));});
}
function hover(g,D,M,xSc,fn){
  const N=D.dates.length,w=(W-M.l-M.r)/(N-1);
  for(let i=0;i<N;i++){const r=el("rect",{x:xSc(i)-w/2,y:M.t,width:Math.max(w,1.4),height:H-M.t-M.b,fill:"transparent"});bind(r,fn(i));g.appendChild(r);}
}
const path=(arr,xSc,ySc)=>arr.map((v,i)=>(i?"L":"M")+xSc(i).toFixed(1)+" "+ySc(v).toFixed(1)).join(" ");
const niceTicks=(lo,hi,step)=>{const out=[];for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step)out.push(v);return out;};

/* ---- Fig 1: levels, rebased to 100 ---- */
(function(){
  const box=document.getElementById("g-levels");
  ORDER.forEach(code=>{const D=ALL[code],N=D.dates.length,M={l:36,r:10,t:12,b:22};
    const e=D.etf.map(v=>100*v/D.etf[0]),r=D.rep.map(v=>100*v/D.rep[0]);
    const lo=Math.min(...e,...r),hi=Math.max(...e,...r),pad=(hi-lo)*.06;
    const ylo=lo-pad,yhi=hi+pad,step=(hi-lo)>90?50:25;
    const xSc=i=>M.l+i*(W-M.l-M.r)/(N-1),ySc=v=>H-M.b-(v-ylo)/(yhi-ylo)*(H-M.t-M.b);
    const svg=panel(box,code,`${D.name} · ETF ${pc(D.stats.etf_tr,1)} / 再現 ${pc(D.stats.rep_tr,1)}`);
    svg.setAttribute("aria-label",`${code} の実際の値動きと再現バスケットの折れ線。2 本はほぼ重なる`);
    const g=frame(svg,D,M,niceTicks(ylo,yhi,step),v=>v,ySc,xSc);switches(g,D,M,xSc);
    g.appendChild(el("path",{d:path(r,xSc,ySc),fill:"none",stroke:"var(--series-1)","stroke-width":3,"stroke-linejoin":"round",opacity:.85}));
    g.appendChild(el("path",{d:path(e,xSc,ySc),fill:"none",stroke:"var(--series-2)","stroke-width":1.3,"stroke-linejoin":"round"}));
    const last=N-1;g.appendChild(el("circle",{cx:xSc(last),cy:ySc(e[last]),r:2.6,fill:"var(--series-2)"}));
    hover(g,D,M,xSc,i=>`${jd(D.dates[i])}\n${code} 実際   ${D.cur}${D.etf[i].toLocaleString()}\n再現バスケット ${D.cur}${D.rep[i].toLocaleString()}\n乖離 ${pc(D.cum[i])}`);
  });
})();

/* ---- Fig 2: cumulative gap, common axis ---- */
(function(){
  const box=document.getElementById("g-cum"),ylo=-1.25,yhi=1.0;
  ORDER.forEach(code=>{const D=ALL[code],N=D.dates.length,M={l:40,r:10,t:12,b:22};
    const xSc=i=>M.l+i*(W-M.l-M.r)/(N-1),ySc=v=>H-M.b-(v-ylo)/(yhi-ylo)*(H-M.t-M.b);
    const svg=panel(box,code,`累積 ${pc(D.stats.cum_end)} · 報酬 ${D.fee}%/年`);
    svg.setAttribute("aria-label",`${code} の ETF と再現バスケットの累積乖離。最終 ${pc(D.stats.cum_end)}`);
    const g=frame(svg,D,M,[1,.5,0,-.5,-1],v=>pc(v,1),ySc,xSc);switches(g,D,M,xSc);
    g.appendChild(el("line",{x1:M.l,x2:W-M.r,y1:ySc(0),y2:ySc(0),class:"zero"}));
    const fee=i=>-D.fee*(i+1)/252;
    g.appendChild(el("path",{d:D.cum.map((_,i)=>(i?"L":"M")+xSc(i).toFixed(1)+" "+ySc(fee(i)).toFixed(1)).join(" "),fill:"none",stroke:"var(--ink-3)","stroke-width":1.2,"stroke-dasharray":"4 4"}));
    g.appendChild(el("path",{d:path(D.cum,xSc,ySc),fill:"none",stroke:"var(--series-1)","stroke-width":1.8,"stroke-linejoin":"round"}));
    const last=N-1;g.appendChild(el("circle",{cx:xSc(last),cy:ySc(D.cum[last]),r:2.6,fill:"var(--series-1)"}));
    if(Math.abs(D.cum[last])>0.3){const lt=el("text",{x:xSc(last)-5,y:ySc(D.cum[last])+(D.cum[last]<0?14:-7),"text-anchor":"end","font-size":10,fill:"var(--accent)"});lt.textContent=pc(D.cum[last]);g.appendChild(lt);}
    hover(g,D,M,xSc,i=>`${jd(D.dates[i])}\n累積乖離 ${pc(D.cum[i])}\n報酬のみ ${pc(fee(i))}`);
  });
})();

/* ---- Fig 3: daily difference, common axis ---- */
(function(){
  const box=document.getElementById("g-diff"),ylo=-60,yhi=60;
  ORDER.forEach(code=>{const D=ALL[code],N=D.dates.length,M={l:40,r:10,t:12,b:22};
    const xSc=i=>M.l+i*(W-M.l-M.r)/(N-1),ySc=v=>H-M.b-(v-ylo)/(yhi-ylo)*(H-M.t-M.b);
    const svg=panel(box,code,`σ ${D.stats.std_bp.toFixed(1)}bp · 20bp 超 ${D.stats.over20} 日`);
    svg.setAttribute("aria-label",`${code} の日次差の棒グラフ`);
    const g=frame(svg,D,M,[40,20,0,-20,-40],v=>v+"bp",ySc,xSc);
    g.appendChild(el("rect",{x:M.l,y:ySc(20),width:W-M.l-M.r,height:ySc(-20)-ySc(20),class:"band"}));
    switches(g,D,M,xSc);
    g.appendChild(el("line",{x1:M.l,x2:W-M.r,y1:ySc(0),y2:ySc(0),class:"zero"}));
    const bw=Math.max((W-M.l-M.r)/(N-1)*0.7,1);
    D.diff.forEach((v,i)=>{const big=Math.abs(v)>20,y0=ySc(0),y1=ySc(Math.max(-60,Math.min(60,v)));
      g.appendChild(el("rect",{x:xSc(i)-bw/2,y:Math.min(y0,y1),width:bw,height:Math.max(Math.abs(y1-y0),.6),fill:big?"var(--series-1)":"var(--series-2)",opacity:big?1:.6}));});
    const wi=D.dates.indexOf(D.stats.maxday);
    if(wi>=0){const v=D.diff[wi];const yy=Math.max(M.t+9,Math.min(H-M.b-3,ySc(v)+(v>0?-4:11)));const t=el("text",{x:xSc(wi)+(wi>N*0.8?-6:6),y:yy,"text-anchor":wi>N*0.8?"end":"start","font-size":9.5,fill:"var(--accent)"});t.textContent=bp(v)+" "+D.stats.maxday.slice(5);g.appendChild(t);}
    hover(g,D,M,xSc,i=>`${jd(D.dates[i])}\nETF ${pc(100*(D.etf[i]/D.etf[Math.max(i-1,0)]-1))}  再現 ${pc(100*(D.rep[i]/D.rep[Math.max(i-1,0)]-1))}\n差 ${bp(D.diff[i])}`);
  });
})();
</script>
"""
html = head + css + body + js
open(S + 'smh_report.html', 'w').write(html)
print('written', len(html), 'bytes')
