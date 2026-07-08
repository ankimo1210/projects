# 検証済み数式 - 日本語版

以下は元PDFの番号付き数式 (1)-(16) を、ページ画像で再確認した上でMarkdown/LaTeXで読みやすく再掲したものです。LaTeX内の変数名は原文に合わせ、日本語は数式外に置いています。

## 式 (1): marginの定義

価格をbid/askの向きで補正し、midからの距離としてmarginを定義します。

```math
margin := \operatorname{sgn}(side) \times (mid - price), \quad
\operatorname{sgn}(side)=
\begin{cases}
+1, & bid \\
-1, & ask
\end{cases}
```

## 式 (2): 単純ロジスティック回帰

percentage market spread capturedだけを使い、auctionに勝つ確率を推定します。

```math
P(y_i = 1 \mid \kappa_i)
= \operatorname{logistic}(\beta_{\kappa}\kappa_i + \beta_0)
= \frac{1}{1+\exp(-\beta_{\kappa}\kappa_i - \beta_0)}
```

## 式 (3): コスト関数

二値ロジスティック回帰の対数損失に正則化項を加えた目的関数です。

```math
\min_{\beta} C \sum_{i=1}^{n}
\left(-y_i \log(\hat{p}(\kappa_i)) - (1-y_i)\log(1-\hat{p}(\kappa_i))\right)
+ r(\beta)
```

## 式 (4): L2正則化

margin係数に対するL2正則化項です。

```math
r(\beta)=\frac{1}{2}\beta_{\kappa}^{T}\beta_{\kappa}
```

## 式 (5): RFQ特徴量を含むロジスティック回帰

RFQ固有の特徴量ベクトルを加えて、曲線をmargin軸方向に平行移動させる形です。

```math
\hat{p}(\kappa_i, RFQ)
= \operatorname{logistic}(\beta_{\kappa}\kappa_i + \beta_0 + \beta_{RFQ}^{T}F_{RFQ})
= \frac{1}{1+\exp(-\beta_{\kappa}\kappa_i - \beta_0 - \beta_{RFQ}^{T}F_{RFQ})}
```

## 式 (6): 全係数に対するL2正則化

```math
r(\beta)=\frac{1}{2}\beta^{T}\beta
```

## 式 (7): market spread capturedの定義

Tradeweb mid、MS quote、side、Tradeweb spreadから、percentage market spread capturedを定義します。

```math
\kappa = \frac{(twMid - MSQuote) \times side}{twSpread} \times (-100)
```

## 式 (8): 数量の対数

```math
log10quantity = \log_{10}(quantity)
```

## 式 (9): dealer count reciprocal

```math
dealerCountReciprocal = \frac{1}{dealerCount}
```

## 式 (10): 満期までの年数

```math
yearsToMaturity = \frac{maturityDate - date}{365}
```

## 式 (11): 発行からの年数

```math
yearsSinceIssue = \frac{date - issueDate}{365}
```

## 式 (12): 残存ライフ比率

```math
lifeRemaining
= \frac{yearsToMaturity}{yearsToMaturity + yearsSinceIssue}
= \frac{maturityDate - date}{maturityDate - issueDate}
```

## 式 (13): winターゲットの定義

```math
win =
\begin{cases}
1, & inquiryState = Done \\
0, & inquiryState \in \{TradedAway, TiedTradedAway, Covered, CoverTied\}
\end{cases}
```

## 式 (14): 実現hit rate

```math
realizedHitRate = \frac{1}{N}\sum_{i=1}^{N}\mathbf{1}_{\{y_i=1\}}
```

## 式 (15): 予測hit rate

```math
predictedHitRate = \frac{1}{N}\sum_{i=1}^{N}\hat{p}_i
```

## 式 (16): hit rate差分

```math
hitRateDiff = \left|predictedHitRate - realizedHitRate\right|
```
