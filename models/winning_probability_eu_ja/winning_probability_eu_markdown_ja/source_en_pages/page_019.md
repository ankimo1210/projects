# Page 19

![Page 19](../assets/page_images/page_019.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
segmentation
| segment-count
_median-rec-count
_min-rec-count
_max-rec-count
none
1
1331524
1331524
1331524
country
u
47366
5804
350265
country-tier
75
3498
8
162871
country-tier-notional
220
1263
1
90986
Table 2: As the number of segmentation axes increases, the number of segments quickly increases
while the number of records in a segment quickly decreases. Records in the dataset include EUGV
and UKGV RFQs from 2024/01/01 to 2024/11/28.
1
1+ exp(—Bxtti — Bo — BhrgF RFQ)
Note that here, p(x,
RFQ) = P(y: = 1|s:, RFQ). With the introduction of RFQ factors, the
cost function remains largely similar, with the exception that the regularization term now becomes:
(xi, RFQ) = logistic( 8.4: + 80 + BhrqF RFQ) =
(5)
r(8) = 56t8
(6)
where 8 accounts for all coefficients of the model apart from the intercept, such that 8 = [9, 8x, Baral:
Critically, observe that presence of F can only translate the curve along the margin axis, as
shown in figure } the steepness of the curve is not adjusted because it is solely governed by the
value of ;.
In order to model curves that have different levels of steepness, the data must be
grouped into segments that share a common slope, thus introducing the need for sample grouping.
3.2.3.
Data Segmentation and the Splintering of Record Counts
Rather than introducing RFQ factors into the logistic function, as per equation (5), we can consider
segmenting the data along various RFQ axes and then calibrating a probability curve for each. The
challenge with this approach is that the number of observed records is finite, and as more axes are
introduced on which to segment the data, the fewer records are available on which to calibrate.
A straight-forward example is shown in table}
where the inquiry data is taken from 2024/01/01
to 2024/11/28. The segmentation column indicates the axes along which the data is segmented.
In the first row, the data is not segmented at all. The subsequent rows then further split the data
into countries, then client tiers, and finally notional buckets (0-100k, 100k-1m, 1m-10m, 10m+).
‘As can be seen the median record count drops precipitously, and there are segments with
only one record.
Based on these types of analyses, it is apparent that a compromise between
segmentation and translation-based factor introduction needs to be struck.
3.3.
Model Inputs and Data
3.3.1
Data Sources
Data sources are comprised of both internal and external feeds, recorded in internal databases for
future access. The section is split into two parts. In the first, the data sources for the probability
curve calibration process are presented - this will be referred to as the ‘offline’ phase of the method-
ology. In the second, the data sources used by the implementation of the model in production are
126
6: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 19 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
