# SDD ledger — plan: johnhull/docs/superpowers/plans/2026-10-03-section-28-2-factor-risk.md

Pre-flight: Task1 API/参照→Task2四図/数値hash→Task3登録/16状態→Task4同じKEYS/26D1/27件。3関数/4keys/235セル/親6Aの境界は全taskで一致。
Ruling: 承認済みP3の節受入工程をM27へ継続し、設計の再承認待ちを置かない — 本人の継続実装指示と新§28.2の下調べに従う — 誤りなら対象節・API範囲の見直し。
Task1 RED: 34 failed because hullkit.factor_risk was absent.
Task1 GREEN: API34、参照/数値7、独立builder30、計71 PASS。2--check PASS、4保存改変+4API変異拒否。
Task 1: complete (commits be9fdb4..754ecdd, tests: python -m pytest johnhull/hullkit/tests/test_factor_risk.py johnhull/hullkit/tests/test_factor_risk_reference.py johnhull/hullkit/tests/test_factor_risk_numerics.py johnhull/hullkit/tests/test_reference_builders_independent.py -q → 71 passed in 0.68s)
Task2 RED: lesson/notebook7 failed because new modules were absent.
Ruling: 28.2依存宣言をTask3からTask2へ前倒し — Task2の全6小節検査が宣言を消費するため — 誤りならBook構築前の新宣言を一時的に検査できない。
Task2 intermediate: 20 tests PASS、fresh検査がMIME差と部分実行のPlotly bootstrapを検出。notebook-checkはまだFAIL。
Task2 invalid completion attempt: 未commitかつfresh出力FAILのためcompletionを取消してTask2を再開。
Task 2: complete (commits 754ecdd..19d85df, tests: python -m pytest johnhull/hullkit/tests/test_factor_risk_lesson.py johnhull/report/tests/test_factor_risk_notebook.py johnhull/report/tests/test_risk_premium_notebook.py johnhull/report/tests/test_chooser_notebook.py johnhull/report/tests/test_cliquet_notebook.py johnhull/report/tests/test_compound_notebook.py johnhull/report/tests/test_forward_start_notebook.py johnhull/report/tests/test_gap_notebook_gate.py johnhull/report/tests/test_nonstandard_notebook_gate.py -q → 20 passed in 6.70s)
Task3 RED: 4cards未登録でregistry1 FAIL。登録後16 testsと初期16実画面PASS。ただし目視でhalf-widthではラベルが密集、追加幅検査がFAIL。
Ruling: 新4図をportalのfull rowへ拡大 — 1000pxの3hedgeパネル/12市場labelsを読めるようにし、幅700px以上をbrowserで保証する — 誤りなら共有CSSの依存変更で旧26節の再描画と証跡payloadが増える。
Task3 GREEN: 16 registry/build tests PASS、Book136warnings（M26の132に新4Plotly MIME warnings、HTML全図表示）、portal186図。幅検査も16状態/16画像PASS。1000px Book寄与/portal hedgeとvalidationを目視、旧26節はCSS依存のため再描画予定。
Task 3: complete (commits 19d85df..cb01aa0, tests: python -m pytest johnhull/report/tests/test_factor_risk_registry.py johnhull/report/tests/test_report_build.py -q → 16 passed in 14.19s)
Task4 RED: 新gate/updater15 testsが未実装でFAIL。台帳契約を27/279・FR01–06へ更新し、旧台帳のfreshness/件数検査がFAIL。
Task4 D1: clean cb01aa08から26節browser/runtime/個別pytest1995/両保管庫復元PASS。CSSのため26 redrawn、画像payload19126473 bytes（実増加容量は未測定）。採用path/hashを統合gateへ固定。
Task 4: complete (commits cb01aa0..09a40e2, tests: python -m pytest johnhull/hullkit/tests johnhull/report/tests -q → 3913 passed, 6 skipped, 2 warnings in 170.57s (0:02:50))
Task4 GREEN: 新gate/updater+台帳16 tests、4--check、台帳artifactとruff20ファイルPASS。全suite3913 passed/6 skipped/既存warning2（170.57s）。最終レビューへ進む。
Final review: one fresh gpt-6-astra/high,010a2bc3..b60a2dc8;64 targeted tests/4--check/8 saved images independent;Critical0/Important1/Minor0/Declined0. Raw report saved in SECTION_28_2_REVIEW. Important severity retained for incorrect educational API bars.
Final fix pass: saved result consumer guard and single-read checked data. RED12 failed/5 passed → GREEN17 passed. Four figures and old224/fresh outputs unchanged;16 states/16 images and integrated26D1 PASS. Full suite rerunning; no re-review.
Final fixed: fullsuite3925 passed/6 skipped/2 existing warnings (167.04s),ruff20 files,4--check,ledger-artifacts PASS. One Important fixed,Minor0/Declined0; M26 Minor M1 remains deferred. Main integration authorized by original user request.
Tracked release pre-commit: rejected 4 changed release files because the contract compares to HEAD, not the staged index. Numeric tests and artifacts remain PASS; commit the verified fix first and rerun the required release gate.
Final verification: 9d604a34 tracked release --require-tracked PASS, clean worktree; raw final review and full-suite-after-review.txt retained. Main fast-forward/push follows under explicit user authorization.
