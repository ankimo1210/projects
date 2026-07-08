# Page 021 - 日本語版

![Page 21](../assets/page_images/page_021.png)

## 日本語メモ

**該当箇所:** 3.3 Model Inputs and Data / 3.4 Outputs

オフライン校正と本番実装で使うデータソース、観測入力、特徴量、ターゲット変数、モデル出力を定義する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
+ percentageTwSpread: Percentage market (Tradeweb) spread captured, . The equations
below detail how this feature is calculated:
_ (twMid — MSQuote) x side
k=
‘Spread
x (-100)
(7)
where side is 1 for buy-inquiries, and -1 for sell. We add a (—100) multiplier such that a pos-
itive value would imply a positive probability of winning the auction. A visual representation
of this is shown in figure
+ log10quantity: Log of notional. This feature is supposed to capture the effect that RFQs
of larger sizes bear more risk. This is simply expressed as:
logl0quantity = logio(quantity)
(8)
The nature of the auction system is such that the customer is likely to choose the best available
price from dealers in competition. Therefore as « becomes small, the probability of winning
becomes larger for a fixed notional.
A higher spread capture is likely to be required to mitigate the risk of a larger-sized inquiry.
Assuming that the dealers in competition for these RFQs follow this logic, it can be expected
that the « values in competition would grow with notional.
If « remains constant,
it can
therefore be expected that an increase in notional (and thus logio(notional)) will increase the
probability of winning.
« dealerCountReciprocal: Reciprocal of dealer count, expressed
1
—_
¢
dealerCount
9)
dealerCount Reciprocal =
It can be expected that an increase in dealer count will decrease the probability of winning
for a fixed x, due to the added competition in the market. As a result, an increase in inverse
dealer count will increase the probability of winning for a fixed x.
Although the relationship between probability of trading and number of dealers is strong, it
is not linear in nature. The reciprocal is used to represent expert intuition that the rate of
decrease in winning probability should become smaller as dealer counts increase. For example,
for an increase from 2 to 3 dealers the decrement would be greater than for an increase from
8 to 9 dealers. This can be approximated using a 1/s relationship.
+ lifeRemaining: The instrument-specific percentage of life remaining until expiry, taking
values between 0 and 1. This is effectively a measure of liquidity - a business assumption is
made here that a newly issued bond is more liquid than an older issue with the same time
until maturity. For instance, a 5-year on-the-run bond with 5 years remaining until expiry
(100% life remaining) is considered more liquid than a 20-year bond with 5 years remaining
until expiry (25% life remaining). The feature is expressed as:
maturityDate — date
rsToM
aturity
=
10
yearsToM
aturity
=
(10)
date
—
i:
Dat
yearsSincel
ssue = "SSUES
(11)
365
:
Winning-Probability Model for EUGV RFQ Pricing
Page
21 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
