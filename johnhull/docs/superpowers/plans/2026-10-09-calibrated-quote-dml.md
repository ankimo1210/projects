# 較正込み市場クオートGreeksのDML Implementation Plan

> **For agentic workers:** `superpowers:executing-plans` で実施し、checkboxで進捗を記録する。現在の実行モードに従い、金融参照・配列境界の学習・レビューなど共有変更のない作業は並行化できる。commitとgateは依存順でまとめる。

**Goal:** RB-F07とRB-F05を接続し、同じ較正・契約・データ・計算予算で価格、市場risk、固定契約ヘッジ、総費用を比較する再実行可能な研究を作る。

**Architecture:** 金融教師とヘッジはtorch-free hullkitの新private modules、学習はdeep_hedge_priceの新private module。研究runnerは配列境界で両者を接続する。独立bootstrap・密度積分・CF価格と、保存重みのNumPy再評価から結果を検証する。

**Tech Stack:** 既存Python/uv、NumPy、SciPy、PyTorch CPU float64、pytest、ruff、nbformat/nbclient、matplotlib。追加production依存なし。

**Spec:** [調査・研究設計](../specs/2026-10-09-calibrated-quote-dml-design.md)。本文のQ01–Q12を根拠とし、版・確認範囲・未再現の性能主張を引き継ぐ。

- 更新日：2026-10-09。**Tasks1–6実装済み。30NN＋4ridgeの本学習、保存重み・独立数値の再検査、core成果の両保管庫からの復元が完了。直近scoped 974 tests PASS。Task7の100反復計時/原価、追加レビュー修正、Task8の3図実行/目視と独立最終レビューを完了。関連3suiteの初回4 FAILをAgg表示修正で解消、11件再検査PASS。`a25345e1`をmainへ統合後、全関連3suite再実行で6919 PASS/6 skip（334.02秒）、release gate PASS。Tasks1–8完了。**
- 本編P0–P8、306節acceptedの状態を変更しない。
- 本人の「研究ロードマップを完遂せよ」に従い、quote DMLを先行し、既存離散バリア→F04→F08→F06と統合研究の後続候補も保持する。

## Global Constraints

- 実行・Gitは `/home/kazumasa/projects` のWSLから。Windows drive pathをLinux pathと混ぜない。
- 金融教師はtorch-free hullkit、学習はdeep_hedge_price、教材は `johnhull/research/RB-F07/quote_dml/`。
- 新規計算はprivate modules。`__init__.py`・公開API・production依存を変更しない。
- 教材のbuild中に学習・ネットワーク・GPU検出を行わない。notebookは保存JSON+NPZだけを読む。
- 数値比較は許容誤差つき。SHAは成果物の完全性だけに用い、数値オラクルには用いない。
- NNは7→64→64→1、tanh、線形出力、CPU float64・1 thread、Adam lr.001、batch256、512 updates、seed11/29/47。
- 5方式×2サイズ×3seed=30 fits。512 updatesが120秒を超えるfitはbudget failureを残す。
- 設計§6–8の分割・seed・尺度・shock・費用・仮説を主実験前に固定する。test結果から設定・許容差を変更しない。
- 既存RB-F07/F05の成果物、別プロジェクト変更、別セッションの受入作業を保持する。
- モジュール追加時に `johnhull/MODEL_INDEX.md` を同じcommitで更新。計画中のモジュールは実装済み索引へ掲載しない。
- 初回は調査・計画のみ。その後の完遂指示により下記の実装・データ生成・学習へ移行する。

## Review Focus

1. 割引微分を落としたquote LRM、指示関数のpathwise微分：Task 1/2で独立積分と負の対照を検査。
2. 同じ曲線の8契約がtrain/testへ混ざる、testで尺度をfitする：Task 3/4で市場ID分割とtrain-only尺度を検査。
3. Theta方式を内部Greekだけで不公平に評価する、物理単位とinput順の混同：Task 4で変換後lossと有限差分を検査。
4. ショック後に保有couponを新parへresetする、元本やPV01の単位を取り違える：Task 6でCF・数量・単位変更を検査。
5. OODのclip、rank不足、ゼロhit/SE、保存PASSフラグが失敗を隠す：Task 2/6/7で明示的失敗・fallback・改変を検査。

## 段階と依存

| 段階 | Tasks | 成果 | 暫定agent作業時間 |
|---|---|---|---:|
| 1 教師・独立参照 | 1–2 | 解析、LRM、conditioning、単位・不連続性の検証 | 2–4時間 |
| 2 データ・比較器 | 3–5 | 市場群分割、5NN、2低次元回帰、公平metric | 3–6時間 |
| 3 固定契約ヘッジ | 6 | 数量、瞬間shock再評価、入口費用、OOD | 1–3時間 |
| 4 記録・研究採否 | 7–8 | 30 fits、raw配列、再計算、3図、結果記録 | 2–3時間 |
| **計** | | **8–16時間。段階1の実測で改訂** | |

commit/gateはTask 1→2→3→4→5→6→7→8の順。配列契約を固定した独立作業は並行可能。学習本実験はTask 7でまとめて1回実行する。
時間は未実測の目安。学習watchdog合計60分には参照生成・計時・レビューを含まない。

## ファイルと配列契約

以下は実装時に作るファイル。現在存在する実装へのリンクとしては扱わない。

| 作成先 | 責務 |
|---|---|
| `johnhull/hullkit/src/hullkit/_quote_dml_teachers.py` | 市場較正の準備、解析digital、6成分のLRM/conditioning教師 |
| `johnhull/hullkit/src/hullkit/_quote_dml_hedging.py` | 固定した6契約の価格・risk、数量solve、shock・入口費用 |
| `deep_hedge_price/src/deep_hedge_price/_quote_dml.py` | train-only尺度、5NN方式、20項回帰、raw価格/勾配、重みexport |
| `johnhull/research/RB-F07/quote_dml/reference_methods.py` | hullkitをimportしない逐次brentq・complex-step J・密度積分・固定CF参照 |
| `johnhull/research/RB-F07/quote_dml/replay.py` | torchをimportしないNN/回帰の重み再評価・物理勾配・配列からの指標再計算 |
| `johnhull/research/RB-F07/quote_dml/build_reference.py` | protocol、データ生成、学習の明示refresh、結果保存・check CLI |
| 同ディレクトリの `protocol.json`、`reference.json`、`reference.npz` | 固定仕様、環境/時間/失敗理由、入力/教師/重み/予測/hedge/shock配列 |
| 同ディレクトリの `build_notebook.py`、`quote_dml.ipynb`、`README.md` | artifact-onlyの3図、実行方法、結果・採否・制限 |
| `johnhull/hullkit/tests/test_quote_dml_teachers.py` | 解析/MC教師と独立参照 |
| `johnhull/hullkit/tests/test_quote_dml_hedging.py` | 固定契約・数量・shock・費用 |
| `johnhull/hullkit/tests/test_quote_dml_research.py` | 分割、record再計算、改変、OOD、notebook |
| `deep_hedge_price/tests/test_quote_dml.py` | loss、物理gradient、train-only尺度、重み再評価 |

データの単位・shapeを全Taskで統一する。

```text
q0 = [.0300, .0320, .0330, .0345, .0360]      # simple rate decimal
pillars = [.5, 1., 2., 3., 5.]              # continuous zero rate nodes
quote_order = [deposit_6m, fra_6x12, swap_2y, swap_3y, swap_5y]
x_quote[n,7] = [q0..q4, spot, maturity]
x_theta[n,7] = [zero0..zero4, spot, maturity]
g_quote[n,6] = [delta_spot, dV_dq0..dV_dq4]  # raw derivative, no bp factor
g_theta[n,6] = [delta_spot, dV_dz0..dV_dz4]
A[n,5,5] = dz/dq                          # theta row, quote column
market_id[n], contract_id[n]              # unique within named split
hedge_order = [stock, deposit, fra, swap2, swap3, swap5]
B[6,6] = dH_i/dx_j                       # rows spot/q, columns hedge
h[6]                                     # shares / contracts of 1m notional
```

swapは年払、2年=(1,2)、3年=(1,2,3)、5年=(1,2,3,4,5)。預金=.5、FRA=(.5,1)。
strike100、sigma.20、cash payout1。全価格は同一の教育用通貨単位。

共通テストから研究ファイルを読むときは `importlib.util.spec_from_file_location` を使う。
研究ディレクトリのmodule名を他プロジェクトと衝突するtop-level packageとして登録しない。

---

## Task 1：解析教師と独立bootstrap／積分

**Files:** 新規teacher module、`reference_methods.py`、teacher test、MODEL_INDEX。

**Interfaces:**

- `prepare_market(q: np.ndarray) -> Market`。Marketはq[5]、既存Calibration、`dz_dq[5,5]`を保持する。
- `analytic(market: Market, spot: float, maturity: float, *, strike=100., sigma=.2) -> dict`。
  keys=`price`, `g_quote[6]`, `g_theta[6]`, `discount`, `integrated_rate`, `amplification`。
- 参照側 `bootstrap(q) -> (pillars, zeros)`、`digital_price(q,S,T) -> float`、`digital_moments(q,S,T) -> dict`。
  momentsは独立score積分の `price`, `g_quote[6]`, `lrm_second_moment[6]` を返す。

- [x] **RED：** 5つの調査ケース、T=.5/1/2/3/5の柱、negative rateの有効曲線を独立参照と比較するtestを作る。
  最初に既存F07の固定CFテストを通し、次の1.5年cashflowで新Marketの座標配線を確認する。

```python
def cf_value(q):
    times, zeros = reference.bootstrap(q)
    return -3_000_000 * np.exp(-1.5 * np.interp(1.5, times, zeros))

q = np.array([.03, .032, .033, .0345, .036])
market = teacher.prepare_market(q)
pv, gz = risk.cashflow_value(market.calibration, (1.5,), (-3_000_000,))
gq = risk.quote_sensitivity(market.calibration, gz).per_unit
width = 1e-5
bumps = np.eye(5) * width
ref_gq = np.array([(cf_value(q + b) - cf_value(q - b)) / (2 * width) for b in bumps])
assert pv == pytest.approx(cf_value(q), abs=1e-6, rel=1e-10)
np.testing.assert_allclose(gq, ref_gq, atol=1e-4, rtol=1e-6)
```

```python
q = np.array([.03, .032, .033, .0345, .036])
market = teacher.prepare_market(q)
for spot, maturity in [(80, .05), (95, .25), (100, 1.5), (110, 4.5), (120, 5)]:
    got = teacher.analytic(market, spot, maturity)
    ref = reference.digital_moments(q, spot, maturity)
    assert got["price"] == pytest.approx(ref["price"], abs=1e-12, rel=1e-10)
    np.testing.assert_allclose(got["g_quote"], ref["g_quote"], atol=1e-10, rtol=1e-9)
    np.testing.assert_allclose(
        got["g_quote"][1:], market.dz_dq.T @ got["g_theta"][1:],
        atol=1e-10, rtol=1e-9,
    )
```

- [x] `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_quote_dml_teachers.py` を実行し、未実装によるFAILを確認。
- [x] **GREEN：** `Quote`/`calibrate`/`discount_factors`/`quote_sensitivity`を再利用し、設計§4.2を実装する。

```python
v = sigma * np.sqrt(maturity)
d2 = (np.log(spot / strike) - np.log(discount) - v * v / 2) / v
price = discount * ndtr(d2)
delta = discount * np.exp(-d2 * d2 / 2) / (np.sqrt(2 * np.pi) * spot * v)
g_z = d_discount_dz * (ndtr(d2) - np.exp(-d2 * d2 / 2) / (np.sqrt(2 * np.pi) * v))
g_q = risk.quote_sensitivity(calibration, g_z).per_unit
A = np.linalg.solve(calibration.jacobian, np.eye(5))
```

参照はscheduleを自身で定義し、逐次brentq（bracket−.2〜1、xtol5e-16、rtol1e-14）を使う。
参照Jは自作quote式をzero座標でcomplex-step幅1e-25、積分は正規密度を `quad` でthreshold〜∞。
productionのJacobianや教師を参照計算へ流用しない。別途q幅1e-4/1e-5/1e-6で再bootstrap中央差分を保存する。
正のspot/T/sigma/strike、finite配列・shape、正のDFを確認。negative quoteを一律拒否しない。
- [x] zero→logDF座標とquote decimal→bpの変換をtest。表示Greek=raw×1e-4、価格・物理riskが不変であることを確認。
- [x] 既存 `test_quote_risk.py` と新testを実行し、変更Pythonのruff/format check、MODEL_INDEX guardを確認。
- [x] scoped commit：`feat(johnhull): add calibrated digital quote-risk teachers`。ROADMAPの研究行を「教師実装・残り未実施」へ更新。

## Task 2：LRM／厳密conditioningと負の対照

**Files:** teacher module、teacher test、reference methods。

**Interfaces:** `samples(market,S,T,z: np.ndarray) -> dict`。zの最後の軸をIID pathsとし、keysは
`payoff`、`lrm[npath,6]`、`conditional_price`、`conditional[npath,6]`、`naive_pathwise[npath,6]`、`discount_omitted[npath,6]`。
単一S/Tでのshapeをまず固定する。MC sampleを主学習へ混ぜない。

- [x] **RED：** S95/100/105×T.05/.25/1.5/4.5、65536paths、seed1107のmean/SEを解析値と比較する。
  pilot seed6017は分散・許容差の根拠確認だけに使う。

```python
z = np.random.default_rng(1107).standard_normal(65536)
out = teacher.samples(teacher.prepare_market(q), 100., .25, z)
expected = reference.digital_moments(q, 100., .25)["g_quote"]
mean = out["lrm"].mean(axis=0)
se = out["lrm"].std(axis=0, ddof=1) / np.sqrt(len(z))
assert np.all(np.abs(mean - expected) <= 6 * se + 1e-10)
assert expected[0] > 0
assert np.allclose(out["naive_pathwise"][:, 0], 0., atol=1e-14)
```

- [x] 同じscoped testを実行し、未実装FAILを確認。
- [x] **GREEN：** 設計§4.3を実装。spot scoreは `Z/(S*v)`、quote scoreは `(-1+Z/v)*a_q`。
  α=.5のconditional教師はnormal CDF/PDFを使い、6成分の条件付きmeanとSEを計算する。
  `a_q=∇q(-log D)` はMarketのAと曲線weightから求める。
- [x] 独立積分でLRM/conditioningのmeanとLRM2次モーメントを検査。割引項を落としたmeanのbiasが `price*a_q` に一致することをtest。
- [x] S80/T.05はexpected hits<20を事前分類。zero hitsやSE0を通常6SEのPASSへ変えないtestを追加。
  pathwiseと割引欠落教師は「検証に失敗すべき推定量」として保存し、ランダムな1回の有意差だけでbiasを証明しない。
- [x] 新teacher tests＋ruff/format check後、scoped commit：`feat(johnhull): verify digital score and conditional quote labels`。

## Task 3：protocolと市場曲線群での分割

**Files:** `protocol.json`、`build_reference.py`、`test_quote_dml_research.py`。

**Interfaces:** `make_dataset(protocol: dict, split: str) -> dict[str,np.ndarray]`。
配列契約のx_quote/x_theta/g_quote/g_theta/Aにprice[n]、market_id[n]、contract_id[n]、integrated_rate[n]、a_quote[n,5]を加える。
`load_protocol(path) -> dict` はschedule・units・fit数を確認する。未知のversionは拒否する。

- [x] **RED：** train2048/validation512/test1024、小train512はtrain先頭64市場、split間で市場群が混ざらないtestを作る。

```python
train = runner.make_dataset(protocol, "train")
test = runner.make_dataset(protocol, "test")
assert train["x_quote"].shape == (2048, 7)
assert test["x_quote"].shape == (1024, 7)
assert set(train["market_id"]).isdisjoint(test["market_id"])
assert np.all(np.unique(train["market_id"], return_counts=True)[1] == 8)
assert np.unique(train["market_id"][:512]).size == 64
```

- [x] 新research testを実行してFAILを確認。
- [x] **GREEN：** `SeedSequence([20261009, split_id])` を使う。q=q0+Uniform(−.005,.005)、spot=Uniform(80,120)、T=exp(Uniform(log(.05),log(5)))。
  同じmarketの8契約でMarketを共有する。testの8契約は設計§6の固定値。
  market IDはsplitを含む整数（例split_id×100000+curve_index）。contract IDは群内0–7。
- [x] protocolに比較5方式、2サイズ、3seed、lambda1、Greek平均6、scale下限1e-8、全shock/OOD、H1–H4、許容差を保存。
  失敗入力・較正残差・rank・増幅を記録し、黙ってresampleしない。生成失敗が主domainにある場合はfitを止め、protocol改訂理由を残す。
- [x] 較正回数がcurve数であること、再生成の数値許容差、未知protocol拒否をtest。
- [x] scoped tests＋ruff/format check後、commit：`feat(johnhull): define grouped quote-DML experiment protocol`。

## Task 4：5NNと公平な市場risk損失

**Files:** `_quote_dml.py`、`test_quote_dml.py`、MODEL_INDEX。

**Interfaces:**

- `fit_nn(train: dict, *, mode: str, seed: int, updates=512, budget_s=120.) -> Fit`。
  modes=`q_price`, `theta_price`, `theta_dml`, `theta_quote_metric`, `q_dml`。
  Fitはmodel、scale、stats。入力はNumPy配列境界で、hullkitをimportしない。
- `predict_nn(fit: Fit, x: np.ndarray, A: np.ndarray) -> dict`。price[n]、g_quote[n,6]、g_native[n,6]。
- `export_nn(fit) -> dict[str,np.ndarray]`。各層weight/biasとtrain-only尺度を保存する。

- [x] **RED：** 同じ固定した小NNの物理勾配を中央差分と比較し、Thetaの勾配をAで変換するtestを作る。

```python
pred = learner.predict_nn(fit, x, A)
np.testing.assert_allclose(pred["g_quote"][:, 0], finite_delta, atol=1e-8, rtol=1e-6)
expected = np.einsum("nij,ni->nj", A, pred["g_native"][:, 1:])
np.testing.assert_allclose(pred["g_quote"][:, 1:], expected, atol=1e-10, rtol=1e-9)
```

finite_deltaは同じfitted NNのspotを±1e-3動かした差分。quote/zeroは±1e-6で検査。
Thetaの物理quote差分はquoteを動かした後のzero変化を使い、zero入力をquoteと誤認しない。
このtestの `fit,x,A,finite_delta` は次の数値fixtureから作る。金融教師への依存なしに、非対角Aと物理chain ruleを検証できる。

```python
def tiny_train():
    q0 = np.array([.03, .032, .033, .0345, .036])
    q = q0 + np.linspace(-.001, .001, 16)[:, None] * np.array([1., -1., .5, -.5, 2.])
    spot, maturity = np.linspace(90., 110., 16), np.linspace(.5, 2., 16)
    a = 2 * np.eye(5)
    a[1, 0] = .3
    w = np.array([.1, .2, .3, .4, .5])
    gq = np.tile(np.r_[.005, w], (16, 1))
    gz = np.tile(np.r_[.005, np.linalg.solve(a.T, w)], (16, 1))
    return {
        "x_quote": np.column_stack([q, spot, maturity]),
        "x_theta": np.column_stack([q0 + (q - q0) @ a.T, spot, maturity]),
        "price": .4 + .005 * (spot - 100) + (q - q0) @ w,
        "g_quote": gq, "g_theta": gz, "A": np.tile(a, (16, 1, 1)),
    }

train = tiny_train()
fit = learner.fit_nn(train, mode="theta_quote_metric", seed=11, updates=2)
x, A = train["x_theta"][:3], train["A"][:3]
up, down = x.copy(), x.copy()
up[:, 5] += 1e-3
down[:, 5] -= 1e-3
finite_delta = (learner.predict_nn(fit, up, A)["price"]
                - learner.predict_nn(fit, down, A)["price"]) / .002
```
- [x] `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests/test_quote_dml.py` でFAILを確認。
- [x] **GREEN：** 生入力tensorに `requires_grad` を付けてからrate5/log(S/K)/logTの特徴化・標準化を行う。
  価格はtrain mean/stdで復元し、その価格の勾配を取る。differential lossでは `create_graph=True`。

```python
gradient = torch.autograd.grad(price.sum(), raw_x, create_graph=True)[0]
native = torch.cat([gradient[:, 5:6], gradient[:, :5]], dim=1)
quoted = torch.cat([
    native[:, :1], torch.einsum("nij,ni->nj", A_tensor, native[:, 1:])
], dim=1)  # theta modes only; q modes use native directly
loss_price = (((price - target_price) / price_scale) ** 2).mean()
loss_risk = (((risk - target_risk) / risk_scale) ** 2).mean()
loss = loss_price + loss_risk  # lambda1 × mean of six squared normalized Greeks
```

price-onlyはloss_priceだけ、Theta-DMLはnative/内部教師と内部尺度、Theta-quote-metricはquoted/quote教師とQ-DML共通尺度。
spot scaleも同一trainデータから求める。特徴stdゼロなら1、price std/Greek RMSの下限1e-8。
- [x] trainのみを受け取るnormalization、domainの異なるtest入力をpredictしてもfit尺度が不変、seedを揃えた初期重み/batch順、CPU thread/RNGの復元をtest。
  smokeはupdates2・小trainを使い、フル学習や勝者をunit testの条件にしない。
- [x] updates数・setup/training実測・budget_failureを返す。途中fitは成功30fitsに数えない。
  minibatchはmin(256, train行数)。smoke fixture16行でも実行でき、主学習512/2048行では固定256になる。
- [x] 新test＋既存digital DML test、ruff/format、deep索引guardを確認し（hull索引は並行Task6の未コミットmodule登録時に再確認）、commit：`feat(deep-hedge): compare quote and parameter DML metrics`。

## Task 5：低次元price／differential ridgeと重み再評価

**Files:** `_quote_dml.py`、`replay.py`、deep learner tests。

**Interfaces:** `fit_ridge(train, *, differential: bool) -> dict`、`predict_ridge(fit, dataset) -> dict`。
`replay.nn_predict(exported,x,A) -> dict`、`replay.ridge_predict(exported,dataset) -> dict` は価格/quote勾配を同じshapeで返す。
reference artifactのreplayはtorchやlearnerをimportしない。

- [x] **RED：** monomialが20項で、3変数の全total degree≤3を含むこと、feature derivativeと物理Greekの一致をtest。

```python
powers = [(i, j, k) for i in range(4) for j in range(4) for k in range(4)
          if i + j + k <= 3]
assert len(powers) == 20
train = tiny_train()  # Task 4で定義した同じtest fixture
fit = learner.fit_nn(train, mode="q_dml", seed=11, updates=2)
x, A = train["x_quote"][:3], train["A"][:3]
torch_pred = learner.predict_nn(fit, x, A)
replayed = replay.nn_predict(learner.export_nn(fit), x, A)
np.testing.assert_allclose(replayed["price"], torch_pred["price"], atol=1e-12, rtol=1e-10)
np.testing.assert_allclose(replayed["g_quote"], torch_pred["g_quote"], atol=1e-10, rtol=1e-9)
```

- [x] scoped testで未実装FAILを確認。
- [x] **GREEN：** u=(log(S/K),R_T,logT)をtrain-only標準化し、20項の値と解析特徴微分を作る。
  physical derivativeは ∂u0/∂S=1/S、∂u1/∂q=a_q、他のspot/quote成分0。Tは固定する。
  price回帰は価格行、differential回帰は同じ価格行＋6Greek行を同じ価格/RMS尺度でstackする。
  行の平均を揃える係数は価格1/√n、Greek1/√(6n)。罰則sqrt(1e-8)×Iを追加し切片列は罰しない。`np.linalg.lstsq`を使う。
- [x] NumPy NN replayは保存済み2層tanh/線形出力、train尺度、tanh導関数のchain ruleを実装。
  Q/Theta全5方式のexport→replay価格/勾配を許容差で検査。bit一致は要求しない。
- [x] 新test＋ruff/format、索引を確認し、commit：`feat(deep-hedge): add reduced differential regression and replay`。

## Task 6：固定契約ヘッジ、shock、費用、OOD

**Files:** hedge module、reference methods、hedge/research tests、MODEL_INDEX。

**Interfaces:**

- `held_prices(market,S,contract_quotes,*,notional=1e6) -> np.ndarray[6]`、`held_risk(...) -> np.ndarray[6,6]`。
- `solve_hedge(B,g_quote) -> np.ndarray[6]`。Bは独立参照の同一行列を全方式へ渡す。
- `entry_cost(h,B,spot,*,rate_halfspread_bp,stock_halfspread_bp) -> float`。
- runner側 `safe_prediction(exported,q,S,T,protocol,*,context: dict | None=None) -> dict` は `status`, `reason`, `raw`, `safe`, `fallback` を返す。
  raw NNの校正済み内部入力にはMarket zeros/Aを使う。安全wrapperはCurve診断と適合性を先に確認する。
  contextはstrike/sigma、pillar/schedule/interpolationの宣言。省略時はprotocolと同じ固定条件。
  exportedのkind（NN/ridge）でreplayを選び、同じdomain・bounds・fallback規則を全学習近似へ適用する。

- [x] **RED：** 5年quote+1bpで元coupon3.6%のPVが−451.6857814、新par3.61%ではほぼ0になる負の対照をtest。

```python
shifted = q.copy()
shifted[4] += 1e-4
market = teacher.prepare_market(shifted)
held = hedging.held_prices(market, 100., q)[-1]
reset = hedging.held_prices(market, 100., shifted)[-1]
assert held == pytest.approx(-451.6857813536834, abs=1e-6, rel=1e-9)
assert reset == pytest.approx(0., abs=1e-6)
```

- [x] 新testを実行してFAILを確認。
- [x] **GREEN：** 設計§4.4の固定CFを実装し、自作CFのcomplex-step＋独立Jでriskを照合する。
  Bの列順=株式/預金/FRA/2/3/5y。L=diag(1,1e-4,...,1e-4)を掛けて `np.linalg.solve(L @ B, -L @ g)`。
  正規化行列のSVDでrank不足を検出しValueErrorを返す。raw condition numberを単独停止閾値にしない。
- [x] notional1m→2mではrate数量半分、同じcashflows・残余になることをtest。
  ゼロshockの残余0、参照Greekの単独微小shockで一次項消去／2次縮小、二重保有や符号反転の負の対照を検査。
- [x] test中心の単独/parallel/steepener±1/10bp、spot±1%、組合せ4本を再評価する。Tとcouponは固定。
  費用はrateの自bucketabs(B[i+1,i+1])*1e-4×半spread0/.1/.5/1bp、株式spot×半spread0/1/5bp×1e-4。
  費用は数量絶対値で合計し、残余と別の指標で保存する。
- [x] 数学的には有効なnegative rate、domain外q±100bp/S70/130/T.01/6、sigma/strike/schedule/pillar/interpolation変更をOODに分類。
  q/spot/TのOOD、対応済みstrike/sigma変更、増幅>10、NN価格が[0,D]外は、較正可能なら全価格・Greekを解析へfallback。
  pillar/schedule/interpolation変更は `unsupported_context` として価格を返さない。数学的に無効なS/T/sigma、較正不能・rank不足はfailure。
  生NN結果・fallback結果・件数を別に記録し、clipしないtestを作る。
- [x] 新teacher/hedge/research tests＋ruff/format、索引guard後、commit：`feat(johnhull): compare frozen-contract quote hedges`。

## Task 7：一括実験、保存配列、改変検査

**Files:** runner、replay、protocol/reference JSON+NPZ、research tests。

**Interfaces:**

- `run_experiment(protocol, *, smoke=False) -> (record: dict, arrays: dict)`。
- `replay.metrics(arrays, protocol) -> dict`、`check_record(record,arrays,*,fresh: bool) -> None`。
- CLI：`build_reference.py --smoke --output /tmp/quote-dml-smoke`、`--refresh`、`--check`。
  checkは学習を起動せず、raw arrays/保存重みから指標と独立価格/リスク/hedgeを再計算する。

- [x] **RED：** smoke recordのprice predictionを1点変えたら価格検査が、Greekを変えたらrisk/数量検査が、couponを変えたらheld/shock再評価がFAILするtestを作る。
  保存PASSフラグだけを変更しても数値検証の成否は変わらないことをtest。
- [x] research testを実行してFAILを確認。
- [x] **GREEN：** JSONへprotocol version、source基準、環境、全fit状態/updates/計時/失敗理由、尺度、指標を保存。
  NPZへ全分割入力・教師・A・IDs、exported重み、全予測、B/h、shock後価格・残余、費用、raw/safe/OOD判定根拠を保存。
  q/zero/spot/T/unitsとshapeをmetadataへ固定し、配列不足・不整合はcheck失敗。
- [x] `--smoke` は市場数とupdatesを縮小し明確にsmokeと記録。主protocolの30fits/4ridgeと混ぜない。
  smokeでAPI・export・replayが通った後だけ、固定protocolの `--refresh` を1回実行する。
  120秒に達したfitは理由を記録し、学習条件を変えて無言で再実行しない。
- [x] 価格/risk/数量/残余/入口費用を設計§8の単位で再計算。2000回のpaired bootstrapは市場ID群、seed20261010。
  test各8行を同じ群で引き、H1/H2はseed別にpaired差の95%CIを保存する。
- [x] timingはraw NNとsafe wrapper、解析・ridge・再bootstrap bumpを分ける。
  single/batch32/batch1024、warmup後100反復、median/p95、較正共有あり/なし、calibration countを保存。
  offlineには教師・尺度・fit・exportを含め、loadを別記。全fit総費用と、1方式/1seedを利用する場合の費用を両方残す。
  損益分岐は `(offline_surrogate-offline_reference)/(online_reference-online_surrogate)`、分母>0のみ。分子≤0は開始時点から費用優位として別表示。
- [x] raw weights→NumPy replayと保存予測、全教師のfresh独立参照、全固定契約shockをcheckする。
  notebookへ読ませる指標に保存済みPASSだけを根拠とする項目を残さない。
  30fitsに失敗があればprotocol完遂は未完了と明記し、失敗そのものは成果物に保持する。
- [x] 生成JSON/NPZが20MBを超えたら学習を繰り返さず、既存ADR 0004保管庫＋small manifestへ移す。合成データ以外は入れない。
- [x] 新tests＋ruff/format、`--check` 後にscoped commit。Task8と合わせて`a25345e1`（`research(johnhull): close calibrated quote-DML v1 evaluation`）に記録。

## Task 8：artifact-only教材と結果・次工程の判断

**Files:** build_notebook、notebook、README、research tests、MODEL_INDEX、CONTENTS_INDEX、ROADMAP、既存研究backlog。

- [x] **RED：** notebookの構文/出力、artifactだけの実行、3図の根拠配列、学習関数への非依存をresearch testで固定。
  build/nbclient実行中のtrainer呼出を例外へ置換し、学習を起動するとFAILする。
- [x] **GREEN：** notebookはJSON/NPZの読込だけにする。図は次の3枚。
  1. 方式別の価格／正規化6Greek誤差、3seedと市場群CI。
  2. fixed hedgeの小/大shock残余と入口費用を別パネルで表示。
  3. exact／ridge／raw NN／safe wrapperの費用・精度、評価回数別総費用。
  日本語図は既存nbplot設定を使い、renderして見切れ・凡例・単位を確認する。
- [x] READMEへH1–H4の結果、全fit失敗/負の結果、teacher/較正/NN誤差の分離、raw/safeの差を記載。
  「瞬間shock」「決定論的単一曲線」「固定sigma」「合成データ」を明示。
  動的hedging、multi-curve、最小二乗、rough、実市場性能へ結果を外挿しない。
- [x] 研究完了は全比較器・全fitの結果と再計算を確認した時点。DMLの勝利は必須にしない。
  速度採用へ自動昇格しない。H1/H2の改善主張には設計§8の全seed条件を使い、他指標の悪化も併記。
- [x] 下記の対象検証と索引guardを1回まとめて行う。旧F07/F05成果物が変わっていないことを確認。
  共有実装を変更していないため、Book全build・306節台帳再受入・D1全復元はこの研究のgateにしない。
- [x] 数式・risk座標・固定契約・公平loss・失敗時の記録を独立レビューへ渡す。
  独立レビューを未実施なら研究状態を「実装/対象検証済み、レビュー未完了」とする。
- [x] 結果と採否、次に離散バリア／高コスト金利／最小二乗のどれを選ぶかをROADMAP/backlogに記録。
  教材/計算の索引と同じ`a25345e1`で更新。統合後検証の記録を後続docs commitへ保持する。

### 最終対象検証コマンド

repo rootのWSLで実行する。実装中は各Taskの対象testだけを使い、下記は締めに1回。

```bash
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_quote_dml_teachers.py \
  johnhull/hullkit/tests/test_quote_dml_hedging.py \
  johnhull/hullkit/tests/test_quote_dml_research.py \
  johnhull/hullkit/tests/test_quote_risk.py \
  johnhull/hullkit/tests/test_digital_teachers.py \
  johnhull/hullkit/tests/test_digital_research.py \
  johnhull/hullkit/tests/test_model_index.py
uv run --no-sync --package deep-hedge-price pytest -q \
  deep_hedge_price/tests/test_quote_dml.py \
  deep_hedge_price/tests/test_digital_dml.py \
  deep_hedge_price/tests/test_model_index.py
uv run --no-sync ruff check \
  johnhull/hullkit/src/hullkit/_quote_dml_teachers.py \
  johnhull/hullkit/src/hullkit/_quote_dml_hedging.py \
  deep_hedge_price/src/deep_hedge_price/_quote_dml.py \
  johnhull/research/RB-F07/quote_dml \
  johnhull/hullkit/tests/test_quote_dml_teachers.py \
  johnhull/hullkit/tests/test_quote_dml_hedging.py \
  johnhull/hullkit/tests/test_quote_dml_research.py \
  deep_hedge_price/tests/test_quote_dml.py
uv run --no-sync --package hullkit python \
  johnhull/research/RB-F07/quote_dml/build_reference.py --check
```

ruff format --checkは同じ対象Pythonへ実行する。notebook builderの既存excludeは維持。
成果物のSHA検査と数値許容差検査の結果を分け、実測からREADME/ROADMAPへ記録する。

## 計画レビュー結果（2026-10-09）

- 設計の教師・公平比較・単位・群分割・OOD・費用・仮説・再計算をTasks 1–8へ対応させた。
- 予測input順とrisk順、Aの向き、株式/100万元本の数量単位を固定した。
- 既存F07/F05を書き換えず、新private modulesと研究subdirectoryで実施する。
- 割引欠落、契約reset、rare event、漏洩、改変、rank不足の負の対照を用意した。
- 文献の公開性能は未再現。研究新規性・本番採用・実市場の優位を完了条件へ入れていない。
- 初回の完了範囲は調査・計画。その後の完遂指示によりTask1の教師と独立参照から実装を開始。

## 実行時の具体化（2026-10-09）

- Task5–6は並行で実装後、独立レビューと一括scoped gateで閉じる。安全wrapperをpolicy.py、MC診断をdiagnostics.py、計時をbenchmark.pyへ分離し、runnerから呼ぶ。各専用testも最終scoped gateへ追加する。
- 群ID・shock/cost軸・train尺度・fit registryを保存フラグとは独立に再検査する。較正/fit例外では入力と部分成果を返して保存する。
- 1方式導入のoffline費用はサイズ別train教師＋setup/fit/export、全比較費用は全分割教師＋全fitとし、評価oracle費用を混同しない。
- 本学習は30本各512updates＋4ridgeを完遂、budget failureなし。fresh独立数値照合はPASS。本計時は保存重みを使う別工程で完了。310測定/288費用対照・loader rawを保存。
- 追加レビューでfit metadataの固定条件、計時measurement registry、保存discountとintegrated rateの不変条件の検査不足を検出。本計時終了後にRED→GREENを確認し、main成果への独立fresh checkもPASS。
- notebook builderの小fixtureはartifact-only実行と3図を確認済み。本成果3図の実行/目視・費用採否・独立最終レビューまで完了。その後のmain統合・全関連suite再実行・release gateまでPASS。smokeの性能は主実験の結論へ使わない。


### 最終検証・採否

34fit/310計時/288原価・fresh独立再計算・最終両保管庫復元・3図実行/目視・独立最終レビューを完了。
関連3suiteは初回6,915 PASS / 4 FAIL / 6 skip、headless Aggの表示不具合を再現・修正し11件再検査PASS。
`a25345e1`をmainへfast-forward統合後、全関連3suiteを再実行し6,919 passed / 6 skipped（334.02秒）、終了コード0。通常make hull-reportもPASS。candidateと統合後mainの`verify_release.py --require-tracked`もPASS。
研究は教材として受け入れ、Q-DMLの標準価格/Greek/速度器への昇格は不採用。
次はF05離散バリア、F04、F08、F06。F05のprivate教師・独立PDE参照は作業branchで着手済み、学習/成果物/研究受入は未完了。
