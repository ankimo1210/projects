# ADR 003: Nikkei 225 PAF=1.0 で近似する

**Status**: Accepted (暫定)
**Date**: 2026-05-19

## Context

Nikkei 225 は価格加重指数で、公式式：
```
Index = Σ(price_i × PAF_i) / Divisor
```

PAF (株価換算係数) は銘柄ごとに異なり、Fast Retailing は 2.4、SoftBank Group は 6.0 等。これを反映しないと公式指数と数%の誤差が出る。

### PAF データ取得経路を調査した結果

| 経路 | 結果 |
|---|---|
| 日経公式サイト | ❌ Cloudflare 403（自動アクセス不可）|
| 公式 PDF ファクトシート | ✅ 直URLでDL可、ただし OCR/抽出が必要 |
| ETF 運用会社開示 | ❌ 野村・大和・BlackRock 全て 403 |
| Wikipedia | ⚠️ 一部主要銘柄のみ記載、完全ではない |
| 第3者API (Quandl等) | ❌ Nikkei PAF を提供しない |

## Decision

**当面は PAF=1.0 で近似する**。誤差はバスケット計算ページで明示する。

将来的には：
- 主要 PAF≠1 銘柄を手動 CSV メンテ
- 公式 PDF の OCR 自動化検討

## Rationale

- **完全自動化は不可** — 全銘柄分の PAF を毎月自動取得する経路がない
- **誤差は小** — 過去2年で +0.85%、年率 +0.4% 程度
- **代替の正確なベンチマーク** — ETF (1321.T) なら 0.5% 以内で指数追随
- **手動メンテのコスト最小化** — N225 全 225 銘柄のうち PAF≠1 は 20 銘柄程度

## Consequences

- バスケット計算ページに「PAF=1.0 近似のため数%の誤差あり」と明記
- N225 で精度が必要なら 1306.T ETF を見るよう案内
- 将来 PAF 対応する場合の拡張ポイント：
  - `_data/nikkei225_paf.csv` を読み込み
  - `basket.py` の `compute_basket_returns` で PAF を乗算

## Code Reference

- `src/stockkit/data/nikkei225.py` の docstring に近似について記述
- `app/pages/basket.py` のUI上部に誤差説明を表示
- 詳細誤差分析は [`docs/METHODOLOGY.md`](../METHODOLOGY.md)
