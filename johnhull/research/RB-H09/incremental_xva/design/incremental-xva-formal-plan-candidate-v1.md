# #11 Incremental XVA, IM and Capital — Implementation Plan Candidate v1

> **For agentic workers:** 実行時は superpowers:subagent-driven-development または superpowers:executing-plans を使用する。現在は文書候補の作成だけで、以下の実装・計算・承認手続きを実行していない。

**Goal:** 同じbook前後とhedge bundleのCVA/DVA・VM/MPOR・非SIMM IM・FCA/FBA/MVA/KVAをprivate計算し、独立参照、96主seed-cells、全原始成果、費用、fresh/両復元、教材、採否まで揃える。

**Architecture:** pure private hullkit modules＋研究専用runner/checker/lesson。共通driver、set別ledger、counterparty-wise資本、paired path差。原数値をcell/chunkごとに保存・検査し、bounded reportは原配列referenceを保持する。

**Tech Stack:** 既存Python/NumPy/SciPy、stdlib Decimal/Fraction/datetime、既存artifact/evidence_storeとnotebook構成。torch・production dependencies・公開__init__への追加なし。

**Spec:** [正式設計候補](incremental-xva-formal-design-candidate-v1.md)、[既存調査](../../../johnhull/research/RB-H09/incremental_xva/RESEARCH.md)。
**Status:** 2026-10-11 / **未承認・未実装の候補**。設計候補・計画候補の独立確認後、既存研究順序#9→#10→#11に従う。旧saved-only承認や別研究の実行予算を#11へ流用しない。

## Global Constraints

- belowの全pathはworkspace root相対。H=`johnhull/hullkit/src/hullkit`、T=`johnhull/hullkit/tests`、R=`johnhull/research/RB-H09/incremental_xva`。新APIは提案であり存在を偽らない。
- before/after/standalone/bundle、主32cells×3seeds、independent validation、原全path/IM/capital/cash/失敗分母を保持。実行停止はpartial、source/math不一致はdefect、unknownを0/PASSにしない。
- skillのRED→最小private実装→GREEN→関係scoped確認を各taskで行う。数学の比較はapprox/allclose/SE、SHAは原source/input/物理byteの由来だけ。
- 日次VM calendar・イベント順序をrefinementで変えない。本文数値の未対応規約を都合よく補完しない。
- Source/計画の変更は新versionとproducer/verifier別由来を残す。実main/復元/CAS/root guardは準備済みの原条件と実予算を実行前固定した後に開始する。
- 全suite/Book・portalビルド/画面確認は研究phase末にまとめる。節単位の新受入scriptのコピーやmain受入台帳更新は作らない。
- 現在のsource85、#9旧raw/guard/入力、既存docsの編集は本候補作成の対象外。以下は後日の実装path指定。

## Review Focus

第一にlegal setとfunding/capitalの別境界、posted/received IM、first-to-default、停止時刻、clean discountの一貫性を確認する。第二に独立式、conditional dimension/root coverage、元rosterの完走と精度、費用の包含/未知、最後のpathまでのsaved/fresh/両restoreを確認する。schema/byte検査だけで金融qualificationを付けない。

## Task 1 — 原典・terms・元rosterを固定する

**Files:** create H/`_incremental_xva_contracts.py`, T/`test_incremental_xva_contracts.py`, R/`study_plan.json`, R/`sources.json`。modify R/`README.md`, R/`RESEARCH.md`は設計採用時の状態/リンクだけ。preserve `design/initial-research-draft.md`とレビュー対象原草稿。

**Consumes:** 設計§3–8、固定CRE52/MAR50/CRE32、CRE99部分参照、既存BusinessCalendar/leg_schedule。**Produces:** frozen terms、axis/ID/event roster、版/係数/単位の由来。

- [ ] 原典画像式・係数・maturity/NICA/RC/add-on/BA-CVAのformula-to-clause表をsources.jsonへ作り独立転記レビュー。CRE99の対象外swaption/EURを除いた全EADを「公式再現」と呼ばない。
- [ ] RED: wrong set/CSA/counterparty参照、duplicate IDs、MPOR/返還event漏れ、negative notional/時間/無効probabilityを拒否するfixture。32cell×3seedとc separate-set validation IDが同時に存在することを検査。
- [ ] StudyTermsはcurrency/N_ref/calendar/market/credit/IM/capital/cost/rosterを保持。TradeTermsは方向・日付・schedule・rate/notional・各map、CSAはTH/MTA/rounding/lag/MPOR/segregation/reuse/返還lag、CostPolicyはspread/cK/phi/stop policyを持つ。event_gridはrefinementを変えても原call/fixing/payment/default/closeout/返還を包含。
- [ ] GREEN: min math/coverage validation、独立dated schedule列挙との比較。opaque object/datetime等の網羅拒否は不要。
- [ ] scoped pytest `uv run --no-sync pytest johnhull/hullkit/tests/test_incremental_xva_contracts.py -q`、変更fileのRuff/format。計画と原典未解決項目をreviewして次taskへ。

## Task 2 — Clean IRS、Q state/discount、realized fixing

**Files:** create H/`_incremental_xva_market.py`, T/`test_incremental_xva_market.py`; extend H/`_incremental_xva_references.py`とT/`test_incremental_xva_references.py`のclean/Gaussian部分。

**Consumes:** terms、caller-provided normals (path,interval,2)。**Produces:** state/integrated-rate、D、known fixing、contractual coupons、clean marksと独立Gaussian参照。

- [ ] RED: clean_irsと独立FRA/coupon-sumが一致、coupon跨ぎで既知fixingを使う、zero vol bond tower、negative rateを許す。無条件forwardでpast fixingを置換したnegative fixtureを用意。
- [ ] hw_driverは既存FlatHWのexact rank-two momentからcaller normalsを変換する。NumPy RNGはrunnerに限定、計算APIに内部seed/RNGを埋めない。
- [ ] clean_irs(trade,time,state,known_fixings,model)はFuture coupon・seasoned coupon・ex/cum dividendを別欄とし、t0 par rateとc hedge DV01を独立coupon sums/bond derivativeで固定する。
- [ ] 直接OU kernelをSciPy quadで積分したconditional discountとpayment-measure identityを比較。単なる同じbond helperの二重呼出しにしない。
- [ ] GREEN/scoped: 新market/references＋既存 `test_numeraire_hw_state.py`, `test_nonstandard_legs.py` の影響対象のみ。全workspace suiteなし。

## Task 3 — 法的cash/VM ledgerとIM口座の骨格

**Files:** create H/`_incremental_xva_margin.py`, T/`test_incremental_xva_margin.py`; referencesにenumerated_cashを追加。

**Consumes:** event axes、marks、fixture IM、terms。**Produces:** VM call/pending/settled、segregated Ip/Ir、remuneration、free cash/返還、account stop axes。このtaskのfixture IMを最終IM算定器と呼ばない。

- [ ] RED: 2state/4pathのDecimal/Fraction台帳でfixing→coupon→call→settle→defaultを列挙。pending VMを控除する不正例、TH/MTA/rounding境界、同一counterparty別setの相殺を検出。
- [ ] reusable/nonreuse received VMを区別、received IMをfree cashへ入れない。F0からposted IM/Kを除外し、OIS carryとexcess costの再帰feed backを分ける。
- [ ] main(c)のsame-setとseparate-set対照でmarks/IM inputの法的mapを独立に固定。別setで旧setが変わることを拒否。
- [ ] GREEN: total cash conservation、perspective reversal、原call/settlement/返還eventsとaccount masks。scoped newmargin/referencesを実行。

## Task 4 — First-to-default/MPOR closeout

**Files:** create H/`_incremental_xva_credit.py`, T/`test_incremental_xva_credit.py`; referencesのcredit integralを追加。

**Consumes:** same driver、VM/IM ledger、共有tau_B/各tau_C/default uniforms、terms。**Produces:** M_gap/C_gap/IpIr_gap、LGD loss、first-default indicators、return cash。

- [ ] RED: M_gap=100,C_gap=80,Ir=15ではEC=5、R=.4のunsecured loss=3。posted Ip=20はreturnであってECをさらに20減らさない。own-perspective reversal、IM過剰返還、default-before-coupon、満期直前closeout延長も列挙。
- [ ] 原default uniformsとpiecewise inverse hazardからtauを生成し、before/after/全setで同じ銀行tau_Bを使う。closeout eventは原経路上の必要state/integralを保持。
- [ ] GBM forward unilateral解析EEとhazard quadrature、lambda_C S_C S_Bのbilateral densityと直接default-time paired MCを比較する。MCは固定seed/6SE（sample独立unit）とdeterministic ref誤差を別に報告。
- [ ] conditional past/current/closeout Gaussian coordinatesを列挙し、rank/order/tailを参照reportへ保存。低次元anchorと一般historyを区別する。
- [ ] GREEN/scoped: 新credit/references＋既存 `test_xva_foundations_credit.py`, `test_xva_foundations_incremental.py`。独立数学レビューでnetting/IM/FTDを確認。

## Task 5 — Conditional full-revaluation IM

**Files:** extend H/`_incremental_xva_margin.py`, H/`_incremental_xva_references.py`; create T/`test_incremental_xva_im.py`。

**Consumes:** clean revaluation、dated horizon/history、P_IM kernel、terms。**Produces:** Ip/Ir、全CDF/root brackets、Gaussian rank、quantile/ES/refinement/tail diagnostics。

- [ ] RED: linear normalのq99/ESとposted/received signs、完全reverse book IM0、eta0 point mass。非単調sum-of-bondsの複数rootを1rootだけで済ませる実装を拒否するfixture。
- [ ] 独立normal式と1D Gaussian quadrature/CDF inversionを先に実装し、conditional_imがrank=1の場合だけそのcoreを使用する。root bracket/tail区間の質量とq left-ruleを保存。
- [ ] coupon-crossingでrank>1なら原座標の独立cubature/nested iid対照へ進む。1Dへ偽って縮約しない。M=256/1024/4096は対照/refinementに使い、各inner/outer再生成replicateの誤差を残す。
- [ ] stress×1.5、固定fat-tail mixture、ES/proxyのmethod labelsを検証。同じhedgeを別setへ置くと旧set IM不変・new IM非負、same-set便益は実測結果としてのみ表示。
- [ ] GREEN/scoped IM+margin+関係references。tail/root/rank不成立はunresolvedで、精度不足を「計算成功」に変えない。

## Task 6 — SA-CCR subsetとreduced BA-CVA

**Files:** create H/`_incremental_xva_capital.py`, T/`test_incremental_xva_capital.py`; referencesにscalar_capital_referenceを追加。

**Consumes:** 元book/set/CSA/marks/IM、synthetic RW/ratioとfixed原典coefficients。**Produces:** RC,NICA,supervisory quantities,bucket/add-on/multiplier/EAD,RWA,SCVA,aggregate K。

- [ ] RED: NICAにsegregated posted IMを混入させない、VM-only Cとeligible IM込みregulatory Cを分離。RC/MTA/MPOR/floor/cap/3bucket境界とzero add-onを独立scalar例で検査。
- [ ] 原典のUSD IRS trade-level参照を部分数値再現として記録。対象外instrument/currency/複数CSAはunsupported理由を出す。
- [ ] non-IMM maturity、SCVAのcounterparty-wide set和、全counterpartyのreduced BA-CVA集計を独立式で検査。2相手で単独Kの単純和と異なること、dealer hを抜いた場合の不一致を確認する。
- [ ] K_CVAへの余分.08係数、MC PFEによるadd-on置換、matured/empty setの残存capitalを拒否。K total>=0とsigned ΔKを保存。
- [ ] GREEN/scoped capital/references。capital formula転記・selected scopeの独立金融レビュー完了後に統合する。

## Task 7 — Cash costs、paired increment、固定台帳の統合

**Files:** create H/`_incremental_xva_costs.py`, T/`test_incremental_xva_costs.py`; referencesのconstant_cost_reference追加。

**Consumes:** market/ledger/capital/account masks。**Produces:** component別全path integrals、before/after差/SE/bpとinternal transfer値。

- [ ] RED: discount1・2年・F0=100/sb=.01/Ip=50/IM spread=.02/K=100/cK=.05ならFCA2,MVA2,KVA10、FBA/COLVA0。別stop timesの積分とpiecewise hazard closed integralを独立再計算。
- [ ] received/posted VMのCOLVA符号、zero trade/hazard/spread/eta、negative incrementとnonnegative totalの各limitを検査。
- [ ] paired_incrementはafter−beforeをpathごとに作り独立unitのsd/sqrt(N)を返す。before/after SEを独立合成するfixtureは誤差が異なることを確認する。
- [ ] phi>0のvalidationはreserve投資勘定を明示してtotal照合、FVA/KVAへの便益二重控除を拒否。own default後のrunning cost停止とIM返還cash保存を分離。
- [ ] GREEN/scoped newcosts＋既存 `test_xva_foundations_funding.py`, `test_xva_foundations_incremental.py`。半再現簡約条件の対応表と独立total式をreviewする。

## Task 8 — 元全条件のrunner、保存checker、費用producer

**Files:** create R/`run_study.py`, R/`check_study.py`, T/`test_incremental_xva_artifacts.py`。既存source/APIはimportして再利用し、#9の固定source authorityをコピーしない。

**Consumes:** study_plan、terms、caller seedbank、計算modules、actual budget。**Produces:** immutable per-cell raw/receipt、metadata-only index、bounded数値report、実cost forest。

- [ ] RED: 2cell小fixtureで全count/末尾path/terms/source/seed/ledger改変、missing raw/extra ID/失敗消去、alias/result writable共有の拒否。保存floatはtol/equal_nanで再検算しdigestで判定しない。
- [ ] runner CLI候補は `--plan <path> --phase pilot|main --output <freshdir> --budget <actualref>`。check CLI候補は `--input <closedroot> --plan <original> --output <freshdir>`。flagsだけでfinance/source/root authorityを作らない。実input/source/receipt/output freshnessをbindする。
- [ ] normal/default banksはrunnerで1回生成保存。数値checkerは全original Nと全components/IM/capital途中量を原配列から1cell/chunkずつ検算・解放。元path digestとinput/source/物理byte認証を維持し、generic全graph deep copy/hydrateを採らない。
- [ ] saved/fresh/restoresは各empty検証context。phase内再利用を導入するなら初回全数値検算済みの同producer/raw/mathargs/source/全physical byteだけ、別法的mapやfresh context共有は不可。
- [ ] cost producerは実ns時計/domain/RSS/bytes/failed/overrun/parent inclusionを記録し、full child終了までの実scopeと自分のpost-stop pending adminを区別。pendingでcharged total=Noneを保持する小fixture。
- [ ] GREEN/scoped artifacts＋private tests。旧literal/artifact API互換を必要範囲だけ確認する。実計算予算はまだ承認しない。

## Task 9 — 4bundle pilot、精度と全工程予算の実固定

**Files:** update R/`study_plan.json`; create R/`PILOT.md`, R/`budget.json`, R/`DECISION.md`のpilot部分。大rawは既存CAS、Gitには小manifest/receipt。

- [ ] 事前pilot rosterに4bundle、独立limits/同set・別set対照、N/M/refinement候補を全登録。seedはroot entropyとdeterministic derivationを原manifestへ固定し結果からseedを選ばない。
- [ ] reference/IM rank/quantile・capital境界/discount/default/MPOR/time誤差を分解して測定。全trial/failure/unsupported/refinementを残す。
- [ ] 同一全payloadのwrite/read/saved replay最大shapeも実測し、individual RSS/wall/3volume容量の候補とunknownを分ける。compressed率や小N speedを最大N保証へ外挿しない。
- [ ] total0.5bp、CVA/MVA/KVA0.1bpを満たすN/grid/order/toleranceと全validationの実予算をmain前固定。無理なら未解決bias・費用と改訂理由を明示しrootへ具体案を渡す。主32cellsを削減しない。
- [ ] pilotの独立数学/金融/予算レビューを受けてmain-readyを記録。元proposalと修正歴史を保持。現時点の所要時間は未測定。

## Task 10 — 32cells×3seeds主実験と採否

**Files:** update R/`DECISION.md`, R/`README.md`; immutable original/validation artifacts、cost receipts、trial indexを保存。

- [ ] 32×3=96seed-cellsを主条件、validationを別rosterで完走。各before/after/standalone/bundleを全required成分で再算定し、符号やerrorを結果から選別しない。
- [ ] fresh independent再実行は原N/grid/terms/seeds/methodを維持し、approx/SEと元failureの照合をする。保存checksumだけで済ませない。
- [ ] exact/quadrature/pairedMC/従来EE-simpleFVA/fullIM-Gaussianproxyを比較。polynomial LSはreferenceが通った後のchallengerで、holdoutportfolio/schedule/TH/market/MPORと全fit費用を固定。
- [ ] accuracyと準備＋query費用のbreak-evenを同error budgetで比較。高速化不採用でも完了可能。費用未閉鎖ならall-in speed claimを保留する。
- [ ] 独立採否reportはsynthetic条件内の採用/条件付き/不採用を記載し、市場優位・規制適合へ一般化しない。

## Task 11 — 両vaultの単独semantic復元とartifact-only教材

**Files:** create R/`lesson.py`, R/`incremental_xva.ipynb`, T/`test_incremental_xva_lesson.py`; update R/`README.md`, `johnhull/MODEL_INDEX.md`, `johnhull/CONTENTS_INDEX.md`, `johnhull/ROADMAP.md`。Book/portalに採用する場合は既存release wiringを最小変更。

- [ ] RED: lessonは保存成果がmissing/改変なら拒否し、solver/RNG/training/networkを呼べないfixture。3図は原arrayからtotal/SE/units/rosterを再計算する。
- [ ] primary Cとmirror Fへ同じclosed manifestでCAS保存。各vaultを単独でfresh restore dirへ復元し、原全blob/source/input/receiptを認証→full数値checker→3図/notebook renderを別contextで実行。
- [ ] source85/#9 rawを#11 rawに付替えない。newverifier使用時はoriginal producerとverifierを別bindingで残す。rootC/Fいずれか欠けた状態を完了にしない。
- [ ] 教材は①standalone/増分/bundle成分とSE、②time口座と資本、③error/all-in expense/TH・MPOR。unknown/unsupported/制限を図/本文に残す。
- [ ] scoped lesson/artifacts tests、必要なrelease/notebook/Book・portal画面を実確認。全figureを同じ保存rawから作る。

## Task 12 — phase末検証・最終レビュー・統合

**Files:** final update R/`DECISION.md`, R/`README.md`, `johnhull/ROADMAP.md`, MODEL/CONTENTS_INDEX。accepted evidenceへのリンクだけ、原ledger件数は変更しない。

- [ ] 影響するhullkit/deep_hedge_price/johnhull-reportの既存phase末suiteを適用範囲に従って1回実行。changed PythonのRuff/format、release tracked-artifacts gatesを実行。過去greenを新sourceの根拠にしない。
- [ ] 独立reviewでformula/sign/legal/accountstop/IMrank/capital/全roster/数値/費用/fresh/両restore/教材/採否を確認。未解決は具体riskと原証跡で保存し、closed statusを捏造しない。
- [ ] done/current/pendingをROADMAPへ、MODEL_INDEXにprivate modulesと実検証範囲を登録。実装済み・未検証・研究完了を区別する。
- [ ] root所有のcommit/push/main統合を実受入結果に従って実施。この候補ではGit/CAS/受入操作をしない。

## 五つの静かな誤りと対応

| risk | 失敗を検出するtask |
|---|---|
| samecounterpartyの別set IM/VM相殺、received IMのfree cash化 | Task3/5の別set・segregated台帳 |
| stochastic Dとloss独立平均、first-to-default省略、posted IM二重控除 | Task2/4のGaussian/FTD/EC=5 anchor |
| rank>1/複数rootを1D単根へ縮約しIM tailを過小評価 | Task5のrank/CDF/root/pointmass/nested対照 |
| CCRとCVA資本の混同、KCVA再.08、dealer capital漏れ | Task6の1/2counterparty・dealer・subset負例 |
| 全raw hydrate/OOM、末尾失敗消去、prefix費用昇格・vault片側欠落 | Task8/9/11のchunk/末尾/timing pending/独立両復元 |

## 仕様の安定境界と開始条件

#10はdated clean/fixingとcurve provenanceを接続可能な形で完了させる。#11 v1はflat/zero-basis単一OISとして独立実装できるが、同時の重い研究runを増やさず既存順序を守る。#10の12quote/object shapesを確定前に仮APIへ依存しない。後日の多曲線XVAは新model/measure/source/誤差revisionで扱う。

設計と計画候補のreview、Task1のformula/terms固定後にprivate実装へ進む。実pilot/mainにはそのsource/元rosterと実測に基づく原予算・root固定が必要。今回は候補文書のみで、上記checkboxはすべて未完了。source/金融/速度/容量/規制qualificationはunknown。

## 自点検

設計§1–14をTask1–12に対応付け、必要な7private modulesと研究runner/checker/教材、独立source/reference/費用/採否/復元を保持した。実装APIの入出力とrank/原axesを指定し、存在しないsymbolを既存APIとして記述していない。routineなcalendar/policy/roster候補は設計に記載、main前に固定。未測定予算や未取得画像数値は偽の固定値で埋めず、担当taskと開始前の検証条件を指定した。
