# Page 65

![Page 65](../assets/page_images/page_065.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
5.5.12
UK
In line with on-going monitoring performance reports, the below results show out-of-sample results
for the UK dataset backtest. Metrics are produced as per the methodology described in section J}
Daily results over the timeframe Jan-Jun 2024 have been reviewed and approved by MRM - the
below shows out-of-sample results for the last business date of each month.
Test Period
HR Diff (%)
AP Score Diff (%)
Jan 24
6.2
28.9
Feb 24
5.8
29.4
Mar 24
6.2
27.8
Apr 24
5.9
27.6
May 24
5.8
27.6
Jun 24
45
31.0
6
Model Limitations, Uncertainties and Mitigations
No limitations have been identified for the model.
7
Model Overlays and Overrides
In the online process, the winning-probability model detailed herein operates within the Algo
Pricing technology component which feeds to the Quote Manager as model-based margin. Overrides
and controls exist in the reconstruction of the probability curves for incoming RFQs.
As algo
components, Electronic Trading Risk Management (ETRM) sets controls on the algo operation,
and these controls are captured by the Model Control System (MCS).
In addition to this, other key stakeholders (Algo Traders) have immediate access to overriding
the use of the model should a different approach for pricing better fit their business requirements
at the time. The model can then be turned back on at any stage. Trading overrides are also used
in potential cases where the model is not providing an output in production, or where input data
cannot be retrieved correctly.
In the offline process, overlays exist in the stakeholders’ ability to override outputs of the model
calibration before implementation in production.
The reasoning and available methods to do so
8
Production Implementation and Controls
8.1
Production Implementation
The production code is written in Java. The production implementation of the covered model(s)
was developed in adherence to the Firm’s software-development lifecycle (SDLC) policy [JJ. The
following table summarizes the locations of the source code, its lifecycle management, and the
location of test artifacts that confirm correct implementation.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 65 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
