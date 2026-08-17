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

## テスト

```bash
uv run --no-sync pytest macrokit/tests           # ネットワーク不要
uv run --no-sync pytest macrokit/tests -m live   # 実 API を叩く（要 FRED_API_KEY）
```
