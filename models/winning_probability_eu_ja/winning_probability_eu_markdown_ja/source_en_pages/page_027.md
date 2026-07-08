# Page 27

![Page 27](../assets/page_images/page_027.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
a client and on a security level.
Segmentation also poses a question of lookback timeframe - as mentioned in section 3, data
grouping affects the number of samples available. A longer lookback may be required for smaller
segments as a solution to this issue. The lookback timeframes used in the tests in section
[5
broadly represent typical timeframes used in production historically. Flexibility is required here on
the basis that new segmentation may lead to smaller and/or larger calibration datasets.
While this flexibility is necessary, the underlying selection process and model still remain the
same as described in previous sections.
4.2.2
Alternative Feature Selection
Out of some previously considered alternative features, a stand-out example would be the inclusion
of mid prices from a variety of market sources (eg. Bloomberg mid). The potential gain in accuracy
from this was outweighed by the complexity and effort required to include this feature both in the
offline and online implementations of the model at this stage.
‘As a whole, features are reviewed regularly to ensure their relevance. Section 4.1.2 gives the
pool of available features that can be used. It needs to be accounted for that any new segmentation
may highlight a new significant feature for the dataset.
‘Again, while flexibility may be necessary here, the underlying selection process and mathemat-
ical approach still remain the same as described in previous sections.
4.3
Contributions from Key Stakeholders and Independent Sources
The stakeholders are the following entities:
« Algo Traders: Key stakeholder whose algorithms use the model.
+ Strats: Building, enhancing and calibrating the model. Strats make sure that the Hit-Rate
Curve model is valid and working properly, or in the opposite case, they have to re-tune and
re-calibrate the model’s parameters. Also, they are responsible for the future enhancement
and development of the model.
+ Technology: Implementing the model to meet the standards of MS for real-time application.
The technology section is responsible for altering the model’s logics developed by strats to an
appropriate programing language (Java) to guarantee its performance in live mode.
+ ETRM: Managing the risk associated with the model.
« Model Owner:
In the case of the Hit-Rate Curve model,
it
is Strats Management.
The
dedicated contact is provided on the front matter of the document.
5
Model Testing
Calibrations were run on the year 2024 for the purpose of diagnostic and backtesting. Quantitative
performance measures were evaluated for each of the calibration runs. Model stress and sensitivity
tests were further carried out and results are presented in this section.
For the most part, the calibrations were based on a 2-month in-sample and 2-month out-of-
sample time periods on a German dataset. Where applicable, calibration outputs for client tier
5 were used to highlight key information.
Expert judgement was applied in choosing the test
datasets. Germany was picked as a representative country for its higher liquidity, providing a basis
129576: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 27 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
