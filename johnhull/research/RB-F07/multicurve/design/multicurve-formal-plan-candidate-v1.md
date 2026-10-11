# #10 Multicurve Integrated Quote Risk and P&L — Implementation Plan Candidate v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推奨）またはsuperpowers:executing-plans。チェックボックスは将来の作業。今回の文書作成では実装・金融計算・試験worker・Git/CASを実行していない。

**Goal:** D/P3/P6の原12quote、全cross-gamma、roll/fixing/表現移行/市場の四項bridgeを、独立参照・全原始成果・saved/fresh/両復元・教材・費用・採否まで完成する。  
**Architecture:** private cashflow→quotes→risk→pnlの4 module。研究ローカル独立参照、case単位JSON+NPZ保存、全roster数値checker、artifact-only notebook。  
**Tech Stack:** 既存NumPy/SciPy/標準ライブラリ、pytest/ruff/nbformat等の既存開発toolのみ。hullkitはtorch-free。  
**Spec:** [multicurve-formal-design-candidate-v1.md](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/multicurve-formal-design-candidate-v1.md)。  
**Status:** 2026-10-11、正式実装計画の**候補**。設計/source/prior/金融結果/launch/研究受入の独立承認は未実施。既存研究完遂指示・private置場の承認を再質問しない。#9採否記録後に金融実装/測定へ進む。

## Global Constraints

- 元D/P3/P6各4node、主12quote、全12×12 H、元market/date/product/wrong controlsを保持。24quote scalingと商品数1/10/100も別familyで予定する。4quote spikeへ縮小しない。
- 公開API/__init__.py/production依存、singlecurve F07 v1、Book/portal、本編accepted件数を変更しない。LS/KKTは式・負例のみ、exact-root主較正へ混ぜない。
- 数値合否は許容誤差・差分h sweep。ビット一致/SHA/solver successフラグを数値参照に使わない。
- 原case ID/attempt/失敗/NaN/unknown/未実行/元費用を保持。未測定を0へ補完しない。改善ケースへの事後selectionで分母を変えない。
- 関連箇所のTDD→scoped tests/ruff。各実装単位のcommitは将来の工程。本ターンは新文書2本のみ、commit/pushはroot担当。
- 研究のsource数学レビュー、resource prior、数値研究レビュー、採否は別。源変更時に旧rawを新producer生成と再ラベルしない。
- source85/live金融check/元rawは不変。本研究から#9のtransport/verifierを新production依存にしない。

## Review Focus

1. 既知resetのzero-J、calendar/day count/publication境界、discountとpseudoDFの区別。
2. D→P3→P6の非対角較正伝播、direct quote項、second calibration response、全cross-gamma。
3. q1=qgで残るVg−Vf、cashの一回計上、t1のfixing-conditioned market center。
4. 全ID/末尾unknown/failureの保持、独立CF/校正参照、source SHAと金融数値の役割分離。
5. whole-path費用/RSS/storageとbounded保存・検算、同じ精度/出力/分母での採否。

## ファイルと依存

以下は**未実装の候補パス/型/API**。実在APIであるとは主張しない。P=project root、M=P/johnhull/research/RB-F07/multicurve、H=P/johnhull/hullkit。

| 将来の変更先 | 単独の責務 |
|---|---|
| H/src/hullkit/_multicurve_cashflows.py | synthetic calendar、resolved schedule、公表済fixing、実現/forecast signed CF |
| H/src/hullkit/_multicurve_quotes.py | D/P3/P6 curve kernel、quote残差/解析微分、exact較正、scaled診断 |
| H/src/hullkit/_multicurve_risk.py | 全gradient/directional curvature/H、単位変換、IFT/随伴 |
| H/src/hullkit/_multicurve_pnl.py | immutable book PV/derivatives、static R1/R2、四項bridge/cash |
| H/tests/test_multicurve_{cashflows,quotes,risk,pnl}.py | 各数式・日付・独立小例・失敗・wrong controls |
| M/fixtures.json, protocol.json | 全resolved入力・主/fresh/validation/scaling case roster、単位/閾値/出力と実件数 |
| M/reference_methods.py, costs.py | main kernelをimportしない独立日付/CF/brent/mixed-bump参照、元費用ledger集計 |
| M/pilot.py, runner.py, checker.py, build_reference.py | prior付き計測、全case演算/保存、保存primitiveの全検算、小成果物 |
| M/tests/test_multicurve_research.py | 全roster/末尾改変/unknown/費用/復元root/独立依存の小fixture試験 |
| M/manifest.json, reference.json, reference.npz, RESULTS.md, REVIEW.md | 小さい図データ・全raw物理参照・全結果/費用/採否・独立判断 |
| M/build_notebook.py, multicurve_risk.ipynb | 保存結果だけの3必須図、fresh artifact-only実行とPNG目視 |
| johnhull/MODEL_INDEX.md、ROADMAP.md、M/README.md | 実装参照/docstring guard、done/current/pending、研究採否の正本更新 |

依存はcashflows→quotes→risk→pnl。cashflowsへquote moduleを逆importしない。forecastはcallerからforward evaluatorを受ける。研究reference_methodsは新4 private moduleをimportしない。runnerが両方式を接続し、checkerはcase単位に解放する。既存公開rfr/rates/swapsは小例の補助oracleとして呼べるが、独立main参照の共有kernelにしない。

### 候補interface（着手前に型を一致させる）

FloatArray=NDArray[np.float64]。型拒否の網羅を目的にしない。数学的に無効な日付/DF/成長factor/欠損既知fixing/quote rankを拒否する。

- cashflows: immutable CalendarSpec（休日/weekend）、ScheduleSpec（unadjusted dates、頻度、EOM/stub/adjustment/各lag/day count）、ResolvedCoupon（accrual/reset/observation/payment、α、index、notional、fixed/spread）、ResolvedContract（id/quantity/currency/coupons/principal/settlement）、FixingRecord（index/date/publication/value/revision/source）、FixingState（as_of、known/forecast-neededの元ID）。
- quotes: CurveGroup（id/node_dates/coordinate/kernel/currency/collateral）、CurveState（valuation/groups/θ）、ResolvedQuote（id/group/raw value/unit/step/transform/contract/abstract-forward flag）、Calibration（state/J/Fq/必要second derivatives/元quote順/全scaled診断）。
- risk: PriceDerivatives（V/Vθ/Vq/Vθθ/Vθq/Vqq）、QuoteRisk（g per-unit/per-step、H per-unit/per-step、単位・順序・solve residual）、方向curvatureはfloat。held book derivative kernelはpnlに置いてriskへ値を渡す。
- pnl: BookValue（全product ID→PV、book PV）、StaticExplain（全product/book ΔV/g/H/R1/R2/分母/status）、BridgeStates（old:Calibration、rolled/fixed:CurveState、represented/market:Calibration）、PnlBridge（V0/Vr/Vf/Vg/V1、C0/Cf、4項、全state/cash ledger、qg/q1、market explain）。BridgeStatesのrolled/fixedはt1 absolute旧knots、represented/marketは同じt1新表現で、valuation_dateと全原契約を検査する。

~~~python
resolve_schedule(spec: ScheduleSpec, calendar: CalendarSpec) -> tuple[ResolvedCoupon, ...]
fixing_state(records: tuple[FixingRecord, ...], as_of: datetime) -> FixingState
realized_cashflows(contract: ResolvedContract, fixings: FixingState) -> tuple[tuple[date, float], ...]
forecast_cashflows(contract: ResolvedContract, fixings: FixingState,
                   forward: Callable[[str, date, date, float], float]) -> tuple[tuple[date, float], ...]
model_quotes(state: CurveState, quotes: tuple[ResolvedQuote, ...],
             fixings: FixingState) -> FloatArray
calibrate_group(groups: tuple[CurveGroup, ...], quotes: tuple[ResolvedQuote, ...],
                fixings: FixingState, *, initial: CurveState) -> Calibration
quote_gradient(calibration: Calibration, price: PriceDerivatives) -> FloatArray
quote_directional_curvature(calibration: Calibration, price: PriceDerivatives,
                            direction: FloatArray) -> float
quote_hessian(calibration: Calibration, price: PriceDerivatives) -> FloatArray
held_book_value(state: CurveState, contracts: tuple[ResolvedContract, ...],
                fixings: FixingState) -> BookValue
held_book_derivatives(state: CurveState, contracts: tuple[ResolvedContract, ...],
                      fixings: FixingState) -> PriceDerivatives
static_explain(center: Calibration, shocked: Calibration,
               contracts: tuple[ResolvedContract, ...], fixings: FixingState) -> StaticExplain
roll_fixing_cash_bridge(states: BridgeStates, contracts: tuple[ResolvedContract, ...],
                       old_fixings: FixingState, new_fixings: FixingState,
                       cash_accumulation: Callable[[date, date], float]) -> PnlBridge
~~~

BridgeStatesへresolved t1表現・旧knots・regrid stateを明示する。cash_accumulation(payment_date,t1)は指定担保口座の無次元累積factorで、policy IDと元入力をprotocolへ保存する。旧/実fixingsのCFを同じpolicyでt1へ換算し、資金調達ledgerを無断追加しない。具体的factorのfixtureはTask1/4で独立照合する。

## Task 1 — 全入力と日付/CFを固定する

**Files:** fixtures.json、_multicurve_cashflows.py、test_multicurve_cashflows.py。  
**Deliverable:** 日付・CFの独立oracleと、全12quote/held contractsのresolved入力。

- [ ] 原RESEARCH §9/§13から全family IDを列挙する。主12quoteのabstract-forward flag、D/P3/P6 node dates、truth θ、held quantities/coupons、各reset/payment、公表timestampをすべて数値で記録する。未確定欄のままpilotへ入らない。
- [ ] 主caseとdate/publication/欠損validationを分け、future holdoutの全入力も結果を見る前に固定する。生成器は決定論的で、MC/RNGを持ち込まない。
- [ ] RED: modified-following/EOM/stub、leap/day count、lookback/shift/lockout、前/後publication、公開後欠損、ex-payment/known fixing freeze。Decimalの原rates・weightsでCFを独立計算する。

~~~python
weights = [Decimal(x) / Decimal(360) for x in (4, 1, 1, 1, 4)]
rates = tuple(map(Decimal, ("0.03", "0.031", "0.029", "0.032", "0.028")))
expected = Decimal(10_000_000) * (math.prod(1 + r*w for r, w in zip(rates, weights)) - 1)
assert realized_coupon == pytest.approx(float(expected), abs=1e-7, rel=1e-12)
~~~

- [ ] REDを保存→最小calendar/CF実装→scoped GREEN/ruff。欠損をforecastで補う誤器が失敗することを確認。
- [ ] 全日付/CFの保存入出力を一度roundtripし、index/docstring参照を追加する。将来commit: “RB-F07 multicurve: resolve dated cashflows and fixing states”。

**Command:** Pのrootから、後述共通環境でpytest -q johnhull/hullkit/tests/test_multicurve_cashflows.py。

## Task 2 — 独立参照と12quote exact較正

**Files:** _multicurve_quotes.py、test_multicurve_quotes.py、reference_methods.py。Task1後。  
**Deliverable:** 元12quoteのfull block Jとtruth復元、全diagnostics。独立参照は独自CF/schedule/brentでmain helperを呼ばない。

- [ ] RED: 原2curve4quote closed form、独立brent、主12quote、negative-rate DF>1、quote/PV residual、同一kernel zero/logDF、入力順permutation、別補間差。
- [ ] 12unknown/12quoteをD→P3→P6の依存を保持してNewton/analyticJでsolve。全residual/J/scaled SVD/rank/response/backward residual/iterations/warningsを返す。singular/非収束を部分successにしない。
- [ ] 0-start abstract forwardとdated known-resetのzero-Jを対比。未公開はforecast、公表後既知rowは主較正へ残せない。coverage外を黙って外挿しない。
- [ ] near-redundant/information-thinケースを独立solverとも比較し、oracle自身の非収束も保存する。
- [ ] scoped RED/GREEN/ruff、Task1回帰。将来commit: “RB-F07 multicurve: calibrate coupled discount and projection curves”。

**独立性確認:** reference_methodsのAST import一覧に新4 multicurve modulesが無いことを研究testで確認。現行quote_dml参照をそのまま新12quote oracleと名付けない。

## Task 3 — 全quoteリスクとsecond IFT

**Files:** _multicurve_risk.py、test_multicurve_risk.py、reference_methods.py。Task2後。  
**Deliverable:** 全144要素Hと元全12bucket gradient、単位・直接依存・非対角伝播。

- [ ] RED: 4quoteの原PV/g/cross-gamma、12quote全再較正bump、direct Vq fixture、PV residual Fq≠−I、coordinate/permutation、LS/GN負例とactive-set左右微分。
- [ ] J solve/随伴と全second-IFT項を実装。12単位方向＋66混合方向からfull Hを作り、対称性とD–P3/D–P6/P3–P6全blockを検算。原Jを凍結して他curveを固定するwrong controlも比較。
- [ ] 独立参照は全market再較正289点/hでHを求める。候補hは2/1/.5/.25/.125bp、全sweep誤差を保存し、安定域無しはunverified。4quote probeの近似Hを厳密解析oracleと呼ばない。
- [ ] g/Hは通貨/bp・bp²、price-point oracleは別単位。下例を全12/144要素と各productへ実施する。

~~~python
np.testing.assert_allclose(primary_g, independent_g, atol=2e-6, rtol=1e-8)
np.testing.assert_allclose(primary_h, independent_h, atol=1e-5, rtol=1e-6)
np.testing.assert_allclose(primary_h, primary_h.T, atol=1e-5, rtol=1e-6)
~~~

- [ ] 収束率はnon-roundoff域とleading coefficient退化を区別する。hが小さいほど成功すると固定しない。
- [ ] scoped RED/GREEN/ruff、Task2回帰。将来commit: “RB-F07 multicurve: compute full quote gradient and calibration curvature”。

## Task 4 — 保有bookと四項P&L bridge

**Files:** _multicurve_pnl.py、test_multicurve_pnl.py、fixtures.json。Task3後。  
**Deliverable:** 全product/bookのstatic R1/R2と、Vr/Vf/Vg/V1/C0/Cf四項を独立再算出できるraw。

- [ ] RED: fixedcoupon保持、payer/receiver、book=sum products、singlecurve極限、basis向き、term-end/advance distinction、paymentcash一回計上。
- [ ] exact rollはabsolute旧knots+t1 anchor、同kernelのDF ratioを保つ。t1新tenor表現への移行を別state/evaluatorとして保存。new horizon欠落/rank不足はunknownにする。
- [ ] 原reviewのzero-market-move regrid反例を固定。q1=qg、market項≈0でもrepresentation項≠0を検算する。

~~~python
assert sum(bridge.components) == pytest.approx(
    bridge.V1 - bridge.V0 + bridge.Cf, abs=cf_atol, rel=1e-12)
assert bridge.market_move == pytest.approx(np.zeros(12), abs=1e-14)
assert bridge.market_component == pytest.approx(0.0, abs=pv_atol)
assert abs(bridge.representation_component) > pv_atol
~~~

- [ ] publication/reset/payment/expiryをmarket smooth slopeから分離。knownfixingをforecastへ戻す、shock coupon reset、diagonal-only H、second calibration省略等の原wrong controlsを全て保存する。
- [ ] scoped RED/GREEN/ruff、Task1–3回帰。source/数式の独立レビューを受け、具体的指摘を修正してfreezeへ進む。将来commit: “RB-F07 multicurve: explain roll fixing representation and market P&L”。

## Task 5 — pilot、whole-path費用、protocol freeze

**Files:** protocol.json、pilot.py、runner.py、costs.py、research/tests。Task4/source数学レビュー後。  
**Deliverable:** 主12quoteのactual rank/coverage/H精度、最大caseの実RSS/保存量/費用と事前固定protocol。

- [ ] protocolは主/validation/fresh/scaling roster、全部のdirection vectors/両符号/move、day/fixing variants、h sweep、product IDs、元denominatorsを列挙・計数。全quote12/24・商品1/10/100の出力数も明示する。
- [ ] measurement前priorを保存。原候補CPU-only pilot300s/main1800sは**未承認の行政cap**であり予測ではない。RSS/各volume reserve/最大expanded byte/同時retentionも測定前に決め、capacityが無ければ実行を止める。
- [ ] pilotは全12quote/全H/最大date productの実演算＋write/read/checkを含む。小N/小quoteへの縮小でfull-size費用を代用しない。primaryと独立参照の費用を別に残す。
- [ ] inclusive wall/CPU/peakRSS、date resolve、truth quote construction、較正/J/H/factorization、PV/risk、mixed-bumps、IO、保存checkerのcall counts/時計を記録。cold/warm共通factorization reuse回数を保存。inclusive parentとcomponent/expense aliasを二重加算しない。
- [ ] RED: 末尾ID欠落/重複、wrong unit、NaN/unknown保存、capとsource defect区別、clock/denominator/expense alias改変。case単位でraw解放する検査を加える。
- [ ] pilot全rowsから元precision候補の到達性を確認。未知/非収束を保存し、閾値を変更する場合before/after・理由・採否影響を独立レビューする。結果を通すために緩めない。
- [ ] source/inputs/protocol/全roster/prior/controlsをfreezeし、独立resource判断を得る。main/fresh/check/両CAS各copy/復元を含むwhole費用・容量を予算化する。行政cap総和をruntimeへ読み替えない。
- [ ] 将来commit: “RB-F07 multicurve: freeze protocol and measured resource prior”。pilot/source checksだけで研究完了としない。

## Task 6 — 本実験、全保存値検算、fresh、両復元

**Files:** runner.py、checker.py、build_reference.py、costs.py、manifest.json、research/tests。Task5 freeze後。  
**Deliverable:** 元全予定caseのfull raw・数値検算・全費用。結果はcase単位で保存し、summaryに金融arrayを重複保持しない。

候補CLI（実装時にそのまま一致させる）:

~~~text
pilot.py --protocol protocol.json --prior prior.json --output pilot/
runner.py --protocol protocol.json --prior prior.json --output main/ [--fresh]
checker.py --protocol protocol.json --artifact main/ --output-check checks/
build_reference.py --artifact main/ --checks checks/ --output reference/
~~~

- [ ] immutable case JSON+NPZ、共有fixture参照、source/environment/control/全attempt receiptを保存。全caseの未実行/失敗/unknownを明示する。自分の最後のreceipt tailは閉鎖まではunknown。
- [ ] mainを実行。calibration/price/gradient/H、full revaluation全shock、全bridge state/CF、独立値/残余/denominators、warnings/failed outputsを保存する。formal caseを通った小subsetへ置換しない。
- [ ] saved checkerは全planned ID/最後/全fieldを読み、元quote/CFから独立に較正・risk・全H・bridge・費用を再算出する。数値不一致/不足は拒否または元unknownを保持し、digestだけで合格にしない。
- [ ] freshは同じfreezeと事前固定fresh rosterで新演算し、全数値を独立参照と比較。warm memoを新独立contextへ渡さない。
- [ ] ADR0004既存store APIでC/Fへ保存。各store1copyとWSL原本/復元の同時占有を別々に確認。C/Fそれぞれ別rootへ復元し、元root不存在の条件で全数値/原費用checkerを実行する。
- [ ] 意味あるtamper: 最後caseのquote/fixing/CF/H/bridge/expenseを個別変更→対応検算が落ちる。physical descriptor/shape/source改変も拒否。missing fieldを0へ埋めない。
- [ ] 全results.statusとplanned件数一致、failed/unknown/scaling/fresh各分母、speed precision-equal比較を固定。保存検算の資源も実測し、bounded=容量保証と呼ばない。
- [ ] 将来commit: “RB-F07 multicurve: save complete study and independent replay evidence”。

## Task 7 — 教材、独立研究レビュー、採否・統合

**Files:** build_notebook.py、multicurve_risk.ipynb、RESULTS.md、REVIEW.md、README/index/ROADMAP。Task6後。  
**Deliverable:** 研究完了を読者が再確認できる教材と採否。mainのunknown数値を未解決のままacceptedへ昇格しない。

- [ ] artifact-only3必須図: 全quote→curve→product risk heatmap、R1/R2 move-size、四項bridge。必要なら悪条件/全費用4図目。notebookから較正/計測/network/GPUを起動しない。
- [ ] fresh notebook実行・nbformat・PNG目視。単位、全失敗/分母、0分母undefined、悪化stress、wrong controls、支持範囲を図と文章へ含める。
- [ ] 独立研究レビューはsource数学・main全結果・saved/fresh/C/F・費用・教材を対象にする。採否は計算成立/二次残余/速度を別々に記録し、不採用/限定/保留も残す。
- [ ] private全module/symbolをMODEL_INDEXへ登録、docstrings/index testsと影響を受けたrates/rfr/swaps/P&L/quote-risk testsを実行。全suiteは章/研究完了時に1回、要求範囲を実記録し“workspace全て”と誇張しない。
- [ ] tracked release、台帳check-artifactsで本編306件不変を確認。Book/portal全再buildやD1全再撮影は依存が変わった場合だけ必要範囲で行う。
- [ ] 同じ最終変更単位でREADME/ROADMAP/backlogへdone/current/pendingと実採否を反映。将来commit: “RB-F07 multicurve: document research adoption and artifact teaching”。

## 実行環境と対象検証（将来コマンド）

Pのrepo rootから共有venv・対象checkoutを使う。uvをmember内で走らせて別venvを作らない。

~~~bash
export PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/johnhull/report:$PWD"
PY=/home/kazumasa/projects/.venv/bin/python
"$PY" -m pytest -q johnhull/hullkit/tests/test_multicurve_cashflows.py
"$PY" -m pytest -q johnhull/hullkit/tests/test_multicurve_quotes.py
"$PY" -m pytest -q johnhull/hullkit/tests/test_multicurve_risk.py
"$PY" -m pytest -q johnhull/hullkit/tests/test_multicurve_pnl.py
"$PY" -m pytest -q johnhull/research/RB-F07/multicurve/tests/test_multicurve_research.py
"$PY" -m ruff check johnhull/hullkit/src/hullkit/_multicurve_cashflows.py \
  johnhull/hullkit/src/hullkit/_multicurve_quotes.py \
  johnhull/hullkit/src/hullkit/_multicurve_risk.py \
  johnhull/hullkit/src/hullkit/_multicurve_pnl.py johnhull/research/RB-F07/multicurve
"$PY" -m ruff format --check johnhull/hullkit/src/hullkit/_multicurve_cashflows.py \
  johnhull/hullkit/src/hullkit/_multicurve_quotes.py \
  johnhull/hullkit/src/hullkit/_multicurve_risk.py \
  johnhull/hullkit/src/hullkit/_multicurve_pnl.py johnhull/research/RB-F07/multicurve
~~~

初期工程では存在する変更済みファイルだけを上の明示一覧から選ぶ。新規module testsと必要な既存対象を工程ごとに選び、同じ全suiteを毎工程繰り返さない。本ターンに上記は未実行。

## 依存・未確定・自己点検

| 残る具体的未確定 | 解消する作業 / 次工程へ渡す証拠 |
|---|---|
| 全12quote日付・truth・held/fresh/scaling numeric roster/全件数 | Task1/5の入力表とpure count。元familyを減らさない |
| 既知reset/publicationのrank/支持範囲、絡むstress | Task2/5 actual residual/J/SVD、独立solver結果 |
| 全H安定h・stress二次悪化・degenerate方向 | Task3/5/6の全sweep/全shock/status。未確認Hをpassにしない |
| t1表示・cash policyの具体的入力 | Task1/4でBridgeStates/累積factorの独立日付oracleを一致させ、Vr/Vf/Vg/V1/cashを全保存 |
| 資源/所要時間/whole bytes、C/F各volume容量 | Task5元最大geometry＋Task6全pathの計測/事前予算。5分/30分は予測ではない |
| source数学/全数値/採否 | Task4/5/7独立判断。source-only/資源判断をfinancial acceptanceへ転用しない |

自己点検: 原12quote/全144H/全crossblock/四項bridge/全product/date/±shock/wrong controls/全分母を保持。5つのReview FocusはTask1–6の正例・負例に対応する。主source実装、独立reference、保存/復元checker、artifact教材は分担可能だが、Task1→2→3→4→5→6→7の依存を守る。同時研究1本と#9終了条件を優先する。

この2候補文書の記述確認は実装/source独立承認ではない。#10の工数・金融精度・RAM/容量は未測定。実測済み4quote spikeや#9の時間を#10 ETAへ転用しない。
