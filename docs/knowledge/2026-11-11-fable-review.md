# Claude Code で Fable にレビューを依頼する

確認日 2026-11-11 JST

レビュー対象、目的と前提、重点的に確認してほしい事項、返答形式を Markdown にまとめる。コーディングモデル評価計画では、既存の Opus 向け文書をそのまま入力に使える。[Opus レビュー引き継ぎ](../superpowers/specs/2026-11-01-coding-model-evaluation-opus-review-handover.md)

## 実行手順

WSL Ubuntu または macOS のターミナルで、リポジトリのルートから実行する。Fable 5.2 には Claude Code 2.1.321 以上が必要で、WSL の 2.1.322 で下記のオプションを確認した。モデル ID を指定し、レビューの effort は `high` にする。[モデル設定](https://code.claude.com/docs/en/model-config#work-with-fable) [CLI リファレンス](https://code.claude.com/docs/en/cli-reference)

```bash
review_doc='docs/superpowers/specs/2026-11-01-coding-model-evaluation-opus-review-handover.md'

claude -p --model claude-fable-5-2 --effort high \
  --tools '' --disallowedTools 'mcp__*' \
  -- '標準入力の引き継ぎ文書をレビューしてください。文書の確認事項と返答形式に沿って、日本語でレビュー結果を返してください。' \
  < "$review_doc"
```

別の案件では `review_doc` を差し替える。レビューに必要な根拠も、共有できる範囲で引き継ぎ文書に含める。この例では組み込みツールと MCP ツールを外し、文書を読んだレビュー結果を標準出力に返す。

返答には着手可否と条件、重大度順の指摘、該当箇所・影響・修正案、必須修正と任意改善を含める。Opus の結果と比較するときは、同じ引き継ぎ文書を使い、モデル ID と effort を結果に添える。
