# Page 028 - 日本語版

![Page 28](../assets/page_images/page_028.png)

## 日本語メモ

**該当箇所:** 5.1 Model Diagnostic Testing

係数の安定性・有意性、モデル予測可能性、バックテスト期間でのreliability plot等を用いた診断テスト。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
for comparison with less liquid sectors in stress tests. Client tier 5 was chosen as a representative
subset.
It is expected that the trends and inferences arising from analysing results in the tier 5
segmentation are also relevant to other segments.
5.1
Model Diagnostic Testing
5.1.1
Coefficient Stability, Significance and Error Handling
The model coefficient outputs are detailed in section [3] of the document. Parameter significance
was evaluated using a standard p-value metric and is presented below:
Intercept p-value
Dealer count reciprocal p-value
1
1
os
os
06
o6
o4
04
o2
0.2
)
o—ee-e-@
©
©
©
©
©
©
0
o-o-0--0-@
©
©
©
©
6
@
Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
 Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
Dpdy p-value
% Tw spread p-value
1
1
08
Os
0.6
06
04
oa
0.2
0.2
0
o-e--e--@-e-e-e-@-e-e-@
0
o-oo
e--0-e-0-e-@-@-@
Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
 Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
Log10 quantity p-value
Life remaining p-value
1
1
08
Os
0.6
06
0.4
04
0.2
02
oO
o—e—e--0-0-@-0-@-@-@-@
ie)
o—0—@-_0
0000-0
@-@
Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
 Jan-24
Apr-24
Jul-24
Nov-24
Feb-25
Figure 10:
Coefficient p-values over a backtest timeframe of January 2024 to November 2024,
example results taken from the client tier 5 segmentation of a German auction dataset. The p-
values remain largely 0 through time, which proves the significance of the features. An exception
can be noticed in the life remaining p-value in the October 2024 calibration. Here the p-value is
higher, showing that the feature is not as significant for this data segment.
It was said previously that segmentation can impact the significance of a feature. This means
that it is possible that some features may be more signficant than others over time, and for different
segments. This is shown in the figure below, comparing life remaining p-values for client tier
1 and
129576: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 28 of
73
[git]
Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
