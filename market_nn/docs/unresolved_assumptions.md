# Unresolved assumptions

`C_PAPER_CONSTRAINED` の出力は以下を必ず同梱する。

| ID | choice used by synthetic profile | alternatives / impact |
|---|---|---|
| SC2019-A001 | stock/day boundaryで hidden state reset | carry across day; state leakage と long-memory interpretationが変わる |
| SC2019-A002 | synthetic 8-feature state、train-only global standardizationなし | paperの完全な state vector/order/transform は未開示 |
| SC2019-A003 | SGD lr=.01、regularization=1e-5 | schedule/係数は未開示。test setで選ばない |
| SC2019-A004 | truncated windows are independent batches | hidden carry + detach between TBPTT chunks is plausible |
| SC2019-A005 | PyTorch default initialization | initialization は未開示 |
| SC2019-A006 | validation loss stopping with fixed smoke epochs | stopping rule は未開示 |
| SC2019-A007 | uniform sampling across assets in pooled batches | volume-proportional sampling is plausible |
| TLOB-A001 | paper profile hidden dimension 144 | paper Table10には明記されず、repository の FI-2010 runtime override から拘束 |
| TLOB-A002 | paper profile uses device/autograd-safe BiN | exact edge behaviorは参照した BiN paper/codeなしでは確定不能 |
| TLOB-A003 | paper profile initialization follows current PyTorch | framework/default version is not paper-specified |
| MLPLOB-A001 | hidden dimension 144 | paper text/tableだけでは確定不能、repository の FI-2010 runtime override から拘束 |
| DL2019-A001 | paper profile native implementation uses PyTorch default initialization | shape verification only。numerical paper runには使用不可 |
| DL2019-A002 | paper validation subset construction is unspecified | strict paper profile does not invent a validation split |
| DL-AUTH-TF-A001 | TF2/Keras runtime version and Adam epsilon remain unpinned | native behavioral comparisonには当時の environment lock または author clarification が必要 |
| DL-AUTH-PT-A001 | PyTorch version/default epsilon and initialization stream remain unpinned | notebook は seed を設定しないため、synthetic smoke seed 7 は run control のみ |
| RUN-CONTROL-001 | deterministic seed 7 | reproducibility control; paper-specified seedではない |

Sirignano–Cont を `B_PAPER_EXACT` に上げるには、complete input vector、normalization、
optimizer schedule、regularization、batching、state reset/carry、TBPTT mechanics、
initialization、stopping、asynchronous update semantics を一次資料で解決する必要がある。
