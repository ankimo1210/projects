# RB-F05 短期・0DTE — 設計草案

2026-10-09。正式v1設計、実装へ移行。本人の研究ロードマップ完遂指示の範囲で、routine choicesを確定する。pilot由来のN・精度条件は主実験前に固定し、未実験値を達成済みと扱わない。

## 1. 推奨する最小v1

**合成cash-settled European call＋明示calendar＋決定論的variance clock＋定数拡散ボラとlognormal Poisson jumps**。

問い: 短期callの正しいspot Delta教師を使うDMLがprice-onlyを改善するか、Gammaにも通用するか、強い級数・積分・Hermite補間に教師生成込みで勝てるか。
Gammaは必須独立診断だが、Gamma loss/PIDE/較正まで同時追加しない。paired seeds11/29/47×price-only/Delta-DMLの6fitsを基本にする。

| 案 | 利点・制約 | 判断 |
|---|---|---|
| GBM short-only | expiry/singularity/SEを最小検証。digitalのT変更だけに近くjump接続が残る | 必須前段・強い対照 |
| **定数ボラ＋Poisson jumps＋calendar clock** | call教師、短期Gamma、rare jumpを独立級数で検証。安いoracleにNNが負ける結果も残せる | 推奨v1 |
| Full Bates/SV+jump＋PIDE | Euler bias、Fourier cutoff、Gamma参照、10入力NN、jump同定を同時に解く必要 | v2以降 |

v1完了はshort teacher/DML研究の完了で、RB-F05全体、Bates、rough、PIDE、dynamic hedgeの完了ではない。

## 2. 既存資産の確認結果

| 資産 | 確認した範囲 | 再利用／不足 |
|---|---|---|
| RB-F05 digital | T=.05–2年、payout1、LRM/CRN/conditioning/ramp/PW0。3seed改善、解析/Hermiteより遅い | 短期証拠ではない。call Deltaへコピーしない |
| _digital_teachers | T>0・sigma>0、digital解析Delta、IID SE、LRM二次モーメント | T=0を通さず、新call教師を別private moduleで導出 |
| RB-F05/discrete | T=.25–2、m12、Markov/PDE、6fits・32timings独立確認済み | 契約/境界/SE/費用規約を再利用。short call oracleではない |
| zero_dte.TradingSession/clock | aware NY時刻、weekday/holiday、9:30–16 synthetic session、U型clock | official SPX商品・early-close calendarではない |
| zero_dte.sv_jump_teacher | Heston full-truncation風Euler＋Poisson、call/put価格・価格SE、CRN Delta/Gamma | **Greek SE無し、bump=.001S固定、expiry0不可**。short Greek oracleに昇格しない |
| P8 R4 | 2026-10-07にnormal/count RNG分離、13起点paired payoff/SE保存 | 前提は解決済み。旧prep未解決表は歴史情報。new教師/Poisson couplingは別検証 |
| alternative_models.merton_jump_price | Hull §27.1 reweighted Poisson＋BSM価格級数 | 強い価格比較器。new independent Greek参照が必要 |
| _digital_dml | 2入力S/logT、discount×sigmoid payout1、price/Delta loss | call payout・3入力・expiry0非対応。新private learnerにする |

読んだもの: docs/prep/design/RB-F05_DESIGN.md・DISCRETE_RESEARCH.md、research/RB-F05/README.md・discrete/README.md、_digital_teachers.py・zero_dte.py・alternative_models.py、deep_hedge_price/_digital_dml.py、P8_STATUS.md、MODEL_INDEX.md §12/RB-F05。

## 3. 契約・calendar・二つの時間尺度

- Synthetic European cash call、K100、payoff=(S_expiry−K)^+、rebate0。expiry=2026-10-08 16:00 America/New_York、regular session09:30–16:00。official SPX/SPXW再現とは呼ばない。
- 主条件はholiday/early close無し。休日・週末/DST/NY↔UTC/open前/close後/post-expiryを専用fixtureで検査。異なるsessionは別契約unsupported。
- carry \(\tau_c=(t_{\rm expiry}^{UTC}-t^{UTC})/(365\cdot86400)\)。
- 主remaining trading timeは1–390分。ACT/365とtrading-yearを混ぜない。
- r=.03、q=0。discount/driftはtau_c。diffusion varianceは
  \[
  W(t)=\frac{.20^2}{252}[1-\mathrm{variance\_clock\_fraction}(t)].
  \]
  weights=(2,.5,2)、edges=(0,.15,.85,1)を保存。
- Delta/GammaはSを動かし、K、timestamp、expiry、calendar、r/q、clock、jump lawを固定。time ADをそのまま市場Thetaと呼ばない。

### Event契約

no-eventはLambda=0。eventは**15:30–16:00の合成Poisson pulse**。実ニュース・FOMC再現ではない。

- muJ=−.05、sigmaJ=.10、full-pulse nominal log-return variance=.00035。
- \(\Lambda_{\rm full}=.00035/(\mu_J^2+\sigma_J^2)=.028\)。
- Lambda(t)=.028×remaining pulse overlap seconds/1800。v1 background jumps=0。
- nominal varianceはcompound-Poisson log-return variance。countが常に1の単発eventではない。
- existing scheduled_varianceの(start,expiry]内の原子的ScheduledJumpをpulse積分へ黙って転用しない。new private契約として保存。
- pulse開始/終了の両側、settlementでLambda0を診断。calendarを変え同じTだけで混ぜない。

### Expiry

| 条件 | 価格 | 通常Delta | 通常Gamma |
|---|---|---|---|
| t<expiry,W>0 | モデル価格 | 評価する | 独立診断する |
| t=expiry,S<K | 0 | 0 | 0 |
| t=expiry,S>K | S−K | 1 | 0 |
| t=expiry,S=K | 0 | **未定義** | **通常微分は未定義／分布的寄与** |
| t>expiry | 契約終了 | invalid/post-settlement | invalid/post-settlement |

callは連続kink、digitalはpayoff jump。expiry ATMにDelta=.5を通常微分として付けない。boundary slotの元の件数/理由を保存し、ordinary-Greek評価分母から定義に従って分ける。

expiryはexact payoff route、min training T未満はanalytic/mixture fallback。raw NNとsafe routeを分離する。expiryのexact routeだけでNNの片側極限が正しいと宣言しない。

## 4. New call教師（独立導出・基礎実装済み、主実験未検証）

\[
S_T=S\exp((r-q)\tau_c-\kappa_J\Lambda-W/2+\sqrt W Z_B+J_\Sigma),
\quad \kappa_J=e^{\mu_J+\sigma_J^2/2}-1,
\]
\[
N\sim{\rm Poisson}(\Lambda),\quad J_\Sigma=N\mu_J+\sqrt N\sigma_J Z_J.
\]
N/ZB/ZJ独立、caller draws、split分離。compensator/martingaleを独立確認する。D=exp(−r tau_c)。

### Call Delta

\[
Y_C=D(S_T-K)^+,\qquad
Y_\Delta^{PW}=D(S_T/S)\mathbf1_{\{S_T>K\}}.
\]
Sがjump/vol lawへ入らずW>0で交換条件が成立する本モデルではcall PW Deltaは正しい候補。digital PW=0をcallへコピーしない。

\[
Y_\Delta^{LR}=D(S_T-K)^+\frac{Z_B}{S\sqrt W}.
\]
Brownian条件付きjoint densityのscore。digitalのsigma sqrt(T)へcarry timeを代入するだけでは異なるclockになってしまう。

### Call Gamma

Deltaのindicatorを素朴に再微分したPW Gamma0は負対照。正しい候補:
\[
Y_\Gamma^{LRPW}=D\frac{S_T}{S^2}\mathbf1_{\{S_T>K\}}
  \left(\frac{Z_B}{\sqrt W}-1\right),
\]
\[
Y_\Gamma^{LR2}=D(S_T-K)^+
  \frac{Z_B^2-Z_B\sqrt W-1}{S^2W}.
\]
LRPWはdensity微分時のS_T/Sの明示的S依存も含める。GBM解析Gamma、density積分、finite differencesと照合してから使用する。

### Brownian全体の厳密な条件付け

N/Jsumを残し、A=exp((r−q)tau_c−kappaJ Lambda+Jsum)、
d2=(log(SA/K)−W/2)/sqrtW、d1=d2+sqrtW:
\[
Y_C^{cond}=D[SA\Phi(d_1)-K\Phi(d_2)],\quad
Y_\Delta^{cond}=DA\Phi(d_1),\quad
Y_\Gamma^{cond}=\frac{DA\phi(d_1)}{S\sqrt W}.
\]
同じpayoffのBrownian randomnessを厳密に積分する。rampは別payoff。Lambda0なら全randomnessを消去するためSE0は妥当。

主price-only/DMLは同じconditioned priceラベル。DMLだけに解析値を渡して教師方式の効果と混ぜない。

## 5. 独立参照・強いbaseline

### GBM極限

Lambda0でindependent Black price/Delta/Gamma、正規density payoff積分、spot bump3幅を照合。digitalのstrike微分関係は検算だが、digital Deltaをcall Delta教師と呼ばない。
small W、ATM/tailsのCDF/call subtraction、underflowを診断。tiny priceのrelative errorだけで判定しない。

### 主oracle: unweighted Poisson-count mixture

count nで
\[
m_n=\log S+(r-q)\tau_c-\kappa_J\Lambda-W/2+n\mu_J,\quad
v_n=W+n\sigma_J^2.
\]
lognormal expectationのCDFからprice/Delta/Gammaを別計算し、Poisson(Lambda)で合成する。現行Mertonはreweighted Poisson/BSMなので、そのコードを呼ぶだけの独立参照にはしない。

- 別algorithmはconditional lognormal densityのadaptive payoff/score積分。domain/cutoff/precisionを変える。
- existing merton_jump_priceはsigma_eff=sqrt(W/tau_c)、intensity_eff=Lambda/tau_cで**価格**を照合。tau_c>0のみ。expiryに割算しない。
- GreekはCDF/densityから直接導出＋3bumpで確認。sv_jump_teacherの固定bumpをGamma oracleへ昇格しない。
- Poisson truncationは精度・count/tailと費用を保存。Lambda*=Lambda exp(muJ+sigmaJ²/2)とするとtail上界の候補は price≤S exp(−q tau_c) SF_{Lambda*}(nmax)、Delta≤exp(−q tau_c) SF、Gamma≤exp(−q tau_c) SF/[S sqrt(2πW)]。実装前に独立導出を再確認する。
- quadrature/cutoff error、MC SE、finite-h bias、NN errorは別記。6SEは不偏性の証明/全域上界/coverage保証ではない。

### 比較器

1. closed GBM/Poisson mixture（price＋Delta、Gamma別）。
2. independent density quadrature（高精度参照）。
3. regime別65spot×33log-time C² quintic Hermite、**価格と同じ補間器**のspot微分をDelta/Gammaにする。pulse時間breakをnodeへ入れ、spot方向C²のquintic、時間方向の線形blendはTheta保証と扱わない。
4. price-only NN、5. spot-Delta DML。同じarchitecture/price labels/seeds/batches/budget。

BSMだけと比べてjumpモデル誤差を計算誤差にしない。級数/HermiteよりNNが速いと仮定しない。digital/discreteの標準器不採用結果も維持する。

## 6. Scenario・noise・学習の候補

**以下は未実測の候補。pilot後main前に固定する。**

- 3features: log(S/K)、log(remaining trading seconds)、event_flag。oracleは同じcontractからtau_c/W/Lambdaを得る。
- Domain remaining1–390分。fixed main times=[1,5,15,30,60,120,240,390]分。30秒・pulse境界両側はfixed diagnostic/OOD。
- train512/validation128、70% ATM x∈[−4sqrtW,4sqrtW]、30% x∈[−.05,.05]。shortでS80–120 uniformとしほぼGamma0のglobal metricだけを良くする設計を避ける。
- independent test=8times×17scaled ATM distances＋4fixed log-moneyness tails×2regimes=336slots候補。重複やendpointも事前ID/weightを固定し、都合よく削除しない。
- split/teacher/init/diagnostic/pilot seed ledger固定、paired NN11/29/47。validationは診断、testでseed/checkpoint/設定を選ばない。train-only normalizations。
- train/validationのIID count/log-jump pairs/scenario数はfull pilotで選ぶ（候補N16384/65536/262144/1048576）、diagnostic65536/pilot別stream。
- n、nonzero counts、max count、mean/SE/M2、price–Delta–Gamma covarianceを保存する。fraction/controlにより同じnormalの比較はできるがsplit間は共有しない。
- Lambda>0でnonzero count0なら**rare-event unresolved**、SE0を「精度よい」としない。Lambda0のdeterministic SE0とは区別。main中だけNを増やしたり成功untilを試して固定Nと混ぜない。
- conditional-count stratificationは必要なら後続。重み付きvariance/独立SE/費用を再設計し、IID SEを転用しない。
- CRN h=[.02,.05,.10]×SsqrtWを診断候補。sampling SE、oracle finite-h target、true Delta/Gammaとのbiasを別記。
- fixed bump=.1やramp幅を対照に使うなら幅/(SsqrtW)を保存。shortの平滑化biasを消さない。
- new private call learner、3→32→32→1 tanh、CPU float64。digital discount×sigmoid payout1をコピーしない。call outputはtrain-only shift/scale付きunconstrained linear total price（C/K）。discounted intrinsic＋smooth residualはATMのkinkを残すため採用しない。価格clipでGreek誤差を隠さない。
- same price labels/initial weights/batch order、512updates/batch128/Adam.003、fit cap120秒を候補にする。Gamma supervisionは増やさずAD Gammaを独立診断。
- Gammaが悪ければDelta改善とGamma未支持を別判定。Gamma mask/clipで悪化slotを除去しない。
- tau0 exact payoff、minT未満mixture fallback、unsupported contract/model/calendar、raw/safe/OODを保存。NNのtau→0極限は保証しない。

## 7. Pilot・全費用・採否

### Pilotの確定事項

calendar/clock agreement、jump martingale/variance、closed/density/Merton価格一致、short ATM/tail/pulse precision、Poisson cutoff、teacher式6SE、negative controls、deterministic/rare-event SE0分類、teacherN/tolerances/loss/fit cap/OOD/benchmark境界。
training smokeが必要でもtinyのみ。本test/mainを見る前にsource/conditions/seedsを独立reviewしてfreezeする。

### 判定は別々に記録

| 判定 | 根拠 |
|---|---|
| teacher採用 | density/級数/GBM極限、SE/reference error、expiry/compensator/rare-event成立 |
| 教育DML採用 | 全paired seeds/original slotsのprice/Delta/Gamma誤差と教師SE |
| spot-Delta改善 | 全3seed、min-T/ATM/event bucketsのRMSE/p99/max、悪化cellも表示 |
| Gamma利用 | 独立oracle精度。Delta lossだけでGammaも正しいとしない |
| 標準高速器採用 | strong baselineと**同じ精度・Greek要求**で全費用回収成立 |
| 動的hedge | v1対象外。price/Delta改善からP&L改善を推定しない |

tolerancesはpilotのreference precision/noise floorから主実験前に固定。価格(currency)、Delta(currency/spot)、Gamma(currency/spot²)、dimensionless C/K・K Gammaを別列にする。3seedから統計的普遍性を主張しない。

費用はprotocol/calendar/source、pilot/reference、teacher、common init、fit/export、weights/archive load、validation、OOD/fallback、saved checker、freshを含む。入れ子setup/trainingを二重加算しない。

- main-onlyと「この凍結研究pipelineのcold」を区別。closed formula単独に数学的に必要なstartupへ共通pilotを言い換えない。
- startup/import/cold IOは計測するか**pending**。未測定を0にしない。CLI wallとカテゴリ合計を分ける。
- BLAS/Torch1thread、hardware/software、batch1/32 whole/padded calls、warmup/repetitions/order固定。返却price/Greeks/routeを保存。
- expiry ATMのordinary Greeksを要求するsafe成功速度はunsupported。invalid/unsupportedも元分母に保持。
- 共通教師の研究費用はunique IDで一意計上、各独立導入caseには1回ずつ課金。scope/methods/budgetを記録する。
- \(Q=(NNoffline-baselineoffline)/(baselineonline-NNonline)\)、分母<=0なら回収不能。seed/bucketを捨てない。p95内訳の和は総費用p95やCIではない。

## 8. 実装・成果の候補

- new private hullkit _short_maturity_teachers.py（仮名）、independent research reference_methods.py。
- new private deep_hedge_price _short_maturity_dml.py（仮名）、plain-array境界。hullkitへtorchをimportしない。
- research/RB-F05/short_maturity/にprotocol/pilot/runner/analytics、README/REVIEW、JSON+NPZ、artifact-only3fig。
- 保存: UTC/local times、contract/clock/pulse/expiry outcomes、seeds/counts、教師mean/SE/moments、reference convergence、weights、raw/safe errors/route、cost receipts。
- 図: (1)teacher bias/SEとshort×distance、(2)price/Delta/Gamma errorとexpiry/unknown、(3)strong baseline対総費用・回収・採否。
- cache checkは保存重み/原始配列/費用を再計算、freshは別費用。checkで再学習しない。
- 新production dependency/public API/__init__、本編台帳/Book/portal、既存digital/discrete成果は変更しない。

## 9. v1未実装として残す項目

Full Heston/Bates/SV、PIDE jump-operator network、10入力parameter-DML、market calibration/quote Greeks、single deterministic scheduled jump、variance jumps/rough/multifactor、Gamma loss/vega/λ学習、execution/コスト付きhedge/実市場/dealer causality。

BSM maturity-gated architectureのpayoff limitをjump OTMの短期price/Greeksへ自動転用しない。short jump tailの挙動は別理論/数値検査が必要。
既存vol22 SV+jump MCの存在はfull Bates short教師/DML完成の意味ではない。Greek SEとdiscretization referenceは未整備。

## 10. 一次資料・調査範囲

1. **Sakuma arXiv2603.07600v5**: local primary
   johnhull/references/processed/2026-sakuma-dml-0dte/paper.md。
   §2 Bates、§3–4 gatedBS/PIDE/jump同定、§5.1 Fourier1024/cutoff1000、AppendixA BS/Merton/Batesを読んだ。
   [version entry](https://arxiv.org/abs/2603.07600v5)を2026-10-09 web確認。revision13Jul2026、本文date14Julは区別する。
   著者の10入力/price-Delta-Gamma-vega/PIDE/3stage/hedge/較正は再現していない。本草案の縮小v1は提案で、論文の性能結論ではない。

2. **Broadie–Glasserman1996**: local
   johnhull/references/processed/1996-broadie-glasserman-security-price-derivatives/paper.md。
   §2、AppendixA/CのPW/LRM交換条件とsecond derivativesの不連続性を確認。new clock/pulse teacherは独立導出の候補で同一契約の原典式とはしない。

3. **Glasserman–Karmarkar v2**:
   docs/prep/sources/sources_S001-S031.md S002とRB-F05既存設計/結果の確認範囲を再読。
   既知のGBM drift/density不整合は標準密度の独立導出を使う。著者code/学習実験の誤りとは判断しない。
   [primary v2](https://arxiv.org/html/2512.05301v2)。

4. **Hull11e GE §27.1 Merton**: existing merton_jump_price/docstring、MODEL_INDEXを確認。この草案でprinted examplesを再照合していない。short clock変換を新しく検証する。

## 11. 実施順と残る判断

1. Rootが正式設計へ昇格。研究完遂指示に従い実装する。
2. Calendar/payoff fixtures→new call教師TDD→GBM/density/Gamma独立照合。
3. Poisson mixture/cutoff/pulse/rare-count/SE/strong interpolation pilot→review/freeze。
4. Fixed main教師＋6fits→保存数値check→独立精度/全費用/3図review→採否。
5. Full Bates/Γloss/PIDEは条件付きrevision。動的ヘッジは全体研究ロードマップの後続必須項目として残す。

実装前に確定するroutine choices: call NN output parameterizationとsmooth Greekの扱い、pilot由来MC N/oracle cutoff/tolerances。Gammaはv1診断のみを推奨。official market calendar/early close/settlementへ広げる場合は一次商品規約を新たに確認し、合成結果を流用しない。

**検証状態:** 一次資料・独立導出・基礎テスト・全84参照精度・pilot-only接続smokeを確認。full MC pilot・主学習・費用・採否は未完了。[基礎記録](../../../research/RB-F05/short_maturity/FOUNDATION_VALIDATION.md)。

## 12. 実装に渡す境界（root確定）

private teacherにClockState(carry_years, variance, jump_mean_count, remaining_seconds, status)、CallParameters(rate, dividend, jump_mean, jump_std)を置く。clock_state(timestamp, expiry, *, event, session, volatility, weights)はaware datetimeの同日合成契約だけを扱い、UTC carry・U-clock・pulse overlapを返す。expiry値の通常Greek未定義はNaN＋reasonで保持。

conditional_values(S,K,state,parameters,counts,z_jump)は[...,3]のC/Delta/Gamma、path_values(...,z_brown,z_jump)はprice/PW・LR Delta/LRPW・LR2 Gamma/naive Gamma、mixture_values(...,nmax=8)はvalues/tail_bounds/terms/status。独立reference_methodsはdensity_quadと既存Merton価格の別検算を提供する。

compact_teacher(...,sample_count,count_seed,jump_seed)は元count全Nを生成し、active indices/count/Z_J、zero_countとC0/D0/G0を保存する。active_only normal policyを固定する。compact_momentsでChan統合し元N・SE・3成分covを再構成する。Lambda0はanalytic_deterministic、actual random draws=0。予約sample slotsを観測MC件数と扱わない。raw estimator診断には別stream/全Brownian drawsを保存する。

learner inputsは[S,remaining_seconds,event]のplain arrays。featuresは[log(S/K),log(seconds),event]。train(inputs,prices,deltas,*,seed,batch_seed,dml,max_updates,batch_size,learning_rate,budget_s,teacher_s,strike)は同一price labels・初期/batch・update budgetで6 fits。predictは同じscalar priceのC/Delta/Gamma、export_fitはplain weights/normalization/stats、numpy_predictは保存重みで再学習なしに再評価する。physical chain ruleはDelta=C_x/S、Gamma=(C_xx-C_x)/S²。raw outputをclipしない。

主比較前に全financial source（新規7件＋呼ぶ既存3件）・seeds・pilot・precision/rare閾値をfreezeする。private API追加は公開API変更ではない。本編、digital/discreteの受入・原始成果は不変。

### 事前精度設計の独立確認

price SE≤.002には候補N2^18が不足する条件を独立second-moment積分で確認した（最大分散1.17279024246）。N候補2^20を主実験前に追加する。これは本pilot/mainの結果ではなく、正式pilotの全stream/SE/rare-count検証を代替しない。
