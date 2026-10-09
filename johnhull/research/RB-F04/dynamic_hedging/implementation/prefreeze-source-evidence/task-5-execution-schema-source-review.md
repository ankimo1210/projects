# A execution-schema independent source review

更新UTC: 2026-10-09T16:36:01.485358+00:00

## 判定 / 承認範囲

**限定 metadata-binding source を承認。未解決 blocker 0。**

対象は deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_execution.py と専用 tests だけ。author の stable final SHA を待ち、実コードと最終 tests を読み、独立に再実行・semantic resealing probe・detach probeを実施した。source/Git/canonical docsは変更していない。

この承認は、宣言された metadata の整合・原義務の集合・SHA/receiptによる結合・局所的分類拒否の source に限る。実金融 checker の原全N/path/status/SE/Greek/Q/refinement再計算、CF/PDE精度、実 source bytes/transitive closure、reviewerの独立性/真正性、事前計画時刻、実費用計時、正式 pilot、実freeze/main readiness/main統合は承認対象外。module自体は金融solverや source registry reader ではない。

root/runner の execution_source_identity/provider 改修（reference_methods/run_freshを含む実closure）もこのsource承認では代替できない。実registry/budget/raw checker/独立review証跡が成立して初めて実freezeを作れる。

## Source bindings

source SHA256:
473d1352fbcebd2c1255e093e1d4757274c7e51a04add5d6f00c58850c229494

dedicated tests SHA256:
27b5eaca7dec461bb2f4d2360dd263c58df254d82ff41a11ef8620fbdba3a508

strict v1 protocol SHA256（HEADとbyte不変）:
5f63d5871cdf6871f83fb08bf8f403b556cf6730c40430c0fc391f5da29bda0f

approved proposal SHA256:
3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b

旧 candidate_protocol/study_roster/main_seedsを変更せず、original_candidate/original_rosterの完全な snapshotを新候補へ格納。旧 strict v1 freeze/assert guard にprojectionしてqualifiedと見せる経路はない。新 schemaは rb-f04-execution-freeze-v1.1、original_v1_financial_qualification=not_claimed。

## 原義務 / closed records

- 元37 quotes +18 states×2 models +44 tiny cells +4 original init11 fits =121 pilot cases。kind/identity/gates・全ID/元N/plan・per-case checker receiptと独立review decisionを保持。
- 元24 monthly teacher groups +10 refinement groups +6 Q groups +2 frequency +9 other obligations =51 required attempts。各 plan/元N/expense/evidence/measurement/reason/receiptとdecisionを必須にする。
- 元candidateの全gates/seeds/train8192/validation2048/512 updates/300s/全12fits/3inits/3test seeds/192,384,768/44cells×9=396 slotsを変更しない。
- current expense scopeは全case/groupおよびcode/math/pilot review、CAS/serialization/saved check/domain selection等の共通scopeを含み、current wall/cpu/overrunをmeasured complete/failedとする。歴史的unknown timingを別historyで保持。
- cap closureには事前plan、到達したmetric/consumption、元bound、wallならactual expense measurement、independent prior budget decisionとのdigest結合を要求。source/integrity unresolved issueがある場合や未到達capをclosedとしない。
- solver/source failureをvalidated structural rejectionに付け替えることを拒否。ill_conditionedは元κgateを超えるmeasurementが必要。その他 structural kindの実root/bound/support数学的妥当性はcallerのraw checkerの責務。
- 全原test N=8192/16384/32768のordered projectionsと数値gateを保持。qualifiedがあれば最小qualified N、なければunavailableを明示したresearch N32768。unknownをqualifiedへ投影しない。
- assert_execution_readyは全12 fit attempts（original slots/N/updates/cap/checkpoint/reason/evidence）と全4 validation closures×14 original Greek/band candidatesを要求。all failedのselected band/baselineはNone＋reason。width0/no-hedge/safeへのfallbackを拒否。
- defined fixed domain と金融qualifiedを分離。全24 date/model domain index geometry、4+ contiguous nodes、事前rule、evidenceを結合。domainの実finite/SE/Greek資格や原全node保持はB/rawcheckerに委譲。
- freezeはcomponents全体をJSONでdetachし、case/group/source/domain/selection/review/pilot/closureへdigestで結合する。新しいfreeze digestを再計算しても、current contractとの比較によりstale sourceやv1 qualified projectionを拒否。

## レビューで見つけた点（修正済み F1）

初読時、measured_precision_failure が「全 declared gates を測定済み・全部PASS」でも unknown＋reasonだけでclosedとなる局所的な分類矛盾を見つけ、author/rootへ連絡した。authorがTDD REDで DID NOT RAISE を再現し、not-passed original gate（失敗値又は理由付きNone）が必要なよう修正した。

authorの元RED: task-5-execution-schema-implementation-classification-red.txt
RED stdout SHA256: 7422cea23438b7bde5bb1f2d604a7e85b3db6c58f7ed07d275403e7085b03ede

独立 preliminary snapshot/probe は修正後の拒否を実行したもので、修正前の独立実行REDだと主張しない。その source/stdout/receiptも保存してある。最終 independent57 probesでは、全gatesPASS precision-failureはreject、実際のgate failureはunknownでcloseする。

raw reported SE=0 と valid uncertainty measure は区別する。unknown_underresolvedのゼロ事象については、raw_measurementsの original N4096 / 原SE0 / primitive status / rare_event_count0 を残し、gate measurement=None＋具体的underresolution理由＋receiptでunknownを保ったままclosedとできる。最終sourceはraw0を削除・zeroへの修復・qualified強制しない。これはmetadata挙動の証明であって、実教師の精度証明ではない。

## 独立検証

- author stable final SHAで scoped **50 passed in 0.99s**、subprocess wall 1.1879314380003052s。
- 対象source/testの ruff check / format --check PASS。
- semantic/adversarial **57 probes（9 accept /48 reject）**すべて期待どおり。receipt/digestを再計算して局所semantic拒否へ到達させた（stale receipt検査を除く）。
- original candidate/gates/seeds変更、121/51欠落/重複/identity変更、state/teacher N削減、solver-as-structural、Q unknownのfalse global qualification、ordered precision欠落・誤ったN、未到達/事後/未承認/費用未計測cap、current costs欠落、history除去、domain幾何/事前選択、source依存欠落、12fit/4validation/14candidate欠落、fit updates/cap/N変更、fallback、不適格finite-score、早期test opening、stale receipt、再署名v1-qualified projectionを拒否。
- raw-zero unknown caseの原raw stats/N保持とunknown拒否truth tableを確認。
- source/domains/selection/current costs/history/candidate gatesの6componentsをcallerが変更してもdetached freezeは不変。元unknown historyのtiming=Noneも維持。
- financial RNG data draw入口をfail-on-callにし、**calls0**。旧v1の固定SeedSequence namespaceの生成はstream openingと扱わず、seed値は元candidateで保持。
- probe wall 0.9717006660011975s。全試料はsynthetic metadata fixture。実金融experiment、12fits学習、正式pilot/main/fresh/CAS、全suiteを実行していない。

## 次工程と限界

実source registry/loader、raw金融checker、budget/cap artifact、全原pilot/refinement、費用計時、独立reviewを新schemaへ正しく結ぶ必要がある。checker名とSHAのformat/整合をAが確認しても、その実行や証跡の真正性をAだけで保証できない。receiptは数値精度証明の代替ではない。

ignored SDDに最終source/tests、独立suite/Ruff、57probesのscript/results、detachment/provenance/最初の修正後probe、command/returncode/SHA/wall receiptsを保存。金銭fees/token chargesはtool outputに存在せず未計測。
