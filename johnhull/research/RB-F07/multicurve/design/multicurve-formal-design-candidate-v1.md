# #10 多曲線統合クオートrisk / 商品横断P&L — 正式設計候補 v1

2026-10-11。状態: **設計候補。独立設計レビュー・実装・pilot/main・研究受入は未実施。** ユーザーの研究完遂指示と、johnhull/research/<RB-ID>/・hullkit非公開計算という既決定の置き場に従う。新たな一般承認質問を実装条件へ足さない。本候補をsource・資源予算・金融結果・launchの承認に読み替えない。

## 1. 目的・到達点

D（担保discount）/P3（3か月projection）/P6（6か月projection）を12個の市場quoteからexact較正し、同じ保有契約・日付・fixingから、価格、全quote gradient、**全12×12 Hessian**、商品別・book別P&Lをつなぐ。市場quoteを変えた際の他曲線への較正伝播と、roll/fixing/表現移行/市場の四項を分離できる研究基盤を作る。

研究の完了は「式を実装した」「速かった」ではない。元の全planned caseと失敗を保存し、独立参照、saved/fresh/両保管庫復元の数値検算、artifact-only教材、全費用、独立レビュー、採否を揃える。本編306節のaccepted件数は増やさない。

### 原調査から維持・具体化する点

| 維持する原範囲 | 本候補で具体化する完了契約 |
|---|---|
| D/P3/P6各4node・主12quote | 実schedule解決→coverage/rankを計測。既知resetのzero-Jを除いて別の小問題に縮めず、主quoteは明示したabstract forwardとする |
| full block IFT・second IFT・全cross-gamma | 全12対角＋66混合組、保存行列は144要素。D–P3/D–P6/P3–P6の全16要素/blockと対称側を保持 |
| exact roll・fixing・regrid・market | Vr/Vf/Vg/V1、C0/Cf、qg、実CF ledgerを保存。zero-market-move表現差の反例を必須化 |
| 全失敗・分母・cold/warm費用 | 元roster/attemptを先に固定し、NaN/unknown/未実行/timeoutを末尾まで照合。速度不採用も研究完了となり得る |
| 保存・fresh・C/F両復元・教材・採否 | 各独立contextで元全数値を検算。参照・SHAは由来の認証、価格/Greek一致は許容誤差による検算 |

## 2. 根拠・選択肢・境界

正本は[調査案](/home/kazumasa/worktrees/johnhull-storage-codec/johnhull/research/RB-F07/multicurve/RESEARCH.md)と[独立再レビュー](/home/kazumasa/worktrees/johnhull-storage-codec/johnhull/docs/superpowers/reviews/2026-10-09-next-research-design-rereview.md)。初回I1は、exact rollを新tenor再較正と混同する問題だった。v2 §8の四項bridgeを採用し、三項へ戻さない。

1. **採用候補: deterministic exact three-curve CF + analytic IFT。** 依存・単位・日付・二次較正responseを小さい独立問題から確認できる。
2. LS/smoothing/制約を同時に主較正へ入れる案。非ゼロ残差の最適性感応度/KKTが別問題になるため、今回は式と負例を残す。F07 v2の無断実装はしない。
3. HW/LMM、確率basis、options/先物convexityまで広げる案。#10完了に不要。決定論的RFR forecastを一般的な無裁定確率モデルの価格とは呼ばない。

単一通貨・synthetic calendar/quotes/fixingsだけ。NumPy/SciPy/標準ライブラリ、torch-free、公開API/__init__.py/production依存は追加しない。計算は新private module4本、研究は既存RB-F07/multicurve。既存singlecurve _quote_risk.py、公開rfr/rates/swapsの契約は維持する。Book/portalへ直接組み込まず、研究notebookをartifact-onlyで作る。

一次資料M1/M2/M3は正方局所可逆IFT・marketquote Jacobianの向き・逐次曲線依存、M5はtenor/interpolation、M7/M8はRFR日次複利・公表と観測日の区別を支持する。確認範囲は原RESEARCH §12の記録を再利用する。M4/M6の本文未取得部分、StrataのJava数値比較、実市場calendar/公表時刻・licensed dataは本候補の根拠に追加しない。これらを必要とする拡張時だけ一次資料を追加確認する。新しい市場時点依存の主張はない。

## 3. 状態・quote・契約

### 3.1 原主roster

| group / node maturity | 元のquote4本（入力順固定） |
|---|---|
| D: 3m,6m,1y,2y | synthetic OIS 3m,6m,1y,2y、主基準payment delay=0 |
| P3: 3m,6m,1y,2y | 0×3m、3×6m **abstract term-end forward**、1y/2y 3m IRS |
| P6: 6m,1y,18m,2y | 0×6m **abstract forward anchor**、1y/18m/2y P3-versus-P6 basis |

P3/P6の0-start anchorは、過去/公開済み実resetを再評価する契約とは別の合成quoteである。主12quoteのrankを既知fixingの影響で黙って失わないための選択。dated actual-reset validationにはpublication前後・既知resetのzero-Jを保存し、主較正へ既知rowを残す誤器を拒否する。t1ではこの区別を再解決する。全12quote constructionは独立CF engineのtruthから行う。

主kernelはabsolute datesのlogDF piecewise linear。zero/logDFは同じkernelの座標変換として検算し、zero-linear対logDF-linearの別補間対照も残す。各node日付はresolved calibration maturityに合わせ、D/P3/P6と全商品CFが支持内であることを実検査する。原4nodeで表せないrollを勝手に4nodeへ圧縮しない。

### 3.2 日付・公表・CF

- curve座標はACT365固定日数。coupon ACT360/ACT365とは分離する。30/360/ACTACTは独立規約を追加するまでunsupported。
- CAL_SYNTHの休日/weekendを入力に保存。following/modified-following/preceding、EOM、short/long stub、spot/payment/reset lagを私的resolverで解決し、unadjusted/adjusted日付とaccrual基準を両方保存する。
- fixingsはindex/observation_date/publication_at（timezone付き）/value/revision/source。publication_at <= as_ofのレコードだけ既知。公開後の必須欠損をforecastへ戻さない。quote bump中はknown fixingを固定する。
- held契約はfixed_coupon/spread、quantity、notional schedule、元本交換、reset/accrual/payment日付、settlement styleを固定する。shocked par couponへ更新しない。
- synthetic日付oracleは原§13をそのまま保持: valuation=2026-12-28、休日2026-12-25/2027-01-01、coupon [2026-12-24,2027-01-04)、ACT360、N=1e7、rates .03,.031,.029,.032,.028、weights [4,1,1,1,4]/360。synthetic次営業日09:00UTC公表の08:59/09:01境界、2027-01-31 modified-following=2027-01-29、2028-02-28→03-01のACT360/365をDecimal/date-tableで検算する。
- term-end FRAはN α D(e)(F-K)。advance settlementはfixing後のN α(L-K)/(1+αL)をsで支払う別oracle。未fixingの確率的期待をF代入だけで厳密としない。
- RFRのΠ(1+r_i w_i)は既知/未知を分離。lookback、observation shift、lockout、simple-added/compounded spreadを混ぜない。lagなし支払eの同D forwardだけtelescopingを使い、他はexplicit daily product。
- book: 18m coupon bond/discount bond、off-pillar forward-start3m IRS、seasoned6m IRS、term-end FRA、3m/6m basis、partial-known RFR OIS、amortizingまたはstub IRS。商品別と全bookを保存し、相殺したbookだけで成功判定しない。

具体的主valuation、truth node数値、全held quantity/schedule、freshケースの変更値はfixture作成時に列挙・固定する。上の日付oracleは、未解決の主12quote全scheduleを確認済みとする材料ではない。

## 4. 数学と独立検算

\(F(\theta,q)=0,\ J=F_\theta,\ A=-J^{-1}F_q\)、順序はD→P3→P6。下三角の非対角blockを保存し、D/P3 shockがP6へ伝播する。PV/quote residual変換はFqも微分する。

\[
g_q=V_q+A^\top V_\theta
=V_q-F_q^\top\lambda,\qquad J^\top\lambda=V_\theta.
\]

主held bookはdirect Vq=0。小さい明示direct-quote fixtureで漏れを検出する。direction v、a=Avに対して、

\[
b=-J^{-1}\{F_{\theta\theta}[a,a]+2F_{\theta q}[a,v]+F_{qq}[v,v]\},
\]
\[
V''[v,v]=a^\top V_{\theta\theta}a+V_\theta^\top b
+2V_{\theta q}[a,v]+V_{qq}[v,v].
\]

全Hは12単位方向と66混合方向から得る。較正curvatureを落とすA.T @ Vθθ @ Aはwrong control。主gradient/Hの計算にbump参照や数値結果flagを使わない。局所pure discount/CF kernelを解析的に微分し、日付branchを微分しない。

\(S=\operatorname{diag}(\text{display steps})\)、\(g_{\rm step}=Sg_q,\ H_{\rm step}=SH_qS\)。rate/basisはstep=1e-4、出力は通貨/bp・通貨/bp²。price-point oracleは別単位。full-revaluationのmove uに対して \(R_1=\Delta V-g_{\rm step}^\top u,\ R_2=R_1-\frac12u^\top H_{\rm step}u\)。

独立参照はmain private calibration/CF/derivative helperをimportしない。独自日付表・signed CF・sequential brent、絡むstressでは別simultaneous root、全再較正central/mixed bumpのh sweepを使う。1 hにつき12 diagonalと66 mixedの全H参照は中心を共用して**289 market再評価**（1+24+4×66）。calibration/price回数は実測し、既存4quote例の費用で代用しない。complex-stepはsmooth pure kernelの補助、date/fixing変更のoracleはDecimal/整数日付表。

LS負例 m=(θ,θ²),q=(1,0)のexact Hessian感応度とGauss–Newton誤器、拘束θ≥0の左右微分0/1を残す。主exact-rootを非正方Jの疑似逆で一般化しない。

## 5. 四項P&L bridge

\[
\mathrm{P\&L}=V_1-V_0+C_f
=\underbrace{V_r-V_0+C_0}_{roll/carry/cash}
+\underbrace{V_f-V_r+(C_f-C_0)}_{fixing/cash差}
+\underbrace{V_g-V_f}_{表現移行}
+\underbrace{V_1-V_g}_{市場}.
\]

- Vr: 保有契約とabsolute旧knotsを保持し、D0(u)/D0(t1)・projection ratioでexact roll。未知fixingは旧deterministic forecast。t1 anchorを加える。
- Vf: 同じrolled evaluatorへ実現fixingを反映。CFは指定担保口座によりt1へ累積。ex-paymentのCFはvalueから除きledgerへ一度だけ加える。
- Vg: t1 calibration instruments/node/kernelで表せるcenter。exact支持内主ケースでVg≈Vfを検査。new-tenor/regrid対照の差を独立項に残す。
- V1: 同じt1表現・fixingsに新quotesを適用。Taylor centerはVg、qg=m_t1(θg,fixings_t1)、move=q1-qg。qrollやt0 tenor quotesをqgへ流用しない。

旧reviewのknots [0,.5,1,2,3]・logDF [0,-.005,-.04,-.07,-.10]・roll .25・new [0,.5,1,2]によるzero-move表現差を独立負例にする。horizon欠落・rank不足はunknown/failedとして保存し、未承認外挿で埋めない。publication/reset/payment/expiryの離散変化はmarket smooth Taylor率へ混ぜない。各Vr/Vf/Vg/V1 evaluator、node/schedule/fixing、C0/Cf ledgerを保存する。

## 6. 全case・採否・精度契約

原§9のflat/sloped/humped、negative rates、±basis、near-redundant、information-thinを維持。single bucket12本、D/P3/basis-only、parallel/twist/mixedの原directionを両符号・0.5/1/2/4/8bp、stress25/50bpで列挙する。数値vectors、shape×direction×dateの組合せ・予定件数はprotocolで明示し、暗黙の全直積や後から成功subsetへ差替えはしない。12quote main、24quote scaling、商品数1/10/100のprecision-equal費用対照を別familyとして保持する。

全date cases（EOM、休日、leap、stub、各lag、公表境界、欠損、payment/expiry、RFR observation3規約）、原wrong controls10種を保持する。wrong controlsは失敗の検出を確認するvalidationであり、主器の成功分母へ足さない。

| 検算 | 原候補基準を引継ぐ |
|---|---|
| exact calibration | max scaled residual≤1e-10、finite、scaled full rank。raw condition numberだけで停止しない。amplification10超は警告 |
| PV / g / H | PV 1e-7+1e-12 sum_abs_notional、g/bp 2e-6+1e-8 abs(gref)、H/bp² 1e-5+1e-6 abs(Href)。H sweep安定域無しはunverified |
| 変換 | 同一kernelのzero/logDF、quote/PV residual、同一problem permutationが単位別許容差内。別補間同士の一致は要求しない |
| 残余次数 | ≥3 non-roundoff moveでR1 slope1.8–2.2、R2 slope2.6–3.4候補。degenerateは元directionを保持し絶対上界で別判定 |
| conservation | product/book PV/g/Hの和、payer/receiver、四項bridge、cash一回計上。絶対基準 1e-7+1e-12 grossCFscale |
| 改善分母 | abs R、bp-notional R、原ΔV/R1/R2、economic floor、valid/statusを保存。floor以下/zeroはratio undefined |

採否は(1)計算の正しさと支持範囲、(2)一次→全二次の残余改善/悪化、(3)precision-equal総費用を分ける。速度・stress改善が無くても全結果から不採用/限定採用/結論保留を記録できれば研究の報告工程は完了。必要数値がunknownなら「数値受入済」とはしない。

## 7. ソース・保存・再検算・教材

依存: _multicurve_cashflows→_multicurve_quotes→_multicurve_risk→_multicurve_pnl。研究reference_methods.pyはこれらから独立。研究runnerはprimary/reference両方を呼び、checkerは保存primitiveから元全CF/較正/gradient/H/bridge/費用を再計算する。notebookは保存済み検算summaryと図配列を読む。

必須rawは全quote/単位/順序、全curve/node/θ、resolved schedule/fixing/held contract、残差/J/必要second-derivative、全PV/g/H/方向/shock/h-sweep/CF ledger、全counterfactual、参照値/誤差、status/attempt/reason/iterations/SVD/backward residual/warnings、費用。再計算に必要な値を図だけへ置換しない。

case単位JSON+NPZでprimitiveを一度保存し、共通fixtureはmanifestで参照する。reportはcase ID・物理参照・小さい検算summaryだけ。全caseをhydrateして重複array/metadataを蓄積しない。logical入力/出力digestは元値・dtype・shapeを保持、byte SHAはsource/物理改変認証だけに使う。#9の新codec/checkerを当然に依存追加しない。#10に必要な小さいliteral保存から始め、実量で不足を示した時だけ限定transport案をレビューする。

saved: 全planned ID/出力/末尾/unknownを照合し元数値を再算出。fresh: 別contextで新しい全planned演算を実行し独立参照と再比較。C/F: ADR0004の既存APIで各storeに保存し、それぞれ別rootへ全必要rawを復元、元pathへ戻らず同じ全数値/費用検算を行う。source changesは旧rawの生成sourceを書換えず、独立確認した新verifier/旧producerを分ける。復元verifiedフラグだけで終えない。

教材は3必須図（risk heatmap、R1/R2 vs move、四項bridge）、任意4図目（悪条件/費用）。artifact-only notebookのfresh実行、図目視、全失敗/分母/単位/採否説明が必須。研究artifactとindex/docstrings/対象regression/release/台帳不変確認を完了時に結ぶ。

## 8. 実施順・資源・未確定

#9研究トラックの採否記録後に#10金融実装・計測を開始する。同時研究1本を維持。本候補作成は文書準備のみ。source85/live saved checker/元rawへ接続・変更しない。

実施: 日付/primitive→12quote較正/独立参照→full IFT/H→四項bridge→source数学レビュー→pilot→protocol/source/roster/prior freeze→main→saved/fresh/C/F→教材/独立研究レビュー/採否。

初回資源候補は原案のCPU-only、pilot300秒/main1800秒。**行政上限候補でruntime見積もりではなく、未承認。** RSS、全path expanded/physical bytes、両store/各復元の同時占有、checker/fresh/I/O費用、24quote/100商品規模は未測定。最大shapeと全case数・fullH289再較正×h数を計数し、事前予算を独立判断へ結ぶ。超過・source fault・oracle失敗・未使用を区別し、未知費用を0で補完しない。源/原入力を縮めてcapへ合わせない。

残る具体的未知: (a)全date/quote/held数値roster、(b)actual12×12 rankとreset/coverage、(c)H sweep精度/degenerate directions、(d)exact rollとt1表現支持、(e)main/fresh/両復元の全時計・RAM・容量、(f)採否。4quote spikeは(a)–(f)の証拠ではない。新source/mechanics、資源prior、金融結果、研究受入はそれぞれ別の判断として記録する。

## 9. 参照固定と今回の範囲

- RESEARCH SHA256 e17e6cbd83c34270f480774b824c494abb97e96b89a37f3077f401463c32250a
- reviewed-research-v2 SHA256 c547b78cca4e21736acd177c0182cb250486004040be3da9817ff90567e5b482
- independent rereview SHA256 6a1e4daa866e02594b87cc80b0ef898c58d609d2ce93ca7e60a6f3cf8300d016
- spike metadata SHA256 9bb7bbd523f84ec261222f5fac2807ee63a2bd4cf8452d8bf325183adf0d5854

本候補は上記記録・既存source境界を読んだ文書。新たな金融計算・試験worker・一次資料取得・source/Git/CAS変更は行っていない。実装計画は[multicurve-formal-plan-candidate-v1.md](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/multicurve-formal-plan-candidate-v1.md)。候補間の記述確認は独立数学/source/研究承認の代用ではない。
