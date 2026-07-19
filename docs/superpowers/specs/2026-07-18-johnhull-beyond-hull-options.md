# johnhull「Hull の先」拡張 — 提案ノート（レビュー・設計反映版）

- 日付: 2026-07-18
- ステータス: **vol 18–25 実装済み・G8 release 完了** — 本文は設計判断の記録として保存し、
  現在の実装状況は本節と Stage Gate 節に反映する。
  正式設計は `2026-07-18-johnhull-beyond-hull-a5-design.md`、実装計画は
  `../plans/2026-07-18-johnhull-beyond-hull-a5.md` を参照する。
- 対象プロジェクト: `/home/kazumasa/projects/johnhull`
- 計画時の到達点: Hull 11e 全 37 章（vol 1–12 + legacy）+ 院レベル深掘り A1–A4（vol 13–17）。
  当時は hullkit 184 tests（report 込み 187 tests collected）、portal 7 themes /
  38 figures、Jupyter Book 20 pages。
- 現行 release candidate: `release_manifest.json` に vol 18–25、portal **11 themes /
  70 figures**、Jupyter Book **28 pages** を登録。全 8 巻に fingerprinted JSON/NPZ、
  artifact-only notebook、巻別 validation report がある。
- Release state: fresh 検証と strict tracked gate は PASS。専用 branch
  `codex/johnhull-beyond-hull-g8` を公開する。巻別 gate の PASS は
  integration/reproducibility のみで、model performance 承認ではない。
- 本文中の 2025–2026 年研究には未査読 preprint を含む。教材の中核と研究トラックを区別する。

---

## 1. 結論と設計原則

Hull 11e の射程を超えた **最近のモデル / 最近のトピック** を、既存 A1–A4 と同じ
「深掘り + オフライン可視化 + Jupyter Book」型で教材化する。第 1 弾 A5 は **3 巻構成を維持**するが、
各巻を独立した stage gate とし、vol 18 の検証完了後に vol 19、vol 20 へ進む。

### ユーザーの関心方向

4 方向すべてに関心あり。特に **NN / Transformer / パターン認識** を強調。

1. ML × デリバティブ ← **第 1 弾に確定**
2. ボラティリティ最前線
3. ポスト LIBOR 金利
4. 新市場への応用

### レビュー反映後の設計原則

1. **単純な基準器を先に置く。** 解析解、既存数値法、線形・計量モデルを通過してから深層モデルへ進む。
2. **実装の正本を一つにする。** 学習・checkpoint・評価基盤は `deep_hedge_price`、金融教師と
   hard validation は `hullkit`、johnhull は教材・可視化・統合に責務を分ける。
3. **hullkit の基底依存に PyTorch を追加しない。** A5 または連携パッケージだけで optional に使い、
   `import hullkit` と既存テストは torch なしでも成立させる。
4. **CPU quick profile を必須、RTX 5080 は任意 benchmark とする。**
5. **「無裁定」「説明可能」「高精度」を検査なしで名乗らない。** hard check と反証可能な指標を先に定義する。
6. **合成データの結論を市場予測へ外挿しない。** 実データを使わない巻は「手法の回復実験」と明記する。

### 「自己完結」の定義

- デフォルトの book/report はネットワークアクセス不要、CPU で再現可能。
- root uv workspace 内の既存パッケージとの明示的な連携は許すが、暗黙の相互 import は作らない。
- 大容量 checkpoint やライセンス不明の市場データは johnhull に複製しない。
- book の既定ビルドは小型の決定論的 reference artifact を使い、live training は別ターゲットに分ける。

---

## 2. 全体ロードマップ（改訂 A5–A8）

| ウェーブ | テーマ | 中核 | 状態 |
|---|---|---|---|
| **A5** | ML × デリバティブ | pricing → calibration → dynamics → hedge | 実装済み（G1–G3 integration PASS） |
| A6 | ボラティリティ最前線 | AFV / PDV / Gaussian polynomial / signature の共通比較、0DTE は別章 | 実装済み（G4 integration PASS） |
| A7 | ポスト LIBOR 金利 | backward-looking RFR の payoff・convexity・multi-curve → smile model | 実装済み（G5 integration PASS） |
| A8a | クリプト市場構造 | perpetual funding、inverse/quanto、liquidation、oracle、AMM/LVR | 実装済み（G6 integration PASS） |
| A8b | 気候・エネルギー | carbon SV+jump、weather の不完備市場・basis risk | 実装済み（G7 integration PASS） |

### A6 の絞り込み

- **共通問題:** SPX・VIX・VIX futures の同時較正と、価格・Greeks・計算時間の比較。
- **主要候補:** Affine Forward Variance / rough Heston、4-factor PDV、quintic OU・Gaussian polynomial、
  signature volatility。
- **0DTE:** 日次ボラの延長ではなく、時刻依存 jump intensity・PIDE・超短期 Greeks を扱う独立章にする。
- すべてを実装せず、正式設計で「主モデル 1 つ + 比較基準 2 つ」を選ぶ。

### A7 の絞り込み

1. compounded-in-arrears、lookback / lockout / observation shift、先決め・後決めを実装する。
2. SOFR/TONA の曲線・futures/forward convexity・RFR multi-curve を扱う。
3. Bachelier、shifted / free-boundary SABR、Bartlett delta、arbitrage diagnostics を smile 層として載せる。
4. SIMM/MVA は金利モデル本体から外し、既存 `xva` との接続章または別ウェーブにする。

### A8 の分割理由

クリプトの funding / liquidation / AMM microstructure と、carbon/weather の非取引可能リスクは、
データ・無裁定条件・ヘッジ可能性が異なる。同じ volume に押し込まず A8a/A8b に分ける。

---

## 3. 実装責務とプロジェクト境界

| 関心事 | 正本 | johnhull の役割 |
|---|---|---|
| BS/Heston/SABR/COS/AAD、金融制約 | `hullkit` | 教師データ・理論・hard check の呼び出し |
| PyTorch 学習、checkpoint、seed、評価 pipeline | `deep_hedge_price` | notebook と比較表から利用 |
| rBergomi/fBM/Hawkes の重い実験 | `rough_volatility` | 小型 artifact の参照、再実装しない |
| RL 執行 | `optimal_execution` | A5 本体から除外し、関連教材へのリンクのみ |
| A5 の説明、図、演習、capstone | `johnhull` | 全体ストーリーと adapter |

`deep_hedge_price/docs/ROADMAP_DEEP_PRICING.md` に既に定義された price/Greeks、Differential ML、
無裁定検査、較正、速度計測を vol 18 で再実装しない。正式設計では、同 roadmap を A5 の計算エンジン仕様として
統合するか、責務を移管して旧 roadmap を閉じるかを決定する。並行する二つの正本は作らない。

### artifact/API 契約

- 中立形式は JSON + NPZ/CSV とし、`schema_version` を持たせる。
- model parameters、sampling design、seed、teacher method、standard error/CI、git SHA、package version を記録する。
- train/validation/test の fingerprint と重複検査結果を保存する。
- checkpoint は正本側に置き、johnhull には小型 metrics/figure fixture だけを置く。
- adapter は schema を検証し、不一致や不足項目を黙って補完しない。

---

## 4. A5 共通データ・評価方針

### データの 3 層

1. **Synthetic Core:** BS/Heston/SABR と必要に応じ rBergomi。CI と book の既定データ。
2. **Redistributable Snapshot:** 出所・ライセンス・quote cleaning を明示できる小型市場データ。
   選定できるまで正式な必須条件にしない。
3. **User-supplied Adapter:** 利用者が所有する option/volatility data。CI と配布物から除外する。

市場データを使わない実験は、model recovery / numerical approximation の結果として報告し、
市場での収益性・予測力を主張しない。

### 分割と leakage 防止

- pricing/calibration: parameter grid を train/validation/test で完全分離し、境界外の OOD shell を別に作る。
- time series: random split を禁止し、purged expanding/rolling walk-forward を使う。
- 複数 horizon の重複ラベル、標準化統計、PCA/autoencoder fit に未来情報を混ぜない。
- 同じ Monte Carlo path を教師と評価へ流用しない。比較手法間では common random numbers を使う。

### 共通パイプライン

```text
teacher pricer / market snapshot
    → price・Greeks・uncertainty artifact
    → surrogate
    → calibration / surface representation
    → surface dynamics forecast
    → hedge decision and economic evaluation
```

### 共通評価

- 価格: MAE/RMSE、relative error、moneyness × maturity bucket、teacher CI との整合。
- Greeks: delta/gamma/vega 等の誤差、price head の autodiff と direct head の consistency。
- 無裁定: bounds、put-call parity、strike monotonicity/convexity、calendar monotonicityの違反率と最大量。
- 較正: parameter recovery、repricing error、複数初期値の分散、非識別性。
- 時系列: QLIKE、RMSE/MAE、regime/horizon 別、block bootstrap または時系列対応 CI。
- 経済評価: transaction cost 込み P&L、hedging error、VaR/CVaR、turnover。
- 性能: warm-up と device synchronization を含む latency/throughput、break-even batch size。
- 再現性: 3 seed 以上、設定・fingerprint・実行環境を保存する。

---

## 5. 第 1 弾 A5 — 改訂 3 巻案

### vol 18「Theory-Guided Surrogates & Greeks」

**問い:** 微分・金融構造・既存モデルを与えると、少ないデータで価格とリスクをどこまで再現できるか。

**中核:**

1. dimensionless BS と解析解を基準器にする。
2. polynomial/spline または小型 MLP の price-only baseline を作る。
3. Heston/COS・Monte Carlo labels と uncertainty を扱う。
4. `hullkit.aad` を使う Differential ML と price/Greeks multi-task を比較する。
5. 絶対価格だけでなく、解析・漸近モデルに対する residual correction を比較する。
6. Differential PCA を高次元 risk factor / basket の発展課題にする。

**研究トラック:**

- Deep BSDE は 20–100 次元など mesh 法が困難な basket に限定する。
- PINN for BS は有限差分法との優劣と payoff kink 周辺の失敗分析を主眼にする。
- parametric PDE family には DeepONet/FNO 等の neural operator を比較候補にする。

**最低 acceptance:**

- BS in-domain price MAE < `1e-3 * K`、delta MAE < `2e-3`。
- test grid 重複ゼロ、OOD shell を必ず報告。
- price-only より複雑な手法が価格または Greeks の少なくとも一方を改善する。
- hard arbitrage check の違反率・最大量を公開する。
- CPU quick profile で dataset → training → report が完走する。
- 改善しない場合も negative result として完了可能にする。

### vol 19「Inverse Problems & Arbitrage-Aware Surfaces」

**問い:** 高速 surrogate を使いながら、識別性と無裁定性を失わずにモデル・曲面を較正できるか。

**中核:**

1. Heston/SABR/rBergomi の **forward pricing map**（parameters → price/IV）を学習する。
2. forward surrogate の上で既存 optimizer を使う two-step calibration を主方式にする。
3. direct inverse map は ablation とし、複数解・初期値依存・posterior uncertainty を可視化する。
4. SSVI または call-price の単調・凸 parameterization を無裁定 baseline にする。
5. unconstrained VAE、soft-penalty VAE、SDE/SSVI parameter decoder の hard-constrained 方式を比較する。
6. conditional normalizing flow / simulation-based inference は posterior の研究トラックに置く。
7. `rough_volatility` の full 100k paths を直接複製せず、小型 artifact または optional live adapter で接続する。

**最低 acceptance:**

- synthetic parameter recovery と market-like noisy quote の repricing error を分けて報告。
- model parameter error だけで成功判定せず、非識別な組合せを明示する。
- 「arbitrage-free」は全 hard check が文書化した tolerance 内で通った方式だけに使う。
- unconstrained / constrained の fit error と violation の trade-off を同じ表で示す。
- batch latency、較正時間、teacher pricer との break-even を CPU/GPU 別に測る。

### vol 20「Surface Dynamics, Forecasting & Hedging Decisions」

**問い:** 過去系列や IV 曲面の情報が将来ボラ予測と下流のヘッジ判断を改善するか。

**予測対象を分離する:**

1. `log(RV)` の 1/5/21 日 horizon。
2. IV 曲面の PCA または autoencoder latent factors。
3. 当日 IV 曲面から将来 realized volatility。

**モデル順序:**

1. naive persistence、EWMA/GARCH、Log-HAR、regularized linear。
2. HARNet/TCN。
3. 小型 LSTM。
4. 小型 encoder-only Transformer（PatchTST/iTransformer 型を候補）。
5. foundation model は zero-shot 研究トラックに限定する。

**説明と capstone:**

- attention map は「説明」ではなく diagnostic と明記する。
- permutation、occlusion、Integrated Gradients と方向・安定性を照合する。
- capstone は surrogate → calibration → forecast → hedge を同じ scenario で接続する。
- `deep_hedge_price` の方策とは common test paths、同じ premium、同じ costs で比較する。
- RMSE だけでなく hedging error、P&L/CVaR、turnover の改善を最終指標にする。

**最低 acceptance:**

- purged walk-forward と horizon overlap 検査。
- Log-HAR を全ての深層モデルの必須 baseline にする。
- QLIKE と経済指標を horizon/regime 別に報告する。
- attention だけから因果・パターン理解を主張しない。
- 複雑モデルが勝たなくても、統計的・経済的な差を記録して完了可能にする。

---

## 6. Stage Gate

| Gate | 完了条件 | 現在の根拠 / 状態 |
|---|---|---|
| G0: 正式設計 | owner、dependency、artifact schema、data policy を確定 | owner 分離、versioned JSON+NPZ、torch-free `hullkit` を実装済み |
| G1: vol 18 | baseline/DML/OOD/no-arb/CPU report | 巻別 validation の integration gate PASS；performance 承認は NO |
| G2: vol 19 | two-step calibration、識別性、制約付き曲面 | 巻別 validation の integration gate PASS；performance 承認は NO |
| G3: vol 20 | leakage-safe forecast、下流 hedge 比較 | 巻別 validation の integration gate PASS；Phase 1 実 checkpoint は未評価 |
| G4: vol 21–22 | joint SPX/VIX、0DTE clock/event/expiry | 両巻の integration gate PASS；performance 承認は NO |
| G5: vol 23 | RFR convention/curve/smile/hedge | 巻別 validation の integration gate PASS；performance 承認は NO |
| G6: vol 24 | perpetual/liquidation/AMM identities | 巻別 validation の integration gate PASS；synthetic cascade |
| G7: vol 25 | carbon/weather/PPA と basis risk | 巻別 validation の integration gate PASS；incomplete-market assumptions を明記 |
| G8: release | fresh tests/lint/artifact/notebook/report/book/full-workspace 検証 | **PASS**；tracked release と専用 branch への push を完了 |

各 gate で 3 回修復しても acceptance を満たさない場合は、問題・試行・縮小案を記録して停止する。
vol 19/20 を同時実装せず、vol 18 の artifact 契約を実証してから進む。

---

## 7. 選択肢と推奨

### 案 A：3 巻 stage-gated（推奨）

- vol 18 → 19 → 20 を順番に承認・実装する。
- 要望を最も満たし、失敗時にも巻単位で止められる。
- 工数は最大だが、評価基盤を各巻で再利用できる。

### 案 B：vol 18 のみ

- surrogate + Differential ML + OOD/no-arb benchmark に集中する。
- 最短で完成するが、Transformer・生成モデルの要望は満たさない。

### 案 C：vol 18–19 研究型

- forecasting を外し、rBergomi / joint calibration / posterior uncertainty を深掘りする。
- 数理ファイナンスとしては強いが、系列パターン認識の要望から外れる。

**推奨は案 A。ただし一括着工ではなく G0–G3 の順次承認とする。**

---

## 8. 研究候補と成熟度

### 教材の中核候補

- Huge & Savine, [Differential Machine Learning](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3591734)
- Horvath et al., [Deep Learning Volatility](https://arxiv.org/abs/1901.09647)
- Bayer et al., [On deep calibration of (rough) stochastic volatility models](https://arxiv.org/abs/1908.08806)
- Han, Jentzen & E, [Deep BSDE / high-dimensional PDE](https://arxiv.org/abs/1706.04702)
- Gatheral & Jacquier, [Arbitrage-free SVI volatility surfaces](https://arxiv.org/abs/1204.0646)
- Ning et al., [Arbitrage-Free IV Surface Generation with VAE](https://arxiv.org/abs/2108.04941)
- Jain & Wallace, [Attention is not Explanation](https://aclanthology.org/N19-1357/)
- Guyon & Lekeufack, [Volatility Is (Mostly) Path-Dependent](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4174589)
- Abi Jaber et al., [Quintic OU joint SPX/VIX calibration](https://arxiv.org/abs/2212.10917)
- Lyashenko & Mercurio, [Backward-looking RFR framework](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3330240)
- Milionis et al., [Automated Market Making and LVR](https://arxiv.org/abs/2208.06046)

### 研究トラック候補（主に 2025–2026 preprint）

- Savine & Huge, [Axes that Matter: PCA with a Difference](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5171819)
- Cuchiero et al., [Signature-based SPX/VIX calibration](https://arxiv.org/abs/2301.13235)
- Alòs et al., [Volatility Modeling with Rough Paths](https://arxiv.org/abs/2507.23392)
- François et al., [Deep Hedging with the Implied Volatility Surface](https://arxiv.org/abs/2504.06208)
- Sakuma, [Differential ML for 0DTE with SV and jumps](https://arxiv.org/abs/2603.07600)
- Brini, [Time Series Foundation Models vs Econometric Volatility Benchmarks](https://arxiv.org/abs/2607.05291)
- Che et al., [SPX-VIX Risk via Perturbed Optimal Transport](https://arxiv.org/abs/2603.10857)
- Kim & Park, [Designing Funding Rates for Perpetual Futures](https://arxiv.org/abs/2506.08573)
- Maymin, [Option Pricing on AMM Tokens](https://arxiv.org/abs/2603.29763)
- Serafini & Bormetti, [Carbon Allowance Options with SV and Jumps](https://arxiv.org/abs/2501.17490)

新しいことだけを採用理由にしない。再現性、データ可用性、既存 baseline に対する増分、教材としての説明可能性を
満たすものだけを中核へ昇格する。

---

## 9. 設計決定と次アクション

正式設計・実装計画では次を既定とし、現行実装もこの責務分離に従う。

1. **案 A の stage-gated 3 巻構成。**
2. **PyTorch を hullkit の必須依存にしない。**
3. **`deep_hedge_price` を学習基盤の正本、`hullkit` を金融教師・検査の正本にする。**
4. **既定データを synthetic core とし、市場データは provenance/licence 確定後に追加する。**

完了した release 手順:

1. `make hull-release` と full-workspace test を fresh 実行した。
2. コマンド、件数、negative results、残存 model risk を `johnhull/VALIDATION.md` に固定した。
3. 明示承認後に追跡済み commit を作り、`make hull-release-check HULL_RELEASE_FLAGS=--require-tracked`
   を通して専用 branch へ push した。
