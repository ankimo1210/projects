# Page 31

![Page 31](../assets/page_images/page_031.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
% Tw spread coefficient
Dealer count reciprocal coefficient
°
8
Dinh
qb
gh
ah
nb
ab
gh
ah
oh
ah
75
2
a
oP
oh
Po
PD
PPP
PP
PP
OP
OP
ES
CPX
Ne
7 NO
65
6
ad
55
to
Ca
a
a
2
SES LPS
NS FE LF
Dpdy coefficient
Intercept
1000
°
800
600
400
200
2
°
ZN
ah ah
gh
oh oh oh oh oh
oh oh oP
og
%
s
SFP FM MS
WN pe oF of VF
Dogh
gh
ah
gh
gh
ah
gh
oh
PP
PP Ph oP
Rae
PLS
SS
POF PN
Life remaining coefficient
Log10 quantity coefficient
0.25
0.2
0.05
gh hh gh oh gh gh ah ah oP
SFP
CWP
HK Ky
oF
Figure 13: Model output coefficients over backtest timeframe of January 2024 to November 2024,
example results taken from client tier 5. The signs of the coefficients along their respective time
series are indicative of stability over time. Here the life remaining coefficients varies in sign, and
can therefore be deemed unstable for the chosen segmentation.
The value of the coefficient is dependent on the underlying auction dataset and is expected to
vary with time. However, coefficients are not expected to vary in sign through time, as features are
expected to have a binary impact on the curve - either increase, or decrease the spread required
to attain a probability of winning an auction. The stability of a coefficient can thus be assessed
according to its sign.
the sign varies with time for the life remaining coefficient, which can therefore
be deemed unstable for the chosen segmentation. We can action a number of solutions to resolve
issues with coefficient stability. Depending on current needs, we may decide to:
+ Keep the current production model and not to update it using the new calibration - this is
the most likely outcome.
+ Apply expert judgement in manually setting coefficient value limits, eg. setting coefficients
to a reasonable, small value of the opposite sign.
+ Run a one-off manual calibration using different parameters - eg. lookback / dataset, in
agreement with model owners. This is least likely outcome, and would only be required if a
model update is absolutely and urgently necessary. An example is shown below, where the
training period was extended to 3 months:
129576: Winning-Probability Model for EUGV RFQ Pricing
Page 31 of 73
[git]
Branch: ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
