# Page 023 - 日本語版

![Page 23](../assets/page_images/page_023.png)

## 日本語メモ

**該当箇所:** 3.5-3.6 Calibration / Numerical Implementation

モデル校正、パラメータ推定、数値実装、パッケージや実行上の注意点を扱う。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
+ RFQs are limited to those involving products of interest - the scope of applicability for the
model is defined in the previous section. Backtesting results are presented in section
for the following countries, for which the model is made available in production: Austria,
Belgium, Germany, Spain, EU, France, Ireland, Italy, Netherlands, Portugal, UK and UK
inflation.
+ The data is then enriched with any and all additional information required specifically for the
calibration process - input features are calculated at this stage using the equations detailed
in section B.3.3)
+ Finally, for each segmentation potential outliers are eliminated. For instance, in an environ-
ment where spreads typically tend to be tighter (eg. competitive liquid market conditions), it
can be expected that the market spread captured should be low for an inquiry to be traded.
‘Done’ inquiries with high spread captured compared to the rest of the dataset can therefore,
in this example, be considered outliers. Expert judgement is applied to the definition and
threshold of outlier inquiries as they may differ depending on the market environment and
for each segmentation. In the examples provided later in the document, extreme outliers are
considered below -100 and above 50 for percentage market spread captured on any inquiry -
for clarity, the thresholds applied are the same for each dataset.
+ The model is not typically applied to single dealer inquiries with a pre-agreed price - these
inquiries are likely to be won, as MS is the only dealer considered for the auction. Other price
constructions can be preferred in these cases, following expert judgement from the business.
In general single-dealer inquiries are removed from calibration datasets as they may skew the
results obtained.
The calibration process is run on the saved data using a Jupyter python notebook which itself
calls a set of python scripts. The location of the underlying code is provided later in this document.
Calibrations are typically first run manually to find the optimal balance between data segmentation,
lookback timeframes, model maintainability, computational efficiency, and accuracy compared to
production data. This is usually done for new datasets or in agreement with traders if the business
focus is changed. Manual calibrations can also be run in case of process failure.
Automated scripts provide the capability to run the calibration process on a schedule, generally
daily, with the latest update trained and tested on the most recent datasets. Model outputs of
automated runs are stored for each data segment in a shared location, accessible by downstream
pricing components.
The python notebook presents results in
a manner that allows us to easily compare the most
up-to-date calibration with the model currently in use, as well as with production data. The metrics
presented help us make an informed decision on the necessity to update the production model. If
the parameters remain stable through time (as detailed in section
and no significant increase
in accuracy is noted, then it is generally the case that the model coefficients will not be updated
in production outside of a pre-defined schedule.
It is typically the case that coefficients will be updated for all segments on a monthly basis, in
order to remain aligned with most recent market information.
3.6
Numerical Implementation
The model is implemented in Python using data that is queried via kdb+ from the BMET database.
Calibration of the model uses the open-source Python tools listed below. No bespoke calibration
tools are used. See section [8.3] for the location of the calibration source code.
129576: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 23 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
