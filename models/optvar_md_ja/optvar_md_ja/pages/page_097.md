# Page 097

![Page 097](../assets/page_images/page-097.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                             Confidential


because Vol(v + 7) = Vol(v) + Vol(z) due to the client bucket risk constraints. So 0 is optimal
after the first CRB step, which means the trajectory only has one step.


6       Model        Limitations,           Uncertainties and Mitigations
No model limitations have been identified.


7       Model        Overlays and Overrides
In this section, we discuss about the overlays and overrides exist within the Opt-Var model and
the autohedger algo.
    At the Opt-Var model level, bookrunners have the ability to override the pre-calibrated model
parameters described in section              [3.3.3|at any time of the day.
       At the algo level, the autohedger has several internal controls to reconcile risk feeds and limit
outgoing orders.        As algo components, Electronic Trading Risk Management                        (ETRM)   also sets
controls and GLM limits on the algo operation, and these controls are captured by the Model
Control System (MCS).

8       Production            Implementation                 and     Controls

8.1.      Production Implementation
    The production code is written in Java. The production implementation of the Opt-Var model
was developed in adherence to the Firm’s software-development lifecycle (SDLC) policy [J]. The
following table summarizes the locations of the source code, its lifecycle management, and the
location of test artifacts that confirm         correct    implementation.


         Production      System                           Name     and   Link

         Tech change management (TCM)                     Production Jira board (BU)
                                                          Production Jira board (US)
         Source-code version control                      Production source-code repository|
                                                          Production source-code repository (CRB optimizer)
         Test artifacts of model implementation           Link to test artifacts   1

                                                          Link to test artifacts 2 (BU)
                                                          Link to test artifacts 3 (US)
                                                          Link to test artifacts 4 (US CRB)

8.2       Model Process and Controls
In production, checks and controls are included to ensure that the model inputs and outputs are valid.
    Model    Parameters     and Inputs    Control

            (i) Checks on the covariance matrix. The code checks if the input covariance matrix is not empty,
                has the right dimension, has valid values, and is positive definite. It throws error if the covariance

130115: Opt-Var                                                                                          Page 97 of 136

                            [git] « Branch: iropt-var@be27d1a = Release:               (2024-10-31)
```
