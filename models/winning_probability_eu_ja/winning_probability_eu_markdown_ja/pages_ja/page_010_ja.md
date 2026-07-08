# Page 010 - 日本語版

![Page 10](../assets/page_images/page_010.png)

## 日本語メモ

**該当箇所:** 2.4 Hit-Rate Curves

価格をサイド補正済みmarginに正規化し、marginと勝率の関係をhit-rate/probability curveとして扱う。図2で曲線の平行移動・急峻化を示す。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
2.4
From Price to Margin and the Introduction of Hit-Rate Curves
For the purpose of this document, we will use the terms hit-rate curves and probability curves
interchangeably. We also assume that the information presented in this subsection is applicable
to margin-related parameters, including market spread that is captured in a quote returned to the
customer. For the probability curve model presented here, we therefore use the following to also
explain the relationship between spread captured and trading probability.
Traders and Strats alike normalize quoted price, such as those pictured in table[I]
into margin,
and while doing so, the offer side is reflected to align with the bid. Margin is defined as
+1,
bid,
“1
ask
(1)
margin := sgn (side) x (mid — price)
where
sgn (side) = {
Margin is illustrated for the bid side in figure[J|
(a). Economically, to quote a small margin means
that the dealer quotes closer to mid and therefore gives up bid-offer spread to the customer, whereas
to quote a large (wide) margin means that the dealer seeks to capture bid-offer spread in the auction.
Margin can go negative, although doing so will lead to a loss over a round trip in position.
The interpretation of a hit-rate curve is pictured in figure [| Returning to pane (a), which
shows the bid side, when a proposed price p is near the bid or below, the probability of winning
the auction is low. As the proposed price increases, the fill probability increases, asymptotically
reaching unit probability for a high enough price. The shape of the curve is subject to study, but it
will monotonically increase from zero to one. Pane (b) flips the axes and plots margin rather than
price on the abscissa. The indicated curve is the hit-rate curve for a particular trade. Such a curve
can be parametric or nonparametric, both treatments have their advantages and disadvantages.
A simple picture of how one might calibrate a hit-rate curve is pictured in pane (c).
Under
this simplification, there are many historical auctions with the same economic parameters and
there is no censoring of the data.
In this hypothetical situation, a histogram of other dealer’s
quoted margins is constructed, from which the right-to-left accumulation leads to a sample-based
cumulative curve that: is, in effect, the hit-rate curve.
For a single curve in isolation, the two degrees of freedom are steepening / flattening, pictured
in pane (d), or left / right translation, pane (e). Steepening the curve is a reflection of inelasticity
in the market, which is to say, the dealer’s quote has to be close to the curve’s midpoint in order
to win the trade. To translate the curve to larger margin is to “fade” the quote in order to capture
more of the bid-ask spread; conversely, translation to smaller margin favors the client.
The driving force around calibration is to be able to compute a real-time hit-rate probability
for a previously unobserved quote request. Moreover, observations are not homogeneous, as the
hypothetical case in pane (c), but range across product type, client tier, dealer count, and other
central factors. For a parametric curve model, practical curves are mixtures of component sigmoid
curves when viewed across the range of observed outcomes.
2.5
The MS Autoquoting Complex
Let us now turn our attention to the Morgan Stanley RFQ autoquoting complex that is pictured
in a summary form in figure
External markets are indicated at the top and right-of-center, and the dotted line delimits the
boundary within which the complex resides. The components of and information flow through the
diagram are addressed in turn:
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 10 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
