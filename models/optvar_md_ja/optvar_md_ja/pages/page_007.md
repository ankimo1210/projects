# Page 007

![Page 007](../assets/page_images/page-007.jpg)

## OCR layout text

```text
Morgan Stanley                                                                             Confidential


                                                     <—   inventory

                  on                                        projected risk—p> 77




Figure 3: This figure is a representation of the risk posed by a new bond purchase (red). This
risk is projected onto the liquid instruments at the maturities 3 or 5, the blue dotted boxes. This
results in the target hedge, given by the dark blue boxes. The concept is that the illiquid red bond
can be hedged by selling the liquid blue.
     ‘The Opt-Var model is the key component of the autohedger algo, which is used for determining
the optimal hedging strategy given a set of constraints. It is used as the primary hedging model for
the Electronic Government Bond business, both in the US and in Europe. The Opt-Var optimization
is called repeatedly throughout the day and prescribes the optimal hedging trades given the current
positions. The model reports a vector of trade quantities that require to be executed to achieve
the lowest risk-adjusted cost of hedging.
    ‘The set of trades that are hedged by the autohedger corresponds to client flow incoming from
external avenues like request-for-quotation (RFQ) or streaming, as well as internal client streams
consisting mainly of hedging activity from other internal Fixed Income desks.
    This document describes the construction of the Opt-Var model, which consists of of a quadratic
optimization problem which relies on the statistical estimation of risk and costs as inputs.
    The model is located within the JAVA market making library, which itself is part of the eRates
technology stack handling the Firm’s electronic rates business. Algorithmic risk controls are handled
by Morgan Stanley’s Electronic Trading Risk Management (ETRM) system, and the controls can
be found in the Firm’s Model Control System (MCS).
1.2.   Model Description Summary
The model covered in this document - Opt-Var - produces as output a proposed set of trades
required to be executed within a reasonable time horizon in order to achieve an optimal hedging
strategy - that is, reaching an optimal balance between the residual risk of the portfolio and the
cost of hedging.
    ‘The residual risk of the portfolio is measured by the total portfolio covariance. This covariance
is calculated by first applying a risk projection of all the portfolio positions onto a finite set of
liquid instrument (in DVO1 dollar value of 1 basis point; or PVO1 present value of 1 basis point in
EU) sensitivities vector. The vector of liquid instrument risks is then multiplied with a covariance
matrix to obtain the total portfolio covariance.
    ‘The cost of hedging is calculated by multiplying the hedge quantity with the hedge cost per unit
ofeach instrument. If any alpha signal is used in the autohedger, the cost of hedging will also include
the reduction of alpha capturing due to the hedging activity. The preference between risk and cost
- that is, the level of risk-aversion of the hedging strategy - is controlled via a hyperparameter
denoted by A. A quadratic optimization problem is posed and solved in order to obtain the optimal
hedging strategy for the current portfolio.


130115: Opt-Var                                                                           Page 7 of 136

                       [git] « Branch: iropt-var@be27d1a = Release:    (2024-10-31)
```
