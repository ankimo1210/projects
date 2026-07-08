# ページ 103

![ページ 103](../assets/page_images/page-103.jpg)

## 原文OCRテキスト

```text
Morgan Stanley                                                                                       Confidential


          TRAIN     component                                    Link

          TCM                                                    |http ://changereview.webfarm.ms .com/app/#/tcm/   ]
                                                                 602929932
          Jira,                                                  http: //jira3.ms. com/jira/browse/EURAH-2116
                                                                 (EU)
                                                                 |nttp://jira3.ms.com/jira/secure/RapidBoard.
                                                                 jspa?rapidView=48196view=planningSissueLimit= |
                                                                 100 (US)
          Test                                                   http: //changereview.webfarm.ms .com/app/#/tcm/
                                                                 602929932| (Testing tab)
          Bitbucket PR.                                          http: //stashblue.ms.com/atlassian-stash/          ]
                                                                 [proj ects/FIDALGO_MMJ/repos/mmj/pull-             ]
                                                                 requests/3863/overview
          Train release build                                    https://train-portalui-prod.ms.com/#/view/         ]
                                                                 {name space/VMS/meta/fidalgo/project/mmj/          ]
                                                                 release/2023. 10. 10-p425-master|

    11. Production environment. Segregation of duties between model development and production de-
        ployment is ensured by TAM. When VMS command is ran to deploy new version, it checks whether
        the person performing the action has valid TAM role. If the TCM or TAP was approved for the given
        role on the specified GRN, then deployment command will proceed. Production runtime environment
        is managed by IR-PM.
    12. Production rollout. Changes will be deployed to the QA version first to be tested. Once the tests
        in QA have passed and been signed off, the QA version including the changes will be released to
        production through TCM. If there is a necessity to rollback new code, it will be rolled back to the
        previous working version via standard TCM rollback.

9       Model       Ongoing Performance Monitoring
9.1      Metrics and thresholds
As part of the ongoing performance monitoring of the model, the following metrics are monitored:
   1. Count of unsuccessful optimizations: We count the number of times the Opt-Var model failed
       to find the optimal solution. If the optimization is unsuccessful, the NAG algorithm will mark it as a
       failure, and success otherwise. Here, successful means the NAG algorithm manages to find the optimal
         solution within the maximum number of iterations we set. For this specific monitoring, we track the
         number of times we have the optimization failure everyday, and alert if it crosses the threshold of 0.
      2. Count of infeasible portfolios: There is a portfolio feasibility check within autohedger that checks
         if the portfolio after executing the Opt-Var proposed hedges will meet certain criteria. If any of
         the criteria fails, autohedger will log a warning message "optimizer produced an invalid result". The
         criteria being checked which are specific to the Opt-Var model are:
             + The net portfolio risk post optimization should be within the hedgeable risk limit.
             + The risk in each bucket post optimization should be within the bucket risk limit.
            + If position increase is not allowed, then no position should be increased post optimization in any
              buckets.
            + The auxiliary variables used in solving the Opt-Var optimization should equal to the absolute
              value of the trade variables.

130115: Opt-Var                                                                                 Page   103 of 136

                           [git] « Branch: iropt-var@be27d1a = Release:     (2024-10-31)
```
