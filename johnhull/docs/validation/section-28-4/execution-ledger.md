# SDD ledger — M29 §28.4
Ruling: 承認済みP3節受入工程を設計再確認待ちなしで継続する — complete P3/main push/次工程の本人指示に従う — 誤りなら対象範囲と数値仕様の手戻り。
Setup: own worktree reused from m28 at main88e03d3f and safely moved m29; branch codex/m29-numeraire-choices, shared uv env, mainM28 PASS4046/6 andliveSHA一致。
Pre-flight: Task1 Q OU state/phi=f0+c ↔Task2 joint Gaussian conditional integral/tower; same signed/rate/time conventions. Task2詳細API/fixtureを実装前に確定して記録する。
Task1 RED: independent conditional integral3/tower1 allFAIL0.54s; Q discounted bond .819735115209901 vs P0(5)=.8187307530779818. Added -B*c(t) while preserving public signature and documented Q OU state. Caller/option/calibration audit pending.
Task 1: complete (commits 88e03d3..7f87b99, tests: pytest -q johnhull/hullkit/tests/test_numeraire_hw_state.py johnhull/hullkit/tests/test_hull_white.py johnhull/hullkit/tests/test_jarrow_yildirim.py johnhull/hullkit/tests/test_hull_pins_exotics_ir.py → 27 passed in 1.53s)

Task2 preflight: private FlatHW scalar finite-real years/rates and array states; reject temporal/bool/string/nonfinite. joint order=(X,I,W), stable small-ah series/rank2 exact sampler. OIS bond/Q and U>=T tilted moments, same stock call Q/T, term fixingT and overnight realizingU/payU, annuity payment-Gaussian mixture. Projection is additive simple-rate deterministic basis per source design (multiplicative teacher is contrasting model, never mixed). Independent kernel quadrature oracle has6/18/21/18 fixtures, price abs1e-9/rate2e-12/moment rel2e-12 and abs1e-25, raw iid MC262144≤5SE; source12 rows and four figure consumption contracts mandatory. Test-first missing module RED then36 PASS; whole ledger stillpending28D1.
Task 2: complete (commits 7f87b99..96587cc, tests: pytest -q johnhull/hullkit/tests/test_numeraire_choices.py johnhull/hullkit/tests/test_numeraire_numerics.py → 40 passed in 9.35s)
Task 3: complete (commits 96587cc..c81160b, tests: pytest -q johnhull/hullkit/tests/test_numeraire_lesson.py johnhull/report/tests/test_numeraire_notebook.py johnhull/report/tests/test_numeraire_registry.py johnhull/report/tests/test_martingale_notebook.py johnhull/report/tests/test_report_build.py johnhull/hullkit/tests/test_model_index.py → 503 passed in 19.16s)

Task4: clean c3303574から28D1すべてredrawn/PASS、462画像/19,960,718B payload/pytest2157/両保管庫復元。gate/updater15 PASS、NC01–06全5軸、branch29/277。初回全suite4123 passed/1 failed/6skip: inventory testが旧28/278、M28参照を保持していた。M29現在値/参照へ更新、全5軸回帰追加、gate再生成/updater後test_section_ledger40PASS。全suite再実行中。
Final review: 1fresh gpt-6-astra/high、88e03d3f..0e21d349、Critical0/Important0/Minor3。原典/96tests/4--check/100条件付きprobe/42不正入力/4画像を独立確認。
Final: minor (deferred): M1 portal practiceが図にない定数金利極限を案内。Book/oracleは正しく、説明の読み違いのみで数理受入への影響なし。
Final: minor (deferred): M2 δ≈1e−12年のterm/forward桁落ち。約32μsのaccrualで、通常のquarterly/semiannualと表示fixtureに影響なし、値の精度限界を記録。
Final: minor (deferred): M3 a*h=1e16でsampler X varianceが消失。非実用的な平均回帰で標本分散が失われるが、通常入力・今回表示価格には影響なし、支持領域の限界を記録。
Final: Ruling: 全16新表示/旧28節の再描画・両保管庫復元はexecutorのfresh producer証跡とレビューのcurrent hash/matrix/storeで判断する — rootが実際に全状態を実行し8画像を目視、reviewerはreadonlyで4画像と全記録を検査 — 誤りなら現行画面/証跡不一致を見逃す。
Final: Ruling: 全suite/release/lintはexecutorのfresh出力を採用する — 全4125/6・ruff21・strictreleaseをrootが実行し、独立96tests/4checks/probesで補強 — 誤りなら広い回帰を見逃す。
Final: Ruling: M30/TN14/TN19/元XLS/LMM/flexicapは後続P3の準備・未受入として保持する — 取得と独立scratchを正式五軸受入へ昇格させない — 誤りなら未完実装/原典入力の受入を水増しする。
Final: Ruling: main統合後の一致とremote到達はexecutorがFF後にfresh検証して判断する — reviewerの固定HEAD/readonlyを統合完了の証拠に使わない — 誤りなら未到達commitや現行配布物差を見逃す。
