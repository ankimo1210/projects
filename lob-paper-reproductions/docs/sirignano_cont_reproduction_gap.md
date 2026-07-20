# Sirignano–Cont reproduction gap

論文から確認できるのは、3層LSTM、ReLU feed-forward、softmax、regularized NLL、
SGD、truncated BPTT、50 units（および150-unit universal variant）、pooled/unseen stock
evaluation、100対5,000 histories までである。

完全な input state vector と順序、price/size/order-flow transformations、optimizer
schedule、regularization coefficient、stock間 batching、hidden state reset/carry、TBPTT
window mechanics、initialization、stopping、distributed async semantics は解決していない。
公式実装も一次資料から確認できなかった。したがって本プロジェクトは
`C_PAPER_CONSTRAINED` のままにし、2つ以上の重要な lifecycle variant を設定可能に
する。昇格条件は [unresolved_assumptions.md](unresolved_assumptions.md) に記載する。

