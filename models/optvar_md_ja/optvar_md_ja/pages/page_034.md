# Page 034

![Page 034](../assets/page_images/page-034.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                        Confidential


3.6      Numerical        Implementation

    In this section, we present the implementation of the Opt-Var model in production environment
as well as the platforms and packages used to calibrate the parameters.
3.6.1     Model Implementation             in Java

The Opt-Var model is represented as a quadratic optimization problem and implemented in pro-
duction in Java with the NAG optimization library - more specifically, with the E04NQ routine.
This routine wraps E04NQF routines in Fortan and is appropriate to solve quadratic optimization
problems.
    This routine takes the following parameters, which are set up explicitly in our production
implementation:
      + Optimality Tolerance: The optimal tolerance is set to the default value 10~°. Decreasing
        the tolerance will increase the number of iterations and achieve more optimal results. However,




    In the implementation, a feasible initial point is also provided to start with. We choose the mid
point of the final upper and lower trade limits to be the initial point to guarantee a feasible point
to start with. The final     up er and lower trade limits are given by Eq. ) when positions increase
are allowed, and by Eq. (8a) and          ) when position increase is not allowed.

3.6.2     Model Reformulation
To fit in the NAG         E04NQ routine in Java, we need to reformulate the Opt-Var model.              We recall
from sections                                                is gi

                  minimize      (q+ u)'(AD + b0Pa)(qt+ u) +C"        ful   +u'Mu-al(q+u)
                     ue 4
                                          d
                  subject to    — Hy < S0(qi+ui) < Hu,
                                         i=1

                                  Sh<w<S?,           vie [d|                                                   (12)
where again we use $/, SY to denote respectively the final lower and upper constraints on the trade
size u; (which may be read from (7) in the case position increase is allowed, and either
depending on the sign of g:, when position increase is disallowed).
     We reformulate the problem explicitly as a quadratic program with linear constraints in order
to implement it numerically. In particular, the constants in the objective function F do not impact
the solution and can be dropped from the computation. We also need to replace the absolute value
|u| by a linear term in an additional state variable z to obtain a quadratic objective function. The
problem becomes:
                   minimize     ul (AD + bx0P\ + M)ut (2q' (AD + 60P,) — a                )ut+Clz
                     we
                  subject to.   2; > ui, Vi € [d]

130115: Opt-Var                                                                                     Page 34 of 136

                            [git] « Branch: iropt-var@be27d1a = Release:   (2024-10-31)
```
