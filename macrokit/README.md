# macrokit — 日米マクロ経済指標のリサーチ基盤

日米の経済指標をポイントインタイムで蓄積し、マクロ計量モデルの土台にする。

設計書: [`docs/superpowers/specs/2026-08-17-macrokit-design.md`](../docs/superpowers/specs/2026-08-17-macrokit-design.md)

## なぜスナップショットを取り続けるのか

**日本の統計には vintage（改定前の値）が存在しない。** e-Stat API には
realtime / vintage / 公表時点を指定するパラメータがなく、日銀・内閣府・財務省の
CSV も上書き公表される。したがって「速報 → 1 次改定 → 2 次改定」を追うには
公表時点のファイルを自分で保存し続けるしかなく、**過去分は原理的に復元できない**。

米国は ALFRED があり全 vintage を遡れる。この非対称が設計の中心にある。

## 使い方

```bash
uv run --no-sync macrokit status          # 指標の実装状態を一覧
uv run --no-sync macrokit catalog list    # カタログの内容
```

コマンドは**リポジトリルート（`/home/kazumasa/projects`）から実行する**前提。
`--data-root` の既定値は `macrokit/data`（カレントディレクトリからの相対パス）で、
スナップショットと DuckDB ファイルはそこに置かれる。別の場所から実行する場合は
`--data-root` で明示すること。

カタログ（`macrokit/catalog/`）はソースツリー内のディレクトリをそのまま参照する
（`default_catalog_root()`）ため、**editable install が前提**。このワークスペースは
全メンバーを editable でインストールするので通常は問題にならないが、通常の wheel
インストールでは `catalog/` が存在せずエラーになる。

## テスト

```bash
uv run --no-sync pytest macrokit/tests           # ネットワーク不要
uv run --no-sync pytest macrokit/tests -m live   # 実 API を叩く（要 FRED_API_KEY）
```
