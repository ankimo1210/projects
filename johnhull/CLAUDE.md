# CLAUDE.md — johnhull（モデルライブラリ / 学習ノート）

Hull 11e 全 37 章 + Beyond-Hull（vol 18–28）の教材・検証済みモデル実装群。
**参照実装カタログ + エージェント作業基盤**として使う。

## ナビゲーション（探す順番）

1. **`MODEL_INDEX.md`** — モデル・手法の横断カタログ。まずここを検索する。
   `package.module:symbol` 形式の実装参照・テスト・使用例 notebook・検証内容つき。
2. `ROADMAP.md` — 巻 ↔ Hull 章の対応と各巻の状態。
3. `release_manifest.json` — vol 18–28 の成果物配線（notebook / portal 図 / semantic tests / reference artifacts）。
4. `VALIDATION.md` — 検証の実行記録。**PASS = integration・数値恒等式・再現性のみ。
   モデル性能・市場予測力の承認ではない**（データは全て synthetic）。

## 実行・検証コマンド（すべて repo root から）

```bash
# scoped テスト
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests
uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests

# 成果物ゲート
make hull-report            # オフラインポータル生成（johnhull/report/site/）
make hull-book              # Jupyter Book
make hull-artifacts-check   # reference artifact の semantic 一致 + byte 再現
make hull-notebooks-check   # vol 18-28 notebook の artifact-only 実行
make hull-core-notebooks-check  # vol 01-17 + 旧 2 冊 (bsm/ir_models) の実行
make hull-release-check     # release 契約（scripts/verify_release.py）
```

acceptance は `johnhull/scripts/frontier_acceptance.py` がコミット済み配列から再計算する
（JSON のフラグを信用しない）。vol 18–28 の全 11 巻について `report/tests/test_frontier_acceptance_tamper.py`
が「選んだ入力を改竄すると、再計算しているチェックと、その入力を共有すると宣言した依存チェック
（`DEPENDENT_FAILURES`）だけが落ちる」ことを固定している。ゼロ入力などで評価が例外になる場合は
`gate_evaluation` の FAIL 記録を返す。配列に根拠がない項目
（vol 18 の Heston 残差 MAE、vol 19 の start 成否、vol 21 の計時フラグ、vol 22 の暦判定）は
保存値のまま（`docs/SECTION_AUDIT_2026-09-14.md` §11.2）。vol 18 の reference 再生成には
`deep_hedge_price/artifacts/pricing/quick/2d4ba8e38acfa5cc`（gitignore、ローカルのみ）が必要。

## 規約と落とし穴

- **hullkit は torch-free。** torch 依存コード（学習・checkpoint・評価 pipeline）は
  `deep_hedge_price` 側に置く。`import hullkit` が torch を引き込んだら release 検証が落ちる。
- **notebook は artifact-only 実行。** build 中の学習・ネットワークダウンロード・GPU 検出は禁止。
  重い計算はコミット済み JSON+NPZ reference artifact（fingerprint 付き）から読む。
- **guard tests がドキュメントの鮮度を強制する:**
  `test_docstrings.py`（両パッケージ、公開 API docstring 100%）と
  `test_model_index.py`（両パッケージ、全モジュール掲載 + `module:symbol` 参照解決）。
  モジュールやシンボルを追加・改名したら MODEL_INDEX.md と docstring を同時に更新する。
- **PDF は 11e Global Edition。** 節・図番号・例題数値が US 版とズレる。引用は毎回 PDF と突合。
- book は notebook を実行しない。vol 01–16 と ir_models はコミット済み出力を表示する
  （ipympl の図は PNG、vol 13–16 の plotly は plotly.js 埋め込み）。builder は出力なしで
  書き出すので、builder を回したら `uv run --no-sync --package hullkit python
  johnhull/scripts/verify_core_notebooks.py --write-outputs` で出力を作り直す
  （`make hull-core-notebooks-check` が出力の型と、stdout・`text/plain` の値の食い違いを検出する。
  `perf_counter` を含む計時セルは型だけ、PNG と plotly の中身は比較しない）。
- vol 21 の timing は通常の再生成では保持され、`benchmark.measurement` に計測時のソース digest と
  環境が残る。再計測は `build_frontier_artifacts.py --volume 21 --refresh-timing`（負荷のない時に）。
  `make hull-artifacts-check` が計測時と現在の generator が一致するかを `[NOTE]` で出す。
- 図に日本語を使う notebook は `japanize_matplotlib`（core は `hullkit.nbplot.setup()`）を読み込む。
  ないと日本語ラベルが豆腐になり、stderr の警告に実行した checkout の絶対パスが残る
  （`test_frontier_notebook_freshness.py` と `test_core_notebook_gate.py` が検出する）。
- build スクリプトは決定的 cell-id 方式。`build_*_notebook.py` は ruff exclude 対象。
- 巻を追加するときは `release_manifest.json` に notebook / portal 図 / semantic tests /
  references を登録し、`make hull-release-check` を通す。

## 境界（正本の所在）

| 対象 | 正本 |
|---|---|
| 金融教師（解析解 / COS / MC）・hard validation | `johnhull/hullkit` |
| torch 学習・checkpoint・walk-forward・経済評価 | `deep_hedge_price` |
| exact rBergomi / fBM / Hawkes の重い実験 | `~/projects/rough_volatility` |
| 執行アルゴ・RL 執行 | `~/projects/optimal_execution` |
