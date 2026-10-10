# Task 6 main：canonical producer参照の限定追加レビュー

2026-10-10。**approved（下記3SHA限定）**。未解決 Critical 0 / Important 0。

| 対象 | SHA-256 |
|---|---|
| run_main.py | 4956903ea0b6f25a2a556fc1e0745b2d98d253ff3d26731e6cf55e5fc253cbc4 |
| check_main.py | ada38ad09270ce4468f33840dba48b83ad74f1922a388103f65ec76b4d3a8134 |
| deep_hedge_price/tests/test_dynamic_hedging_main.py | f24564687cbfd54501dbba7e2318b52b96c3808e3461a8e9e57bcde42e06faad |

旧4517f766/ada38ad0/0e7368d0への承認・72tests/24反例/N32保存unitは歴史として保持。作者のformal DAG dry-runで、prior helperの$job表記が実resolverのjob表記と違う接続問題を発見。独立レビューの最初の正例も$jobを使い、actual dependency resolverを経由していなかった。追加レビューでは実resolverと接続して確認した。canonical-ref-followup.jsonの保留を、この固定source判定で解消する。

## 修復の範囲

- main._prior_three_stream_recordsは実canonical {job} / {job,path:[]} のwhole rawだけを受け付ける。
- declared cell_pair/paired_pnl producerとそのmarket_pairへ結合し、両方の元N4096、元3 reserved seedsの順序、異なる3 producer IDsを確認。
- inline paired_pnlではrecord自身とshared_marketの元N4096、role/refinement、順序付きseedを確認。
- validate_refinement_outcomesへdeclared rowsを渡す1callを変更。
- check_mainのSHAは不変。旧run_mainの完全なsource copyをSHA4517f766として検証し、新旧ASTを独立比較した。変更されたtop-level nodesは上記2関数だけで、finance/cost/resume/stat等の他全nodesは不変。

## 独立確認

- 接続専用pytest **14 passed / 66 deselected / 1.34秒**。
- Ruff check、format --check：3files PASS。固定3source before/after一致。
- 実pilot._dependency_ids → pilot._resolve → prior guardを、6 canonical producer refsとそのmarket dependenciesで確認。解決前と解決後の双方が元ordered streams/N4096で通る。
- canonical whole-path empty表記も実resolverで確認。
- **新しい自己整合receipt付き18反例を全拒否**：重複/未宣言producer、$job、partial raw、producer/marketの元N削減、異なるoperation、wrong seed、missing market、inline record Nのみ削減/欠落、market N/role、seed順序、kind不一致。
- RNGと金融dispatcherを禁止し、純粋なreference/metadata接続だけを実行。
- 作者全80scoped PASS31.26秒のlogも確認。独立に全80を再実行したとは記さない。

正式planの全date/state/Q scope、producer DAGの金融算術、正式pilot/freezing/396 finance/full wall/allcost/fresh/CAS/受入は別gateとして未承認。この追加レビューは上記接続問題だけを扱い、元raw・証跡・コード・Git・正本docsは変更していない。

## 証跡

- task-6-main-independent-final-review-canonical-unit.py
- task-6-main-independent-final-review-canonical-results.json
- task-6-main-independent-final-review-canonical-unit/（新18反例）
- task-6-main-independent-final-review-canonical-ast-scope.json
- task-6-main-independent-final-review-canonical-{tests,unit,ruff,format}.txt
- task-6-main-independent-final-review-canonical-decision.json
- task-6-main-independent-final-review-canonical-manifest.json
