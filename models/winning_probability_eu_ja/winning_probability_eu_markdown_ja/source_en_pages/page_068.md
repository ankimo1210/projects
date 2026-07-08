# Page 68

![Page 68](../assets/page_images/page_068.png)

## Extracted OCR/Text Layer

```text
Morgan Stanley
Confidential
9. Re-calibration: Offline model calibration is performed daily, and coefficients to be used in
the online implementation are generally updated monthly.
Updating model coefficients online is performed by uploading the required coefficient csv
to the production java application. This is
a manual process performed after performance
verification of the new coefficients - this is described in section
10. TRAIN: The application where the live model resides is onboarded to TRAIN, Please find
examples below for production releases - note that these are not related to the EUGV Prob-
ability Curve model, but concern the algopricer application which houses it.
« Example jira: http: //jira3.ms.com/jira/browse/AIMEXPNEGB- 6934)
+ Example test: |nttp://train-zipviewer-prod.ms.com:5000/zipviewer/docs/afs/fidalyo/
erates /06958_fidalgo_erates_master-2023.12.04-p13_test- results. tar.xz/| other tests
available under the ‘Testing’ section here: http: //jira3.ms
. com/jira/browse/AIMEXPNEGB-
« Example TCM: http: //changereview.webfarm.ms
. com/app/#/tcm/602975777|
+ Example PR:|http://stashblue
.ms
. com:11990/atlassian- stash/projects/FIDALGO_ERATES/
[repos/erates/pull - requests/5952/overview|
11. Production support: The segregation of duties between model development and production
deployment is ensured by TAM. When the VMS command is run to deploy a new version of
the code, checks are performed as to whether the person performing the action is assigned a
valid TAM role.
If the TCM or TAP was approved for the given role on the specified GRN,
the deployment command will proceed. The production runtime environment is managed by
IR-PM.
12. Production rollout. The rollout follows the SDLC cycle.
It is phased through a QA cycle,
then a passive/active production instance turnover (as described previously). Instant rollback
is made available by switching back passive/active instances of the component housing the
model (managed by Strats), or pointing the component to a previous release build if required
(managed by Technology).
9
Model Ongoing Performance Monitoring
9.1
Metrics being monitored
‘As per discussions with MRM, as part of the ongoing performance monitoring of the model, the
following metrics are monitored:
+ HR diff
+ AP score diff
Recall from section
B]that the HR diff is defined as:
hit RateDif f = |predictedH
it Rate — realizedHit Rate|
18)
where
129576: Winning-Probability Model for
EUGV RFQ Pricing
Page 68 of 73
[git]
= Branch:
ir.eugy-hit-rate-curve @9676cba
= Release:
(2025-03-12)

```
