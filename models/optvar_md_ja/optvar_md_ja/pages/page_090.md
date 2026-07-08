# Page 090

![Page 090](../assets/page_images/page-090.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                   Confidenti.


                                                 Below          Specified Risk Limit
                                                True                     False
                          Net   Portfolio Risk | 100                       0
                                  SHTZ            100                      1)
                                 BOBL                100                  0
                                 BUND                100                  0
                                 BUXL                100                  0
                                  OAT                100                  0
                                  BTS                100                  1)
                                  BTP                100                  0

           Table 30: Count of Risk Below Specified Limits After Trading Opt-Var Hedges


5.5.3    Trade Size Limit

To test this criteria, we check that the trade size of Opt-Var proposed hedges are all below the
specified trade size limit for all the 100 examples we test. Table  [31] below summarizes the results.
According to the table, the trade sizes for all the buckets are below the trade size limit for all the
100 examples. This verifies that the trade size limit criteria is satisfied.
                                           Below    Specified Trade Limit
                                           True              False
                                 SHTZ        100                    0
                                 BOBL        100                    0
                                BUND | _ 100                        0
                                BUXL | 100                          0
                                 OAT         100                    0
                                 BTS         100                    0
                                 BTP         100                    0

                   Table 31: Count of Opt-Var Hedge Trade Size Below Specified Limits



5.5.4    Portfolio Variance

In this test, we prove that the portfolio variance after trading the Opt-Var proposed hedges is
always smaller than the original portfolio variance for different non-zero \ values. Figure[?4]gives the
comparison for a specific example with initial portfolio PV01 {SHTZ, BOBL, BUND, BUXL, OAT,
BTS, BTP}         = {-981.47, 6405.88, -21370.15, 7235.52, -1203.48, 629.40, -1203.48}.       The horizontal
axis gives the \ values ranging from 1e-6 to 2e-4 with every increase of le-6. The vertical axis
shows the portfolio variance value. The blue line gives the portfolio variance value after trading
the Opt-Var proposed hedges for different A values, and the orange line gives the portfolio variance
without trading any hedges. As shown in the plot, the portfolio variance after trading the Opt-Var
hedges is always smaller than without hedging.             Figure              in section     show the same
plots for all the 100 examples introduced in section       We see that the portfolio variance after
Opt-Var hedges are always below the portfolio variance without any hedges for all the 100 examples
and satisfy the portfolio variance testing criteria.


130115: Opt-Var                                                                                     90 of 136

                          [git] « Branch: iropt-var@be27d1a = Release:         (2024-10-31)
```
