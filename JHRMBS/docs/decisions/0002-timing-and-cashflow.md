# ADR 0002: 支払月基準の時点整合と deterministic cashflow

- Status: Accepted
- Date: 2026-07-20

## Context

JHF 表の債券年月、loan 回収月、MBS 支払月には lag があり得る。予定 Factor、実績 Factor、任意 CPR、
差替・解約率も同じ経済概念ではない。これらを同月説明変数として扱うと leakage や二重計上を招く。

## Decision

1. panel grain は JHF の `issue_id × 債券年月` とし、列名を `payment_month` とする。
2. model feature は pool state と外部系列に原則1か月 lag を置く。正確な回収／支払 lag を確認できない
   点は仮定として残し、同月実績を feature にしない保守的な契約を選ぶ。
3. 任意 CPR、長期延滞、その他解約は別列で保存する。Factor 逆算値との reconciliation は診断であり、
   等式制約にしない。
4. cashflow engine は純粋関数とし、JHF 予定 Factor による約定元本後に任意 SMM を適用する。
   clean-up call は既定で無効、明示時のみ threshold / lag を適用する。
5. MVP の valuation はフラット年複利 yield の dirty price とし、prepayment path 固定の duration / convexity
   と明記する。

## Consequences

- 将来情報混入と予定／任意元本の二重計上を避け、unit test で順序を固定できる。
- 1か月 lag が実際の商品 cashflow timing と完全一致する保証はなく、商品資料で確認後に設定可能な
  timing provider へ拡張する必要がある。
- OAS には stochastic rate path ごとの refinancing feature 更新と cashflow 再生成が別途必要になる。
