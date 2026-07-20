# ADR 0001: 公開プールデータ MVP と fractional logit

- Status: Accepted
- Date: 2026-07-20

## Context

JHF MBS の借手別 loan tape と過去の統一的な住宅ローン借換金利は公開されていない。一方、回号別の
予定／実績 Factor、WAC、WAM、WALA、任意期限前償還率等は年度 workbook で公開される。MVP は
有料データなしで end-to-end に動き、後から高度 model / OAS を追加できる必要がある。

## Decision

1. immutable raw object + snapshot manifest、標準化 panel、lagged features、model run、prediction、
   cashflow/report の層を分ける。
2. 固定 PSJ を必須 baseline とし、最初の推定器は pool 月次 fractional response に適した
   fractional logit とする。
3. 既定モデルの金利変数は全期間で JGB 10年 proxy に統一して flag し、PDF graph の座標抽出はしない。
   同一定義の住宅ローン金利履歴が十分揃った場合だけ、設定を切り替えて別 run として推定する。
4. 高度 model は `predict_smm(DataFrame)` と run artifact 契約に追加する。OAS 用金利 path は
   deterministic forecast/cashflow の外側に provider interface として追加する。

## Consequences

- 公開情報だけで取得から risk report まで再現でき、係数・時点・入力 hash を監査できる。
- pool 内 heterogeneity と個別借換行動は識別できず、JGB proxy の係数を純粋な借換効果と解釈できない。
- PDF parser の脆弱性を避ける代わりに、公式フラット35 snapshot の履歴は運用開始後に蓄積される。
- 高度 model の追加前に、同じ時系列/vintage OOS 契約で明確な改善を示す必要がある。
