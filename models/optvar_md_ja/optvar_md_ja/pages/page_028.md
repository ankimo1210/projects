# Page 028

![Page 028](../assets/page_images/page-028.jpg)

## OCR layout text

```text
Morgan Stanley                                                                              Confidential


as a function of change in market conditions.

Sample    Covariance Matrix

    We generate the sample covariance matrix from the yield change time series of the hedge in-
struments. The changes in yield are sampled every 5 minutes during the active market hours. For
EGB, the moment this document is written, we are sampling the data from London time 7:30 to
17:30, and we will change the sampling time to London time 8:00 to 17:30 when FLG is added (the
trading time for FLG starts from London time 08:00). For UST, we sample the yield data from
9:30 to 17:30 New York time. The lookback period of the yield data typically ranges from 2 weeks
to 3 months, and changes based on the market condition judged by bookrunners.
    The covariance matrix is evaluated by calculating the covariance of each pair of the hedge
instruments q! and q? in the standard way, via

                                                          G)@G-@)
                                                           —1            >
where q}, q? are the i‘h observation in the yield change time series of g! and q?, respectively; 7',
@ are the means of all observations in the yield change time series of g! and q”, respectively, and
nis the number of observations in the yield change series.

Shrinkage Covariance Matrix (US)

     Outliers are defined as 5 minutes yield changes of more than 10 bps. These moves are extremely
unlikely to happen if we consider the data distribution. In the US, if they detect outliers in the
yield change time series, strat     an decide to cap the outliers at 10bps.
If the covariance matrix is ill-conditioned, it can be difficult to invert numerically.   This can lead
to instabilities in the optimizer even though it is a strictly positive definite (and hence invertible)
matrix. To estimate a covariance matrix in such a way as to avoid excessively large condition num-
bers, shrinkage is a powerful procedure. In [5], Ledoit and Wolf consider the following estimation
problem for the covariance matrix. Let X = (X1,---,Xn) € RP*” be an iid sample of n inde-
pendent realizations of p centered random variables with correlation ©. The empirical covariance
estimator is S, = *<* and we consider the Frobenius norm |l-||- : A € RPXP +                   ). ‘They
propose solving the Yinear shrinkage optimization problem given by
                                        min E [liz =i [2|
                                              =p = pil+ p2Sn,
The solution to this problem is given by
                                                eB       oo
                                         d= Galt
with                                             ms
                                             p= 2D
                                             a==|b- ul\|p
                                             B= |S — Xp
                                             & = || —pl|lp,
130115: Opt-Var                                                                           Page 28 of 136

                       [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
