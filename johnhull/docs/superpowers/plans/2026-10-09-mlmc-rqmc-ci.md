# RB-F08 MLMC・RQMC CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. この計画作成ターンでは実装・実験・commit・pushを行わない。

**Goal:** GBM Euler欧州callについて粗細結合、biasとsamplingの分離、固定pilotによる配分、総費用を検証し、別系列の独立scramble RQMCについてStudent型CIの被覆率を調べ、4図・独立レビュー・採否を保存する。

**Architecture:** hullkitの新しいprivateモジュールを純粋な乱数再生・統計に限定し、`research/RB-F08/`で乱数生成、pilot、protocol freeze、主反復、費用会計、独立参照、保存checker、artifact-only教材を配線する。GBM Euler MLMCを主研究にし、厳密GBM終端法とBSMは強い比較器と真値診断に使う。MLMCとRQMCを合成しない。

**Tech Stack:** 既存NumPy/SciPy、Python >=3.12、CPU、torch-free。確認した共通環境はNumPy 2.4.6 / SciPy 1.17.1（2026-10-09、importのみ）。

**Spec:** [RB-F08_DESIGN.md](../../prep/design/RB-F08_DESIGN.md)、[研究ロードマップ](../../../ROADMAP.md#研究ロードマップの実行2026-10-09)、[研究バックログ](2026-09-27-research-backlog.md)。

## Global Constraints

- 設計の開始条件は「RB-F04の採否記録後。P4 Ch21受入後が望ましい」。F04主比較中は計画・軽量な独立作業に留め、研究主実験を競合させない。
- 置き場は `research/RB-F08/` とhullkit非公開モジュール。NumPy/SciPy・CPU、外部データなし。
- hullkitはtorch-free。公開API・production依存・本編節台帳を変更しない。
- notebookはartifact-only実行。実験、乱数生成、ネットワーク、GPU検出をnotebook内で行わない。
- 粗い正規乱数は隣接する細乱数の和/sqrt(2)で作る。同一レベル内で粗細を結合し、レベル推定・主反復は独立streamにする。
- Eulerの負の株価が出た経路を黙って切り捨てない。刻み・係数・発生率を保存する。
- CIの標本数は点の総数でなく独立なscramble推定値の数。Student型CIは近似CIと明記する。
- 単一seedの絶対誤差をRMSEと呼ばない。秒数、step数、乱数数、hardwareを区別する。
- 巨大pathを常時保存せず、集計と再生成条件を残す。SHAは来歴・完全性の検査であり、数値主張の検証は保存された観測から再計算する。
- 数値結果・再現性の比較は許容差付き`np.testing.assert_allclose`または`pytest.approx`で固定する。入力非変更・整数件数・seed台帳などのmetadata一致はexact比較を許可する。
- Heston算術Asianは設計の次段階として残す。観測は月次12点、S0を平均へ含めない。13列（S0＋月次12点）を`arithmetic_asian_details(..., include_initial=False)`へ渡す。v1を解析GBMや時点0の計算に置換しない。
- この計画にはcommit/pushコマンドを含めない。統合・公開はrootの既存権限と指示に従う。

## Review Focus

1. レベル間で同じstreamを再利用するとvariance和の式が壊れる。Task 3でstream台帳の重複・phase交差を拒否する。
2. 有限pilotのゼロ分散、符号が変わる差分平均、非正則なweak rateを過度に信用しない。Task 3でfloor・未支持rate・階層上限と停止理由を固定する。
3. Euler負株価・非finite経路・不足試行を除去して成功扱いにしない。Task 1/4で元の分母と件数を保持し、非finiteはrun全体を失敗とする。
4. 同じ総点数でもRが違うStudent区間、全scramble同値の幅0、clip変更を識別する。Task 2/5でR-1自由度・変換真値・退化区間を検査する。
5. 保存JSONだけ改変した採否や、pilotを見ずにmainを再配分した結果を受け入れない。Task 4/6で固定roster、配分・source・review指紋、配列からの採否再計算を検査する。

---

## 0. 読んだ実装・再利用と追加差分

| 既存ファイル / 記号 | 再利用する内容 | 今回追加する内容 / 制限 |
|---|---|---|
| `hullkit._numerical_mc:gbm_paths_from_normals` | supplied normals、Q drift=r-q、exact/Euler、負株価を保持 | MLMCでは必ず`scheme="euler"`。既定exactを暗黙利用しない |
| `hullkit._stochastic_foundations:stock_paths` / `euler_stock_moments` | 株価再生・Euler積の解析的第1/第2モーメント | 粗細結合wrapperと負状態診断。独立testは自前の積・モーメント式で照合 |
| `hullkit._numerical_mc:sobol_normal_points` | Sobol `random_base2`、uniform配列・逆CDF結果 | 独立scrambleの子seed/endpoint件数を保存、Student型CI |
| `hullkit._numerical_mc:randomized_qmc_price` | `SeedSequence.spawn`、scrambleごとの`samples`、SE | 既存1.96 CIを変更せず、新private wrapperでt区間・子seed台帳を作る。既存推定値との一致test |
| 新private `hullkit._rqmc_ci:rqmc_gbm_call_from_seeds` | 既存Sobol/GBM primitiveへ確定childseedを直接渡すseam | 研究orchestratorはfrozen台帳を使用。legacy互換wrapperの内部spawnを研究mainで呼ばない |
| `hullkit.mc_advanced:plain_price` / `control_variate_price` | 厳密終端比較器・既存形式 | 公開APIは不変。q=0で照合。研究CVは別pilotでbetaを固定し、推定費用を計上する |
| `hullkit.mc_advanced:qmc_price` / `error_vs_n` | 図形式・点推定の対照 | 前者clipは1e-10、private samplerはnextafterで異なる。混同しない。単一seed曲線を研究RMSEに流用しない |
| `hullkit._numerical_mc:control_adjustment` | fixed betaのCV標本 | 独立pilot betaと主標本を分離。q≠0のcontrol期待値はS0 exp(-qT) |
| `research/RB-F05/discrete/artifacts.py` | `load_bundle(directory, stem=...)`, `store_large(directory, stem=...)`、20MB閾値・両復元 | 明示directoryとpilot/reference/diagnosticの既存stemを使用。新汎用保管基盤を作らない |
| `research/RB-F04/build_reference.py` / `build_notebook.py` | freeze/review来歴、pickleなし読込、checker、artifact-only実行の形式 | F04専用価格面・PDEはコピーしない。F08の統計と費用に必要なschemaだけ実装 |
| `hullkit._model_dynamics:aggregate_normals` / `heston_monthly` | 次段階の2factor集約・full-truncation log Euler・13観測 | F04採否後のHeston Asianで再利用。GBM 1factorへAPIを広げない |
| `test_numerical_mc_replay.py`, `test_numerical_mc_variance.py`, `test_mc_advanced.py` | 既存基線・SE統計単位の固定 | 新機能のTDDと既存基線の退行確認を分ける |

`MODEL_INDEX.md`は全privateモジュールも登録するguardがある。新モジュールは追加タスクと同時に索引へ列を追加する。既存同時変更（F04の面/動学/ROADMAP/MODEL_INDEX）を保持し、編集する箇所だけ追記する。

## 1. 固定する研究契約と数式

### 1.1 GBM Eulerの主対象

- 単位：年、株価・価格は同じcurrency、sigmaは年率、r/qは連続複利の年率。
- 主ケース：S0=100、K=100、r=.03、q=0、sigma=.20、T=1、欧州call、満期払。
- 診断ケース：同じS0/r/q/sigma/T、K=80/120。配当q=.02、sigma=0、負Euler状態は単体/独立参照testで固定する。
- ベースstep M0=4、M_l=4*2**l、h_l=T/M_l、pilot l=0…8（最大1024steps）。主実験では各epsilonごとにpilot選択済みLを使用する。

\[
S_{j+1}^{(l)}=S_j^{(l)}[1+(r-q)h_l+\sigma\sqrt{h_l}Z_{l,j}],\qquad
P_l=e^{-rT}(S_{M_l}^{(l)}-K)^+.
\]

主GBMのschemeは上の通常Euler乗算で固定する。log EulerはGBMの厳密終端と一致して時間離散化biasが消えるため、このMLMC主実験のschemeには採用しない。exact/log経路は比較器とpaired bias診断に限定する。

\[
Z_{l-1,j}=(Z_{l,2j}+Z_{l,2j+1})/\sqrt2,
\quad Y_0=P_0,\quad Y_l=P_l-P_{l-1},
\quad \widehat P_L=\sum_{l=0}^L\bar Y_l.
\]

レベルごとに独立なN_l試行を使う。SEの標本数は粗細pair数であり、payoff評価数2N_lではない。

\[
\widehat v=\sum_l s_l^2/N_l,\qquad
\operatorname{MSE}(\widehat P_L)=\operatorname{Var}(\widehat P_L)+[E(P_L)-P_*]^2.
\]

誤差目標epsilon=[.40,.20,.10] currency。sampling予算v_target=epsilon**2/2、bias目安b_target=epsilon/sqrt(2)。pilotのV_lと1pair費用C_lから

\[
N_l=\max\left(32,\left\lceil {\sqrt{V_l/C_l}\sum_j\sqrt{V_jC_j}\over v_{target}}\right\rceil\right).
\]

分散floor=1e-12 currency²をpilot推定に適用し、その使用レベルを保存する。N_lは整数ceil、主実験では再計算・追加samplingしない。C_lはisolated計測のmedian秒/試行、step数proxyによる別配分も診断用に保存するが主配分を後で選び直さない。最適配分と独立レベルの前提、条件付き計算量の根拠は[Giles (2008), §2–3](https://people.maths.ox.ac.uk/gilesm/files/OPRE_2008.pdf)。Euler Lipschitzの場合の理論率は条件付き説明に留め、実測率が不安定なら今回の達成率として宣言しない。

### 1.2 biasの停止規約と真値診断

固定pilotに全候補レベルを走らせる。Euler fineと同じBrownian終端を使ったexact payoffとの差D_l=P_l-P_exactを別に保持する。exactがEuler MLMCの推定量へ混入することはない。

- 各level、3独立pilot stream×16384 pathsをpool。D_lのmean/SEと両側99% t半幅を保存する。
- 候補Lは2…8から最小を選び、`B_L=abs(mean(D_L))+t_.995,df * SE(D_L) <= epsilon/sqrt(2)`を要求する。これは有限pilotからの経験的bias上限であり、保証付き停止定理と呼ばない。
- D_lはEulerとexactのpaired差。Euler価格の単独SEをbiasSEに代用しない。
- 併せて差分平均・分散の隣接log2傾きalpha/betaを保存する。alphaはabs(mean(Y_l))>3SEを満たす連続3レベルでのみ計算し、満たさなければ`unresolved`。符号反転も保存する。pilotによるratefitが未支持でも直接bias診断に基づく経験的選択は可能と明記する。
- LまでのEuler負状態の観測率が1e-5を超えればその候補は`coarse_grid_invalid`。試行分母・状態分母とexact比較を保存し、経路は除去しない。閾値は「確率の厳密上限」ではない。
- 全候補不合格なら当該epsilonを`bias_unresolved`として保存し、主実験を勝手に易しい商品へ切り替えない。追加pilotが必要なら別protocol revisionとしてレビューする。
- candidate capはN_l総数2,000,000/run、step総数100,000,000/run。主比較前のpilot reviewで候補capの予算妥当性と有効cellを判断し、採用するcap・全cell状態をfreezeする。frozen capを超える候補は`budget_failure`として保存する。他の有効cellと失敗cellを教材へ表示する。main観測後にcapを変更して不利なcellを除去したり、試行数を短縮したりしない。

主実験のsampling CIはE(P_L)を対象にする。BSMへ対するその経験的被覆率はbias込みの診断であり、E(P_L)自体の被覆率を測ったとは主張しない。MLMCはa_l=s_l²/N_lとしてSatterthwaite自由度

\[
\nu=(\sum a_l)^2/\sum[a_l^2/(N_l-1)]
\]

を使う近似t区間を記録し、a_lが全0ならwidth=0、df=null、`degenerate=true`とする。加えて固定pilot B_Lを両端へ加えたbias-aware区間を別列に置く。sampling CIだけのBSM被覆率をbias保証と呼ばない。

### 1.3 別系列RQMCのCI・被覆率

GBM厳密終端の1D積分で独立scrambleをR組作り、各組2**m点。主rosterはK=[80,100,120]、m=[8,10]、R=[8,16,32]、outer反復B=512。各outer反復でR個の別scrambleを生成する。

\[
Q_r={1\over2^m}\sum_i g(U_{r,i}),\quad
\widehat P={1\over R}\sum_r Q_r,\quad
SE=s_Q/\sqrt R,\quad CI=\widehat P\pm t_{.975,R-1}SE.
\]

- 使用するclipは既存private samplerの`[np.nextafter(0.,1.), np.nextafter(1.,0.)]`。値、float.hex、endpoint/clip件数、SciPy版、scramble seedを保存する。
- `.qmc.Sobol(..., scramble=True, seed=int_seed).random_base2(m)`を使い、point0を落とさず、thin/任意点数を使わない。SciPy実装のLMS+shiftをOwenの全nested scrambleと同一と呼ばない。[SciPy Sobol公式仕様](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html)。
- t区間はscramble推定値の有限R分布について一般に厳密ではない。[Jain et al. arXiv v2, §1–2, §5](https://arxiv.org/html/2504.18677v2)の有界integrand向けEBCI/HBCI保証を非有界callへ移さない。EBCI/HBCIの実装はこのv1に含めない。
- 解析BSM真値と、clipされた積分の独立参照P_clipを両方保存する。被覆率は両対象に対し別に計算する。1e-10の公開qmc clipとの差はpilot診断で固定seed比較し、主clipを結果を見て変更しない。
- hits/B、平均幅、median/p95幅、bias、RMSE、degenerate数を保存。hitsの不確実性は二項Wilson 95%区間（Task 5の自前式）を使う。
- 被覆率の良さでm/Rを主データから選ばない。全18cellを保持。512反復では95%付近のSEは約.0096なので、1–2 percentage pointの差を断言しない。

### 1.4 費用・反復・stream・採否

- Euler MLMC/同じLのplain Euler/exact terminal plain/exact terminal fixed-pilot CVの主反復はB=256、epsilonごとに別run stream。plain EulerのNはpilotのVar(P_L)からceil(V/v_target)、exact比較も同じsampling予算でNを固定する。
- CV betaは独立pilotからCov(P,C)/Var(C)。C=e^-rT S_T、E(C)=S0e^-qT。Var(C)=0ならbeta=0として記録し、main標本でbetaをfitしない。
- Phase roots：pilot=83101、main=83201、coverage=83301、fresh_review=83401、timing=83501、method_order=83601、bootstrap=83701。root→固定case roster→budget→run→method→level→scrambleのSeedSequenceをlogical childとし、候補roster生成時に全phaseの物理seedを一意に確定する。RQMC主rosterだけで172,032子scrambleがあり、32bit出力の衝突を単に失敗とする規約は採用しない。
- 衝突解決の順序は上のphase順→case/budget/run/method/level/scrambleの固定ordinal順。logical childにcandidate ordinal k=0,1,…を付けた次child（`spawn_key=logical_spawn_key+(k,)`）からuint32を生成する。すでに台帳にあるseedならそのlogical childのkを増やす。最初の候補`raw_seed`、採用した`seed`、全`candidate_seeds`、`retry_count`、`entropy`、`logical_spawn_key`、採用候補の実`spawn_key`を保存する。衝突解決は候補台帳生成時だけ行い、価格・CI・計時を参照しない。
- pilot開始前にpilot用台帳を確定する。全main/coverage/fresh/timing/method_order/bootstrap台帳は主観測を見る前にfreezeする。主実験はfrozen台帳だけを読み、衝突解決・seed再生成・失敗run補充による台帳書換えを禁止する。case/roster変更は主比較前のprotocol revisionと再レビューで扱い、既に走らせたpilotの台帳と観測の対応を保持する。全level0…8の候補main slotを予約し、pilotで選ばなかったslotも未使用と明示する。
- 一意なuint32 seed台帳は同じ初期化の偶発的再使用を防ぐ契約であり、PRNGやscrambleの真の独立性の数学的証明ではない。独立randomizationの仮定、SeedSequence/SciPyの生成方式、再現性を記録する。
- block_size=2048、single process、OMP/OPENBLAS/MKL threads=1。main methodの順序はmethod_order phaseの確定seedを使うbalanced置換表として保存する。wall timeはRNG+path+payoff+集計を含み、importは別setup欄。
- timerはfloat秒、cost-counterは整数。level0はM0*N株価update、M0*N normal、N payoff。level>0は(M_l+M_l/2)*N update、M_l*N normal、2N payoff、M_l/2*N coarse aggregation。fineとcoarseが同じnormalから派生しても乱数数を2倍にしない。
- 保存費用はpilot秒、timing calibration秒、epsilon/method別の配分計算`allocation_s`、freeze検証`freeze_validation_s`、main RNG/engine/summary合計、serialization秒、fresh review秒を分ける。allocation timerはL選択・Nの整数丸め・cap検査を含む。online mainのみ、cold=必要pilot+calibration+allocation+freeze+one main、amortized=offline/K+one main(K=1/10/100)を併記する。
- 費用台帳の各項目にunique expense_idと必要method/epsilonを付ける。Euler MLMC/同L plainのcold比較には全候補levelを調べたbias pilotと配分費用を含め、採用Lのprefixだけへ後から削らない。exact plain/CVには各々の必要pilot/beta推定/配分費用を対応させ、Euler専用pilotを必須費用として押し付けない。method単独cold図では必要な共有費用を各々含めるが、研究総費用はunique expense_idの和で一度だけ数える。共有pilotを256runや3epsilonへ無条件に重複計上しない。
- 費用改善の判断は同じepsilon、同じ価格/格子、RMSEを満たすか、実測secondsとstepを別に見る。RNG数一致だけで同費用としない。
- `teaching_retained`は有効なcoupling、全roster/失敗理由、再検算、4図、独立レビューが揃えば可能。`speedup_supported_vs_euler`はGBM Euler比較で3epsilon中2つ以上に実測RMSE<=epsilon、main費用ratio median<1、paired ratioのrun bootstrap 95%上端<1を要求する。bootstrapは主点推定を変更せず、bootstrap phaseの確定seed、2000 resamplesで固定する。cold費用で不利ならそのまま別表示する。
- exact terminal比較に勝つことは完了条件にしない。`standard_accelerator_rejected`はexact法に劣る場合、pilotが重い場合、差分分散が減らない場合、または誤差予算を満たせない場合に理由付きで保存する。公開API昇格は別判断。

### 1.5 全主条件のfreeze

epsilon/case/product、scheme・M0/候補level/観測規約、pilotのstream数とpaths、全cap、minimum/floor、bias/negative閾値、Euler主反復256、RQMC coverage512・K/m/Rの全18cell、CI level・clip、block/thread、timing warmup/反復数、CV beta、L/N、bootstrap2000、採否基準、最終seed台帳とsource/dependency/review指紋を全て主比較前にfreezeする。本計画の全数字は主比較前のpilot reviewで採用する候補であり、主観測に合わせて動かす調整値ではない。変更が必要ならmain開始前にprotocol revisionを作り、変更理由・pilot影響・新台帳をレビューする。pilotそのものの入力を変更した場合は当該pilotを再実行する。

## 2. ファイル境界

| Create / Modify | 責任 |
|---|---|
| Create `johnhull/hullkit/src/hullkit/_multilevel_mc.py` | GBM supplied-normal粗細pair、stable moments、MLMC統計、整数配分。乱数・I/Oなし |
| Create `johnhull/hullkit/src/hullkit/_rqmc_ci.py` | supplied scramble推定値のStudent CI、既存Sobol primitiveを使うseed記録wrapper |
| Create `johnhull/research/RB-F08/reference_methods.py` | hullkitをimportしない独立BSM、one-step Euler call、clip積分、scalar Euler replay |
| Create `johnhull/research/RB-F08/protocol.py`, `protocol.json` | schema、固定roster・stream、fingerprint、candidate→frozenのvalidator |
| Create `johnhull/research/RB-F08/pilot.py` | fixed pilot、cost calibration、bias/variance/negative診断、CV beta、候補配分 |
| Create `johnhull/research/RB-F08/analytics.py` | RMSE/bias/CI被覆率/Wilson/費用会計/採否再計算 |
| Create `johnhull/research/RB-F08/build_reference.py` | frozen主実験、compact配列、save/load/check/fresh配線 |
| Create `johnhull/research/RB-F08/build_notebook.py`, `mlmc_rqmc_ci.ipynb` | 保存結果のみを使う4図・表・限界 |
| Create `johnhull/research/RB-F08/README.md`, `PILOT_REVIEW.md`, `REVIEW.md` | protocol・status・独立レビュー・採否の正本 |
| Create `johnhull/hullkit/tests/test_multilevel_mc.py`, `test_rqmc_ci.py`, `test_mlmc_rqmc_reference.py`, `test_mlmc_rqmc_protocol.py`, `test_mlmc_rqmc_pilot.py`, `test_mlmc_rqmc_research.py`, `test_mlmc_rqmc_notebook.py` | 純粋契約、独立参照、freeze/改変/費用、artifact-only試験 |
| Modify `johnhull/MODEL_INDEX.md`, `johnhull/ROADMAP.md` | 新private部品の登録、F08の着手→pilot→main→レビュー→採否の実測状態だけ更新 |

## Task 1: supplied BrownianによるGBM Euler粗細pairとMLMC統計

**Files:** Create `_multilevel_mc.py`、`test_multilevel_mc.py`。Modify `MODEL_INDEX.md`のprivate表。

**Interfaces:**

```python
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class GBMCall:
    spot: float
    strike: float
    rate: float
    sigma: float
    maturity: float
    yield_rate: float = 0.0

def coarse_normals(fine: np.ndarray) -> np.ndarray: ...
def gbm_level_samples(contract: GBMCall, normals: np.ndarray, *, level: int,
                      base_steps: int = 4) -> dict: ...
def block_moments(samples: np.ndarray) -> dict: ...
def merge_moments(blocks: list[dict]) -> dict: ...
def mlmc_summary(levels: list[dict], *, confidence: float = .95) -> dict: ...
def allocate_paths(variances: np.ndarray, costs: np.ndarray, *,
                   sampling_variance: float, minimum: int = 32,
                   variance_floor: float = 1e-12) -> np.ndarray: ...
```

`GBMCall`はfinite S0/K/T>0、sigma>=0、finite r/qを要求。levelはboolでない非負int、base_stepsは正int。`normals.shape=(N,base_steps*2**level)`、N>=2、finiteを要求。入力配列は変更しない。

`gbm_level_samples`は`fine_payoffs`, `coarse_payoffs`（level0はNone）, `differences`, `paired_exact_bias`, `fine_negative_states`, `coarse_negative_states`, `negative_paths`, `cost_counts`を返す。negative_statesは各株価update後、negative_pathsは粗細のどちらかで負だった元のpath数。nonfinite結果は例外としてrunを失敗にし、pathをfilterしない。

各moments dictは`count, mean, m2`（m2=sum((x-mean)**2)）を持つ。mergeはdelta=mean_b-mean_a、M2=M2a+M2b+delta² n_a n_b/(n_a+n_b)を使用。summaryは`price, variance, standard_error, confidence_level, interval, df, degenerate, level_counts`。

- [x] **Step 1: 以下のRED testを保存する。**

```python
def test_pair_uses_sum_of_fine_brownian_and_euler_not_exact():
    from hullkit import _multilevel_mc as m
    c = m.GBMCall(100, 100, .03, .2, 1, .01)
    z = np.array([[.3, -.2], [-3., 1.], [.4, .1]])
    result = m.gbm_level_samples(c, z, level=1, base_steps=1)
    zc = z.sum(axis=1) / np.sqrt(2)
    fine = 100*np.prod(1+.02/2+.2*np.sqrt(.5)*z, axis=1)
    coarse = 100*(1+.02+.2*zc)
    expected = np.exp(-.03)*(np.maximum(fine-100, 0)-np.maximum(coarse-100, 0))
    np.testing.assert_allclose(result["differences"], expected, rtol=0, atol=1e-12)
    np.testing.assert_allclose(m.coarse_normals(z), zc[:, None], rtol=0, atol=1e-12)
    np.testing.assert_array_equal(z, [[.3, -.2], [-3., 1.], [.4, .1]])

def test_negative_euler_path_retained_in_original_denominator():
    from hullkit import _multilevel_mc as m
    c = m.GBMCall(100, 100, 0, 1, 1)
    result = m.gbm_level_samples(c, np.array([[-4.], [0.], [2.]]),
                                 level=0, base_steps=1)
    np.testing.assert_allclose(result["differences"], [0, 0, 200], rtol=0, atol=1e-12)
    assert result["negative_paths"] == 1
    assert m.block_moments(result["differences"])["count"] == 3

def test_mlmc_variance_uses_independent_level_sample_counts():
    from hullkit import _multilevel_mc as m
    levels = [m.block_moments(np.array([1., 2., 3., 4.])),
              m.block_moments(np.array([-.1, .1, -.2, .2]))]
    out = m.mlmc_summary(levels)
    expected = (5/3)/4 + (.1/3)/4
    assert out["price"] == pytest.approx(2.5)
    assert out["variance"] == pytest.approx(expected)
    assert out["level_counts"] == [4, 4]
```

- [x] **Step 2: 未存在moduleによるREDを確認する。** Run `... pytest -q johnhull/hullkit/tests/test_multilevel_mc.py`。数値違いでREDになったら期待式を独立に確認する。
- [x] **Step 3: 最小実装を加える。** coarse=`z.reshape(N,M//2,2).sum(axis=2)/sqrt(2)`。fine/coarseは既存`gbm_paths_from_normals(..., scheme="euler")`、exact biasはfineのnormal和/sqrt(M)で1step exactを再生。負状態はpayoffの前に数える。配分は§1.1の式を直接実装する。
- [x] **Step 4: invalid shape/奇数step/NaN/overflow/level0/sigma0、stable merge、整数ceil/floorを追加してGREEN。** 配分fixture V=[4,1], C=[1,4], v_target=.5, minimum=2, floor=0ではN=[16,4]、sum(V/N)=.5。全V=0は全minimumで`floor_used`を保存する。
- [x] **Step 5: 索引登録と対象ruff。** Euler粗細と独立level統計を索引の検証列に記載。新private部品をfresh subprocessでimportし、`assert "torch" not in sys.modules`を固定する。全追加関数/classのdocstringを記す。失敗を既存F04の同時変更へ帰属させず、必要な基線を比較する。

## Task 2: 独立scramble Student型CIとseed/clip記録

**Files:** Create `_rqmc_ci.py`、`test_rqmc_ci.py`。Modify `MODEL_INDEX.md`のprivate表。

**Interfaces:**

```python
def student_summary(estimates: np.ndarray, *, confidence: float = .95) -> dict: ...
def rqmc_gbm_call(contract: GBMCall, *, power: int, scrambles: int, seed: int) -> dict: ...
def rqmc_gbm_call_from_seeds(contract: GBMCall, *, power: int,
                             child_seeds: list[int],
                             child_metadata: list[dict] | None = None) -> dict: ...
```

`student_summary`はfinite1D、R>=2、0<confidence<1を要求。返り値`price, estimates, scrambles, standard_error, df, confidence_level, interval, width, degenerate, approximate=True`。wrapperは`child_seeds`, `child_spawn_keys`, `points_per_scramble`, `payoff_evaluations`, `uniform_clip`, `clipped_points`, `normal_dimensions=1`も返す。

`rqmc_gbm_call_from_seeds`はR=len(child_seeds)とし、重複のない確定uint32列と対応metadataをそのまま消費する。内部でspawn/retryを行わない。metadataがある場合は同じRで`seed`がchild_seedsに一致することを検証し、raw_seed/retry_count/実spawn_keyを結果へ保存する。legacy`rqmc_gbm_call`は従来の`SeedSequence(seed).spawn(R)`列をseamへ渡して互換testを維持する。研究mainはfrom_seedsだけを使う。

- [x] **Step 1: RED test。**

```python
def test_t_interval_uses_scrambles_not_raw_sobol_points():
    from hullkit import _rqmc_ci as r
    from scipy.stats import t
    q = np.array([8., 10., 12., 14.])
    out = r.student_summary(q)
    se = np.std(q, ddof=1)/2
    assert out["df"] == 3
    assert out["standard_error"] == pytest.approx(se)
    assert out["interval"] == pytest.approx([11-t.ppf(.975, 3)*se,
                                             11+t.ppf(.975, 3)*se])
    assert out["approximate"] is True

def test_existing_private_rqmc_estimates_are_preserved():
    from hullkit import _rqmc_ci as r, _numerical_mc as old
    from hullkit._multilevel_mc import GBMCall
    c = GBMCall(50, 50, .05, .3, .5)
    out = r.rqmc_gbm_call(c, power=4, scrambles=4, seed=21708)
    existing = old.randomized_qmc_price(50, 50, .05, .3, .5,
                                        power=4, scrambles=4, seed=21708)
    np.testing.assert_allclose(out["estimates"], existing["samples"], atol=1e-12, rtol=0)
    expected = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(21708).spawn(4)]
    assert out["child_seeds"] == expected
    assert len(set(expected)) == 4

def test_research_primitive_consumes_frozen_child_seeds_without_respawning():
    from hullkit import _rqmc_ci as r, _numerical_mc as numerical
    from hullkit._multilevel_mc import GBMCall
    c = GBMCall(50, 50, .05, .3, .5)
    seeds = [41, 43, 47, 53]
    out = r.rqmc_gbm_call_from_seeds(c, power=4, child_seeds=seeds)
    manual = []
    for seed in seeds:
        z = numerical.sobol_normal_points(4, scramble=True, seed=seed)["normals"]
        terminal = numerical.gbm_paths_from_normals(50, .05, .3, .5, z,
                                                    scheme="exact")[:, -1]
        manual.append(np.exp(-.05*.5)*np.maximum(terminal-50, 0).mean())
    np.testing.assert_allclose(out["estimates"], manual, rtol=0, atol=1e-12)
    assert out["child_seeds"] == seeds
```

- [x] **Step 2: 対象testのREDを確認。** 小さい2**4点×4scrambleのみ。
- [x] **Step 3: 確定childseed seamを実装し、legacy wrapperは`SeedSequence(seed).spawn(R)`をseamへ渡す。** 各childseedで既存`numerical.sobol_normal_points`を再生する。子seed、uniform0/1と逆CDFclip件数を保存する。CIは`scipy.stats.t.ppf`で計算する。[t公式仕様](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html)。公開`qmc_price`や既存normal CIを変更しない。
- [x] **Step 4: R=1/非integer/bool/非finite、全estimate同値、replay、別seedをGREEN。** 全0ではwidth0・degenerate=trueを保ち、被覆保証を付けない。powerはboolでない0…20のint、seedはboolでない0…2**32-1のint、scramblesは2…1024のintとする。
- [x] **Step 5: 索引登録・対象ruff・既存`test_randomized_qmc_se_from_independent_scrambles`を実行。**

## Task 3: 独立参照・固定protocol・stream台帳

**Files:** Create `reference_methods.py`, `protocol.py`, `protocol.json`, `test_mlmc_rqmc_reference.py`, `test_mlmc_rqmc_protocol.py`。

**Interfaces:**

```python
# reference_methods.py: hullkitをimportしない
def black_call(parameters: dict) -> float: ...
def one_step_euler_call(parameters: dict) -> float: ...
def scalar_euler_payoffs(parameters: dict, normals: np.ndarray) -> np.ndarray: ...
def clipped_black_call(parameters: dict, clip: tuple[float, float]) -> float: ...
# protocol.py
def candidate_protocol() -> dict: ...
def validate_protocol(p: dict, *, require_frozen: bool = False) -> None: ...
def _candidate_seed(logical_row: dict, retry: int) -> int: ...
def resolve_seed_roster(logical_rows: list[dict], *,
                        candidate_seed_fn=_candidate_seed) -> list[dict]: ...
def build_seed_ledger(p: dict) -> list[dict]: ...
def seed_roster(p: dict, phase: str) -> list[dict]: ...
def source_fingerprint(paths: list[Path]) -> dict: ...
def freeze_protocol(candidate: dict, pilot_record: dict, pilot_arrays: dict,
                    review: dict, *, source: dict) -> dict: ...
```

protocol schema=`RB-F08-mlmc-rqmc-v1`, state=`candidate|frozen`, §1の全候補・root・予算・roster・CI/clip/費用規約を保存。freezeにpilot JSON/NPZ、独立review、対象source、dependency versionのSHAを含め、main codeで同一性を確認する。対象sourceは新private2本、既存_numerical_mc/_stochastic_foundations/bsm、F08 reference_methods/protocol/pilot/analytics/build_referenceの固定リストとする。§1.5の全条件・最終seed台帳を含むfrozen objectをdeepcopyし、mutation後はdigest不一致を拒否する。

`build_seed_ledger`は固定全phase/全候補slotのlogical_rowsを作り、一度`resolve_seed_roster`へ渡す。各rowは`logical_id, phase, entropy, logical_spawn_key`とcase/budget/run/method/level/scramble ordinalを持つ。`_candidate_seed(row,k)`は`np.random.SeedSequence(row["entropy"], spawn_key=tuple(row["logical_spawn_key"])+(k,)).generate_state(1)[0]`をintへ変換する。resolutionは固定順序のused-seed setに対してkを増やし、重複logical_idまたは同じentropy/logical_spawn_keyは拒否する。`seed_roster`は保存されたp["seed_ledger"]をphaseでfilterする読取関数とし、再resolutionしない。final ledgerの全uint32一意性、172,032 coverage slot、全候補levelのmain予約、raw/retry/実spawn_keyの一致をfreezeで検査する。

- [x] **Step 1: 独立参照のRED test。** one-step Eulerはa=S0(1+(r-q)T)-K、b=S0 sigma sqrt(T)、d=a/b、e^-rT[a Phi(d)+b phi(d)]（b=0はdeterministic）。own math.erfのBSMと既存bsmをK80/100/120・q0/.02・sigma0で1e-11照合。scalar loopとTask1 pairを手指定2/4stepで1e-12照合する。
- [x] **Step 2: 最小参照実装とGREEN。** clip積分は端点質量l*g(l)+(1-h)*g(h)と、z∈[max(Phi^-1(l),z_K),Phi^-1(h)]のlognormal partial expectationを足す。高tailはsfを使い桁落ちを避ける。clip=(1e-3,1-1e-3)を独立`scipy.integrate.quad`のu積分と1e-9照合し、主nextafter clipと公開1e-10との差を保存する。
- [x] **Step 3: protocol/streamのRED test。**

```python
def test_candidate_cannot_run_main_and_mutated_frozen_roster_is_rejected():
    p = protocol.candidate_protocol()
    with pytest.raises(ValueError, match="frozen"):
        protocol.validate_protocol(p, require_frozen=True)
    p["state"] = "frozen"
    with pytest.raises(ValueError, match="pilot|review|fingerprint"):
        protocol.validate_protocol(p, require_frozen=True)

def test_phase_and_level_streams_are_distinct_and_replayable():
    logical = [
        {"logical_id": "pilot.l0", "phase": "pilot", "entropy": [83101],
         "logical_spawn_key": [0, 0]},
        {"logical_id": "main.l0", "phase": "main", "entropy": [83201],
         "logical_spawn_key": [0, 0]},
        {"logical_id": "main.l1", "phase": "main", "entropy": [83201],
         "logical_spawn_key": [0, 1]},
    ]
    p = {"seed_ledger": protocol.resolve_seed_roster(logical)}
    rows = protocol.seed_roster(p, "pilot") + protocol.seed_roster(p, "main")
    keys = [(tuple(r["entropy"]), tuple(r["spawn_key"])) for r in rows]
    assert len(keys) == len(set(keys))
    assert len({r["seed"] for r in rows}) == len(rows)
    assert rows == protocol.seed_roster(p, "pilot") + protocol.seed_roster(p, "main")

def test_uint32_collision_is_resolved_before_results_and_audited():
    logical = [
        {"logical_id": "a", "phase": "pilot", "entropy": [83101],
         "logical_spawn_key": [0]},
        {"logical_id": "b", "phase": "coverage", "entropy": [83301],
         "logical_spawn_key": [0]},
    ]
    def forced_candidate(row, retry):
        return 100 if retry == 0 else 101
    rows = protocol.resolve_seed_roster(logical, candidate_seed_fn=forced_candidate)
    assert [r["raw_seed"] for r in rows] == [100, 100]
    assert [r["seed"] for r in rows] == [100, 101]
    assert [r["retry_count"] for r in rows] == [0, 1]
    assert rows[1]["candidate_seeds"] == [100, 101]
    assert rows[1]["spawn_key"] == [0, 1]
    assert rows == protocol.resolve_seed_roster(logical, candidate_seed_fn=forced_candidate)
```

- [x] **Step 4: validator実装・GREEN。** r/q finite、sigma0を許容、T0を拒否、epsilon順序・case roster・m/R/B integer/bool・phase root重複・解決済み台帳のseed重複・raw/retry/spawn_key矛盾・CI alpha/clip/上限・cost定義の欠損を具体的に拒否する。強制衝突fixtureでは正常resolutionを確認し、frozen seed/coverage512/main256/capの各改変はfingerprint不一致として拒否する。exact terminal/control期待値にqが落ちた対照testを追加する。
- [x] **Step 5: READMEへcandidate状態・次のレビュー条件を記す。** 現時点の数値候補は結果ではない。root .venvがworktreeにない場合にuvが空envを作らないよう、次節の共通環境指定を使う。

## Task 4: fixed pilot、cost calibration、review後freeze

**Files:** Create `pilot.py`, `pilot.json/npz`, `PILOT_REVIEW.md`, `pilot_review.json`, `test_mlmc_rqmc_pilot.py`。Modify README/ROADMAP。

**Interfaces:**

```python
def run_pilot(protocol: dict, *, mode: str = "full") -> tuple[dict, dict]: ...
def choose_allocations(record: dict, arrays: dict, protocol: dict) -> dict: ...
def cost_counts(*, level: int, base_steps: int, paths: int) -> dict: ...
def validate_pilot(record: dict, arrays: dict, protocol: dict) -> dict: ...
```

Full pilotは§1.2の3×16384全9level、exact paired bias、coarse/fine負状態・V/mean/SE、同L plain Var、exact/CV pilotを保存する。cost calibrationはwarmup1＋7計測、各level4096pairs、time scopeを揃えてmedian/p95を保存。warmup・全計測もpilot総費用へ加える。smokeは32paths/3levels/1pilot streamで配線確認だけ、`mode=smoke`からfreezeを拒否する。

- [ ] **Step 1: moments fixtureからの配分/停止のRED test。** mean(D)=[-.20,-.08,-.02]、SE=[.01,.01,.001]、epsilon=.10はL2の経験的bias基準に合格。mean(D_L)=.20なら上限L8でも`bias_unresolved`。coarse negative rate=2e-5なら`coarse_grid_invalid`。V/C配分はTask1のfixtureと一致する。mode=smoke、source不一致、reviewのpilot SHA不一致はfreeze不可。
- [ ] **Step 2: REDを確認し、全候補固定pilotと配分選択を実装。** pilotの乱数生成開始前にcandidate全phaseのseed台帳を作り、resolutionのraw/generated seed・retry・実spawn_keyを保存する。台帳はNPZのtyped列としてpilot bundleへ保存し、protocol JSONには台帳のdigest/件数/column registryを記す。`p["seed_ledger"]`は保存台帳を読み込んだin-memory表とする。途中meanを見てpathを増やさず、pilotstreamを主推定へpoolしない。per-block n/mean/M2、seed、負path/state数、RNG/update/payoff/aggregation数、秒数を保存する。
- [ ] **Step 3: F04採否後、無負荷時にfull pilotを実行。** Cost calibrationを主比較前に行いhardware/OS/CPU/thread/backendを保存する。秒数の精密な比例をsmall unit testへ要求しない。
- [ ] **Step 4: 独立pilotレビュー。** fresh agentが粗細係数、N式、bias target、負株価、seed phase/resolution、CV費用、clip差と全候補rosterを再検算し、PILOT_REVIEW.mdとmachine-readable reviewへ対象fingerprintを記す。candidate capの選定・予算妥当性はここで主比較前に判断する。512coverage・256mainなど全候補数字、未支持cell、最終台帳を確認する。未知のrateは`unresolved`のまま記す。
- [ ] **Step 5: 合格pilotからprotocol freeze。** `freeze_protocol`で§1.5の全条件を保存する。L/N/betaだけでなく、epsilon/商品/格子、pilot条件、512coverage・256main、全K/m/R、全cap・閾値・block/thread/timing/CI/clip/採否基準、最終seed台帳を主実験前に固定する。reviewがFAILなら当該原因を修正しprotocol revisionと必要な新pilot/台帳を作る。主実験の結果を用いてfreezeを書き換えない。

## Task 5: 主反復のanalytics・被覆率・費用会計

**Files:** Create `analytics.py`, `test_mlmc_rqmc_research.py`の純粋統計部分。

**Interfaces:**

```python
def error_summary(prices: np.ndarray, truth: float) -> dict: ...
def coverage_summary(intervals: np.ndarray, truth: float) -> dict: ...
def cost_account(pilot: dict, runs: list[dict], *, amortizations=(1, 10, 100)) -> dict: ...
def decision(record: dict, arrays: dict) -> dict: ...
```

- [x] **Step 1: 手計算fixtureのRED test。**

```python
def test_rmse_is_across_runs_and_coverage_uses_original_trials():
    prices = np.array([9., 10., 11., 12.])
    result = analytics.error_summary(prices, 10.)
    assert result["bias"] == pytest.approx(.5)
    assert result["rmse"] == pytest.approx(np.sqrt(1.5))
    intervals = np.array([[8., 9.], [9., 11.], [10., 10.], [11., 13.]])
    result = analytics.coverage_summary(intervals, 10.)
    assert result["hits"] == 2
    assert result["trials"] == 4
    assert result["coverage"] == pytest.approx(.5, rel=0, abs=1e-12)
    assert result["mean_width"] == pytest.approx(1.25, rel=0, abs=1e-12)

def test_shared_pilot_is_not_multiplied_by_main_run_count():
    pilot = {"pilot_s": 2., "calibration_s": 1.,
             "allocation_s": .5, "freeze_validation_s": .25}
    runs = [{"main_s": 4.}, {"main_s": 6.}]
    out = analytics.cost_account(pilot, runs)
    assert out["experiment_s"] == pytest.approx(13.75, rel=0, abs=1e-12)
    assert out["cold_mean_s"] == pytest.approx(8.75, rel=0, abs=1e-12)
    assert out["amortized_mean_s"]["10"] == pytest.approx(5.375)
```

- [x] **Step 2: RED後、独立run誤差・被覆率の式を実装。** MSE=mean((price-truth)**2)、bias=mean(price)-truth、empirical variance=mean((price-mean(price))**2)、MSE=bias²+empirical varianceを同じ分母Bで固定する。ddof1のsample varianceは別列。coverage端点はinclusive。
- [x] **Step 3: Wilson 95%を実装してGREEN。** z=norm.ppf(.975)、p=hits/B、den=1+z²/B、center=(p+z²/(2B))/den、half=z*sqrt(p*(1-p)/B+z²/(4B²))/den。hits0/B・allhits/Bも有効区間になる。B<1、NaN、逆順CI、missing runは拒否し、退化区間も元のtrialsへ含める。
- [x] **Step 4: 費用会計と採否をfixtureで固定する。** `experiment_s=pilot+calibration+allocation+freeze+sum(main)`、cold/amortizedはmethod/epsilonごとの必要expense_idを明記する。重複expense_idの異なる金額、欠損offline費用、negative secondsを拒否する。saved採否フラグを引数にせず、固定rosterの誤差・費用・couplingから`decision`を再計算する。全cost ratio=.5 / 1.2の2fixturesで固定bootstrapと速度採否を確認する。未有効cellは理由ごとに数える。

## Task 6: frozen main・compact証拠・改変/fresh checker

**Files:** Create `build_reference.py`, `reference.json/npz`, `test_mlmc_rqmc_research.py`の実験/改変部分。Modify README/ROADMAP。

**Interfaces:**

```python
def run_reference(output: Path, *, protocol_path: Path, mode: str = "main") -> dict: ...
def save_result(output: Path, record: dict, arrays: dict) -> None: ...
def load_result(output: Path) -> tuple[dict, dict]: ...
def check_record(record: dict, arrays: dict, *, fresh: bool = False) -> dict: ...
```

main modeはfrozen/review/source/全数値条件/最終seed台帳/rosterが全一致の場合だけ実行。fixture modeは計測/採否に使わない。既存reference上書きを拒否し、再実行は別directory。各method/epsilon/run/levelのn/mean/M2、block summaries、sampling/bias-aware CI、全scramble pricesとraw/generated seed・retry・実spawn_key、負数、cost-counter、timing observationとsource/protocol snapshotを保存する。全Eulerpathを保存しない。

- [ ] **Step 1: Tiny fixtureのRED。** B=4、m=3、R=4、L=2、N_l=[16,8,4]のfixtureを使う。これはmain protocolと別schemaで`fixture`と明示。JSONのprice/SE/coverage/decision、N_l、clip、子seed、review digest、level M2を1つずつ改変してcheckerが拒否するtestを書く。
- [ ] **Step 2: main配線を最小実装してGREEN。** per-run independentlevels、fixed allocations、block generator、plain Euler/exact/CVを配線。RQMCはfrozen台帳の当該R行を`rqmc_gbm_call_from_seeds(..., child_seeds=..., child_metadata=...)`へ渡す。legacy wrapperとcandidate resolutionをmainでmonkeypatchして例外にし、mainが呼ばないtestを追加する。RNG/engine/summary timerを保存。partial runで例外が出たら失敗recordを保存し、completed rosterへ補充しない。
- [ ] **Step 3: 保存checker。** NPZ `allow_pickle=False`、array registry/shape/dtype、n/M2>=0、nのint、negative<=paths/states、price/SE/df/CI/費用/roster/採否を再計算する。fingerprintが合ってもstatistical summary改変は通さない。
- [ ] **Step 4: fresh検証と独立参照。** 固定seedから代表caseごとの最初/最後runと全levelを再生成しblockmomentsを1e-10相対/1e-12絶対で照合。全scramble推定値はsmall referenceの全件、full mainは全seed台帳＋各18cellの3代表outerrunを再生成する。fresh-review rootは追加の独立256pair/caseでscalar Euler replayとcouplingを照合し、主反復へpoolしない。
- [ ] **Step 5: F04採否後に全mainを実行。** B=256 Euler系列、B=512の18RQMCcellを満たす。smokeをmainへ昇格しない。frozen未支持cell・失敗件数も保存する。明らかな負荷競合/バックエンド変更があった計時は理由付きで別revisionへ再計測し、良い時間だけ選ばない。
- [ ] **Step 6: 保管。** 20MB以下は小さなsynthetic bundleを研究資料へ保持。超える場合は既存`artifacts.store_large(output, stem="reference")`でprimary/mirrorを使い、各copyから独立復元とSHA/数値checkerを実施する。保管庫marker未接続を空folder作成で迂回しない。

## Task 7: artifact-only 4図・教材・独立最終レビュー・採否

**Files:** Create `build_notebook.py`, `mlmc_rqmc_ci.ipynb`, `test_mlmc_rqmc_notebook.py`, `REVIEW.md`。Modify README/MODEL_INDEX/ROADMAP。

**Interfaces:** `build(directory: Path, output: Path | None = None, *, execute: bool = False) -> Path`。artifact directoryは`JOHNHULL_MLMC_ARTIFACTS_DIR`、source directoryは`JOHNHULL_MLMC_SOURCE_DIR`の明示overrideを許可し、既定はbuilderのdirectory。saved checkerが失敗したbundleを描画しない。

4図を固定する。

1. **階層差分分散：** pilot Var(Y_l)とVar(P_l)、coupled/unpaired診断、alpha/betaの未支持表示、negative incidence。同じplotに単一seed絶対誤差をRMSEとして置かない。
2. **経路配分：** epsilonごとのN_l、level別predicted/observed cost share、bias/sampling予算。小さいfine allocationとpilot/配分費用を明示する。
3. **RMSE対費用：** Euler MLMC/plain Euler/exact plain/frozen CVの独立run RMSE、main/cold/amortized秒数、step費用の別panel。BSM解析評価は価格真値/時間比較器として別表示し、Euler研究から除去しない。
4. **CI被覆率：** R/m/KごとのStudent nominal95%、empirical coverageとWilson区間、幅median/p95、BSM/P_clipの区別、退化数。MLMC sampling vs bias-awareの真値被覆も表で添える。

- [ ] **Step 1: artifact-onlyのRED test。** fixture bundleからbuilderを実行し、PNG display_dataのあるfigure cellが4個、seed/clip/CI近似/bias/費用/失敗理由/採否が本文に現れることを固定する。主計算関数をmonkeypatchして例外にし、notebookを実行しても呼ばれないことを確かめる。
- [ ] **Step 2: builderの最小実装・GREEN。** nbformat deterministic cell-id、`hullkit.nbplot.setup()`またはjapanize_matplotlib、matplotlib、保存配列checkerのみ。欠損/壊れたbundleは明示エラー。計測秒数の再現をnotebook実行で要求しない。
- [ ] **Step 3: 4図を実行・render・目視。** 日本語glyph、軸/legend/CIラベルの衝突、log軸で0/unsupported点を隠していないか、cost内訳が表と一致するかを確認する。HTMLを付ける場合はworkspaceの`docs/templates/claude-report/`を適用する。
- [ ] **Step 4: 独立最終レビュー。** fresh reviewerが原始block/scramble観測から配分、bias/SE、RMSE/coverage、費用・採否を再計算し、代表fresh replay、source snapshot、clip bias、4図を確認。Critical/Importantは修正して再検査する。reviewerの自前Black/Euler計算を証跡に残す。
- [ ] **Step 5: 完了記録。** READMEに問い・固定条件・反復roster・有効/失敗cell・検証・採否・限界・後続Hestonを保存する。ROADMAPは実測を根拠にF08 v1完了として更新し、未実装Hestonを完了に数えない。勝利・理論改善率・公開API昇格を完了条件にしない。

## Task 8: Heston算術Asianの次段階を保持する

設計が明示する次段階であり、GBM v1に混ぜてbias真値を偽装しない。F04の採否とsource fingerprint確定後、次revisionの実施計画・pilotへ進む。

- 商品：F04と同じS0=100、r=.03、q=0、v0=.04、kappa=2、theta=.04、xi=.3、rho=-.7、T=1、K=100、月次i/12、初期S0を平均へ含めず満期払。
- scheme：F04の`heston_monthly`が実装するfull-truncation log Eulerを採用候補とする。varianceのdrift/diffusionにmax(v,0)、raw negative varianceは保持。F04が独立レビューで採用した規約を別schemeへ無断変更しない。
- M_l=12*2**l、2factor fine driverの両成分を`aggregate_normals(...,2)`で集約。同じ月次13列を取り、内部の全step平均やS0平均に置換しない。
- scalar independent Heston Euler recurrenceとxi=0の時間依存deterministic variance、rho=±1、negative variance fixtureを先にTDDする。粗細Asian差分からMLMCのmean/varianceを評価する。
- 解析Asian真値はない。別streamのhigh-resolution plain reference、1段/2段refinementとsamplingSEを分け、referenceの未解消biasを誤差に含める。F04のAsian価格を真値と呼ばず、同一scheme/観測条件を確認する。
- bias停止は隣接レベル差の複数レベル安定性と独立reference refinementで別に固定する。安定しない場合は未解決を残し、GBMのalpha/betaやCI被覆を移植しない。
- 同じ4図、全pilot/費用、固定条件、独立レビュー、採否を次段階の完了条件にする。GBM v1の検証・成果は保持し、Heston着手時には専用protocol revisionと計画を作る。

## 3. CLIと実施順序

すべてworktree root `/home/kazumasa/worktrees/johnhull-research-roadmap`でWSL bashから実行する。共通envを明示し、worktreeに空の.venvを生成しない。

```bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
export UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv
export PYTHONPATH="$PWD/johnhull/hullkit/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

# 各タスクのRED/GREEN（Task 1では先頭1fileから順次追加）
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_multilevel_mc.py \
  johnhull/hullkit/tests/test_rqmc_ci.py \
  johnhull/hullkit/tests/test_mlmc_rqmc_reference.py \
  johnhull/hullkit/tests/test_mlmc_rqmc_protocol.py \
  johnhull/hullkit/tests/test_mlmc_rqmc_pilot.py \
  johnhull/hullkit/tests/test_mlmc_rqmc_research.py \
  johnhull/hullkit/tests/test_mlmc_rqmc_notebook.py

# 配線専用: freeze禁止
uv run --no-sync --package hullkit python johnhull/research/RB-F08/pilot.py \
  --protocol johnhull/research/RB-F08/protocol.json --mode smoke \
  --output johnhull/research/RB-F08/smoke

# F04採否後・無負荷時
uv run --no-sync --package hullkit python johnhull/research/RB-F08/pilot.py \
  --protocol johnhull/research/RB-F08/protocol.json --mode full \
  --output johnhull/research/RB-F08
uv run --no-sync --package hullkit python johnhull/research/RB-F08/pilot.py \
  --check johnhull/research/RB-F08 --fresh

# 独立PILOT_REVIEW.md / pilot_review.json作成後
uv run --no-sync --package hullkit python johnhull/research/RB-F08/pilot.py \
  --freeze johnhull/research/RB-F08 --review johnhull/research/RB-F08/pilot_review.json
uv run --no-sync --package hullkit python johnhull/research/RB-F08/build_reference.py \
  --protocol johnhull/research/RB-F08/protocol.json --output johnhull/research/RB-F08
uv run --no-sync --package hullkit python johnhull/research/RB-F08/build_reference.py \
  --check johnhull/research/RB-F08 --fresh
uv run --no-sync --package hullkit python johnhull/research/RB-F08/build_notebook.py \
  --artifacts johnhull/research/RB-F08 --execute

# 既存関係suite: F08部分検証後、F04主実験と競合しない時点
uv run --no-sync --package hullkit pytest -q \
  johnhull/hullkit/tests/test_numerical_mc_replay.py \
  johnhull/hullkit/tests/test_numerical_mc_variance.py \
  johnhull/hullkit/tests/test_mc_advanced.py \
  johnhull/hullkit/tests/test_stochastic_foundations_stock.py \
  johnhull/hullkit/tests/test_model_index.py \
  johnhull/hullkit/tests/test_docstrings.py

# 最終統合ゲート: 前の実験が完了してからrootが実施
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests
uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests
make hull-release-check
```

ruffは今回追加/変更したPythonだけに`uv run --no-sync ruff check <files>`、`ruff format --check <files>`を実施する。全suiteの過去greenを現行変更の検証と取り違えない。失敗時は関連基線を同じ環境で比較する。上記CLIは実装すべき仕様であり、この計画作成時点では未存在scriptを実行した結果ではない。

## 4. 完了条件と今回の確認

| 設計要求 | 実装/検証タスク |
|---|---|
| Euler粗細結合、independent levels、負株価 | Task 1/3/4/6 |
| bias/sampling予算、fixed pilot配分、弱率の制限 | Task 1/3/4/5/6 |
| step/normal/seconds/hardwareとpilot費用 | Task 4/5/6 |
| independent scrambles、t CI、clip/有界保証の区別 | Task 2/3/5/6 |
| repeated RMSE/bias/coverageと失敗cell | Task 5/6 |
| artifact-only4図、独立レビュー、採否 | Task 7 |
| 固定月次Heston Asianの次段階 | Task 8、専用revisionを未完として保持 |

計画作成時点の実施済みは関連guide/設計/索引/ロードマップ/private MC・QMC/F04再利用箇所の読解、一次文献とSciPy仕様の確認、共通NumPy/SciPyのimportだけ。重いpilot、全suite、実装ソース変更、commit/pushは未実施。新規worktree .venvは環境確認中にuvが生成したため、絶対パスと非symlinkを確認して除去済み。

**実装前に残る決定:** 本計画の候補値（epsilon、pilot/反復数、cap、negative観測閾値、cost配分方式）は明示済み。rootが現在の研究順序に沿って採用し、独立pilotレビューでcap/全rosterの候補を選定する。主比較前に§1.5の全数字と解決済み最終seed台帳をfreezeする。これはユーザーへの権限再確認を要求する項目ではない。pilotが失敗した場合の新revision、Heston次段階の開始、公開API昇格はそれぞれ異なる判断であり、未実装を研究完了と数えない。

**難しい点:** 有限pilotからのbias推定と厳密誤差保証の違い、非常に小さいlevel差分のrate不安定性、費用計時の負荷依存、少数Rのt区間の非正規性、clipされた変換と経済真値の違い。成功fixtureだけで研究有効性を認定せず、固定全roster・失敗理由・fresh再生・独立レビューで限定した採否を残す。

一次資料確認日: 2026-10-09。Giles著者公開PDF、Jain et al. arXiv v2本文、SciPy Sobol/t公式ドキュメントを確認した。S020の出版社Version of Record全差分を新たに照合したとは主張しない。

2026-10-09実装前レビュー修正：数値再現比較をallcloseへ統一し、32bit seedのcandidate時限定・決定的衝突解決と直接seed seam、pilot reviewでのcap選定と全主条件freezeを追加した。変更対象はこの計画1fileのみ。実装・主実験・commit/pushは実施していない。
