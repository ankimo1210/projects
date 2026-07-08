# Page 043

![Page 043](../assets/page_images/page-043.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                       Confidential


                                            Parameter/Input            | Value
                                           Hedgeable Risk Limit         | 10,000
                                             Bucket Risk Limit         | 30,000
                                              Trade Size Limit      50,000
                                          Allow Position Increase | True
                                          Risk Aversion Factor A | 2e-5

                        Table 4: Other EU Parameters and Inputs asof 06/26/23

                  shows the objective function value after each iteration for a given initial portfolio
PV01 {SHTZ, BOBL, BUND, BUXL, OAT, BTS, BTP} = {-981.47, 6405.88, -21370.15, 7235.52,
-1203.48, 629.40}. The horizontal axis gives the iterations from 0 to 100, and the vertical axis gives
the objective function values. The blue line shows the convergence path for Java implementation,
and the orange line gives the convergence for Python implementation. According to the plot, the
objective function values converge to the same value within 10 iterations. The path to converge
is different for the two implementations as the two implementations are using different algorithms
and with potentially different starting points. Since the two implementations converge to the same
objective function value, the different paths they follow to converge is not a concern. Figure
plots the proposed trade after each iteration by future. Similarly, the blue lines indicate the Java
solution and the orange lines indicate Python solution. Both Java and Python converge to the
same solution within 10 iterations for all the futures.
    We check the convergence of all the 100 examples we tested following the above method. The
plots for the objective function values for all these 100 examples are shown in the appendix in
section      i                    and       According to the plots, Java and Python converge to the same
results   within 100 iterations for all the test examples.
    The testing results of this section and section                    both demonstrate that most probably the
Opt-Var model has a unique solution as the global minimum, and the minimum is achieved by
both Java and Python implementations.                   Otherwise, two different algorithms could by chance
return different outputs. It also proves that the Java parameters described in section [3.
chosen appropriately. Based on this testing results, we will provide analysis and additional testing
using Python implementation.
                                                                                           —
                           6500                                                            — by
                           6000
                         § 5500
                         5 5000
                        2 4500
                       & aoo0
                           3500
                          3000
                                    © 5 10 15 20 25 30 35 40 45 50 55 60 65 70 75 60 85 90 95100
                                                              Iteration

                          Figure 19: Java and Python Convergence Comparison

130115: Opt-Var                                                                                    Page 43 of 136

                          [git] « Branch: iropt-var@be27d1a = Release:             (2024-10-31)
```
