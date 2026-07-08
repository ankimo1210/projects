# Page 018 - 日本語版

![Page 18](../assets/page_images/page_018.png)

## 日本語メモ

**該当箇所:** 3.2 Model Specification

単純ロジスティック回帰からRFQファクターを導入した拡張形までを定式化し、データ分割とサンプル数低下のトレードオフを説明する。

## 原文OCR/Text Layer

> OCR由来のため、誤認識があります。正確な図表・数式・レイアウトは上のページ画像を確認してください。

```text
Morgan Stanley
Confidential
6. Sample size: The sample size is sufficiently large to obtain valid conclusions from the model
fit. The data segmentation process is described in sections
3.2
Model Specification
3.2.1
Logistic Regression
The purpose of the model is to estimate the probability P of winning the auction given a spec-
ified percentage market spread captured x. The previous section explained the rationale behind
approximating a probability curve as a sigmoid function.
To this effect, a logistic functional approach has been elected as the best candidate as it is
sigmoid in nature. The model is well documented and understood in the literature, and is readily
available in standard, open-source Python packages.
For calibration we use the standard logistic regression Python implementation from the sklearn
package. Detailed documentation for the underlying mathematical logic is made available by the
developers [II].
The binary logistic regression function can be expressed as:
1
P(yi = 1 ki) = logistic(8.Ki + 80) = Trexp
ani — Bo)
(2)
Here, P is the predicted probability of winning the auction given a percentage market spread
captured «;, and is assumed to take values in the range of (0, 1). y; is the target variable, taking
values of 0 or 1. In our case, this would correspond to winning (1) or losing (0) the auction. Bo
and 8, are model constant and margin coefficient respectively.
Setting P(y; = 1|xi) = p(mi), the binary logistic regression will minimize a cost function ex-
pressed
as:
mn
( — yilog(p(wi)) — (1 — yi)log( — p(mi))) + 7(8)
(3)
Here,
represents model coefficients such that 8 = [80, Bx].
C is the inverse regularization
strength - to set no regularization, C can be set to a high value. r() is the regularization term.
Our setup uses L2 regularization, which is expressed as:
(3) = 568 Be
)
Additional detail on the solver and process are provided in the numerical implementation section
of this document.
3.2.2
Introduction of RFQ Factors and the Necessity of Data Segmentation
Recall from earlier that the purpose of the model is to build a map from given RFQ parameters
and the independent percentage market spread parameter # to the probability that the auction
will be won. The conditioning on an RFQ was specified in the exposition but not translated into
a concrete representation; that is the purpose of this section.
Let F denote a vector of factors associated with an RFQ. Factors can have numeric values,
such as log-notional or PVO1, or one-hot categorical values, such as customer tier. Such factors are
introduced into the model by extending the logistic regression function to the form:
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 18 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)
```
