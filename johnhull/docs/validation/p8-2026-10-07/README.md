# P8 最終検証（2026-10-07）

- p8-check.json：検証したsource commit、全suite、各ゲート、制限。
- d1-final-check.json：既受入33節の最終D1。初回のd1/は表示修正前の履歴で、現行参照は直下のsection-*。
- ledger-evidence-refresh.json：受入要件・statusを維持した証跡更新の前後。
- p8-browser-check.json：影響6巻の18画面状態、数値改変拒否、画像参照、生成HTMLの完全性。
- p8-browser-manifest.json：画像18枚。p8-validation-manifest.json：実行ログと検査プログラム。実体はC:・F:の両保管庫に保存し、双方から復元済み。

実行は既存の共通ツールとsource checkoutを使用。個別節の新しい受入スクリプトは作成していない。
最終コマンド：pytest -q johnhull/hullkit/tests johnhull/report/tests、pytest -q deep_hedge_price/tests、
verify_frontier_artifacts.py、verify_frontier_notebooks.py、verify_core_notebooks.py、
verify_section_ledger.py --check-artifacts、verify_release.py --require-tracked。
D1はd1_preflight_compare.py redrawを既受入33節に適用。画像の完全性はSHA、数値の再現は許容差・SEで検査する。
