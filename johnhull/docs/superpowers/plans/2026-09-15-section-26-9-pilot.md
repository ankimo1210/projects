# §26.9 Barrier Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Hull 11e GE §26.9 (pp.620–622) を、説明・計算・図・配布画面・独立検証まで一つの学習単位として完成させる。

**Architecture:** 既存の barrier_call / barrier_put / BGK と vol10 の教材生成スクリプトを使用する。既存の portal 図 ID と公開関数の引数を維持し、8種類を比較できる図に拡張する。全体の完了判定を変更せず、この節の証拠を独立した対応表に残す。

**Tech Stack:** Python / NumPy / SciPy / pytest / nbclient / matplotlib / Plotly / Jupyter Book / 既存の Playwright。

**Spec:** [§26.9 受入条件](../../SECTION_26_9_ACCEPTANCE_2026-09-15.md)

## Global Constraints

- ユーザー承認済みの1節のパイロット。johnhull 外の変更を保持する。
- 新しい production 依存関係・公開 API・volume を追加しない。
- コミット・push・公開は行わない。
- 同じ作業ディレクトリで対象ファイルに限定して実装する。
- 教科書の数値例がない箇所の数値は「教材用の合成例」と明記する。
- 連続観測の厳密式、離散観測の BGK 近似、Parisian の契約例を区別する。

### Task 1: 独立した数値検証
Files: `hullkit/tests/test_barrier_reference.py`, `hullkit/src/hullkit/exotics.py`（誤りが確認された場合のみ）
- [x] 既存 exotics / exotics_puts / plotly テストを実行（79 passed）。
- [x] Brownian bridge の条件付き到達確率と終端密度の積分を独立の oracle にする。
- [x] 8種類・H と K の大小・H=K・初期到達・配当を検証する。
- [x] 発見した不具合を修正し、対象テストを再実行する。

### Task 2: 説明と配布図を完成させる
Files: `volumes/10_exotics_martingales/build_exotics_notebook.py`, `hullkit/src/hullkit/plotly_viz.py`, `report/report_builder/figures.py`, `hullkit/tests/test_plotly_viz.py`
- [x] 図の選択肢・価格範囲・S0 比の軸を確認するテストを先に実行して不足を確認する。
- [x] 到達時の payoff 分解、全分岐、8種類、BGK、負のベガ、Parisian を説明する。
- [x] 同じ終値で到達履歴が違うパス、8種類、観測頻度、ベガ、滞在期間を可視化する。
- [x] portal の既存図を拡張し、vol10 からも同じ操作図を表示する。

### Task 3: 配布物の検証とフィードバック
Files: vol10 notebook / `docs/SECTION_26_9_ACCEPTANCE_2026-09-15.md` / `VALIDATION.md` / 既存 feedback
- [x] vol10 の出力を再生成し、別の fresh run と比較する。
- [x] Book と portal をローカルで構築する。
- [x] 実ブラウザで初期表示・切替操作・数式・図の見切れを確認し、証跡を保存する。
- [x] 関連テスト・lint・release gate を実行する。
- [x] 独立レビューの指摘を処理し、対応表と feedback を更新する。

完了：2026-09-15。画面検査で発見した共通 renderer の幅追従と Book の Thebe 重複宣言も修正。最終証跡は Spec の受入メモを参照。

- [x] 再確認：BGKが元の契約の厳密ゼロ条件を保持する24ケースを追加・修正。
- [x] 再確認：表示価格64点とブラウザの8種類を独立積分に照合し、誤配分の入力改変を拒否。
