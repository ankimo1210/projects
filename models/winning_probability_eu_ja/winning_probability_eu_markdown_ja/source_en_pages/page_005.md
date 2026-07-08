# Page 5

![Page 5](../assets/page_images/page_005.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
+ The behaviour of market participants is stable between regression training periods.
+ Standard logistic regression statistical modelling assumptions apply.
No limitations have been identified for the model.
1.4
Overall Model Performance Assessment
The model performance was assessed on a number of statistical metrics evaluated across a range
of scenarios. More information is provided on this in section
The model was first tested for predictability and stability, with an evaluation of output coeffi-
cient significance and consitency. A strong relationship between data segmentation and coefficient
stability was found. However the model performed well overall and was found to be reliable through-
out.
Stress testing showed that the model performed well under ‘unstable’ market conditions. This
included testing in a volatile environment, as well as in sectors with lower liquidity.
A sensitivity analysis was carried out to evaluate the impact of features on the output probability
of trade. The study showed that the model could perform well in the range of features tested -
output probability curves were estimated to be well within an acceptable range.
Tt was finally found that quotes constructed from the model probability cuves were within the
accepted market spread benchmark.
1.5
Summary of Results
The probability curve model is capable of capturing the relationship between the percentage market
spread charged and the probability of trade in the EUGV and UKGV spaces effectively.
2
Business and Algo Description
The purpose of the Winning-Probability Model detailed in this document is to assist with Mor-
gan Stanley’s autoquoting (AQ) of customer inquiries in the request-for-quotation (RFQ, at times
referred to as ‘inquiry’) EUGV and UKGV (including inflation) bond markets, and in doing so,
to balance the best price to the customer with the trading desk’s current objectives. The EUGV
space accounts for the following countries: Austria, Belgium, Cyprus, Denmark, Germany, Greece,
Finland, France, Ireland, Italy, Netherlands, Portugal, Spain and Slovenia. The scope of applica-
bility of the model also extends to other EU-issued bonds, which exhibit the same properties as
the other issuers mentioned and can be traded on the same platforms. The UKGV space accounts
for the United Kingdom. As is the case for EU bonds, the scope of applicability extends to UK
inflation bonds.
The model uses a statistical modelling method that leads to a prediction of the probability
of winning an auction at a given price. Historical data is fit to a logistic curve based on factors
such as dealer count and client tier.
However, complexity is introduced because the available
information is censored by the marketplaces; that is, RFQ marketplaces provide the winner of an
inquiry information that others do not receive, and within the set of non-winning dealers, some will
receive partial information.
In order to understand how a model might be constructed for censored RFQ-based markets, it
is necessary to first understand the RFQ auction process, and to do so, it is best to begin with the
economic incentives of market participants.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page
5 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
