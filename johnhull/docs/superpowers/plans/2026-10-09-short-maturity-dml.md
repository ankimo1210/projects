# RB-F05 短期・0DTE v1 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Steps use checkbox syntax.

**Goal:** 合成cash-settled欧州callの短期spot Delta教師を独立検証し、price-only / Delta-DMLのpaired 6 fits、Gamma、強い標準器、全費用を比較する。

**Architecture:** ACT/365のcarry、252日で正規化した分散時計、Merton複合Poisson pulseを別々に積分して終値を厳密生成する。Brownian conditioningのprice/Deltaラベルをprivate learnerへ渡し、独立count-mixture・密度積分で検証する。結果を保存しartifact-only notebookで表示する。

**Tech Stack:** 既存Python / NumPy / SciPy / PyTorch CPU float64 / pytest / ruff / nbclient / matplotlib。新production依存なし。

**Spec:** ../specs/2026-10-09-short-maturity-dml-design.md。2026-10-09の調査・計画提案。正式pilotの独立承認後、source10・条件・N1048576を固定済み。主6fits/全336点・追加検証・両復元・実3図・全採否・最終独立レビューを完了。main統合は次。 本人の継続指示に従い、rootとsubagentsが実装し独立レビューする。

## Global Constraints

- v1はK=100、rebate=0、same-day European cash call、expiry=2026-10-08 16:00 America/New_York、session09:30–16:00。主領域は残り1–390分。
- r=.03、q=0、diffusion annual vol=.20、252 sessions/year、U clock weights=(2,.5,2)、edges=(0,.15,.85,1)。calendar/時計は合成研究の定義。
- eventは15:30–16:00のPoisson pulse、background=0、log jump mean=-.05/std=.10、full nominal log-return variance=.00035。no-eventはΛ=0。
- Delta/GammaはSだけを動かし、K・時刻・expiry・calendar・clock・pulse・Q-jump lawを固定する。
- 新しい計算はprivate module。公開API/__init__/本編section ledger/既存digital・discrete成果は不変。hullkitはTorchをimportしない。
- 学習はprice-only×seeds11/29/47とDelta-DML×同3seed。Gammaは診断のみ。全paired seeds・元のslot・失敗・unknownを保存する。
- main前に条件・source全件・seed ledger・pilot・独立reviewをfreeze。mainでN/seed/checkpoint/toleranceを選び直さない。
- notebook/saved checkerはRNG・optimizer・学習・network/freshを実行しない。数値比較は許容誤差付き。MCはSEとrare件数を併記。
- rootがGit・正式docs・ROADMAP/INDEX・受入後のmain統合を所有。rootがbranch/commit/main/pushを担当する。

## Review Focus

1. expiry ATMのordinary Delta/Gammaは未定義。exact payoffとreason付きunknownを保存（Task1/3/4）。
2. UTC carry・variance clock・pulse overlapを独立検算。spot bumpで時計が変わらない（Task1）。
3. Λ>0の未観測jumpによるSE0と、Λ=0の厳密conditioning退化を分ける（Task1/2）。
4. tiny W、価格cancel、Gamma、Poisson/quad cutoffを別許容差で検証（Task1/2）。
5. raw/safe/fallback、元分母、費用カテゴリ合計/CLI wall/共通費用を区別（Task3/4/5）。

## 1. 数式の整合性：独立導出、未数値検証

UTCでcarry年数 \(\tau_c=(T_{\rm UTC}-t_{\rm UTC})/(365\cdot86400)\)、
discount \(D=e^{-r\tau_c}\)。既存variance_clock_fractionの累積をu(t)とすると
\(W=.20^2[1-u(t)]/252\)。時計のnormalizerは.15×2+.70×.5+.15×2=.95。

\[
\Lambda=.028\,|(t,T]\cap[15{:}30,16{:}00]|_{\rm seconds}/1800,\qquad
.028=.00035/(.05^2+.10^2).
\]
Λ(μ_J²+σ_J²)はcompound-Poisson log-return variance。pulseは確実に1回発生する原子的ScheduledJumpとは別の契約。Q-jump lawを合成価格モデルとして指定する。補償だけから一意な市場jump risk premiumは導かない。

\[
g=e^{\mu_J+\sigma_J^2/2},\quad \kappa_J=g-1,\quad
N\sim{\rm Poisson}(\Lambda),\quad J=N\mu_J+\sqrt N\,\sigma_J Z_J,
\]
\[
S_T=S\exp[(r-q)\tau_c-\kappa_J\Lambda-W/2+\sqrt W Z_B+J].
\]
N/Z_B/Z_J独立。決定論的clock・intensityの積分なので欧州終値にEuler/time-grid biasはない。
\(E[S_T]=Se^{(r-q)\tau_c}\)、\(Var(\log(S_T/S))=W+\Lambda(\mu_J^2+\sigma_J^2)\)を検算する。

### Call教師

\[
Y_C=D(S_T-K)^+,\quad
Y_\Delta^{PW}=D(S_T/S)1_{\{S_T>K\}},\quad
Y_\Delta^{LR}=Y_C Z_B/(S\sqrt W),
\]
\[
Y_\Gamma^{LR2}=Y_C(Z_B^2-Z_B\sqrt W-1)/(S^2W),\qquad
Y_\Gamma^{LRPW}=D(S_T/S^2)1_{\{S_T>K\}}(Z_B/\sqrt W-1).
\]
callのPW Deltaはlocal Lipschitz/有限平均multiplierで交換を正当化できる。indicatorの素朴な再微分Gamma=0は負対照。digital PW0をcallへ転用しない。

主教師はBrownianを積分する。\(A=e^{(r-q)\tau_c-\kappa_J\Lambda+J}\)、
\(d_2=(\log(SA/K)-W/2)/\sqrt W\)、\(d_1=d_2+\sqrt W\):
\[
Y_C^{cond}=D[SA\Phi(d_1)-K\Phi(d_2)],\quad
Y_\Delta^{cond}=DA\Phi(d_1),\quad
Y_\Gamma^{cond}=DA\phi(d_1)/(S\sqrt W).
\]
Lambda=0なら全randomnessが消える。actual_random_draws=0、analytic_deterministic、SE=0を保存。未生成pathsを観測数・費用に計上しない。expiryではprice exact payoff、S≠KのDelta0/1・Gamma0、S=Kのordinary Greeksはunknown。post-expiryは契約終了。

### 独立参照とcutoff

ordinary Poisson(Λ) weightsでcount-mixtureを別実装。count nのlog-terminal mean
\(m_n=\log S+(r-q)\tau_c-\kappa_J\Lambda-W/2+n\mu_J\)、
variance \(v_n=W+n\sigma_J^2\)、
\(A_n=e^{(r-q)\tau_c-\kappa_J\Lambda+n(\mu_J+\sigma_J^2/2)}\)。
d2_n=(m_n−log K)/sqrt(v_n)、d1_n=d2_n+sqrt(v_n)として
C_n=D[S A_n Φ(d1_n)−K Φ(d2_n)]、Delta_n=D A_n Φ(d1_n)、
Gamma_n=D A_n φ(d1_n)/(S sqrt(v_n))。

Λ*=Λg、n>nmaxのtailの上界は
\(B_C=Se^{-q\tau_c}SF_{\Lambda^*}(nmax)\)、
\(B_\Delta=e^{-q\tau_c}SF_{\Lambda^*}(nmax)\)、
\(B_\Gamma=e^{-q\tau_c}SF_{\Lambda^*}(nmax)/(S\sqrt{2\pi W})\)。
導出はp_Λ(n)D A_n=e^-qτ p_Λg(n)、payoff≤S_T、Φ≤1、φ≤1/sqrt(2π)、v_n≥W。
価格cutoffだけでGamma精度を保証しない。

第二参照はcountごとのstandard normal densityをpayoff×scoreでadaptive積分。
z=(log S_T−m_n)/sqrt(v_n)、積分下限z_K=(log K−m_n)/sqrt(v_n)、
Delta score=z/(S sqrt(v_n))、Gamma score=(z²−z sqrt(v_n)−1)/(S² v_n)。
CDF/teacherを呼ばず、Gaussian densityとexp(log-terminal)の積をlog領域で組み立ててoverflowを避け、quad tolerance1/4・tail range拡張の再計算差を保存する。quad error estimateは厳密上界とは呼ばない。
既存Merton価格との別照合はtau_c>0に限りsigma_eff=sqrt(W/tau_c)、intensity_eff=Λ/tau_cを使う。

## 2. 再利用と新規範囲

| 既存ファイル（johnhull/hullkit/src/hullkit/下、別記除く） | 再利用・限界 |
|---|---|
| zero_dte.py TradingSession / variance_clock_fraction | aware session・U clock。private same-day contract stateにUTC carry/pulseを追加 |
| zero_dte.scheduled_jump_intensity / sv_jump_teacher | 単位・normal/count分離の規約を参考。Euler/fixed .001S bumpにはGreek SEがなく主oracleにしない |
| alternative_models.merton_jump_price | reweighted価格級数による別照合。independent oracleはordinary count-mixture/density |
| _digital_teachers.py | IID SE・conditioning/負対照規約。digital payout/T領域は引き継がない |
| _multilevel_mc.block_moments / merge_moments | shifted M2集計。3-vector covarianceを追加検証 |
| deep_hedge_price/src/deep_hedge_price/_digital_dml.py | plain arrays/train-only scales/CPU float64。新call learnerは3features・unconstrained linear C/K output・Gamma対応 |
| research/RB-F05/discrete/reference_methods.py | 独立densityの境界/error分離を参考。barrier/PDEは流用しない |
| research/RB-F06・RB-F08 | 小さいschema、source/seed/review/CAS/費用receiptの規約 |

新金融sourceはprivate teacher/private learnerとresearch/RB-F05/short_maturity/のreference_methods.py、protocol.py、pilot.py、build_reference.py、analytics.py（計7件を候補）。表示builderは金融freezeと分ける。既存zero_dte.py / alternative_models.py / _multilevel_mc.pyを呼ぶ実装なら、その3件もsource registryへ含める（新7件＋再利用3件が初期候補）。SOURCE_FILES全件存在が必須。
既存研究成果を複製・上書きしない。正式ファイル名はrootが計画採用時に確定する。

## 3. Pilotの候補条件と固定規則（pilot前・未実測）

- pilot:残り分=[1,5,30,58.5,331.5,390]×log-moneyness=[-4,-2,0,2,4]sqrt(W)及び[-.05,+.05]×2regimes＝84slots、3独立streams。
- N候補=[16384,65536,262144,1048576]。最大Nを1回生成したprefix集計で比較。候補間の観測を独立と数えない。
- MC精度候補: SE(C)≤.002 currency、SE(Delta)≤.0005、
  SE(K Gamma)≤.01 max(1,abs(K Gamma_ref))。
- oracle許容差候補: C absolute1e-9K＋relative1e-10、Delta absolute1e-9＋relative1e-10、
  K Gamma absolute1e-7＋relative1e-9。Poisson tail・quad再計算差へ各1/4の枠を割く。
- 独立MC検算はabs(mean−oracle)≤6SE＋oracle tolerance。6SEは不偏性/coverage保証ではない。
- active jump slotはobserved nonzero count>=100も必要（工学的閾値、SE保証ではない）。
  Λ>0 & count0→rare_event_unobserved、count1..99→rare_event_unresolved。
  Λ=0のanalytic deterministicとは分ける。全slot/streamに通る最小Nをmainへ固定。
- capでも不成立ならfreeze拒否。slot削除・seed変更・mainでN追加・解析値への暗黙置換をしない。count-stratification等は別revision。
- 解析的規模確認で1分eventΛ=.028/30。N16384/65536/262144の期待nonzero数は約15.3/61.1/244.6。
  30秒diagnosticのN262144は約122.3、1秒は約4.08。主1分以上とOOD診断を混ぜない（MC実測値ではない）。
- boundary診断:remaining0/1/30秒、pulse/clock break両側1秒、S=K/非ATM、post-expiry、NY↔UTC、夏冬offset、設定holiday/weekend、session外。
- CRN h=[.02,.05,.10]S sqrt(W): finite-h oracle、sampling SE、true Greekとの差を分離。
- pilotでnormal/count/scenario/fit/batch/freshのseed roster、N、all tolerances、loss/scales、interpolation grid、caps、採否を保存し独立reviewでfreeze。
- Financial code全件（learner/runner含む）が揃ってからfull pilot/freeze。Task2とTask3の実装は並行可能だが、mainはfreeze後。
- 主教師のN選択対象はconditioning。raw/PW/LR/LRPW/CRNはpilot検算と負対照のみ。
- no-eventのSE0は厳密退化。active jumpの小さいSEだけでrare componentの検証成立とはしない。

## 4. 最小task分割

作業root=/home/kazumasa/worktrees/johnhull-research-roadmap。以下はroot相対パス。

### Task1: exact core teacher＋独立参照

Files: johnhull/hullkit/src/hullkit/_short_maturity_teachers.py、
johnhull/research/RB-F05/short_maturity/reference_methods.py、
johnhull/hullkit/tests/test_short_maturity_teachers.py。

Interfaces: 正式spec §12のClockState/CallParameters、clock_state、conditional_values、path_values、mixture_values、compact_teacher/compact_moments。dictのextra配列と費用metadataは保存境界へ渡し、expiry通常GreekはNaN+reasonを保持する。

- [x] failing testsを先に作る:別UTC時刻でも同instant同state、時計積分、martingale/jump variance、
      Lambda0のBlack/density、nonzeroΛのmixture/density/Merton、
      PW/LR/Gamma/conditioningのSE検算、expiry ATM unknown、active count0。
- [x] witnessed RED→最小private実装→GREEN/ruff。例えばordinary expiryは
      assert expiry_result["price"] == pytest.approx(0)
      assert expiry_result["delta_status"] == "undefined_atm"
- [x] 同値退化M2=0、chunk統合と一括統計を許容差比較。normal/countはcaller drawsにする。
- [x] rootへ式・commands・RED/GREEN・未検証領域を報告。独立review後Task2へ。

### Task2: protocol / pilot / freeze

Files: short_maturity/protocol.py、pilot.py、
johnhull/hullkit/tests/test_short_maturity_protocol.py / test_short_maturity_pilot.py。

Interfaces（案）: candidate_protocol()->conditions、
build_seed_ledger(p)->rows、run_pilot(p,directory,mode)->record/arrays、
validate_pilot(record,arrays,p)->deterministic checks、
freeze_protocol(p,pilot,arrays,review)->frozen。
schemaはsource/seed/condition/allocation digestsをbind。smokeはfreeze拒否。

- [x] RED:source欠落/seed重複/count0 SE0/rare件数不足/precision不足/smoke/改変reviewのfreeze拒否。
- [x] GREEN/ruff後、全financial source完成までfull samplingを待つ。
- [x] isolated full pilot、保存mean/M2/covariance/counts、cutoff/quad/CRNの元分母を独立検査。
- [x] selected_N=min(ready_candidates)の全slot規則で固定。空ならunsupportedを記録してfreezeしない。
- [x] 独立reviewが条件・原始配列・N・費用を承認してfreeze。mainデータはまだ使わない。

### 主教師のcompact IID保存境界

- Λ>0では全original N個のPoisson countsを生成する。Nは統計の元分母。
  n0のconditioned(C,Delta,Gamma)は同一なのでzero_countと定数vector(C0,D0,G0)を保存する。
  nonzero_index / count N_j / normal mark Z_JのみをNPZへ保持し、Brownian drawsはconditioning主教師に不要。
- nonzero_indexはpilotのprefix N比較にも必要。各prefixでzero_count=N−active件数を再構成する。
  保存方法はIID標本のlossless compact化で、count-stratification/success-until samplingではない。
- 再計算はnonzero marksから(C,D,G)を評価し、定数zero blockとnonzero blockの安定Chan mean/M2/cov統合を行う。
  sample covariance=M2_matrix/(N−1)、各SE=sqrt(diag(M2_matrix)/(N(N−1)))。
  zero/active件数、prefix IDs、joint momentsをsaved-only checkerで照合する。
- normal/count streamは分離。normal_draw_policyはfull_N_then_compact又はactive_onlyの一方をfreezeする。
  active_onlyではcountを先に全N生成、sorted active indicesへ独立standard normalsを割当てる。
  n0ではmarkがpayoffへ入らないのでIID lawを保持できるが、stream消費・fresh replay契約は両policyで異なる。
  初期推奨はactive_only、実装前にrootが確定。actual_random_drawsをNと誤記しない。
- Λ=0はanalytic_deterministicとしてcount/normal生成を省き、MC標本のSE0と区別する。
  active markを省略した状態でunconditioned/PW/LR pilotを再構成できるとは主張しない。
  raw estimator検算のpilotは別のdiagnostic draws/seed/保存scopeを使う。
- N262144×train全件をfull paths保存する数GB規模を避ける。
  compactが小さくてもsampling/教師計算の全N費用、normal生成policy、元N、rare件数は保存する。

### Task3: 6 NN比較＋strong baselines＋saved runner

Files: deep_hedge_price/src/deep_hedge_price/_short_maturity_dml.py、
short_maturity/build_reference.py / analytics.py、
deep_hedge_price/tests/test_short_maturity_dml.py、
johnhull/hullkit/tests/test_short_maturity_reference.py。

Interfaces（案）: train(inputs,prices,deltas,seed,dml,settings)->weights/scales/stats、
predict(weights,inputs)->price/delta/gamma、
run_study(frozen,output)->record/arrays、
load_result(output)->record/arrays、check_record(record,arrays,fresh=False)->checks。

- [x] RED:plain-array boundary、train-only scales、paired init/batches、weights replay、
      log-spot physical chain rule、Gamma、raw/safe route/expiry/unknown保持。
- [x] 3features=(x=log(S/K),log(remaining seconds),event flag)、3→32→32→1 tanh、
      normalized C/Kのunconstrained linear outputを初期候補にする。softplus/gatingはrootの数式検討後に別途判断し、真のGreek評価をclipしない。price/deltaはsame scalar priceから微分:
      Delta=C_x/S、Gamma=(C_xx−C_x)/S²。event flagは0/1契約のみ。
- [x] raw出力をclipしない。safeはexpiry exact、minT未満/契約OOD/nonfinite/bound違反をmixtureへfallback。
      safe routeは未知のpricing error検知を保証しない。raw誤差と検出不能な悪化を残す。
- [x] 512train/128validation、70% ATM/30% log-moneyness[-.05,.05]、balanced regimes、
      train-only normalization、512updates/batch128/Adam.003、fit cap120秒を候補にする。
      同updatesがprimary比較。capで未完は失敗として保持し、unequal-updatesをpaired成功扱いしない。
- [x] main test候補は8時刻[1,5,15,30,60,120,240,390]×
      (17 ATM distances[-4,4]sqrtW＋fixed x=[-.05,-.025,.025,.05])×2＝336slots。
      重複endpointもID/weightを固定。seed/test/checkpoint選択に使わない。
- [x] baselineは独立count-mixture、density（精度参照）、既存Merton価格、
      **C² quintic Hermite**（C/C_x/C_xxをnodeで一致、Gammaも同じ価格の微分）。
      C_x=SDelta、C_xx=S²Gamma+SDelta。SciPy BPoly.from_derivativesを使える。
      cubic HermiteのC¹ nodeで通常Gammaが一意でない問題を避ける。
      spot65/time33相当とclock/pulse breakを候補とし、採用gridはpilotで固定。
      baselineのGamma oracle/offline費用・同一精度達成も報告。
- [x] 全financial codeのfixture GREEN/ruff→Task2full pilot/freeze→固定main教師・6 fits。
      training teacherが固定precision/rare gateを満たさない場合も元のslotとreasonを残し、黙って置換しない。
- [x] price/Delta/GammaのRMSE/p99/max、time/ATM/event buckets、教師SE、
      raw/safe/OOD/失敗元分母、paired全3seedsを保存checkerで再計算。

### Task4: saved artifact-only notebook

Files: short_maturity/build_notebook.py、
johnhull/hullkit/tests/test_short_maturity_notebook.py。
後でshort_maturity_dml.ipynbを生成。

- [x] RED:toy JSON/NPZのschema読取、optimizer/RNG禁止、expiry unknown/failed slots保持、3PNG。
- [x] 数値計算を保存checker/analyticsに限定。deterministic cell IDs、nbplot.setup。
- [x] 図1=teacher誤差/SE/rare counts、図2=price/Delta/Gamma＋expiry/失敗、
      図3=強いbaseline対main/cold費用・回収・採否。単位と元分母を表に残す。
- [x] 実mainをguarded kernelで実行、3PNG目視。glyph/legend/zero/unknownを確認。
      教材表示成功、数値研究受入、標準器採用は別status。

### Task5: 費用 / 独立review / 受入後main

Files: short_maturityのREADME/REVIEW/費用receipts/manifest、root所有docs/ROADMAP/INDEX。
Task3で費用registryを最初から実装し、ここでは保存費用の照合と最終表示を行う。

- [x] teacher/pilot/oracle/grid/common init/train/export/load/evaluation/fallback/check/freshをunique expense_idで保存。
      nestingを二重計上しない。独立導入caseごとには共通費用を1回課金。
- [x] BLAS/Torch1thread、hardware/version、warmup1＋7reps、固定順/別seed、
      batch1/32、返却price/全Greeks/routes、whole-call時間を保存。cap/overrunも残す。
- [x] main-only、凍結研究pipelineのvalidation込みcold、カテゴリ研究費用合計、
      measured CLI wall、serialization、freshを分離。未計測はpending、測定0にしない。
- [x] teacher成立、Delta改善、Gamma利用、標準高速器採用を別decision。
      NN候補accuracyはprice abs.01、Delta abs.005、
      K Gamma abs.05＋relative.05（未承認）。全seeds/bucketsの劣化も表示する。
      回収Q=(NNoffline−baselineoffline)/(baselineonline−NNonline)、分母<=0は回収不能。
      baselineも同じ要求Greeks/precisionを達成しているcaseだけで速度採否。
- [x] 原始配列/重み/route/全費用の独立review→全関連3suite7998 PASS/6 skip、19Pythonruff/format→tracked release/CAS gate。
- [ ] 受入後main統合/pushとmainの復元・saved数値/release。正式docs/ROADMAP/INDEX更新を同じcommitで記録。

## 5. 一次資料・公式情報の再確認（2026-10-09）

- [Merton original working paper, MIT repository](https://dspace.mit.edu/entities/publication/e63635d9-d2bf-40ce-a79b-67786dd9f105):
  MITの1975 WP787-75記録をweb確認。downloadは405で本文取得できず、PDF本文を読んだとはしない。
  JFE1976の原著DOIは[10.1016/0304-405X(76)90022-2](https://doi.org/10.1016/0304-405X(76)90022-2)。
  上のclock/pulse・tail boundsは本計画の独立導出で、原著の同一実験再現とはしない。
- [Broadie–Glasserman 1996, author PDF](https://www.columbia.edu/~mnb2/broadie/Assets/bg_ms_1996.pdf):
  著者サイトのPDF存在をweb確認。local原典processedのAppendix A/C、
  European LR Delta/Gamma(37)/(39)と交換条件を再読。本modelへの条件付き拡張は独立導出。
- [Glasserman–Karmarkar v2](https://arxiv.org/html/2512.05301v2):
  call PWとdigital PW、DMLの微分ラベル/NN微分、Gamma hybridの論点をweb再確認。
  local記録済みGBM drift/density表記の不整合へは標準密度を独立導出して対応し、著者codeの誤りとは判断しない。
- [Sakuma v5 metadata](https://arxiv.org/abs/2603.07600v5),
  [primary HTML](https://arxiv.org/html/2603.07600v5):
  v5 revised13Jul2026、Bates補償/PIDE/10入力/Greek supervisionを確認。
  web HTMLの表示日Aug24とlocal PDF本文日Jul14は異なるため、日付だけで版の変更と断定しない。
  localprocessed原典・versionをpinする。本v1は合成Merton限定の提案で、著者のBates/PIDE/hedge性能を再現したものではない。
- [NYSE hours/calendar](https://www.nyse.com/trade/hours-calendars):
  09:30–16:00 core sessionを公式確認。252正規化/U weights/pulse数値は本研究の選択であり公式規則ではない。
- [Cboe SPX specifications](https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications):
  公式ページには通常SPXW expiry16:00/half-day13:00及び一般regular hours16:15との区別がある。
  v1は合成契約。実SPX/SPXW/holiday/AM-PM/early-close再現へ拡張する場合は別契約・公式calendar・settlementを検証する。
- [SciPy BPoly.from_derivatives](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.BPoly.from_derivatives.html):
  node values/derivativesを指定するpiecewise polynomialを公式確認。C² quintic化とphysical Gamma chain ruleは本計画の設計判断。

## 6. 終了基準 / 未実装として残す範囲

v1終了=正しい合成short教師、paired6 fits/未成功理由、独立price/Delta/Gamma照合、
strong baseline/全費用/採否、保存checker/実3図/独立reviewが揃うこと。
NNが標準器に負ける結果も研究成果として受け入れる。採用を目的化しない。

Full Bates/Heston/rough、PIDE/jump-operator NN、Gamma loss、vega/quote Greeks、較正、動的ヘッジ、
実市場/dealer causality、単一の原子的scheduled jump、実商品calendarは後続。
本計画作成時はMC/training未実施。各taskの結果を実測と独立検算から更新する。
採用前にrootがcontract/precision/rare閾値/NN/grid/capsを確定し、選択済みNはfull pilot後に記入する。

## root確定のinterfaces・実行

正式spec §12にあるClockState/CallParameters、clock_state、conditional_values、path_values、mixture_values、compact_teacher/compact_momentsをTask1へ渡す。Task3はraw [S,seconds,event]からlog featuresを作り、train/predict/export_fit/numpy_predictを実装する。独立レビューが指摘したintrinsic＋smooth residualのATM kinkは避け、linear total priceを使う。Gammaはlog-feature chainを含め、TorchとNumPy・spot差分で検査する。

実行は既存research worktreeのcodex/rbf05-short-maturity。共有Python /home/kazumasa/projects/.venv/bin/python、uvはrepo rootのみ。scoped pytestは変更taskだけ、全johnhull+report+deep_hedge_price suiteは最終gateで1回。source freeze後に金融コードを変更する場合は元pilot/主成果を不変保持し、revision/pilot/freezeからやり直す。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python -m pytest -q johnhull/hullkit/tests/test_short_maturity_teachers.py
/home/kazumasa/projects/.venv/bin/ruff check johnhull/hullkit/src/hullkit/_short_maturity_teachers.py
```

Task1の最小RED例：
```python
assert core.conditional_values(100,100,clock,model,np.array([0]),np.array([0.]))[0,2] == pytest.approx(reference_gamma,abs=1e-10)
assert core.mixture_values(100,100,clock,model,nmax=8)["values"][0] == pytest.approx(independent_quad_price,abs=1e-10)
```

Task3の最小RED例：
```python
export=learner.export_fit(fit)
assert np.allclose(learner.numpy_predict(export["weights"],export["normalization"],inputs),learner.predict(fit,inputs),atol=1e-10,rtol=1e-10)
```

これらは型/chain/数式の検査であり、mainの精度・速度・採否を先取りしない。

### N候補の事前補足

独立centered second-moment積分（42event条件）で最大価格教師分散1.17279024246、N2^18でSE.0021151、2^20で.0010576。SE≤.002を維持し、main/本pilot観測前に2^20を候補へ追加した。正式pilotの観測SE・3stream・Delta/Gamma・rare gateは別途必要。[記録](../../../research/RB-F05/short_maturity/PRICE_VARIANCE_PROBE.md)。count RNGだけの計時を教師全費用と扱わない。

## 実装状態（2026-10-09、基礎checkpoint）

Task1教師/独立参照36+47 tests、Task2protocol10 tests、Task3learner25+補間/集計11 tests、pilot-only16条件32updates接続smokeを完了。Task2 full pilot/独立freeze、Task3 main runner/6fits、Task4教材、Task5全費用/最終受入は未完了。[基礎証拠](../../../research/RB-F05/short_maturity/FOUNDATION_VALIDATION.md)。

Ruling:時刻端点はexp(log())後の近接floatを別nodeとせず、定義値60/23400秒をunion前に確定する。同じlog値の分母ゼロを避け、契約・比較gridの意味を維持する。費用は全祖先のcharged状態を確認し、known call price lower boundはrawを保持してsafe fallbackへ渡す。

## 正式pilot前checkpoint

実装確定の金融registryは新7件＋既存zero_dte.py/alternative_models.py/bsm.pyの10件。_multilevel_mc.pyは今回呼ばない。教師・独立参照・protocol・pilot・learner・analytics・runner・教材builderは実装済み。全short対象と両package guardは1270 PASS（19.85秒）。独立runner再レビューの残lifecycleを修正し46回帰と独立11witness/実failureを確認。最終対象gate1275PASS/20.73秒、16Pythonruff/formatPASS、残Critical/Important0。fullpilot/freeze/mainは次に実施する。toy教材3PNGの実行は正式main教材の受入と区別する。

## v1最終受入（2026-10-09）

主640教師/6fit×512updates/336点、追加12条件180推定枠、全費用の定義、両保管庫、artifact-only3図を検証。最終独立208checks PASS、Critical/Important0。関連3suite7998PASS/6skip、表示文言後の対象22PASS、19Pythonruff/formatとtracked releasePASS。NNはraw/safe全fitで固定精度未達、Hermite336/336PASS。教師/教育比較保持、標準NN不採用。元acceptedFalse/pendingとQNoneを保存。未測定をゼロにせず、外部5費用IDの解消と全研究費総額を区別する。[最終受入](../../../research/RB-F05/short_maturity/validation.json)／[結果](../../../research/RB-F05/short_maturity/RESULTS.md)。
