# Task 5 formal pilot / freeze feasibility audit

2026-10-10。Read-only audit。原設計・source・Gitは変更していない。計算は保存済み独立CF値/教師SEに対する算術のみ。正式pilot/主実験の承認ではない。

## 結論

1. **現行v1のqualified pilot / freezeはN追加・格子細分化だけでは達成不可能。** 必須元state15.Heston（t=11/12,S80,v.02）の独立Cv=0.30937758からκQ=0.808074>.25。3幅bumpすべてで同じ拒否。原κ閾値を満たすには|Cv|>=1が必要であり、これはMC不足/価格格子誤差の障害と異なる。
2. **negative feasibilityだけで研究完了にはできない。** 元DESIGN §1の全market/policy/seed/level/attempt、cash/費用/Q診断、独立fresh/CAS/3図/notebook/reviewを残す。
3. 元v1のfreezeを緩めず、**別schemaのprefreeze revisionでexecution readinessとfinancial qualificationを分ける**案は、上記全deliverablesを維持する限り研究目的と整合する。v1数値精度契約を満たしたという結論にはならない。

## 一次証拠と契約

- DESIGN.md:13–20：全roster実行又は理由付き失敗、unknown/不支持も成果。ただし静的shock/欧州call/旧価格比較で動的研究を代替不可。
- DESIGN.md:150–155：κQ=.01/|Ctheta*s_theta|>.25は未解決、near-zero denominator/不確実性を別検査。
- DESIGN.md:222–232,380–392：18元states、N上限65536、未達はmain前revision、failed状態除外による最小N選択不可、safe policy追加なし。
- DESIGN.md:309–363：全原N unknown判定、12fits/44cells/3seeds/3levels、費用/freeze/fresh/saved replay/3図を維持。
- _dynamic_hedging_protocol.py:289–395：fixed original v1 candidateとの同一性、qualified flag、全gates worstcase有限実測、exact元counts、独立code/math/pilot reviewを要求。failed/unmeasuredをqualified化して通す余地はない。
- pilot/selected-calls/jacobian.json：18元state、3幅独立CF、state15のcondition .808074、原積分receipt保存。
- pilot/selected-calls/refined/selected-calls.json：state15.H status unknown / reason ill_conditioned、独立CFのQ=.0017373254975669161。latent vでteacherを救済していない。
- pilot/teacher-n1024/preflight.json / REPORT.md：36slots中35計算、全unknown、SE同時6、underresolved5/fitunknown1。

## 実行readiness revision案（承認対象）

### A. 元v1を保全する

- 既存candidate.json / freeze_contract /旧artifactを変えず、新schema例 `rb-f04-execution-freeze-v1.1` と別のcandidate/assessment/artifact directoryを作る。
- 新protocolが元v1 candidate＋revision内容＋全pilot原始証拠＋source closure＋独立レビューへbindする。`formal_v1_financial_qualification=unknown/not_qualified` を残す。
- v1 main guardへ `force` / `allow_unqualified` を付けたり、verificationフラグだけで既存qualified gateを通過させない。v1の拒否テストを維持し、新revisionの独立入口/semantic checkerをTDD・レビューする。
- test streams未開封の現在に固定。main後のsource/teacher/N/閾値/selection変更は必ず新revision、旧費用/失敗/resultsを保持。

### B. 新readinessが認証する対象

`execution_readiness=approved_for_full_roster_evaluation` は、価格/リスクが正しいという認証ではなく、**全元条件について計算できる範囲と拒否を正しく評価・保存する**認証。

必須条件：
1. 元37quotes・18states×2モデル・全tiny44cells・元4tinyNN等のrequired pilot rosterを省かない。原始N/seed/state/date/model IDs、source/driver/geometry/費用・保存境界が照合済み。
2. 各元caseに `measured_within_envelope` / `validated_structural_rejection` / `measured_precision_failure` / `attempt_failed_at_declared_cap` を付け、原数値・uncertainty・reason・費用・未測定項目を別に保存。金融qualificationのstatusは別。
3. structural rejectionは独立参照が現行ルールの拒否を確認したものに限る。state15.Hを記録し、fit/state/target unknownを保持。solver正常終了だけでは精度certificationを与えない。
4. finite-support、κ、Ctheta誤差、非一意root、教師underresolutionの**事前validity envelope**を観測可能量（t,S,Q,A,n）と原fit定義で固定。評価時のG latent v、payoff/future draw、test成績でenvelopeを作らない。
5. within-envelope教師SE/error義務は従来のNprefix/grid/refinement・上限・work capに従って実測/試行する。単にN1024でbadと分かったことを「formal pilot完了」にしない。上限到達又は独立レビュー済みの予算/教師revisionによる試行終了を証拠付きで閉じる。
6. 一方で「全上限の全直積を機械的に実行」は元設計にもない。各次jobのpath-step/byte/costを事前保存し、原義務を満たす適切なrefinement又はdeclared cap終了を選ぶ。
7. 未測定を0誤差にしない。精度unqualifiedだが算術定義されるtarget/P&Lと、算術自体がinvalidなfit/target/P&Lを分ける。後者をhold/zero/nearestへ救済しない。
8. source/code/math/pilot reviewがすべてapproved、未解決source defect/未検証integrityなし。source bugと数値手法の不採用・構造的拒否は別分類。重要なバグ、検証器の未実装、required pilot attempt未完、source-binding不一致、原分母消去、RNG/leakage、費用不明scopeはreadinessを拒否。
9. 各required独立oracle/fresh精度作業は実施又は事前の合法reason/capを保存。unknownをレビュー済み拒否へコピーするだけではreadinessにならない。
10. semantic checkerが拒否case混入、元N保持、unknown伝播、原truth表、inactive callの厳密0 exposure、linear claimの厳密branchを独立再算出。dtype/seed/hashだけでfinancial validationを置き換えない。

### C. Financial qualificationは元ルールのまま

- priceSE .03、hSSE .002/hQSE .005、Asian price .05/position .01、call .001/CS .002/scaledCtheta .01、κ .25、Q drift/refinement gateは保持。
- envelope外拒否は数値精度PASSに数えず、36元slotsのfinancial qualificationはunknown/not_qualified。coverage母数を17/18や35/36へ書き換えない。
- main全原Nの1pathでもinvalid/unqualifiedならそのpolicy/baseline/family全体はunknown。finite-only曲線/統計はdescriptive、採否・CI・speedupを支持しない。
- all-failed baseline/bandは選択None＋原理由。width0/no hedgeへの暗黙置換不可。NN全3init IUT、paired d/r閾値・numerical envelopes・original bootstrap分母を維持。
- MSE/価格/モデル差が識別されなかった研究結果とsource実装が壊れたことを混同しない。raw算術結果があっても金融支持を付けない。

### D. 全mainの契約

- 12fits（G2×U2×init3）、512updates/300s cap、train8192/validation2048、全attemptとclosed selectionを維持。全fit失敗も理由・weights/events/費用を保存して12枠を閉じる。
- 評価44cells × 3test seeds × 192/384/768、同original path IDs/N、主12hedges/月次12fixings、固定K100/T1.25 call、費用・終端決済を維持。
- κ rejectionを理由にGreek/band slotsを削除しない。target不適格の各pathに最初のfailure date/reason/rawstateを保存し、以降P&L unknown。成功pathだけで比較しない。
- NN/no hedgeはそれ自身のmarket/price/source/error qualificationを適用。Greek baseline invalidだけでNN P&Lを消す必要はないが、強baselineとの改善family支持はunknown。
- 原testN選定がall-failed pilotで未定義なら `smallest qualified` を捏造しない。別revisionに事前の固定research-N規則（例：原candidate最大32768）と `precision_selection=unavailable` を明示、財務精度支持はunknownのまま。N規則はレビューを通し、test後に変更しない。
- premium/oracle/Q diagnostics、同holdingゼロ費用counterfactual、全費用、saved replay、独立fresh、C/F別復元semantic、3図/notebook、最終受入/full suites/main統合を削らない。
- acceptanceは「full-roster research evaluationの完全性」と「financial support/nonadoption」を別assessmentにする。元v1 precision-qualified research達成というラベルは禁止。

## 主な反論・限界

1. **「精度未達のmainを開けば元guardの骨抜き」**：その危険はある。対策はv1を残してv1.1を別契約にし、独立したreadiness、全required pilot試行、元SE/error判断、原44cells/全N unknownを義務化する。単なる全unknown artifact/未測定だらけのtestは拒否。
2. **「expected rejectionを後からsuccess扱いするcherry-picking」**：state15はtest前の独立CFで既知、ルールと母数を固定。rejectはfinancial unknownであり合格数ではない。反例のvalue/reasonとsource/費用を保持する。
3. **「数学的IFTはCv非ゼロなのにκ>閾値は不可能性ではない」**：正しい。本監査は全quote-map不可能性を主張しない。**この1cent・s_v=.04・κ .25という元実装契約の不達**を示している。δQを変更/θをlogへ変更/κを緩めて元gate PASSにすることは提案しない。
4. **「全main unknownなら研究価値が弱い」**：その可能性は明示する。原実験をすべて実行し、どのモデル/方策/観測領域でcalibration・teacher・market pricesが拒否されたかを分析すれば元問いに対する実証結果になる。成功を保証しない。別instrument/rolling ATM/第二quote/regularized安全方策は将来revisionで、元主実験の代用品にしない。
5. **「precision failureをreadinessで閉じれば教師改善を省略できる」**：不可。元N/grid上限・required独立比較・費用/上限の試行を満たすか、fullmainを保持した教師/予算revisionを事前レビューする。現在のN1024 evidence単独ではまだreadyとは言えない。
6. **「全費用/独立fresh/図/受入まで保つとETAは変わらない」**：正しい。今回のrevisionは不可能なgateを繰り返す時間を除き、残りの実仕事は削らない。多数source files/保存receiptを作るだけで研究完了にしない。

## 他案の比較

| 案 | 元主実験との整合 | 判定 |
|---|---|---|
| N65536まで増やす/格子細分化だけ | MC/grid精度には有効だがκは不変 | freeze解決にならない |
| κ threshold/1cent bumpを変更、log-v座標で低conditionを表示 | 元市場quote/単位の基準を変える | 不採用 |
| state15を除く・latent vでteacherを再開 | 元case/observable情報を破る | 不採用 |
| 失敗報告だけでdone、mainをtiny/静的で代用 | 元deliverablesを満たさない | 不採用 |
| 新instrument/第二quote/rolling ATM/regularized救済policy | 有望だが元contract/universeを拡張する | 別将来revision、元主実験を保持 |
| 別schemaのreadiness + financial qualification、fullmain | 元研究問い/全deliverablesを保持、元v1不達を隠さない | 推奨、独立設計/code/pilot承認後のみ |

## 時間に関係する教師SE診断

同じ直接bump推定量のiid N^(-1/2)を仮に延長すると、Heston worst hSのN必要量は約275,482、hQは約69,351で元上限65536を超える。これは16block小標本・有限bumpの診断でありproduction cubic derivativeの必要N予測/精度保証ではない。状態感応度推定とunderresolutionを改良するか予算/教師を正式にrevisionする必要があることを示す。最大Nにすれば全部通るという所要時間見積もりは支持されない。

全numeric/source bindings・3幅κ・SE外挿は隣接task-5-freeze-feasibility-audit.json。canonical source/docs/Git変更なし。

## 追加：具体schemaとvalidator責務（root確認用）

### Freeze receiptの例（**未作成、設計案**）

```json
{
  "schema": "rb-f04-execution-freeze-v1.1",
  "original_v1_candidate_binding": "<original-v1-candidate-provenance>",
  "revision": {
    "changes": ["execution_readiness_separated_from_financial_qualification"],
    "forbidden": ["changed_financial_thresholds", "removed_original_cases", "latent_state_rescue", "safe_or_hold_fallback", "post_test_selection"]
  },
  "execution_readiness": {
    "status": "approved_for_full_roster_evaluation",
    "code_review": "approved",
    "math_review": "approved",
    "pilot_execution_review": "approved",
    "unresolved_source_or_integrity_issues": [],
    "required_pilot_attempts_closed": true,
    "all_original_ids_and_denominators_preserved": true
  },
  "financial_qualification": {
    "status": "unknown",
    "original_v1_precision_contract": "not_achieved",
    "unknown_or_failed_original_case_ids": ["state15.heston"],
    "unchanged_gates": "<exact original candidate.gates>",
    "primary_decision_rule": "any_original_required_path_or_baseline_unqualified_implies_unknown"
  },
  "pilot_case_outcomes": "<every original case, measured values/errors/status/reason/cost/evidence>",
  "selected_teacher_n_and_grid": "<pre-test fixed, real N/grid plus precision status>",
  "test_n_selection": "<explicit pre-test rule and qualification; unavailable is never smallest-qualified>",
  "source_and_raw_evidence_bindings": "<exact closures, original bytes and numerical checker receipts>",
  "main_execution_obligations": "<unchanged full roster + source/refinements/fresh/CAS/costs/plots/acceptance>"
}
```

このschema例のbooleanは証拠からvalidatorが算出する結果であり、callerがTrueを書くだけでは通らない。金融値は許容差つき再計算、digestはsource/artifact同一性用。

### Validatorごとの責務

| validator | 必須検査 | 拒否する例 |
|---|---|---|
| revision scope validator | 元candidateのclaim/market/universe/費用/閾値/N候補/rosterとの exact logical identity、許可したprocedural fieldsだけ変更 | κ=.5への変更、state15削除、rolling callに変更、512未達をcompleted |
| raw pilot checker | 原37quotes、18×2state、44tinycells、4元tinyNN等の全IDs・原N・SE/error/条件数・cost・attemptを原配列から再計算 | maxを成功casesだけで計算、unmeasuredを0、underresolved zeroSEを合格 |
| envelope / rejection checker | 観測可能S/Q/A/nのfit、独立Ctheta/referenceerror、root uniqueness/bounds、元κ規則、reject伝播 | actual latent v代入、rejectionをprice/Greek PASS、solverが停止しただけでstructural rejection |
| source / integrity validator | 実import closure/env/source一致、独立code/math review、saved reconstruction、source defectなし、required production generators/teacher/refinement/fresh source実装 | main consumerだけの未実装runner、checker未実装、Important bug、欠損NPZ、original count消去 |
| execution-readiness validator | 全required pilot obligationsを実施又は事前規約に基づく理由付きattempt/拒否/capとして閉じたか、レビュー未解決0、未知scope一覧 | original phaseを単に飛ばす、N1024診断だけで十分と宣言、未知errorをreview flagで承認 |
| selection / test-open validator | source+revision+pilot閉鎖、全12fit/validation attempt閉鎖・実weightsをpayloadへbind、test loader前に独立再検算、事前N/width/checkpoint固定 | test supplied weightsがclosed weightsと異なる、失敗bandをwidth0へ置換、test後にN追加 |
| main saved checker | 44×3seeds×3levels=396元evaluation slots、same IDs/N、rawstate/price/target/holdings/cash/gains/fees/payoff/qual masks/初回failure、12fitsのhistory | partial successful seedsだけ保存、P&L nonfiniteを除いてMSE、未知targetのhold、inactive exposure以外のprice0代入 |
| decision validator | 原Nでcell/family/global primary qualification、8NN families全3init IUT、paired d/rと同bootstrap/数値envelope、全unknown含む | finite-only CIでprimary support、original fitunknownをfalsequalified、全方法のknown arithmeticだけでglobal qualified |
| final acceptance validator | required Q/empty claim/one-step+binned drift、premium、独立SDE/teacher/grid/refinement、fresh、C/F別復元semantic、全費用、3図/notebook/full suites/final review/main integration | negative-feasibilityだけでdone、静的/欧州call/tinyをfullmainと呼ぶ、速度の精度条件を省く |

### 低Qの拒否とsolver失敗を区別する

元state15.HではQ=.0017373、独立3幅のCv≈.30938。rootはresidual≈1.46e-14まで解かれているが、元κ規則によりrefusal。これは **root未収束ではなく、元精度規則のexpected ill-conditioning rejection**。
- 「C_v=0なので数学的IFTが存在しない」とは呼ばない。C_vは非ゼロで数学的局所IFT自体は定義できる。
- 元価格・quote bumpスケールで許容されたrisk同定ができないという数値/運用条件の拒否を、精度errorと区別して記録する。
- Actual solver failure（maxiter/nonfinite/no-root/nonunique）は別reason。独立参照とsource検証で合法なsupport failureとsource bugを区別できない間はreadiness拒否。
- 数値未測定の状態を「たぶんexpected rejection」と推定してmainを開かない。
- 金融qualification unknownのままsourceの正しいfail-closed動作を認証する。quote/Greek/κ rejectionをqualifiedの測定値へprojectしない。

### 元実行条件：一切免除しない

| 範囲 | 元条件・実施義務 |
|---|---|
| claim/資産 | 月次12fixings arithmetic Asian K100/T1、S0除外、U1 stock/cash、U2+固定K100/T1.25 call |
| markets/models | G Heston/local、M Heston/local、observablesのみで同Qにrefit、current actual varianceをMの救済にしない |
| accounting | r.03/q0、stock.0005/call.005、初期/中間/終端費用、claim1回・terminalcall売却1回、独立gain式 |
| market/main | 全G、192/384/768、3testseeds、元testN/IDs、全44cells=396seed-level slots、全原failure/cost |
| train/validation | G2×U2×init11/29/47=12fits、train8192/G・validation2048/G、512updates/batch256/Adam.003/cap300s、全weights/events/scaler/未達 |
| teachers | 実Heston/localfield、12restart caches、16sharedIIDblocks、原N候補1024/4096/16384/65536・coarse/high、source/driver/boundary/support/SE/error/unknownを全記録 |
| pilot | 元37initialquotes、18selectedstates×2M、全tiny44cells・4tinyNN、call/Asian/Greeks/IFT/価格面/refinement/費用のrequired measurement/理由付きrefusal |
| Q/独立参照 | mandatory empty claim・bounded controls・one-step/state-bin gains、reserved premium65536/1536、独立conditional MC/CRN・SDE/teacher/grid/envelopes・selected fresh |
| statistics | 全original N、全3init IUT、paired d/r、Bonferroni .05/8、same saved block indices、ESindividual、finite-only descriptive |
| evidence | immutable metadata/rawarrays/protocol/source、C/F別復元＋semantic、cold/pilot/train/main/check/fresh/archive/plot全expense scopes |
| completion | saved-only3図/notebook実行と目視、関連3suite1回、独立final review、研究assessment、release/main integration/push |

source主実装、full teachers/refinements/fresh/費用をreadiness revisionで免除しない。expected rejectionの元caseはattempt/原N/原理由を明示して閉じるだけであり、元mainの残りを小さなsuccessful subsetへ変更しない。
