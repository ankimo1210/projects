# Page 099

![Page 099](../assets/page_images/page-099.jpg)

## OCR layout text

```text
Morgan Stanley                                                                                        Confidential


           (ii) We also check that CRB optimization outputs verify the constraints. If it is not the case no
               trade will happen.
               http: //stashblue.ms. com:11990/atlassian- stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
               inmj /src/main/java/erates/hedging/CrbOptimalMat   cher. java#535|
               inttp: //stashblue. ms. com:11990/atlassian- stash/projects/FIDALGO_MMJ/repos/mmj/browse/fidalgo.
               mmj /src/main/java/erates/corvo/CorvoOrderExecutor.     java#209|
          (ili) The CRB swing engine controls are described in Sectior
                 «   Risk change control /http: //stashblue.ms.com:11990/atlass ian-stash/projects/FIDALGO_|
                     MM3 /repos /mmj/browse/fidalgo .mnj/src/main/java/erates/corvo/CorvoOrderExecutor.   java#
                      243 and its test http://stashblue .ms.com:11990/atlassian- stash/projects/FIDALGO_MMJ/
                     (repos /mmj /browse/fidalgo.mmj /src/test/java/erates/corvo/CorvoOrderExecutorTest.  java#

                 « Aim not hedging|http://stashblue .ms .com:11990/atlassian- stash/projects/FIDALGO_MMJ/|
                     {repos/mmj /browse/fidalgo.mmj /src/main/java/erates/corvo/CorvoOrderExecutor. java#246|
                     and its test|ht tp: //s tashblue.ms . com: 11990/at lassian- stash/projects/FIDALGO_MMJ/repos/
                     {nmj /browse/fidalgo.mmj /src/test/java/erates/corvo/CorvoOrderExecutorTest. java#717)

8.3       Model      Code Change         Control and Version Control
    The model research and testing code is written in Python. The software that implements the Opt-Var
model was developed in adherence to the Firm’s software-development lifecycle (SDLC) policy [J]. The
following table summarizes the locations of the source code and its lifecycle management.
                        Model-Development      System      Name and Link
                      Tech management control              model-development    Jira board (EU)
                                                           model-development Jira board (US)
                      Code version control                 model-testing source-code repository

8.4.      Software Development Lifecycle (SDLC)
The software development lifecycle follows the same structure in EU and US, which we discuss in this section.

       1. GRN: The Opt-Var model is used by the Autohedger algo for Morgan Stanley’s Electronic Trading
          Business for Government Bonds. The GRN of the Autohedger is /ms/fid/bondtrading/fidalgo. The
          model is also used for CRB optimization by the CRB swing engine.
       2. High-level application architecture. Figure [77] below gives the high-level architecture for EU
          autohedger, and figure [78] below shows the high-level architecture for US AIM. As shown in the
          figures, for both regions, the Opt-Var model is embedded within the Hedge Calculator component of
          the autohedger algo. On a high level, the autohedger algo monitors the positions of the trading book
          and outputs the hedge orders to manage the risks. In the US, the OptVar model is also used for CRB
         optimization    (stashblue.ms.com).




130115: Opt-Var                                                                                    Page 99 of 136

                            [git] « Branch: iropt-var@be27d1a = Release:       (2024-10-31)
```
