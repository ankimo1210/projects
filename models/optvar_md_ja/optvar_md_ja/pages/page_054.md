# Page 054

![Page 054](../assets/page_images/page-054.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                        Confidential


    The eigenvalues of the covariance matrix , computed by the Python function numpy. Linalg. eigvals,
are 8.12, 9.47, 9.74, 10.42, 10.80, 11.17, 11.60, 12.16, 13.13, 24.71, 41.56, 100.27 and 1076.14 The con-
dition number of this matrix is equal to 44!4 = 133. The eigenvalues for the matrix with ETFs
are between 1.15 — 1551, giving a condition number of 1350; this matrix is also positive definite.
    In practice, what matters for the well-posedness of the optimization problem is the condition
number of the quadratic term AX + d..P,+M, as visible in the objective function of (3) and with
(4), when ) is in the range used in production.          For the US ETF case, when \ < 100e — 8, this
condition number is smaller than 663. In the EU case, when \ < 200e— 6, this condition number is
smaller than 142. After calibration we manually check that this condition number is smaller than
1000.

5.1.5    Stability

This section is devoted to an analysis of the stability properties of the Opt-Var problem. Every
time the risk changes - through updates in position due to the flow, or our own hedging actions -
the optimization routine is called. We are interested in the behavior of the system as this process
is iterated. This analysis is important for the business, because we want to ensure that the costs
induced by hedging according to Opt-Var do not increase without bound by calling the Opt-Var
model repeatedly. If the system is unstable, the model would be liable to perpetually provide new
orders, leading to spiraling execution costs. On the other hand, if the system is indeed stable,
understanding the stability region allows for better control of the portfolio risk, and simplifies the
task of choosing appropriate parameters.
    For convenience, let @ = (H,B, S,allowIncreasePosition, \, 5, d.0,C, M,a) denote the vector
of Opt-Var parameterg" Let A, = Ag(@) denote the set of admissible controls - that is, the set of
all uC R@ such that all constraints in     (12) are satisfied. Further, let Z denote the admissible area,
that is the set of positions that simultaneously satisfy all the bucket and total risk limit constraint
and let S CI denote the stable area - the set of positions from which the optimal hedge is zero:
    T={qeR!| Hi<1'¢< Au,-Bi<
                          a < Bivie [d},                              S={q¢ RB? | argmin F,(u) = 0}.
                                                                                       ue Ag
Through the rest. of this section, we prove the system that repeatedly calling Opt-Var model is
stable by giving an overview of two fundamental conclusions: firstly, that the positions will con-
verge to the admissible region Z after a finite number of steps, irrespective of starting inventory,
and secondly that the positions g” converge to the stable region in the limit as n + 00. We also
provide an empirical illustration of this phenomenon at the end of the section.
Assumptions

   The results outlined in this section hold under the following assumptions:

   i) The alpha factor a in the objective function is smaller than the linear part of the cost pa-
      rameter C, namely |a| < C.
  ii) The covariance matrix © is positive definite.

 iii) The trading limit S is positive.
  ®As we have seen, Py is a function of (A, ¥,M) and is therefore not a problem parameter per se.



130115: Opt-Var                                                                                     Page 54 of 136

                        [git] « Branch: iropt-var@be27d1a = Release:       (2024-10-31)
```
