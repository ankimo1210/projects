# Architecture Decision Records (ADR)

設計判断の記録。1ファイル1判断。後から「なぜこう作ったか」を辿るための文書。

## 一覧

| # | タイトル | 状態 | 日付 |
|---|---|---|---|
| [001](./001-claude-api-not-claude-max.md) | AIチャットに Anthropic API を使う（Claude Max ではない） | Accepted | 2026-05-17 |
| [002](./002-flask-on-separate-port.md) | AIチャット用Flaskを別ポート (8051) で動かす | Accepted | 2026-05-17 |
| [003](./003-paf-approximation.md) | Nikkei 225 PAF=1.0 で近似する | Accepted (暫定) | 2026-05-19 |
| [004](./004-current-composition-backtest.md) | バスケットは現在構成銘柄を過去全期間に適用する | Accepted | 2026-05-19 |

## 書き方テンプレート

新しい ADR を作るときの最小フォーマット：

```markdown
# ADR NNN: タイトル

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Date**: YYYY-MM-DD

## Context
なぜこの判断が必要になったか。背景・制約・選択肢。

## Decision
何を決めたか（短く、明確に）。

## Rationale
なぜそう決めたか。代替案を退けた理由。

## Consequences
良い影響・悪い影響・将来の制約。
```
