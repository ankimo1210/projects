# #11 増分XVA正式設計候補 — 独立設計レビュー v1

2026-10-11。Reviewer: multicurve_design_review（#10とは別のレビュー対象として#11を確認）。判定: **設計と実施工程の完成契約として承認。Critical 0 / Important 0 / Minor 1。** scope=design_contract_only。数値結果、source実装、資源prior、pilot/main launch、規制適合、phase/main統合の承認ではない。

対象候補:
- incremental-xva-formal-design-candidate-v1.md: SHA256 9258819a189bbfefaa1dd82c4edc0895fc0a58c7abe0120bfa9298a261a3a399
- incremental-xva-formal-plan-candidate-v1.md: SHA256 2ddb3feb4d98ef4cc8fc72194a0ebb072095ea9d6fdf8f65338c8abbbee8e36d

RB-H09/incremental_xvaの正本README/RESEARCH、v2草稿、既存初回レビュー・再レビュー、既存FlatHWのQ座標説明を読んだ。新規変更は本レビューとdecision JSONだけ。既存文書/source/Git/CAS/source85/保存検算85801には変更せず、金融・RNG・solver・MC・pytest・ruff・試作計算は実行していない。

## 1. 元研究の範囲を維持している

| 原要件 | 候補の対応と評価 |
|---|---|
| book before/after、単独、a/h bundle | design §1/8、plan Task7/10。追加差・単独・marginal/Eulerを別量とし、同原始経路で全成分を再評価する |
| 4bundle×4CSA×2policy×3seed | design §8、plan Task1/9/10。32主cells、96主seed-cellsを維持。validationや失敗を使って削減しない |
| same-set異満期hedge c | design 119/122行、plan Task3/5。主cを同legal setとする既存I2修正を保持。h量は追加aのt0 DV01だけで固定 |
| 同じhを別non-nettable setへ置く対照 | design 126行、plan Task1/3/5。旧set IM不変＋新set IM非負を検査。資金pool/資本集計便益をIM nettingへ読み替えない |
| fully margined dealer hedge d | design 120/122行、plan Task6/10。dealerは別counterparty/setとしてcredit/IM/funding/CCR/BA-CVAを再計算。M1のCSA範囲明記が必要 |
| VM/MPOR | design §4/5、plan Task3/4。call/pending/settledを分け、default時のlast settledを凍結。coupon/gap/closeoutと返還eventを保存 |
| 算定した非SIMM IMとMVA | design §6、plan Task5。99% posted/received full-revaluationを主器、stress/fat-tail/ES/proxyを別labelとする。外生定数で代替しない |
| IRS全capital subset | design §7、plan Task1/6。RC/NICA、duration/delta、3bucket、maturity/MPOR、multiplier floor、EAD cap、CCRとreduced BA-CVAを保持 |
| FCA/FBA/MVA/KVA/COLVA | design §2/4/7、plan Task7。全path積分とsigned増分、口座別stop masks、原cashを保存する |
| 全独立参照 | design §10、plan Task2–7。列挙cash、OU/discount、unilateral GBM、FTD密度積分、IM CDF/多root、scalar capital、定残高費用を残す |
| 原始成果・末尾・失敗・unknown | design §11、plan Task8–10。全normals/default/ledger/IM/capital/cost/independent unitを保存。seedやdigestだけで数値PASSにしない |
| saved/fresh/両semantic restore | design §11、plan Task8/10/11。全元条件、新context、C/F各単独全blob復元と数値checker・教材renderを要求 |
| 全費用と資源 | design §11、plan Task8/9/10。cold、pilot/main/reference/fit/check/C/F/restore/review/render、実時計/RSS/bytes、overrun/unknown尾を保持。inclusive二重加算しない |
| 3図・artifact-only教材 | design §11、plan Task11。成分/SE、時点口座/資本、誤差とall-in費用の3図。MC/training/networkをbuildから呼ばない |
| 採否・最終研究レビュー | design §12、plan Task10/12。same error budgetと全費用で採否、challenger不採用でも研究の報告を完了できる。未解決bias/費用/復元は未完扱い |
| source境界と実施順 | design §3、plan 12/175行。#9→#10→#11、同時金融研究1本。#10新APIに依存しないflat/zero-basis v1、private/torch-free/既存依存/公開API不変 |
| 最終suite・index・release・roadmap | plan Task12。phase末適用suiteとRuff/release、実検証範囲・状態更新。本編306件を研究だけで増やさない |

この表は文書上の完成契約の確認であり、未実装のgateを実証PASSにしたものではない。元研究をCVAだけ、低次元anchorだけ、小Nだけへ縮める変更は認めていない。

## 2. 数学・因果順序・sign/units

### Credit、担保、IM

clean V>0を銀行資産、C=received VM−posted VM、Ip/Irを非負segregated IMとする。EC=[Mgap−Cgap−Ir]+、EB=[−Mgap+Cgap−Ip]+の向きは銀行・相手のperspective reversalに整合する。posted Ipはcounterparty defaultで別返還cashになり、ECから二重控除しない。secured/full recoveryとunsecured/LGD、余剰IM返還を別欄にした。

CVA/DVAはfirst-default indicator、D(0,tau+g)、対応LGD claimの積をQで平均する。独立hazardの密度lambda_C SC SBと銀行側lambda_B SB SCを参照にする。E[D]E[loss]への分解やunilateral survivalだけの代用を拒否する。共有銀行tau_B、counterparty/set map、before/after共通uniformsも指定されている。

fixing→coupon/upfront settlement→call calculation→due settlement→defaultの順序を固定し、別timing対照を保存する。MPORでpending callを担保へ混入しない。満期後closeout/IM返還までevent horizonを伸ばす。F0、posted IM、資本のrunning stopは一律first-default survivalにまとめていない。

### Funding、資本費用、internal value

Vcredit=Vclean−CVA+DVA、A=FCA−FBA+MVA+KVA+COLVA、Vdesk=Vcredit−Aの符号は一致する。F0>0は借入、F0<0は投資で、running sb F0+−sl F0−を費用として保存する。segregated Ipとblocked KをF0から除き、MVAとKVAの別口座に計上する。received IMの資金利用、EEの資金残高への代用、excess costのF0への再帰feedbackを主器で認めていない。

COLVA=(rVM−rOIS)C、主rVM=rOISで0。cKは資本運用利息控除後のannual excess charge。phi>0対照はreserveの取り崩しと投資収益を別ledgerに載せ、FVA/KVAへ資金便益を二重控除しない。DVA/own-default windfallをliquidity spreadへ追加しない。これは明示したinternal desk policyであり、一般の再帰funding fair-value解を主張していない。semi-replicationの簡約条件対応表と独立total式もTask7に保持する。

### Q marketとP_IM、精度

既存FlatHWはQのzero-mean OU座標xとr=x+phiを区別している。候補はexact state/discount integralを同じ規約で使い、IMのphysical/stressed kernelとは別にする。主IMはGaussian full revaluation、posted=max(q99(−DeltaPi),0)、received=max(q99(DeltaPi),0)。eta0/完全offset/point mass/複数root/低tail densityの扱いを要求する。

coupon/reset/historyを含む実conditional Gaussian rankを数えるため、一因子だから全参照を1D/2Dへ縮約する仕様にはなっていない。rank>1はcubature/nested対照、誤差と費用の実測へ進む。Task1/5でP_IMの「zero drift」の対象座標、各dated intervalのmean/covariance、cum-cash基準を具体的な入力・独立式で固定する必要がある。Q用joint_momentsのmeanをそのままphysical kernelとする承認ではない。

paired after−beforeをpathで先に作り、independent unitのsd/sqrt(N)を使う。antitheticはpair平均、nestedはinner/outer再生成、quantileはpoint mass等を考慮したintervalを別に扱う。clean、求積tail、default/MPOR/time、IM、capital、MC、challengerの誤差を分け、relative errorをnear-zeroへ強制しない。

## 3. 固定BCBS版・公式例subset

公式の固定版本文を追加確認した。一般の最新規制や管轄適合の承認ではない。

- [CRE52](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05)：52.1–2のset別EAD/cap、52.17–18のsegregated posted IM除外とnet VM sign、52.22–23のmultiplier floor、52.74–75の複数margin/nettingの特例。候補のnormal setと特殊coverageの区別に使用。
- [MAR50](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08)：50.14の全counterparty集計・0.65 scalar・rho=.5、50.15のset和/EAD/alphaとnon-IMM maturity参照、50.16のsector/quality区分を確認。K_CVAをcapital額として扱い余分な.08を掛けない点は整合する。
- [CRE32](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/32/inforce/2023-01-01/published/2020-03-27)：32.46/49のmaturity floorとnotional加重、32.51の短期eligibility条件を確認。MAR50の5年cap除外と、元満期>=1年の主IRSに一般floorを適用する候補は整合する。
- [CRE99](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/99/inforce/2023-01-01/published/2020-03-27)：99.22/29/31/32を確認。Example1はUSD IRS2本とEUR swaption1本。候補が原典再現をIRSのtrade-level duration/delta/bucketに限定し、例全体のEADと呼ばない判断は正しい。

画像数式の完全転記、全係数fixture、capital source実装の一致は未検証であり、Task1/6の独立転記/金融レビューに残る。手製IMをSIMM、synthetic RW/ratioを監督承認、selected Kを銀行全資本と呼ぶ変更はない。

## 4. Minor M1 — 「複数CSA unsupported」の集計範囲を明確にする

対象: design 95行、plan 94行。候補は「複数CSA」を無修飾でunsupportedとしている。一方、主bundle d（design 120/122行）はclientとdealerに別legal set・別CSAを要求し、dealer資本の算定も必須である。実装でbook全体のCSA数を1に制限すると、正常なdの全8cells×3seedsやdealer capitalがunsupportedへ落ち、元研究範囲を失う。

**必要な具体化:** v1は複数legal sets/counterpartiesを扱い、各setが一つの対応CSAで覆われる正常なbookは支持する。unsupportedは、同一legal setの複数CSA、margined/unmargined混在、複数setに共通collateralを配賦するCSAなど、CRE52.74–75の未実装な特殊coverageへ限定する。元scopeの別legal-set dを拒否しない。

Task1/6に、dのclient+dealer別CSAが双方のEAD/SCVA/IM/費用へ入る正例と、同じsetへの未対応重複coverageを理由付き拒否する負例を置く。正常な複数setのunsupported判定を防ぐ具体的gateであり、表記だけの指摘ではない。既存のdealer map・set別capital・dealer漏れnegative gateで意図は明白なため設計承認は止めないが、terms/capital実装前に追記すること。

元候補2文書はこのレビューから修正していない。正本採用時の追記と実装前gateはroot担当。元32×3の削減や別CSA正常bookの除外を承認していない。

## 5. 判断範囲と残るゲート

1. 設計採用時にM1を補足し、元全terms/IDs/CSA map、calendar、IM kernel/cum-cash、capital式/係数/単位をTask1で固定。
2. Task2–7のsource数学、conditional rank・root・tail、信用/担保台帳、資本・費用・独立参照を検証。
3. pilotでN/M/grid/order・precision・最大shape保存/読取・whole工程費用と容量を実測し、独立priorとroot実承認を別に取得。
4. #9→#10→#11、同時金融研究1本を守り、元96主seed-cellsとvalidationを実行。全status/unknown/原費用を保持。
5. saved/fresh/C/Fそれぞれの全数値、3図教材、phase末検証と独立研究レビュー・採否が完了して初めて研究完了を判断する。

scope=design_contract_only。source_implementation_approved、resource_budget_prior_approved、financial_numerical_acceptance_approved、pilot_main_launch_approved、regulatory_compliance_approved、phase_or_main_acceptance_approved、capacity_or_runtime_guaranteedは全てfalse。

