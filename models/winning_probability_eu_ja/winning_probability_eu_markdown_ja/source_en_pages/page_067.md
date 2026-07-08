# Page 67

![Page 67](../assets/page_images/page_067.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
8.4
Software Development Lifecycle
1. GRN: The GRN for the application is fidalgo, EON Id 3655.
2. High-level application architecture:
Please find answers in section
of the model
documentation.
3. High-level description of interfaces: Please find answers in sections
[2
4, Languages: The online model is implemented in java. The offline calibration is performed
in python, which is also used for calibration research. The offline calibration process produces
a csv of output coefficients which is read by the downstream java application, therefore no
direct communication is required between python and java processes.
The runtime production instance uses java. The model is propagated to production through
the SDLC process in the ERates repository (see section
8.1), which is managed by IT devel-
opers.
5. Environments: Development/research of the model is performed offline for the coefficient
calibration process using historical data in a local development environment.
Development/research of the online implementation of the model is performed locally in the
java environment of the component housing the model (algopricer). A simulation/backtesti
module using either mock or production historical auction data can be run (see section
Following updates to the java code and expected performance verification, a release candidate
is propagated to QA where independent testing is performed using QA data (e.g. QA auction
data input)
The live production environment is used to recreate probability curves for live in-coming
RFQs.
6. Automated testing and continuous integration process: The probability curve offline
calibration process is tested manually by model developers.
Tests are incorporated within the SDLC process of the ERates repository for the online
implementation of the model:
* Unit testing of functionality
« Regression test suites testing end-to-end outputs
Simulation backtesting for the algo component housing the model
+ Unit and regression tests are run automatically upon each pull request build, which will
fail if any tests fail or code coverage is insufficient.
7. Testing process: Please see item above.
Additional verification is performed prior to online production turnover. The algo component
housing the model has two production instances, each corresponding to separate QA instances
(passive/active). Releases to production are performed on the passive side, which is used to
perform sanity checks and run performance evaluation before turnover to ‘active’ instance.
8. QA: Test. plans (unit/regression) are verified by model experts and separate Technology
team. Tests are automated and required to pass for release builds to complete. Other perfor-
mance assessments are discussed with model experts. Production release candidate testing is
performed by an independent QA function.
6: Winning-Probability Model
for
EUGV
RFQ Pricing
Page 67 of 73
[git]
= Branch:
ireugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
