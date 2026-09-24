# §26.16 M8 レビュー（2026-09-25）

状態は **pending_validation**。VS01–VS06 の独立参照・公開 API・教材 6 小節・共有 4 図・
Book/portal の実画面確認まで揃えたが、これまでの節で毎回行ってきた**独立レビューは未実施**である。
独立レビューか利用者の明示的な免除（§26.13 の先例）があるまで accepted にしない。
原典は Hull 11e Global Edition §26.16、印刷・PDF pp.629–632（p.632 で §26.17 が始まる）を照合した。
§26.14–§26.15 と違い、この節には Example 26.4 と 26.5 が印刷されているので原典の数値アンカーがある。
設計は [2026-09-25-section-26-16-variance-swaps-design.md](superpowers/specs/2026-09-25-section-26-16-variance-swaps-design.md)。

## 着手時の状態

ledger は unreviewed。vol10 には平坦スマイルのストリップ複製を示す説明なしのコードセルが 1 つあり、
`hullkit.variance_swaps` は式 26.6–26.10 と Example 26.4/26.5 のピンを既に持っていた。
既存コードは受入の根拠にならないので、独立参照を別に作り、そこから教材と図を組み立てた。

## 要求契約

| ID | 満たすべき契約 | 根拠 |
|---|---|---|
| VS01 | 実現ボラ（$n-2$／$n-1$）、2 つの給付、$\bar V=\bar\sigma^2$、$L_{\rm var}=L_{\rm vol}/(2\sigma_K)$、分散スワップは実現ボラについて凸でボラスワップは線形 | `realized_variance` / `realized_volatility` / `variance_notional`、GBM 日次推定量の厳密期待値と MC、給付図 |
| VS02 | 式 26.6 を積分として示し、対数契約が現れる理由と $S^*$ 非依存を説明、平坦スマイル以外でも検証 | 平坦 BSM を 5 つの $S^*$ で、Heston 3 市場を閉形式 $E(V)$ と比較 |
| VS03 | 式 26.8、$\Delta K_i$、$S^*$、$Q(K_i)$、Example 26.4 の印刷値、連続積分に対する格子・打切り誤差 | 印刷 $Q$ 9 本（2 桁）、0.008139、0.0621、1.69、3 範囲 × 4 刻みの誤差 |
| VS04 | 式 26.9、Example 26.5 の 0.2484 と 1.82、厳密 $E(\sqrt V)$ と MC に対する近似誤差、$E(\sigma)<\sqrt{E(V)}$ | CIR ラプラス変換の厳密値、厳密 CIR 遷移 MC、ξ 10 点 |
| VS05 | VIX：$\ln(F_0/S^*)$ の 2 項打切り（式 26.10）とその大きさ、30 日補間と年率化（CBOE 規則全体ではない） | Example 26.4 で打切り差、23/37 日から 30 日への補間誤差、`vix_index` |
| VS06 | vol10 §4.6 の 6 小節と共有 4 図を Book/portal 両面に置き、領域と限界を明示 | notebook 検査、ブラウザー検査（両面 × 2 幅 × 全メニュー状態） |

単位：価格・行使価格は通貨、$T$ は年、$r,q$ は連続複利年率、ボラは年率小数、分散は年率、
$E(V)T$ は無次元の累積分散、想定元本はボラ 1 単位／分散 1 単位あたりの通貨。

## 独立参照（M8a）

[build_variance_swap_reference.py](../scripts/build_variance_swap_reference.py) は NumPy/SciPy だけを import し、hullkit を使わない。

- Example 26.4/26.5 を自前の BSM で再計算（印刷値の丸めは 2 桁の $Q$ と表示桁で照合）。
- 式 26.6 を $x=\ln(K/F)$ の有限区間で `quad` 積分。平坦 BSM は $\sigma^2$、Heston は
  $\theta+(v_0-\theta)(1-e^{-\kappa T})/(\kappa T)$ が答え。Heston 価格は trap-stable な特性関数の
  Lewis 一重積分。深い OTM では約 $10^{-11}$ の相殺ノイズが出る（`strip_min_q` = −2.06e-11）が、
  $1/K^2$ の重みの後の $E(V)$ への影響は $10^{-15}$ 未満。
- $\operatorname{var}(\bar V)=\xi^2\int_0^T b(s)^2E[v_s]ds/T^2$（伊藤等長）、
  $E(\sqrt{\bar V})$ は CIR ラプラス変換の積分。相殺を避けるため $\delta=2\xi^2s/(\gamma+\kappa)$ と
  log1p/expm1 で書き、$t<10^{-2}$ はテイラー展開。
- MC は非心カイ二乗による厳密 CIR 遷移、250 ステップの台形、100,000 パス、seed 20260925。

`--check` で [reference.json](validation/section-26-16/reference.json) と
[numerical-check.json](validation/section-26-16/numerical-check.json) を byte 単位で再生成する（日時なし）。

## 実測値

| 対象 | 値 |
|---|---|
| Example 26.4 | strip 0.00813874、$E(V)$ 0.06210083、価値 1.69307（印刷 0.008139／0.0621／1.69） |
| Example 26.5 | $E(\sigma)$ 0.24839097、価値 1.82080（印刷 0.2484／1.82） |
| 平坦 BSM の式 26.6、$S^*/F_0=0.8$–1.25 | 最大差 8.3e-17 |
| Heston 3 市場の式 26.6 | 閉形式との最大差 1.51e-12（求積誤差推定の最大 8.4e-13） |
| ストリップ誤差、wide（10–400） | $\Delta K=10\to1.25$ で 3.39e-3 → 5.31e-5（刻み半分で約 1/4） |
| ストリップ誤差、narrow（70–140） | 3.10e-3 → −5.93e-4（打切りで符号が反転し、刻みを細かくしても 0 に行かない） |
| 式 26.9、ξ=0.3 / 1.0 | 近似誤差 −1.9e-5 / −4.6e-3、素朴な $\sqrt{E(V)}$ は +2.6e-3 / +2.5e-2 |
| MC（ξ=0.3/0.6/0.9） | $E(\sqrt V)$ の最大 1.08 SE |
| 日次推定量（GBM、n=64、σ=25%） | $n-2$ の期待値 0.063509（$\sigma^2$ に対し +0.00101）、$n-1$ は +5.0e-7 |
| VIX 打切り（Example 26.4） | 累積分散の差 1.385e-5（3 次の主要項 1.414e-5） |
| 30 日補間（23/37 日） | ボラの誤差 −3.24e-4 |

誤差は選んだ合成市場と格子での実測で、全域の上界ではない。

## 実装と教材（M8b）

- 公開 API：`realized_variance`、`realized_volatility`、`variance_notional`、`vix_index` を
  `hullkit.variance_swaps` に追加（`exotics.py` は触らず、既受入節の lesson hash を保つ）。既存関数の契約は不変。
- 図：`hullkit._variance_swap_lesson` の `varswap_payoff`、`varswap_strip`、`varswap_replication`、
  `volswap_convexity`。保存 JSON（source hash 付き）だけを読み、図の生成で求積も MC もしない。
- vol10 §4.6：4.6.1 実現ボラと 2 契約、4.6.2 静的複製、4.6.3 離散ストリップと Example 26.4、
  4.6.4 ボラスワップと Example 26.5、4.6.5 VIX、4.6.6 適用範囲と理解の確認。
  既存の分散スワップのコードセルはそのまま残した（後の assertion セルが変数を読む）。
- portal：`figures.py` に 4 図を登録（exotics 30 図、全 110 図）、`style.css` に全幅指定。

## 検証

- notebook：115 セル、§4.6 の外の 101 セルは基準コミット f6a2b62e と一致。
  保存された 4 図は `_figures()` と data・layout ともに一致。既受入 6 節の 24 図も基準と一致。
- ブラウザー：Chromium 145、Book/portal × 1440/1000 px × 4 図 × 2 状態 = 32 状態を独立参照
  （[build_variance_swap_browser_reference.py](../scripts/build_variance_swap_browser_reference.py)、hullkit 非 import）と照合。
  ξ=0.6 の式 26.9 の値を +0.5 %pt 改変すると両面で拒否され、元に戻る。Book の MathJax 105 式、エラー 0。
- 既受入 7 節（§26.9–§26.15）：共有の notebook・builder・portal・stylesheet が変わったので、
  各節のテストとブラウザー検査を最終ビルドで再実行し `m8-recheck.json` と `browser-m8-recheck.json` に記録（全 PASS）。
  保存 lesson data を持つ 4 節（§26.12–§26.15）はそれが基準コミットと byte 単位で一致。過去の記録は書き換えていない。

## 限界と対象外

- 複製は連続パス・連続観測の拡散を仮定する（TN22 の導出）。Hull の契約は日次の離散観測。
- ジャンプ、GBM の実測 1 ケースを超える離散観測補正、現金配当、CBOE VIX の完全な手順
  （上場行使価格の選択、分単位の補間、フォワードの決め方）は対象外。
- Example 26.4/26.5 以外の市場はすべて合成。
- 独立レビューは未実施。
