# Task 6 main 実行器：独立最終レビュー

2026-10-10。判定：**approved（固定した3ファイル限定）**。未解決 Critical 0 / Important 0。

## 対象

| ファイル | SHA-256 |
|---|---|
| johnhull/research/RB-F04/dynamic_hedging/run_main.py | 4517f766e435ac34feafb89301442839e1d797ec646e87aaae4cf7e31fb168bd |
| johnhull/research/RB-F04/dynamic_hedging/check_main.py | ada38ad09270ce4468f33840dba48b83ad74f1922a388103f65ec76b4d3a8134 |
| deep_hedge_price/tests/test_dynamic_hedging_main.py | 0e7368d0a50fc508e42c8b6e13763bf8592376ddd5870d985b768005e6595bbb |

コード、Git、正本docsは変更していない。追加したのは本prefixの独立レビュー証跡のみ。unknown xaaは読んでいない。全3suiteは実行していない。

## 独立検査

- 専用pytest：**72 passed / 30.60秒**。Ruff check、format --check：3ファイルPASS。
- 固定3sourceのbefore/afterが一致。
- **自己整合receiptを作り直した24反例をすべて拒否**。元source/rawや作者の証跡は変更していない。
- 元36 evaluation rawを読み直し、396 records / 132 summariesを保持。元のlevel192/768交換反例は数値resultを変えずに主比較を変えていたが、修正後はmain_statistics入口とsaved checkerで拒否。
- minimum outcome rosterの正例：numeric3groups各24 comparison IDs、各side独立3 producer refs、selected Greek/band frequency96 slots、Q両model×3 reserved streamsの6 slotsを保持。
- N32 / 2 chunks / high cache axes / analytic16blocksの実risk workerを呼び、不変artifactへ保存・復元後にsaved-only checkerを実行。全8 Greek/band×model×universeでcash、fee、mask、target、qualificationがfull/view同値。元quote、root、16block rawはchunksに保持。
- 上の独立source-unitではRNG、CF/PDE、MC/oracle、teacher、trainingの入口を禁止。saved-only段階ではproducerも禁止。全used source identityのbefore/afterも一致。
- append-only追加resume費用2件を実clock差から検査し、元target receipt/bytes不変、source/input/clock/path/sequenceの不一致を拒否。最終receipt自己書込みはNone/pendingを保持。

## レビューで検出し、修正後に閉じた問題

| 問題 | 修正と独立確認 |
|---|---|
| evaluation外側のgenerator/seed_slot/level/universeがjob IDに未結合 | checkerの全loopとmain_statistics入口で照合。元immutable label-swap反例を再実行し拒否。 |
| 同じQ jobを全5 refinement groupsへ使い、必須比較をmetadataだけで埋められた | outcome groupsをdisjointにし、typed operation/group・元24 numeric comparison IDs・3 producer streams・元N4096・frequency96/Q6の最低rosterを事前検査。actual outcome metadataもplanに結合。元1Q全groups反例、欠落/重複stream/減らしたN/別operationを拒否。 |
| 成功workerの既知計時がouter clockと結び付かず、削除/None化でもcap照合を回避できた | main_market/main_risk/Q/bump_risk、evaluation result、delegated chunked_workerの既知current wall/CPU観測を必須・有限にしouter以内へ拘束。overrun/statusも再計算。独立削除・None化・CPU過大・完了overrun反例を拒否。historical producer費用を再課金しない。 |

作者のRED→GREEN記録も読み、独立反例は別prefix/新しいimmutable artifactsへ保存した。

## 元契約の保持

- 元main18 cases×2U×11 cells=396、3 levels×3 test seeds、44 cells、N32768 research選択、全12fit＋4×14baseline closureの後にtestを開く境界を保持。
- full execution_source_identityの全10 phase＋closure registryをsource/input/frozen/rawへ結合。MAIN_SINK_SOURCE.mdの古いsink承認SHAを現sourceの代用にしない。
- risk chunk 256MiB、prior soft cap、原分母/未処理paths/failed rawを保持。solver/source exceptionはunclosed source defectとして拒否し、hold/0/safeへ変えない。
- actual cash/liquidation/fee/P&LとQ/数値精度maskを再計算し、finite-only表示と主支持を分ける。d/r、Bonferroni .05/8、各family3init IUTを保持。
- numerical envelopesは固定weights・独立reserved streamsによるempirical diagnostics。最高teacher N65536の比較は元DESIGN §7.5の独立reserved stream/grid例外を許し、同Nをhigher-Nと呼ばない。
- exact resumeの元job/stat/main receiptと費用は変更せず、新load/replay/check/serialization仕事を別receiptへ追記。未測定を0へ変えない。

## 承認の限界

**正式pilot plan、source freeze、正式main金融実験、all-cost完了、金融精度達成を承認したものではない。**

- outcome guardはroot承認の最低roster境界。Qの元18states・全date・conditional one-step・empty claim・bin等の全scopeとproducer DAG/cap coverageは正式plan/raw gateで別検査が必要。
- 3 SDE levelsのmainを保存するが、primary level768の24 NN comparisonsへ最低numeric envelopeを事前拘束。その他levelの支持は独立envelopeがない場合unknown。
- 独立N32 source-unitのteacherはanalytic fixtureでoriginal teacher NはNone。97,843,532 bytesの保存量、worker開始後3.6936秒はそのunitの測定で、正式N32768の保存量/RAM/全wall/教師精度ではない。
- 型・数値算術・費用矛盾のguardを確認した。clock receiptをmetadataだけから実世界の時間として暗号的に認証したとは主張しない。
- full original pilot/freeze/396 finance/fresh/両CAS/full suites/3図・notebook/final金融reviewは別gateとして未完。

## 証跡

最終判定：
- task-6-main-independent-final-review-decision.json
- task-6-main-independent-final-review-fixed-sources-2.json
- task-6-main-independent-final-review-scoped-tests-2.txt
- task-6-main-independent-final-review-lint-2.txt
- task-6-main-independent-final-review-guard-unit.py / -guard-unit-results.json
- task-6-main-independent-final-review-guard-unit/（新しい24反例と追加費用ledger）
- task-6-main-independent-final-review-final-saved-source-unit.py
- task-6-main-independent-final-review-final-saved-source-unit-results.json
- task-6-main-independent-final-review-final-saved-source-unit/（不変raw）

元反例：
- -metadata-counterexample.py/json/txt と -metadata-unit/
- -plan-group-counterexample.py/json/txt

撤回された初回3SHA（run_main7b465cea、test0bced90c）は承認対象から除外。初回53PASSログとsource-unit原rawは保持。初回unitは全算術assertion後の結果JSON書出しがndarray serializationで失敗しexit1だったため、最終sourceで新artifactへ実行し直し、成功した証跡だけを最終判定に使用した。
