# ADR 001: AIチャットに Anthropic API を使う（Claude Max ではない）

**Status**: Accepted
**Date**: 2026-05-17

## Context

stockkit に自然言語で投資分析を依頼できる AI チャット機能を追加したい。Claude を使う方針は決定済みだが、課金経路として以下が候補：

1. **Anthropic API** (api.anthropic.com) — 従量課金
2. **Claude Max plan** ($100/月、claude.ai および Claude Code CLI で使用)
3. **OpenAI API** — 同等機能だがプロバイダ違い

## Decision

**Anthropic API を使う**。

## Rationale

- **Max プランは API 用途に使えない** — Max は claude.ai ウェブ/デスクトップアプリと Claude Code CLI 向けで、プログラマティックな `api.anthropic.com` 呼び出しは別契約
- **従量課金で十分** — 個人の分析用途なら月数百円〜数千円程度
- **tool_use 機能が充実** — Claude API の `tools` パラメータでデータ取得/コード実行を自然に統合可能
- OpenAI も技術的には可能だが、ユーザーが既に Anthropic 環境を使用中で統合容易

## Consequences

- **要 API キー発行 + クレジット購入** — console.anthropic.com で別途登録
- **コスト発生** — Sonnet 4.6 は入力 $3 / 出力 $15 per MTok。1チャットで $0.01-0.05
- **将来 LLM 変更可能** — Tool 定義 (`app/api/tools.py`) は LLM 非依存なので、OpenAI 等に乗り換える際は `claude_agent.py` のみ書き換え
