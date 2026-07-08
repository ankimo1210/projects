# ページ 020

![ページ 020](../assets/page_images/page-020.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                              Confidential


where H, € R_, Hy, € R,, are the hedgeable risk limits within which the net portfolio PVO1 must
be after the optimization. This constraint is imposed so as to explicitly impose that the net portfo-
lio risk is admissible after the optimization - although high values of \ will induce proposed trades
that pushes the net portfolio risk towards zero, without this constraint, it is not guaranteed the
net portfolio risk after optimization will be within a given range.
Bucket    Risk Limit Constraint

                                      -BiS<qtus Bi,              Vie (d|                               (3)
where B; € Ry is the bucket risk limit for instrument i in PVO1, within which the risk of bucket i
must be after the optimization. From the risk management point of view, it is considered ill-advised
to hold large positions in any buckets. The constraint in Eq. @) ensures that the net portfolio risk
is within a certain limit, but it does not guarantee that the risk in each bucket is bounded. With-
out the bucket risk constraints, the optimizer might propose trades that would establish arbitrarily
large long positions in one bucket, with correspondingly large short positions in another, provided
the overall risk satisfies (2); the bucket risk limit constraints preclude this possiblity.
Trading Size Limit Constraint

                                         —Si<u<S;,          Vie [d]                                    (4)
where S; € R, is the maximum trade size the proposed hedge trades can have.                We set this
constraint to prevent us from executing excessively large trades in the market, which may cause
market impacts that will not be captured by the a signal. We call S; the upper trade limit and
—S; the lower trade limit.
    Aditionally, when the product is in scope for the short sell constraint, which is the case of bond
ETFs, it means Opt-Var model should not propose trades that will lead to a negative position in
that product (aggregated over the fixed income Rates desks). The locate service gives a minimal
trading size —S;. It has the effect of modifying the trading size limit into
                                   max(—S;,—Si)       <u < Si,      Vi € [d]

Allow Increase Position Constraint
This constraint only applies if the parameter allow increase position is set to false. When this is
the case, it means Opt-Var model should not propose trades that will increase the position in any
bucket, nor flip the sign of the position; for example, when q; > 0 this means that we restrict u; to
[-qi. 0]. In this case, we find that the constraint is expressed by:

                                O<u<—q           Yield)     suchthat       gi <0
                              —q<u<0             Vield)    suchthat        g >0.                       (5)

3.2.4    Opt-Var      Model

Combining the objective function described in Eq.                and constraints Eqs.
Opt-Var optimization problem is given by:

                  minimize    (q+ u) (N+ bx0Py(q+u)+C"\ul+ulMu—al(q+u)

130115: Opt-Var                                                                           Page 20 of 136

                         [git] « Branch: iropt-var@be27d1a = Release:      (2024-10-31)
```
