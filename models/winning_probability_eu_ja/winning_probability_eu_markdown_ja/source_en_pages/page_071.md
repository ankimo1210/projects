# Page 71

![Page 71](../assets/page_images/page_071.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
9.2
Escalation criteria
The following conditions would trigger escalation.
Metric thresholds:
+ HR diff > 15%, OR
+ AP score diff < 0
Historical data, backtesting results and baseline thresholds were used to determine the upper
limits above. Threshold breaches are accepted by the business for segments which account for lower
than 10% of the total inquiry count or notional. A breach of one of the two metric thresholds above
for 10 consecutive business days, for a segmentation with a percentage of the inquiry flow higher
than 10%, would trigger an escalation to MRM.
Upon trigger of the pre-agreed thresholds between MRM and the model owner, the model devel-
opers will send a notification to the MRM as soon as possible but within 1 week. The notification
will include information on the trigger and the explanation of the reason of the trigger. If remedia-
tion or any action is required, model developers need to let MRM know the associated actions taken
to remediate the trigger. The review of the triggers as well as the conclusions will be presented to
MRM within 6 weeks. If for any reason the notification on threshold breach or the conclusion are
not going to be sent within the deadline, MRM is notified prior to the deadline and Strats provide
a new expected deadline for the completion of the action.
9.3
Data shared with MRM
Model developers generate performance metrics on a daily basis using an automated process. The
data is stored in
a
Gobi database that MRM has been given access to: table name ‘eratesOngMon-
Metrics’, kdb gateway bmet-gobi-eratesmrm-prod.ms.com.
10
Model Change Log
Rational and Commentary of Changes
1
2023-03-13
| Initial submission.
2
2024-01-05
| Tiering justification provided.
3
2024-01-29
| On-going monitoring, monitoring metric and SLDC criteria updated.
4
2024-07-15
| Model scope expansion to EU bonds.
5
2024-09-05
| Model scope expansion to UK Gilt bonds and use of a three-feature calibration
for Gilts.
6
2024-12-04
| Model revalidation.
7
2025-03-12
| Model scope expansion to UK inflation bonds.
11
References
[1] “ISG model control procedures for algorithmic trading model,” 2023.
129576:
Winning-Probability Model
for
EUGV
RFQ
Pricing
Page 71 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
