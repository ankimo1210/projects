# Data Normalization for Bilinear Structures in High-Frequency Financial Time-series

Dat Thanh Tran ∗ , Juho Kanniainen ∗ , Moncef Gabbouj ∗ , Alexandros Iosifidis †

Department of Computing Sciences, Tampere University, Finland

Department of Engineering, Aarhus University, Denmark

∗ †

Email: { thanh.tran, juho.kanniainen, moncef.gabbouj } @tuni.fi, alexandros.iosifidis@eng.au.dk

Abstract -Financial time-series analysis and forecasting have been extensively studied over the past decades, yet still remain as a very challenging research topic. Since the financial market is inherently noisy and stochastic, a majority of financial timeseries of interests are non-stationary, and often obtained from different modalities. This property presents great challenges and can significantly affect the performance of the subsequent analysis/forecasting steps. Recently, the Temporal Attention augmented Bilinear Layer (TABL) has shown great performances in tackling financial forecasting problems. In this paper, by taking into account the nature of bilinear projections in TABL networks, we propose Bilinear Normalization (BiN), a simple, yet efficient normalization layer to be incorporated into TABL networks to tackle potential problems posed by non-stationarity and multimodalities in the input series. Our experiments using a large scale Limit Order Book (LOB) consisting of more than 4 million order events show that BiN-TABL outperforms TABL networks using other state-of-the-arts normalization schemes by a large margin.

## I. INTRODUCTION

Although we have observed great successes in time-series and sequence analysis [1], [2], [3], [4], [5], [6], and the topic in general has been extensively studied, we still face great challenges when working with multivariate time-series obtained from financial markets, especially high-frequency data. In High-Frequency Trading (HFT), traders focus on short-term investment horizon and profit from small margin of the price changes with large volume. Thus, HFT traders rely on market volatility to make profit. This, however, also poses great challenges when dealing with the data obtained in the HFT market.

Due to the unique characteristics of financial market, we still need a great amount of efforts in order to have the same successes as in Computer Vision (CV) [7], [8], [9], [10], [11], [12] and Natural Language Processing (NLP) [13], [14]. On one hand, the problems targeted in CV and NLP mainly involve cognitive tasks, whose inputs are intuitive and innate for human being to visualize and interpret such as images or languages while it is not our natural ability to interpret financial time-series. On the other hand, images or audio are well-behaved signals in a sense that the range or variances are known or can be easily manipulated without loosing the characteristic of the signal, while financial observations can exhibit drastic changes over time or even at the same time instance, signals from different modalities can be very different such as the stock prices. Thus data preprocessing plays an important role when working with financial data.

Perhaps the most popular normalization scheme for timeseries is z-score normalization, i.e. transforming the data to have zero-mean and unit standard deviation, or min-max normalization, i.e., scaling the values of each dimension into the range [0 , 1] . The limitation in z-score or min-max normalization lies in the fact that the statistics of the past observations (during training phase) are used to normalize future observations, which might possess completely different magnitudes due to non-stationarity or concept drift. In order to tackle this problem, several sophisticated methods have been proposed [15], [16]. In addition, hand-crafted stationary features, econometric or quantitative indicators with mathematical assumptions of the underlying processes are also widely used. These financial indicators can sometimes perform relatively well after a long process of experimentation and validation, which, however, prevents their practical implementation in HFT [17].

Different from the aforementioned model-based approaches, data-driven normalization methods aim to directly estimate relevant statistics which are specific to the given analysis task in an end-to-end manner. That is, the normalization step is implemented as a neural network layer whose parameters are jointly optimized with other layers via stochastic gradient descend. Perhaps the most widely used formulation is Batch Normalization (BN) [18], which was originally proposed for visual data. BN, however, is mostly used between hidden layers to reduce internal covariate shifts. Proposed for the task of visual style transfer, Instance Normalization (IN) [19] was very successful in normalizing the constrast level of generated images. For time-series, an input normalization layer that learns to adaptively estimate the normalization statistics in a given time-series, which outperforms existing schemes, was proposed in [20].

Existing data-driven approaches, however, neglect the tensor structure inherent in multivariate time-series, performing normalization only along the temporal mode of time-series. In order to take advantage of the tensor representation, the authors in [1] proposed TABL networks which separately capture linear dependency along the temporal and feature dimension in each layer. Since TABL network performs a sequence of weighted sum alternating between the temporal and feature dimension, we propose a data-driven normalization strategy that takes into account statistics from both temporal and spatial dimensions, which is dubbed as Bilinear Normalization (BiN). Combining BiN with TABL, we show that BiN-TABL networks significantly outperforms TABL networks using other normalization strategies in the mid-price movement prediction problem using a large scale Limit Order Book dataset.

The remainder of the paper is organized as follows. Section 2 reviews related literature in data normalization. In Section 3, we describe the motivation and processing steps of our Bilinear Normalization layer. In Section 4, we provide information about experiment setup, present and discuss our empirical results. Section 5 concludes our work.

## II. RELATED WORK

Deep neural networks have seen significant improvement over the past decades thanks to the advancement in both hardware and algorithms. On the algorithmic side, training deep networks comprising of multiple layers can be challenging since the distribution of each layer's inputs can change significantly during the iterative optimization process, which harms the error feedback signals. Thus, by manipulating the statistics between layers, we have seen great improvements in optimizing deep neural networks. An early example is the class of initialization methods [21], [22], which initialize the network's parameters based on each layer's statistics. However, most of the initialization methods are data independent. A more active approach is the direct manipulation of the statistics by learning them jointly with the network's parameters with the early work called Batch Normalization (BN) [18]. BN estimates global mean and variance of input data by gradually accumulating the mini-batch statistics. After standardizing the data to have zero-mean and unit variance, BN also learns to scale and shift the distribution. Instead of minibatch statistics, Instance Normalization [19] uses sample-level statistics and learns how to normalize each image so that its contrast matches with that of a predefined style image in the visual style transfer problems. Both BN and IN were originally proposed for visual data, although BN has also been widely used in NLP.

We are not aware of any data-driven normalization scheme for time-series, except the recently proposed Deep Adaptive Input Normalization (DAIN) formulation [20], which applies normalization to the input time-series via a 3-stage procedure. Specifically, let { X ( i ) ∈ R D × T ; i = 1 , . . . , N } be a collection N time-series where T denotes the temporal dimension and D denotes the spatial/feature dimension. In addition, we denote x ( i ) 2 ( t ) ∈ R D the representation (temporal slice) at time instance t of series i . Here the subscript denotes the tensor mode (1 for feature slices and 2 for temporal slices). DAIN first shifts the input time-series by:

<!-- formula-not-decoded -->

where W a ∈ R D × D is a learnable weight matrix that estimates the amount of shifting from the mean temporal slice ( a ( i ) ) calculated from each series.

After shifting, the intermediate representation y ( i ) 2 ( t ) is then scaled as follows:

<!-- formula-not-decoded -->

where W b ∈ R D × D is a learnable weight matrix that estimates the amount of scaling from the standard deviation ( b ( i ) ) along the temporal dimension. In Eq. (2), the square-root operator is applied element-wise; ⊙ and varoslash denote the element-wise multiplication and division, respectively.

The final step in DAIN is gating, which aims to suppress irrelevant features:

<!-- formula-not-decoded -->

where W c ∈ R D × D and W d ∈ R D are learnable weights.

Overall, DAIN takes the input time-series X ( i ) and outputs its normalized version ˜ X ( i ) by manipulating its temporal slices. As we will see in the next Section, our BiN formulation is much simpler (requiring few calculations) and more intuitive compared to DAIN when using with TABL networks.

## III. BILINEAR NORMALIZATION (BIN)

Our proposed BiN layer formulation bears some resemblances to DAIN and IN in that BiN also uses sample-level statistics to manipulate the input distribution. That is, each input sample is normalized based on its statistics only. This is different from BN, which uses global statistics calculated and aggregated from mini-batches. BiN differs from DAIN and IN in that we propose to jointly normalize the input timeseries along both temporal and feature dimensions, taking into account the property of bilinear projection in TABL networks.

The core idea in TABL networks is the separate modeling of linear dependency along the temporal and feature dimension. That is, the interactions between temporal slices and feature slices are captured by bilinear projection:

<!-- formula-not-decoded -->

where W 1 ∈ R D 1 × D and W 2 ∈ R T × T 1 are the projection parameters, and Y ( i ) ∈ R D 1 × T 1 is the transformed series.

In Eq. (4), W 2 linearly combines T temporal slices x ( i ) 2 ( t ) ( t = 1 , . . . , T ) in X ( i ) . That is, the function of W 2 is to capture linear patterns in local temporal movement. On the other hand, W 1 linearly combines a set of D feature slices x ( i ) 1 ( d ) ∈ R T ( d = 1 , . . . , D ), i.e., row vectors of X ( i ) , to model local interactions among D different univariate series.

Due to the above property, it is intuitive to shift and scale not only the distribution of temporal slices x ( i ) 2 ( t ) but also that of feature slice x ( i ) 1 ( d ) . To this end, we propose BiN, which can learn how to jointly manipulate the input data distribution along the temporal and feature dimension.

The normalization along the temporal dimension in BiN is described by the following equations:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

where γ 2 ∈ R D and β 2 ∈ R D are two learnable weight vectors of BiN. In addition, 1 T ∈ R T is a constant vector having all elements equal to one and 1 T T ∈ R 1 × T is its transpose.

In short, given an input series, we first calculate the mean temporal slice ¯ x ( i ) 2 ∈ R D and its standard deviation σ ( i ) 2 ∈ R D as in Eq. (5a, 5b), which are then used to standardize each temporal slice of the input as in Eq. (5c) before applying element-wise scaling (using γ 2 ) and shifting (using β 2 ) as in Eq. (5d).

In order to interpret the effects of Eq. (5), we can view the input series X ( i ) as the set T ( i ) consisting of T temporal slices, i.e., a set of points in D -dimensional space. The process in Eq. (5c) moves this set of points around the origin and as well as controlling their spread while keeping their arrangement pattern similarly. If we have two input series X ( i ) and X ( j ) with T ( i ) and T ( j ) spread and lie in two completely different areas of this D -dimensional space but have the same arrangement pattern, without the alignment performed by Eq. (5c), we cannot effectively capture the linear or nonlinear 1 arrangement patterns of these points using W 2 in Eq. (4). Here we should note that although BiN applies additional scaling and shifting as in Eq. (5d) after the alignment, the values of γ 2 and β 2 are the same for every input series, thus still keeping their alignments. Since γ 2 and β 2 are optimized together with TABL network's parameters, they enable BiN to manipulate the aligned distributions T ( i ) to match with the statistics of other layers.

1 Nonlinear patterns can be estimated by several piece-wise linear patterns (by setting the second dimension of W 2 larger than 1, i.e., T 1 &gt; 1 )

While the effect of non-stationarity in the temporal mode are often visible and has been heavily studied, its effects when considered from the feature dimension perspective are less obvious. To see this, let us now view the series X ( i ) as the set D ( i ) of D points (its D feature slices) in a T -dimensional space. Let us also take the previous scenario where two series, X ( i ) and X ( j ) , have T ( i ) and T ( j ) scattered in different regions of a D -dimensional co-ordinate system (viewed under the temporal perspective) before the normalization step in Eq. (5). When T ( i ) and T ( j ) are very far away, being viewed from the feature perspective, these two series are also likely to possess D ( i ) and D ( j ) which are distributed in two different regions of a T -dimensional co-ordinate system, although having very similar arrangement. This scenario also prevents W 1 in TABL networks to effectively capture the prominent linear/nonlinear patterns existing in the feature dimension of all input series. Thus, BiN also normalizes the input series along the feature dimension as follows:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

where γ 1 ∈ R T and β 1 ∈ R T are two learnable weights, and the superscript ( . ) T denotes the transpose operator.

Overall, BiN takes as input the series X ( i ) and outputs ˜ X ( i ) , which is the linear combination of ˜ X ( i ) 1 and ˜ X ( i ) 2 from Eq. (6d) and (5d), respectively:

<!-- formula-not-decoded -->

where λ 1 ∈ R and λ 2 ∈ R are two learnable scalars, which enables BiN to weigh the importance of temporal and feature normalization. Here we should note that λ 1 and λ 2 are constrained to be non-negative. This constraint is achieved during stochastic optimization by setting the value (of λ 1 or λ 2 ) to 0 whenever the updated value is negative.

## IV. EXPERIMENTS

## A. FI-2010 Limit Order Book Dataset

In finance, a limit order placed with a bank or a brokerage is a type of trade order to buy or sell a fixed amount of assets with a specified price. In a limit order, the trader must specify three pieces of information: the type (buy or sell), the price of a unit of the asset, and the volume (the number of stock items he or she wants to trade). Basically, with a limit order, the trader only wants to buy or sell an asset at a price that is at least as good as what he or she specifies. That is, with a buy (sell) limit order, the trader only wants to buy (sell) an asset with the price equal or lower (higher) than the price he or she specifies. The buy (bid) and sell (ask) limit orders form

![Image](images/image_000000_248dcc76f7f26315359cffc4c58046e680dfa5f086cc880d5695f5cd7d7150e5.png)

Fig. 1. Network Topologies

two sides of the LOB: the bid and the ask side. At time t , the best bid price ( p 1 b ( t ) ) and the best ask price ( p 1 a ( t ) ) are defined as the highest bid and the lowest ask price that exist in the LOB, respectively. When a new limit order arrives, the system aggregates and sorts the orders on both sides so that the best bid and best ask orders are placed on the top, which is called the first level. If there are limit orders where the bid price is equal or higher than the lowest ask, i.e. p 1 b ( t ) ≥ p 1 a ( t ) , those orders are immediately fulfilled and removed from the LOB.

In order to evaluate the proposed BiN layer in the problem of financial forecasting, we conducted empirical analysis on FI-2010 [23], a large scale, publicly available Limit Order Book (LOB) dataset, which contains buy and sell limit order information (the prices and volumes) over 10 business days from 5 Finnish stocks traded in Helsinki Exchange (operated by NASDAQ Nordic). At each time instance, the dataset contains the prices and volumes from the top 10 levels of both buy and sell sides, leading to a 40 -dimensional vector representation.

Using this dataset, we investigated the problem of midprice movement prediction in the next H = { 10 , 20 , 50 } events. Mid-price at a given time instance is the mean value between the best bid and best ask prices, which is a virtual quantity since no trade can take place at this price at the given time. Its movements (stationary, increasing, decreasing), however, reflects the dynamic of the LOB and the market. Therefore, being able to predict the future movements of the mid-price using the current and past order information is of great importance. For more information on FI-2010 dataset and the limit order book, we refer the reader to [23].

## B. Experimental protocols

We followed the same experimental setup proposed in [1] which used LOB information from the first 7 days to train the models and the last 3 days for evaluating purpose. The input to all the models consists of the prices and volumes of the top 10 levels over the 10 most recent events, i.e., each input sample is a matrix of size 40 × 10 . The target is the mid-price movement after H = { 10 , 20 , 50 } events. H is also referred to as the prediction horizon, and here we should note that different models are trained for each value of the prediction horizon.

Furthermore, we also followed [1] and used the the same TABL architectures that produced the best performances in [1] to evaluate, denoted as B(TABL) and C(TABL) as in [1]. B(TABL) is an architecture that has only one hidden layer while C(TABL) has two hidden layers. The topologies of B(TABL) and C(TABL) are illustrated in Figure 1. The results for C(TABL) networks applying our BiN layer and BN layer as an input normalization layer are denoted as BiN-C(TABL) and BN-C(TABL), respectively.

For weight regularization, we experimented with two types of weight regularization: weight decay with a coefficient of 1 e -3 and max-norm constraint with the maximum norm set to 10 . 0 . After each hidden layer, we also applied dropout regularization with the dropout rate set to 0 . 1 . ADAM optimizer was used to optimize the networks' parameters. Each model was trained for a total of 80 epochs with the learning rate starting at 1 e -3 and dropping to 1 e -4 , then to 1e -5 at epoch 11 and 71 , respectively. Since the objective is to train each model to predict the future movement of the mid-price, cross-entropy was used as the loss function. Similar to [1], [24], a weighted cross-entropy loss function was used to counter the effect of data imbalance in the FI-2010 dataset. That is, the loss term associated with each class is multiplied with a constant that is inversely proportional with the number of samples in that class.

Accuracy, averaged Precision, Recall and F1 are reported as the performance metrics. Since FI-2010 is an imbalanced dataset, we focus our analysis on the F1 measure. In addition, each experiment was run 5 times and the median value is reported.

## C. Experiment Results

Table I shows the experiment results in three prediction horizons H = { 10 , 20 , 50 } of the proposed BiN-C(TABL) networks in comparisons with the original TABL architecture C(TABL), other input normalization strategies BN-C(TABL), DAIN-MLP, DAIN-RNN (the lower section of each horizon) as well as recent state-of-the-art results for deep architectures (the upper section).

It is clear that our proposed BiN layer (BiN-C(TABL)) when used to normalize the input data yields significant improvement over the original TABL networks (C(TABL)) in all prediction horizons. Especially, for the longest horizon H = 50 , BiN enhances the C(TABL) network with up to 10% improvement (from 78 . 44% to 88 . 06% ) in average F1 measure. Compared with DAIN, the performances achieved by our normalization strategy coupled with TABL networks far exceed that of DAIN coupled with MLP or RNN. Regarding BN when used as an input normalization scheme, it is obvious that BN deteriorates the performance of the C(TABL) network. For example, in case of H = 10 , adding BN to C(TABL)

TABLE I EXPERIMENT RESULTS. BOLD-FACE NUMBERS DENOTE THE BEST F1 MEASURE AMONG THE NORMALIZATION STRATEGIES

| Models                    | Accuracy %                | Precision %               | Recall                    | %                         | F1 %                      |
|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|
| Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 |
| CNN[25]                   | -                         | 50 . 98                   | 65 . 54                   |                           | 55 . 21                   |
| LSTM[26]                  | -                         | 60 . 77                   | 75 . 92                   |                           | 66 . 33                   |
| C(BL) [1]                 | 82 . 52                   | 73 . 89                   | 76 . 22                   |                           | 75 . 01                   |
| DeepLOB [2]               | 84 . 47                   | 84 . 00                   | 84 . 47                   |                           | 83 . 40                   |
| DAIN-MLP [20]             | -                         | 65 . 67                   | 71 . 58                   |                           | 68 . 26                   |
| DAIN-RNN [20]             | -                         | 61 . 80                   | 70 . 92                   |                           | 65 . 13                   |
| C(TABL) [1]               | 84 . 70                   | 76 . 95                   | 78 . 44                   |                           | 77 . 63                   |
| BN-C(TABL)                | 79 . 20                   | 68 . 48                   | 72 . 36                   |                           | 66 . 87                   |
| BiN-C(TABL)               | 86 . 87                   | 80 . 29                   | 81 . 84                   |                           | 81 . 04                   |
| Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 |
| CNN[25]                   | -                         | 54 . 79                   | 67 . 38                   |                           | 59 . 17                   |
| LSTM[26]                  | -                         | 59 . 60                   | 70 . 52                   |                           | 62 . 37                   |
| C(BL) [1]                 | 72 . 05                   | 65 . 04                   | 65 . 23                   |                           | 64 . 89                   |
| DeepLOB [2]               | 74 . 85                   | 74 . 06                   | 74 . 85                   |                           | 72 . 82                   |
| DAIN-MLP [20]             | -                         | 62 . 10                   | 70 . 48                   |                           | 65 . 31                   |
| DAIN-RNN [20]             | -                         | 59 . 16                   | 68 . 51                   |                           | 62 . 03                   |
| C(TABL) [1]               | 73 . 74                   | 67 . 18                   | 66 . 94                   |                           | 66 . 93                   |
| BN-C(TABL)                | 70 . 70                   | 63 . 10                   | 63 . 78                   |                           | 63 . 43                   |
| BiN-C(TABL)               | 77 . 28                   | 72 . 12                   | 70 . 44                   |                           | 71 . 22                   |
| Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 |
| CNN[25]                   | -                         | 55 . 58                   | 67 . 12                   |                           | 59 . 44                   |
| LSTM[26]                  | -                         | 60 . 03                   | 68 . 58                   |                           | 61 . 43                   |
| C(BL) [1]                 | 78 . 96                   | 77 . 85                   | 77 . 04                   |                           | 77 . 40                   |
| DeepLOB [2]               | 80 . 51                   | 80 . 38                   | 80 . 51                   |                           | 80 . 35                   |
| DAIN-MLP [20]             | -                         | -                         | -                         |                           | -                         |
| DAIN-RNN [20]             | -                         | -                         | -                         |                           | -                         |
| C(TABL) [1]               | 79 . 87                   | 79 . 05                   | 77 . 04                   |                           | 78 . 44                   |
| BN-C(TABL)                | 77 . 16                   | 75 . 70                   | 75 . 04                   |                           | 75 . 34                   |
| BiN-C(TABL)               | 88 . 54                   | 89 . 50                   | 86 . 99                   |                           | 88 . 06                   |

TABLE II IMPROVEMENT COMPARISON BETWEEN BIN-C(TABL) VERSUS BIN-B(TABL)

| Models                    | Accuracy %                | Precision %               | Recall %                  | F1 %                      |
|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|
| Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 |
| B(TABL) [1]               | 78 . 91                   | 68 . 04                   | 71 . 21                   | 69 . 20                   |
| C(TABL) [1]               | 84 . 70                   | 76 . 95                   | 78 . 44                   | 77 . 63                   |
| BiN-B(TABL)               | 86 . 92                   | 80 . 43                   | 81 . 82                   | 81 . 10                   |
| BiN-C(TABL)               | 86 . 87                   | 80 . 29                   | 81 . 84                   | 81 . 04                   |
| Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 |
| B(TABL) [1]               | 70 . 80                   | 63 . 14                   | 62 . 25                   | 62 . 22                   |
| C(TABL) [1]               | 73 . 74                   | 67 . 18                   | 66 . 94                   | 66 . 93                   |
| BiN-B(TABL)               | 77 . 54                   | 72 . 56                   | 70 . 22                   | 71 . 29                   |
| BiN-C(TABL)               | 77 . 28                   | 72 . 12                   | 70 . 44                   | 71 . 22                   |
| Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 |
| B(TABL) [1]               | 75 . 58                   | 74 . 58                   | 73 . 09                   | 73 . 64                   |
| C(TABL) [1]               | 79 . 87                   | 79 . 05                   | 77 . 04                   | 78 . 44                   |
| BiN-B(TABL)               | 88 . 44                   | 89 . 36                   | 86 . 92                   | 87 . 96                   |
| BiN-C(TABL)               | 88 . 54                   | 89 . 50                   | 86 . 99                   | 88 . 06                   |

network leads to more than 10% drop in averaged F1. This behaviour is expected since BN was originally designed to reduce covariate shift between hidden layers of Convolutional Neural Network, rather than as a mechanism to normalize multivariate time-series.

Comparing BiN-C(TABL) with the state-of-the-arts CNNLSTM architecture having 11 hidden layers called DeepLOB [2], it is clear that our proposed normalization layer helps a TABL network having only 2 hidden layers to significantly close the gaps when H = 10 and H = 20 ( 81 . 04% versus 83 . 40% for H = 10 , and 71 . 22% versus 72 . 82% for H = 20 ), while outperforming DeepLOB by a large margin when H = 50 ( 88 . 06% versus 80 . 35% ).

In order to investigate the extent of improvement with respect to different TABL network topologies when using our proposed normalization layer, we also conducted experiments with a smaller TABL network, namely B(TABL) as proposed in [1]. B(TABL) has only one hidden layer with a total of 5843 parameters, compared to C(TABL) which has two hidden layers with a total of 11343 parameters. The results are shown in Table II. First of all, it is obvious that adding the proposed normalization layer significantly enhances both B(TABL) and C(TABL) in different prediction horizons. More surprisingly, BiN-B(TABL) networks perform as well as BiN-C(TABL) networks in all prediction horizons, making the additional parameters in BiN-C(TABL) redundant. Here we should note that adding our proposed BiN normalization layer to B(TABL) networks only leads to a mere increase of 102 parameters while achieving the same performances as BiN-C(TABL) networks, which have double the amount of parameters.

Since BN has been widely used for hidden layers, we also compared the performance of BiN and BN when applied to all layers in Table III. The upper section of each horizon shows the performance of BiN and BN when applied only to the input layer while the lower section shows their performance when applied to all layers. As we can see from Table III, there is virtually no differences between the two arrangements. This result shows that adding normalization to the hidden layers bring no improvement to both strategies and the improvements obtained for TABL networks are indeed attributed to the input data normalization performed by BiN.

## V. CONCLUSIONS

In this paper, we propose BiN, a data-driven time-series normalization strategy which is designed to tackle the potential difficulties posed by noisy, non-stationary financial timeseries. Our proposed normalization layer takes into account the property of bilinear projection in TABL networks and aligns the multivariate time-series in both feature and temporal dimensions. Using a large scale limit order book dataset focusing on stock movement prediction, we demonstrated that BiN can greatly enhances the performances of previous stateof-the-arts TABL networks while requiring few additional parameters and computation.

## TABLE III

## COMPARISONS BETWEEN BILINEAR NORMALIZATION AND BATCH NORMALIZATION WHEN APPLIED TO ONLY INPUT LAYER (BIN-C(TABL) AND BN-C(TABL)) OR ALL LAYERS (BIN-C(TABL)-BIN AND BN-C(TABL)-BN

| Models                    | Accuracy %                | Precision %               | Recall %                  | F1 %                      |
|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|
| Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 | Prediction Horizon H = 10 |
| BN-C(TABL)                | 79 . 20                   | 68 . 48                   | 72 . 36                   | 66 . 87                   |
| BiN-C(TABL)               | 86 . 87                   | 80 . 29                   | 81 . 84                   | 81 . 04                   |
| BN-C(TABL)-BN             | 78 . 72                   | 68 . 02                   | 72 . 58                   | 69 . 98                   |
| BiN-C(TABL)-BiN           | 86 . 84                   | 80 . 25                   | 81 . 85                   | 81 . 03                   |
| Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 | Prediction Horizon H = 20 |
| BN-C(TABL)                | 70 . 70                   | 63 . 10                   | 63 . 78                   | 63 . 43                   |
| BiN-C(TABL)               | 77 . 28                   | 72 . 12                   | 70 . 44                   | 71 . 22                   |
| BN-C(TABL)-BN             | 71 . 28                   | 63 . 77                   | 63 . 65                   | 63 . 75                   |
| BiN-C(TABL)-BiN           | 76 . 68                   | 71 . 15                   | 70 . 48                   | 70 . 80                   |
| Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 | Prediction Horizon H = 50 |
| BN-C(TABL)                | 77 . 16                   | 75 . 70                   | 75 . 04                   | 75 . 34                   |
| BiN-C(TABL)               | 88 . 54                   | 89 . 50                   | 86 . 99                   | 88 . 06                   |
| BN-C(TABL)-BN             | 76 . 74                   | 75 . 34                   | 74 . 66                   | 74 . 97                   |
| BiN-C(TABL)-BiN           | 88 . 44                   | 89 . 36                   | 86 . 92                   | 87 . 96                   |

## REFERENCES

- [1] D. T. Tran, A. Iosifidis, J. Kanniainen, and M. Gabbouj, 'Temporal attention-augmented bilinear network for financial time-series data analysis,' IEEE transactions on neural networks and learning systems , vol. 30, no. 5, pp. 1407-1418, 2018.
- [2] Z. Zhang, S. Zohren, and S. Roberts, 'Deeplob: Deep convolutional neural networks for limit order books,' IEEE Transactions on Signal Processing , vol. 67, no. 11, pp. 3001-3012, 2019.
- [3] N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Temporal bag-of-features learning for predicting mid price movements using high frequency limit order book data,' IEEE Transactions on Emerging Topics in Computational Intelligence , 2018.
- [4] D. T. Tran, M. Gabbouj, and A. Iosifidis, 'Multilinear class-specific discriminant analysis,' Pattern Recognition Letters , 2017.
- [5] D. T. Tran, M. Magris, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Tensor representation in high-frequency financial data for price change prediction,' IEEE Symposium Series on Computational Intelligence (SSCI) , 2017.
- [6] N. Passalis, A. Tsantekidis, A. Tefas, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Time-series classification using neural bag-of-features,' in Signal Processing Conference (EUSIPCO), 2017 25th European , pp. 301-305, IEEE, 2017.
- [7] S. Ren, K. He, R. Girshick, and J. Sun, 'Faster r-cnn: Towards real-time object detection with region proposal networks,' in Advances in neural information processing systems , pp. 91-99, 2015.
- [8] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, 'You only look once: Unified, real-time object detection,' in Proceedings of the IEEE conference on computer vision and pattern recognition , pp. 779-788, 2016.
- [9] A. Iosifidis, A. Tefas, and I. Pitas, 'View-invariant action recognition based on artificial neural networks,' IEEE transactions on neural networks and learning systems , vol. 23, no. 3, pp. 412-424, 2012.
- [10] D. T. Tran, A. Iosifidis, and M. Gabbouj, 'Improving efficiency in convolutional neural networks with multilinear filters,' Neural Networks , vol. 105, pp. 328-339, 2018.
- [11] D. T. Tran, M. Yamac, A. Degerli, M. Gabbouj, and A. Iosifidis, 'Multilinear compressive learning,' arXiv preprint arXiv:1905.07481 , 2019.
- [12] D. T. Tran, M. Gabbouj, and A. Iosifidis, 'Multilinear compressive learning with prior knowledge,' arXiv preprint arXiv:2002.07203 , 2020.
- [13] D. Bahdanau, K. Cho, and Y. Bengio, 'Neural machine translation by jointly learning to align and translate,' arXiv preprint arXiv:1409.0473 , 2014.
- [14] J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, 'Bert: Pre-training of deep bidirectional transformers for language understanding,' arXiv preprint arXiv:1810.04805 , 2018.
- [15] X. Shao, 'Self-normalization for time series: a review of recent developments,' Journal of the American Statistical Association , vol. 110, no. 512, pp. 1797-1817, 2015.
- [16] S. Nayak, B. B. Misra, and H. S. Behera, 'Impact of data normalization on stock index forecasting,' Int. J. Comp. Inf. Syst. Ind. Manag. Appl , vol. 6, pp. 357-369, 2014.
- [17] A. Ntakaris, G. Mirone, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Feature engineering for mid-price prediction with deep learning,' Ieee Access , vol. 7, pp. 82390-82412, 2019.
- [18] S. Ioffe and C. Szegedy, 'Batch normalization: Accelerating deep network training by reducing internal covariate shift,' arXiv preprint arXiv:1502.03167 , 2015.
- [19] D. Ulyanov, A. Vedaldi, and V. Lempitsky, 'Instance normalization: The missing ingredient for fast stylization,' arXiv preprint arXiv:1607.08022 , 2016.
- [20] N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Deep adaptive input normalization for price forecasting using limit order book data,' arXiv preprint arXiv:1902.07892 , 2019.
- [21] X. Glorot and Y. Bengio, 'Understanding the difficulty of training deep feedforward neural networks,' in Proceedings of the thirteenth international conference on artificial intelligence and statistics , pp. 249256, 2010.
- [22] K. He, X. Zhang, S. Ren, and J. Sun, 'Delving deep into rectifiers: Surpassing human-level performance on imagenet classification,' in Proceedings of the IEEE international conference on computer vision , pp. 1026-1034, 2015.
- [23] A. Ntakaris, M. Magris, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Benchmark dataset for mid-price forecasting of limit order book data with machine learning methods,' Journal of Forecasting , vol. 37, no. 8, pp. 852-866, 2018.
- [24] D. T. Tran, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Data-driven neural architecture learning for financial time-series forecasting,' arXiv preprint arXiv:1903.06751 , 2019.
- [25] A. Tsantekidis, N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Forecasting stock prices from the limit order book using convolutional neural networks,' in Business Informatics (CBI), 2017 IEEE 19th Conference on , vol. 1, pp. 7-12, IEEE, 2017.
- [26] A. Tsantekidis, N. Passalis, A. Tefas, J. Kanniainen, M. Gabbouj, and A. Iosifidis, 'Using deep learning to detect price change indications in financial markets,' in Signal Processing Conference (EUSIPCO), 2017 25th European , pp. 2511-2515, IEEE, 2017.
