# Dynamic hedging prefreeze revision proposal

2026-10-10。**実装前候補・独立設計レビュー待ち。旧v1 source/candidate/freezeを保持、新main未開封。**

## 根拠と維持する目標

[独立監査](preflight-diagnostics/task-5-freeze-feasibility-audit.md)でstate15.Hは3幅κ≈.808>.25、元1cent/s_v=.04条件でN/grid改善だけでは不適格が消えないと確認。Cv非ゼロでIFTは局所的に存在する。閾値や原caseを変更しない。

月次Asian/Heston/local/固定callの全44cells×3test seeds×192/384/768、12fits、独立premium/Q/teacher/position/P&L refinement、全費用、saved/fresh/CAS、3図/notebook/full suites/レビュー/main統合を完遂する。negative feasibility/tiny/静的比較だけでdoneにしない。

## A. execution readiness / financial qualificationの分離

- 旧 `candidate_protocol/freeze_contract/assert_main_ready` はstrict v1として保持。新private入口と別schema `rb-f04-execution-freeze-v1.1`・artifact namespaceを追加。force/allow_unqualified/内部false-qualified projectionは使わない。
- 新candidateは元candidate全体・revision・source closure・pilot原証跡・独立reviewへbind。元SE/error/κ/Q/refinement閾値、原37quotes/18states×2/全N・seed・全44cells/12fitsを維持。
- readinessは全元計算・拒否を評価/保存できることの認証。financial qualificationは別truth tableでunknown/not-qualifiedを保持し、v1 precision-qualified達成とは記さない。
- 全元caseをwithin-envelope、独立確認済み構造的拒否、測定済み精度未達、事前cap到達失敗へ分類。原数値/誤差/理由/first failure日/費用を保存。solver failureを構造的拒否へ付け替えない。
- source defect、source/原分母/乱数隔離の不一致、required pilot attempt未完、integrity未検証はreadinessを拒否。
- N1024だけで正式pilotを閉じない。元N/grid/refinement/独立oracle義務を試行し、事前cap又は独立承認した予算/教師revisionで閉じる。次jobのbyte/path-step/費用を保存。
- 元費用のscope/実測/未測定/failedを保持。歴史的unknownを0へ変更せずspeedup/payback支持を禁止。必要な現行phase計時を省略しない。
- smallest-qualified test Nがあれば元規則を使用。なければtest前に固定したresearch N=32768（元上限）・precision_selection=unavailableを新schemaへ明示。金融精度PASSとしない。
- 12fitsは8192train/2048validation/512updates/300s capと全closed selectionsを維持。baseline全失敗はNone＋理由、width0/no-hedge/hold/safeへ救済しない。
- 原Nの1pathでもinvalid/unqualifiedなら対応policy/baseline/family支持はunknown。finite-onlyはdescriptive。NNの算術結果と強baseline比較支持を区別する。

## B. 日付固定finite Cartesian評価domain

[測定](preflight-diagnostics/task-5-cache-domain-report.md)で全108groupsのfull-ready curveは0。4date/model条件にATMを含むfinite box候補が存在した。

- 原axes/range[0,24]・全node/status/NaN/16blocks/原Nを保存。zero/nearest/既知auxで未知値を補完しない。
- 日付/モデルごと一つのCartesian boxをpilot streamsで選び、main前にbounds/選択規則を固定。local t0は専用sheet。test成績/latent v/future drawを使わない。
- declared box上の従来not-a-knot tensor cubic、全block共通固定linear operatorから価格/全Greeksを計算。同じC2面を使用し、元global面とは別revisionと明記。
- box外/必要node不適格は全原N unknown。支持拡張/case除去/精度認定と扱わない。
- callの原common full-domainで全root・一意性・条件を検査してから、取得stateのAsian patch支持を検査する。patchでcall fit bounds/root集合を狭めず、原fit roots/residual/statusを保存。patch外はAsian/risk側unknown。
- exact linear/settled branchは従来どおりpatch/state fit不要。C1/C2は各固定box内部と境界での内側微分についてのみ確認し、unknown gapを越える連続性を主張しない。
- 各date/modelのboxは軸の連続node index範囲を明示し、各cubic軸4点以上、選択rule/全元node status/provenanceを固定。適格boxがなければそのdateはunknown。候補boxをSE/Greek精度qualifiedと扱わない。
- query毎4点cubicはd jumpを生むため不採用。Hermiteは次候補として今回sourceを広げない。
- full-domain一致、遠方/内部NaN、N/block保持、local chain/t0、境界C1、bounds/saved replayをTDD・独立レビュー。selected oracle/SE/grid/bias gateは別実測。

## 実装順

1. この候補を独立設計レビュー。全deliverablesとunknown/拒否truth tableを照合。
2. Bのprivate source/TDD/レビュー。旧default/public APIを保持。
3. Aの別schema/validator/TDD/レビュー。v1拒否テスト・旧artifactを保持。
4. 本物pilot・限定grid/N/refinementを実行し全attempt/費用を閉じて独立review。
5. readiness固定後、全main/fresh/CAS/図/受入。金融支持/不採用理由を別assessment。

新candidate/source/pilot/readinessは現時点で未承認・未固定。β最適化/QMC、別instrument/第二quote、安全方策、API/依存追加は範囲外。
