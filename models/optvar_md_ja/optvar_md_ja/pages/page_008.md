# Page 008

![Page 008](../assets/page_images/page-008.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                                Confidential


     The Opt-Var model is classified as Tier 3 model determined by its medium materiality and low
complexity.
     Materiality and Complexity are each derived from two sub-tiers. For Materiality, the two sub-
tiers are ‘Usage’ and ‘Reliance’. For Complexity the two sub-tiers are ‘Specificity’ and ‘Processing’.
Guidance on tiering assessments for each component can be found in section 5 of the tiering docu-
mentation [i].
    The Materiality of the model is medium due to high Usage and low Reliance. The model
is deemed to have high Usage as all models within eRates have conservative usage estimations.
Reliance is low; this is because there is an alternative simple hedge calculator available within the
autohedger and the autohedger can function without the opt-var model.
    The complexity of the model is low due to medium Specificity and low Processing. The model
is deemed to have medium Specificity because the autohedger uses a numerical vector output of
optimization to determine the quantity to hedge. The model is deemed to have low Processing; it
has low risk of implementation error as it simply performs a basic operation of calling an external
optimization library routine.
    ‘As per the tiering documentation, the overall tier of the model is 3.
1.3.       Key Assumptions             and Limitations
Ina nutshell, the key assumptions of the Opt-Var model are as follows:
   i) From a data point of view, it is assumed that the model parameters are properly tuned,
      estimated, and sensible. This covers the covariance matrix, hard risk constraints, trade size
      limit and risk-aversion factor (as we shall see, this is controlled by the parameter A).
  ii) From statistical perspective, assumptions exist so that the hedging trades are in fact being
          properly determined by the Opt-Var opti     nizer. It is assumed that the various trading and risk
          constraints are (at least usually!) consistent. It further assumes the alpha factor is smaller
          than the cost vector.

  iii) From a business point of view, it is assumed that the optimization objective, given in (I
       provides an adequate representation of the trade-offs between portfolio variance, execution
       costs and alpha capturing. This is discussed in detail in subsequent sections.
       There are no noteworthy limitations that have been identified for this model.

1.4        Overall Model          Performance         Assessment
The model was found to perform adequately in all of our tests. We have documented comprehen-
sive demonstrations of stability, convergence, adherence to parameter assumptions, and agreement
between development and production in Section[5| Stress testing under various scenarios is carried
                          and sensitivity analysis is done i      The results of the outcome analyses in
Section           indicate that the model behaves properly in all cases.

1.5        Summary         of Results
Based upon the tests that we have documented here, and others carried out during the development,
we have concluded that the model performs adequately, and is satisfactorily robust to inputs.
       'It is expected that occasionally this will not be the case. In this case, we proceed in a manner detailed in section
B23
130115: Opt-Var                                                                                              Page 8 of 136

                              [git] « Branch: iropt-var@be27d1a = Release:          (2024-10-31)
```
