# macrokit — 日米マクロ経済指標のリサーチ基盤

日米の経済指標をポイントインタイムで蓄積し、マクロ計量モデルの土台にする。

設計書: [`docs/superpowers/specs/2026-08-17-macrokit-design.md`](../docs/superpowers/specs/2026-08-17-macrokit-design.md)

## なぜスナップショットを取り続けるのか

**e-Stat の API は vintage（改定前の値）を返さない。** realtime / vintage /
公表時点を指定するパラメータがなく、日銀・内閣府・財務省の CSV も上書き公表
される。だがこれは「vintage が存在しない」ことを意味しない —— 内閣府 ESRI は
公表ごとの統計表そのものをアーカイブし続けているため、公表を 1 件ずつ取得すれば
GDP の vintage は復元できる（`sources/esri_gdp.py`、`macrokit gdp vintages`）。
この branch は 2008 Q4 以降の日本の実質 GDP 公表 約 141 件をこの方法で
再構築し、同日の JGB カーブの動きと突き合わせている。API が返さないことと
記録が失われていることは別で、後者だけが「原理的に復元できない」。

米国は ALFRED があり API から全 vintage を遡れる。この非対称
（米国は API 越しに取れる／日本は公表ページを 1 件ずつ archaeology する必要が
ある）が設計の中心にある。

## 使い方

```bash
uv run --no-sync macrokit status                      # 指標の実装状態を一覧
uv run --no-sync macrokit catalog list                # カタログの内容
uv run --no-sync macrokit rates                       # MoF の JGB カーブ（2 本の CSV）を取り込む
uv run --no-sync macrokit gdp releases                # e-Stat の GDP 公表カレンダーを取り込む
uv run --no-sync macrokit gdp vintages                # 各公表の統計表を 1 件ずつ取得（~15 分、~141 fetch）
uv run --no-sync macrokit gdp expectations             # 公表前に知り得た期待値を計算
uv run --no-sync macrokit gdp panel --out panel.csv    # 公表とレート変化のイベントパネルを CSV へ書き出す
```

`gdp vintages` は再開マーカーの無い逐次ループなので、`skipped` が出た、または
途中で中断した場合は、その後に必ず `gdp expectations` を再実行すること
（`docs/known-limitations.md` §8）。

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
uv run --no-sync pytest macrokit/tests                        # ネットワーク不要（既定）
MACROKIT_LIVE=1 uv run --no-sync pytest macrokit/tests        # ESRI/MoF 等、実サイトも叩く
FRED_API_KEY=xxx uv run --no-sync pytest macrokit/tests       # ALFRED の実 API も叩く（要キー）
```

ネットワークに触るテストは個別に `@pytest.mark.skipif` でゲートしてあり、
`-m live` のようなマーカー選択には依存しない。ESRI/MoF（内閣府・財務省の
静的ページ）系は `MACROKIT_LIVE` 環境変数、ALFRED（FRED）系は `FRED_API_KEY`
環境変数の有無で個別にスキップ判定する。どちらも未設定なら、実 API 系は
すべて自動的にスキップされる。
