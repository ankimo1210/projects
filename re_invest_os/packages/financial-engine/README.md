# financial-engine (`re_engine`)

re_invest_os 計算エンジン。**すべて純粋関数**で構成され、I/O・LLM呼び出し・グローバル状態を含まない。

仕様: `/docs/architecture/calculation_engine_spec.md`

## 構成

```
src/re_engine/
  models.py        # Pydantic v2: Assumptions, AnalysisResult, ...
  constants.py     # 法定耐用年数、税率、構造区分
  loan.py          # 元利均等返済、残債計算
  cashflow.py      # GPI/EGI/NOI/BTCF/ATCF プロジェクション
  tax.py           # 減価償却、課税所得、譲渡税
  exit.py          # 売却シナリオ
  irr.py           # IRR、Equity Multiple、Payback
  score.py         # 100点スコア
  max_offer.py     # 最大買付価格 (二分探索)
  sensitivity.py   # 感応度シナリオ
  cross_asset.py   # クロスアセット比較
```

## 開発

このパッケージは `~/projects/` のトップレベル uv workspace のメンバーです。依存はワークスペース全体で一括解決されます。

```bash
# 初回のみ：ワークスペースルートで sync
cd ~/projects && make install     # = uv sync --all-packages

# テスト（ワークスペース .venv が自動検出される）
uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -v

# このパッケージのディレクトリからでも OK
cd re_invest_os/packages/financial-engine
uv run --no-sync pytest -v
```

## バージョニング

`engine_version` (semver) を全結果に保存。互換性破壊時は major++。
