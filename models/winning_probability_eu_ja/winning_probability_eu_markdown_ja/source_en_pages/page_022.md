# Page 22

![Page 22](../assets/page_images/page_022.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
yearsToM aturity
maturityDate — date
lifeR
ini
=
=
ifeRemaining =~ ToMaturity
+ yearsSincelssuc ~ maturityDate
— issueDate
(12)
A lower percentage life remaining introduces more risk, as its liquidity is assumed to be lower.
Following the logic detailed above for the log]0quantity feature, if « remains constant, it can
therefore be expected that a decrease in lifeRemaining parameter will increase the winning
probability.
+ dpdy: The dpdy of each instrument in question.
This is a measure of risk, relating the
change in price with respect to the change in yield of a security.
A higher dpdy represents higher risk. Following the logic detailed above for the log1Oquantity
feature, if x remains constant, it can therefore be expected that an increase in dpdy will
increase the winning probability.
The model target variable is the outcome of the auction, ie.
the win/loss result.
It can be
expressed as:
.
1,
if inquiryState is Done,
(as)
win =
0,
if inquiryState is one of TradedAway, TiedTradedAway, Covered, CoverTied.
3.4
Model Outputs
The offline calibration outputs coefficients for the chosen features. No transformation of the output
data is necessary for consumption by downstream pricing components in production.
For the
he coefficient:
features described in section
e as follows:
Bo: intercept (constant).
+
Bi: coefficient of percentageTwSpread.
+
By: coefficient of log]Oquantity.
+
83: coefficient of dealerCountReciprocal.
+
B4: coefficient of lifeRemaining.
+ Bs: coefficient of dpdy.
The online implementation of the model ouputs the probability curve for each incoming RFQ,
using equation 5. The curves are created using the model coefficients relevant to the inquiry - those
corresponding to the calibrated segment in which the inquiry sits.
3.5
Model Calibration and Parameter Estimation
The inquiry datasets are fetched from the internal MS BMET database and stored in a shared drive
location. The files can be backfilled in case of process failure, or in case new information is to be
added.
The data is first refined using the following steps:
: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 22 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
