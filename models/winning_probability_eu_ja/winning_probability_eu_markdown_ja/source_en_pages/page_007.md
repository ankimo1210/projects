# Page 7

![Page 7](../assets/page_images/page_007.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
a)
b)
QuoteRequest
Quote
ane
security
+> dir 2
]
security
dir 2
}
;
Tw
.
quantity
ar3
quantity
dr3
# dealers
++ dir4
]
# dealers
dir4
|
c)
~~
prices
async
ExecutionReport
done, cover px, tie status
choose dlr 1
ah
| dir
2) done away
Tw
[|
>
{ars | done away } possible additional information
+
—f dir
4) done away
QuoteResponse
Figure 1: The RFQ lifecycle for a single outright trade. a) A customer initiates an RFQ sequence by
sending an inquiry to a marketplace such as Tradeweb. The inquiry includes economic information
such as security, size, and side, as well as a list of dealers who are invited to quote. TW in
turn communicates to the selected dealers the economic information along with the identity of the
customer. b) The dealers respond with a Quote message. c) The customer chooses the best price,
and in the case of ties, choses the winning dealer. TW then communicates selective information
back to all dealers.
To begin, pane (a) shows the initiation of an inquiry.
Here, a customer specifies security,
quantity (or size), side (buy or sell), a list of dealers who are invited to quote, and a maximum
timeout period for which the auction will be live. The customer message is sent to a marketplace,
such as Tradeweb, that in turn sends QuoteRequest messages to the specified dealers, four in this
case. The QuoteRequest message includes the economic and timing information specified by the
customer along with the customer details. In pane (b), the dealers respond to the RFQ with quotes
(prices). They do so by sending a Quote message, and these messages are received by TW as the
dealers respond (assuming they respond within the timeout period).
In pane (c), the customer
chooses the quote that has the best price, and if two or more dealers tie, the customer chooses
the dealer with whom they would like to trade. As pictured, the customer chooses dealer 1. How
Tradeweb replies to all dealers involved in the auction creates complexity, and that is the topic of
the next section.
2.3.
Censored Economic Information from RFQ Auctions
From a business perspective, marketplaces that host RFQ auctions offer minimal information leak-
age to market participants, and for this reason, complexity exists in how the marketplace informs
the participating dealers of an auction’s outcome. The partial information transmitted to dealers
after the auction is an example of censored information.
From a dealer’s perspective, there are four pieces of economic information that are important
given the outcome of an auction: The first is the winning price.
The dealer who receives an
ExecutionReport message knows the winning price because it is theirs. The second is the cover
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page
7 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
