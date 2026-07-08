# Verified Numbered Equations

This file manually checks the numbered equations against the rendered page images. Use the page images as the final visual source of truth.

## Page 10, Equation (1)

```math
margin := \operatorname{sgn}(side) \times (mid - price), \quad
\operatorname{sgn}(side)=
\begin{cases}
+1, & bid \\
-1, & ask
\end{cases}
```

## Page 18, Equation (2)

```math
P(y_i = 1 \mid \kappa_i)
= \operatorname{logistic}(\beta_{\kappa}\kappa_i + \beta_0)
= \frac{1}{1+\exp(-\beta_{\kappa}\kappa_i - \beta_0)}
```

## Page 18, Equation (3)

```math
\min_{\beta} C \sum_{i=1}^{n}
\left(-y_i \log(\hat{p}(\kappa_i)) - (1-y_i)\log(1-\hat{p}(\kappa_i))\right)
+ r(\beta)
```

## Page 18, Equation (4)

```math
r(\beta)=\frac{1}{2}\beta_{\kappa}^{T}\beta_{\kappa}
```

## Page 19, Equation (5)

```math
\hat{p}(\kappa_i, RFQ)
= \operatorname{logistic}(\beta_{\kappa}\kappa_i + \beta_0 + \beta_{RFQ}^{T}F_{RFQ})
= \frac{1}{1+\exp(-\beta_{\kappa}\kappa_i - \beta_0 - \beta_{RFQ}^{T}F_{RFQ})}
```

## Page 19, Equation (6)

```math
r(\beta)=\frac{1}{2}\beta^{T}\beta
```

## Page 21, Equation (7)

```math
\kappa = \frac{(twMid - MSQuote) \times side}{twSpread} \times (-100)
```

## Page 21, Equation (8)

```math
log10quantity = \log_{10}(quantity)
```

## Page 21, Equation (9)

```math
dealerCountReciprocal = \frac{1}{dealerCount}
```

## Page 21, Equation (10)

```math
yearsToMaturity = \frac{maturityDate - date}{365}
```

## Page 21, Equation (11)

```math
yearsSinceIssue = \frac{date - issueDate}{365}
```

## Page 22, Equation (12)

```math
lifeRemaining
= \frac{yearsToMaturity}{yearsToMaturity + yearsSinceIssue}
= \frac{maturityDate - date}{maturityDate - issueDate}
```

## Page 22, Equation (13)

```math
win =
\begin{cases}
1, & inquiryState = Done \\
0, & inquiryState \in \{TradedAway, TiedTradedAway, Covered, CoverTied\}
\end{cases}
```

## Page 34, Equation (14)

```math
realizedHitRate = \frac{1}{N}\sum_{i=1}^{N}(y_i == 1)
```

## Page 34, Equation (15)

```math
predictedHitRate = \frac{1}{N}\sum_{i=1}^{N}\hat{p}_i
```

## Page 36, Equation (16)

```math
hitRateDiff = \left|predictedHitRate - realizedHitRate\right|
```
