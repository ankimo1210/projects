# Page 006 - 日本語版

![Page 6](../assets/page_images/page_006.png)

## 日本語メモ

**該当箇所:** 2.1 The Search for Liquidity / 2.2 RFQ Lifecycle

RFQ市場が流動性と情報秘匿をどう両立するか、また顧客・マーケットプレイス・ディーラー間のRFQライフサイクルを説明する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
2.1
The Search for Liquidity
Liquidity is a central concern for market participants: some participants seek to profit by providing
(making) liquidity, while others seek to profit by holding positions that they acquire by taking
liquidity. Two key economic roles of security marketplaces are to organize a market and to pool
liquidity so that prices are transparent and transactions are easier to access, and it is on these
marketplaces that liquidity makers and takers can meet. Yet, all market participants are econom-
ically driven to not show their full intent, for doing so would lead other participants to react to
their own advantage while disadvantaging overly expressive participants. Accordingly, makers do
not display their total available liquidity, nor do takers reveal the true size that they wish to get
done. On streaming marketplaces, such as equities, treasuries, and foreign exchange (FX), market-
places help—in some cases and to a degree—participants mask their intent while still promoting
best execution.
For instance, some equities markets offer non-display order types for liquidity
providers whereby orders rest latently but hidden from view on the marketplace’s orderbook; some
FX markets offer so-called iceberg orders that achieve the same purpose; and treasury markets like
BrokerTec have a workup phase wherein a taker can show true size once the trade price is agreed.
Bouchaud et al. quantitatively show that the equilibrium between makers and takers on streaming
markets is only marginally stable, and that liquidity replenishment is fundamental to the stability
of the markets [J chs. 18-20].
‘An alternative to streaming markets are multilateral auction markets. Tradeweb (TW) was
a pioneer in the development of RFQ markets for EUGV bonds, where, historically, dealers were
reluctant to display liquidity to streaming markets, where intent would be broadcast to all observers,
albeit anonymously. Tradeweb’s success has led to their expansion to other likeminded security
classes such as credit, repo, and swaps, in both domestic and international markets; and their
success has also led other marketplaces to add an auction model, Bloomberg being a well-known
example.
In the RFQ markets, which are typically business-to-customer, or “b2c,” a customer initiates
an auction, a limited number of dealers are invited to quote on the customer’s request, and the
hosting marketplace intermediates the deal, which may or may not end in a trade. By using the
RFQ auction process, the customer partially masks his or her intent by inviting a limited number
of dealers, and the dealers need only respond to a particular inquiry, thus satisfying the incentives
on both sides to not broadcast intent. Such RFQ auctions are discrete in the sense that an auction
begins at customer initiation and definitively ends in a deal or no deal. Moreover, the auctions do
not occur on a schedule but only when a customer initiates.
Today’s RFQ markets are highly automated. While there are several factors that drive automa-
tion, one of them is to relieve the trading desk from having to quote on a daily basis hundreds of,
if not a few thousand, requests that can be classified as “business as usual.” Tickets that have a
large size, or edge close to the risk limits, or are for unusual securities, go manual because they
require additional human attention. Automation has in turn driven the need for fast response times
in order to compete with other dealers. Regardless of which quantitative model is chosen for the
RFQ markets, it has to cover business-as-usual tickets and be simple enough to quickly compute a
quote. Moreover, good quantitative models have behavior that is explainable.
2.2
The RFQ Lifecycle
It is necessary to understand the RFQ process before contemplating the design of a model, and
for this purpose, figure [I] illustrates a three-step RFQ lifecycle for a simple, single inquiry for an
outright security.
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 6 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
