# Dynamic Cross-Model Hedging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 合成の同一初期vanilla面から、月次Asianの自己資金・費用込みヘッジをHeston/local、Greek/band/NNで比較し、保存値から検証できる研究v1を完成する。

**Architecture:** Torch-freeの金融core、条件付き教師、共通価格面、市場クオートリスクをhullkitのprivate moduleへ置く。Torch policy・訓練・全attempt runnerはdeep_hedge_priceに置き、JSON+non-object NPZを境界とする。研究資料と独立参照はjohnhull/research/RB-F04/dynamic_hedgingへ保存する。

**Tech Stack:** 既存Python3.12、NumPy、SciPy、PyTorch CPU float64、pytest、ruff、JSON/NPZ、既存CAS。新依存なし。

**Spec:** johnhull/research/RB-F04/dynamic_hedging/DESIGN.md
**Research:** 同ディレクトリのRESEARCH.md、CONDITIONAL_FEASIBILITY.md、DESIGN_REVIEW.md。
**Date / base:** 2026-10-09 / 43953298。codex/rbf04-dynamic-hedgingで開発し、phase受入後mainへ統合する。未知のxaaと別project変更を保持する。

## Global Constraints

- 主claimはK100/T1の月次12fixing arithmetic Asian。S0を平均へ含めない。
- 市場G=Heston-Q/local-Q、評価M=Heston/local、U1=stock+cash、U2=stock+cash+固定K100/T1.25 call。市場callを共通約定価格にする。
- 主hedge gridは月次12を固定。24/48は別の取引頻度診断であり、数値誤差の近接gateにしない。claimfixingは増やさない。
- 主費用は合成half-spread stock.0005/call.005、初期/中間/終端すべて。cash borrow/lendともr=.03。
- 実varianceや将来乱数をNN/Greekfitへ渡さない。local forecast倍率ℓは条件付き予測で固定、毎rebalance同じ観測Qへ再fitする。
- CM2-lognormal varianceは二次moment発散のため不採用。正CIR drift-implicit+old-v adapted log-stockを使い、有限四次moment条件を別gateにする。
- private moduleのみ。public API、__init__.py、既存demoの会計規約、production依存を変更しない。
- raw failure、支持外、fit非一意/悪条件、全原始分母を保存する。隠れたhold/zero/nearest/price clipでrepairしない。
- financial比較は許容差または固定seed＋SE倍数。hash/seed identityはprovenanceのみ。
- source/candidate/pilot/独立reviewを固定してからmain。main後のseed/N/閾値/selection/teacher調整は新revisionへ分離する。
- notebook/checkerは保存artifactだけを読む。RNG、training、optimizer、networkを禁止する。
- scoped testsとruffを各taskで行い、hullkit+report+deep_hedge_price全suiteは最終gateで1回。
- Q primary/empty-claim診断必須。合成Pdrift診断はsecondary optional、歴史市場の再現ではない。

## Review Focus

1. 正CIR schemeのstock二次/四次momentが存在し、MSEのSEを使えるか。Task1でfixed-grid十分条件と旧CM2反例を検査。
2. localのnormalized価格がspotに依存し、VSの追加chain termを落としていないか。Task2/3で非constant係数のCRN bumpを検査。
3. ℓ=1等の価格面nodeでCθが普通の微分として存在し、root一意性/near-zero Jを検査しているか。Task3でnode・複数root・boundのfixtures。
4. 月次観測順序、配当CF、終端手仕舞いとcash-settled claimを一回だけ数えるか。Task1/4で独立gain式と手計算fixture。
5. 5%改善の判定でランダムbaselineの不確実性を含め、失敗pathを除外しないか。Task5でpaired relative score、境界反例、元分母のtamper。

## File / interface map

| Owner | File | Responsibility |
|---|---|---|
| financial core | johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py | 正CIR更新、calendar recorder、Asian memory、vector CF/cash会計 |
| financial teacher | johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py | last-step CE、auxiliary GBM control、primitive-to-label/block moments |
| price/cache | johnhull/hullkit/src/hullkit/_dynamic_hedging_surfaces.py | calendar call snapshots、同一C1 cacheの値/微分、quote-state fit |
| risk | johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py | IFT、minimum-variance stock target、PSD covariance、band、paired statistics |
| learner | deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_policy.py | 9features/2action、Torch training、NumPy weight replay |
| runner | deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_study.py | 全attempt、source/protocol freeze、pilot/main/check、expense registry |
| independent reference | johnhull/research/RB-F04/dynamic_hedging/reference_methods.py | 既存独立CF/calendar PDEのsnapshot拡張、別conditional direct MC/CRN |
| artifact orchestration | 同directoryのrun_reference.py / run_fresh.py / build_notebook.py | 明示phase CLI、fresh receipt、3図だけの保存表示 |

隣接taskのsignatureを変える必要が出たら、依存task開始前に本表とspecを同じcommitで更新する。既存moduleへ追加機能を混ぜない。新private moduleはMODEL_INDEX.mdへ同時登録する。

### Task1: 正CIR calendar recordsと独立自己資金会計

**Files:** Create _dynamic_hedging_core.py、johnhull/hullkit/tests/test_dynamic_hedging_core.py。Modify MODEL_INDEX.md。

**Produces:**

~~~text
cir_implicit_step(v: np.ndarray, z_v: np.ndarray, dt: float, parameters: HestonParameters) -> np.ndarray
moment_certificate(parameters: HestonParameters, horizon: float, p: int = 4, epsilon: float = .01) -> dict
heston_records(parameters: HestonParameters, normals: np.ndarray, times: np.ndarray,
               record_indices: np.ndarray, *, spot=None, variance=None) -> dict
local_records(parameters: HestonParameters, surface: LocalVarianceGrid, normals: np.ndarray,
              times: np.ndarray, record_indices: np.ndarray, *, spot=None, multiplier=1.) -> dict
asian_memory(record_spots: np.ndarray, record_times: np.ndarray, fixing_times: np.ndarray) -> dict
cash_account(times: np.ndarray, prices: np.ndarray, holdings: np.ndarray, payoff: np.ndarray,
             *, premium: float, rate: float, cashflows=None, cost_rates=None) -> dict
~~~

timesはabsolute calendar time、normal形状(N,steps,2)、localは第1stock shockを使う。recorderは(N,record dates)のspot/variance、path mask/reasons、支持/wing/proxy/失敗件数を返す。cash prices=(N,m+1,d)、holdings=(N,m,d)、CF=(N,m+1,d)、fee=(d,)；terminal liquidationは関数が一度だけ行う。

- [x] failing tests：deterministic variance constant時のexact GBM、負normalでも正CIR、moment certificate、calendar/claim順序、unsupported local保持、2asset/CF/terminal fee fixtures。

~~~python
def test_two_asset_cash_matches_independent_discounted_gain():
    times = np.array([0., .5, 1.])
    prices = np.array([[[100., 6.], [104., 8.], [102., 5.]]])
    holdings = np.array([[[.4, .5], [.6, .2]]])
    out = cash_account(times, prices, holdings, np.array([3.]),
                       premium=7., rate=.05, cost_rates=np.array([.001, .005]))
    assert out["discounted_pnl"][0] == pytest.approx(2.2171179961044647, abs=1e-12)
    assert out["costs"][0] == pytest.approx([.055, .0328, .0662], abs=1e-12)

def test_fourth_moment_sufficient_condition():
    p = HestonParameters(100., .03, 0., .04, 2., .04, .3, -.7)
    c = moment_certificate(p, 1.25)
    assert c["qualified"]
    assert c["gaussian_quadratic_coefficient"] == pytest.approx(.99421875)
~~~

- [x] scoped pytestを実行してmissing module/functionのFAILを確認。
- [x] CIRはa=(4κbarv−ξ²)/8、b=κ/2、c=ξ/2、D=1+b dt、u=√v+c√dt Zv、y'=(u+√(u²+4Da dt))/(2D)。u<0にはrationalized rootを使い、xi0はdeterministic transitionを返す。stockは旧vでlog-Euler。normal/RNGはcaller所有。
- [x] cash再帰と独立discounted gainを別に計算。CFはevent支払時に受領。失敗後のcash/P&LをNaN・理由付き保持、原path数を変えない。
- [x] 上のscoped tests/ruff/formatを実行し、source/tests/索引だけcommit。

### Task2: Conditional Asian / auxiliary GBM primitives

**Files:** Create _dynamic_hedging_conditional.py、test_dynamic_hedging_conditional.py。Modify MODEL_INDEX.md。Consumes Task1。

**Produces:**

~~~text
conditional_tail(b, c, mu, sigma, x) -> dict
auxiliary_geometric_mean(spot: float, variance: float, fixing_delays: np.ndarray,
                         expiry_delay: float, *, rate: float, dividend_yield: float,
                         memory_sum: float, strike: float, total_fixings: int = 12) -> float
teacher_primitives(model: str, parameters: HestonParameters, normals: np.ndarray, *,
                   calendar_times: np.ndarray, fixing_indices: np.ndarray,
                   spot: float, state: float, memory_count: int, surface=None) -> dict
primitive_labels(primitives: dict, thresholds: np.ndarray, *, blocks: int = 16) -> dict
~~~

primitiveには(b,c,mu,sigma)、last-left spot/variance/coefficient、aux logG prefix/loading、状態/全Nを保存。model/auxを同じlast Zでconditionし、β=1の差+既知meanを作る。normalはdate/nodeで明示CRN共用、market/train/test/oracleから独立。

- [x] failing tests：last-tailと独立1D quadrature、aux m1のBlack、A≥12Kのexact linear、sigma0 atom unknown、local spot-dependent chain、state-dependent controlを全bumpで再計算。

~~~python
def test_tail_against_independent_quadrature():
    from scipy.integrate import quad
    from scipy.stats import norm
    b, c, mu, sig, x = 2., 1.2, -.01, .3, 3.1
    ref = quad(lambda z: max(b + c*np.exp(mu+sig*z)-x, 0.)*norm.pdf(z),
               -12., 12., epsabs=1e-10)[0]
    got = conditional_tail(b, c, mu, sig, x)
    assert got["f"] == pytest.approx(ref, abs=2e-9)
~~~

- [x] red test確認後、tail positive strike / linear / deterministic atom branchを実装。underresolved全0/SE0をreadyへ昇格しない。
- [x] future calendar fixingを正しく使うGBM controlのmeanと同一priceのCRN bumpsを実装。Heston/local自身のgeometric価格を解析既知と扱わない。
- [x] 16IID blocksを同一CRN clusterのまま保存し、Nをnode数倍にしない。保存primitivesから価格/Greek covarianceまで再検算できるようにする。
- [x] scoped tests/ruff/format、索引登録、commit。

### Task3: Calendar call snapshots / C1 Asian cache / quote fit

**Files:** Create _dynamic_hedging_surfaces.py、test_dynamic_hedging_surfaces.py、research/reference_methods.py。Modify MODEL_INDEX.md。Consumes Task1/2。

**Produces:**

~~~text
build_call_cache(parameters, surface, *, dates, spot_nodes, state_nodes, model) -> dict
build_asian_cache(primitive_groups: dict, *, model: str, axes: dict) -> dict
evaluate_call(cache: dict, date_index: int, spot, state) -> dict
evaluate_asian(cache: dict, date_index: int, spot, state, memory_sum, memory_count) -> dict
normalized_price_greeks(spot, discount, threshold, f, f_x, f_state, *, model, state, f_log_spot=0.) -> dict
fit_quote_state(cache: dict, date_index: int, spot, quote, *, state_scale: float) -> dict
~~~

evaluate returns value/spot derivative/state derivative/status+error; modelstateはv又はell。fitはroot/residual/Ctheta/condition、bound/非一意/solver/支持外reasonを返す。call/Asianのtheta-support共通部分だけを使う。

- [x] failing tests：scalar analytic fixtureのnode微分/coordinate不変、複数root、unreachable quote、near-zero J、calendar-timeとremaining-timeの差、local chain、linearA branch。

~~~python
def test_local_normalized_spot_chain():
    # f(z,w,x)=2+0.1*z+0.2*w-x*0.3: smooth fixture with nonzero f_z.
    spot, disc, f, fz, fx = 100., .97, 1.4, .1, -.3
    x = 1.2
    expected = disc*(f+fz-x*fx)/12
    homogeneous = disc*(f-x*fx)/12
    got = normalized_price_greeks(spot, disc, x, f, fx, .2, model="local",
                                 state=1., f_log_spot=fz)
    assert got["spot_derivative"] == pytest.approx(expected)
    assert got["spot_derivative"]-homogeneous == pytest.approx(disc*fz/12)
~~~

- [x] call HestonCFはcurrent v/spot/残存T1.25−t、localは元calendar coefficientのPDEをellごとに一回後退し全snapshotを保存。独立CF/PDEのorder/domain/time/spot refinementを実装。
- [x] fixed tensor cubicを採用しtheta各軸4nodes以上、priceと全derivativeを同じsurfaceから出す。solver/境界/overshootを検査し、bounds外はunknown。
- [x] Heston V=DSf/12、VS=D(f−xfx)/12、Vv=DSfv/12；local VS=D(f+fz−xfx)/12、Vell=DSfw/(12ell)。観測jumpをtime interpolateしない。
- [x] pieceのextremaと微分から全rootを列挙し一意性を確認、scaled Brentでfit（実装判断：候補Newton-bisectionから変更、速度はpilotで測定）。endpoint bracketだけで一意扱いしない。t0 nearS0は専用sheet。
- [x] scoped tests/ruff/format・索引・commit。selected actual CF/PDE/conditional oracle gateはTask5 pilotで測る。

### Task4: Quote risk / band / observable Torch policy

**Files:** Create _dynamic_hedging_risk.py、test_dynamic_hedging_risk.py、deep private _dynamic_hedging_policy.py、deep tests/test_dynamic_hedging_policy.py。Modify MODEL_INDEX.md。Consumes Task1–3。

**Produces:**

~~~text
quote_positions(v_s, v_theta, c_s, c_theta, *, denominator_error=0.) -> dict
stock_only_target(positions: dict, c_s, c_theta, *, model, spot, xi=0., rho=0.) -> np.ndarray
price_covariance(model, spot, state, c_s, c_theta, dt, *, xi=0., rho=0., base_variance=None) -> dict
band_holdings(old, target, covariance, width: float) -> dict
improvement_scores(base_squared, candidate_squared, relative_improvement: float = .05) -> dict
observable_features(spot, time, memory_sum, memory_count, quote, old_holdings, spreads) -> np.ndarray
numpy_policy(weights: dict, features: np.ndarray, scaler: dict, *, universe: str) -> np.ndarray
fit_policy(dataset: dict, *, universe: str, seed: int, updates: int, batch_size: int,
           learning_rate: float, cap_seconds: float) -> dict
~~~

- [x] failing tests：IFTと独立Q/S re-fit bump、theta/logtheta不変、Σ PSD/ρ/multiplier、rank1 band null方向、feature latent禁止、Torch/NumPy inference・cash/gradient一致。

~~~python
def test_ift_two_asset_coordinates():
    r = quote_positions(.7, 5., .6, 10.)
    assert r["stock"] == pytest.approx(.4)
    assert r["call"] == pytest.approx(.5)

def test_band_rank_one_no_costly_null_trade():
    old = np.array([[0., 0.]])
    target = np.array([[1., -2.]])
    cov = np.array([[[1., .5], [.5, .25]]])
    out = band_holdings(old, target, cov, .01)
    assert out["holdings"] == pytest.approx(old)
~~~

- [x] U2 hQ=Vtheta/Ctheta、hS=VS−hQ CS。U1 minvariance hS=VS|Q+VQ betaM、Heston betaM=CS+Cvρxi/S、local betaM=CS。
- [x] band sd=sqrt((old−target)'Σ(old−target))、sd≤widthはold、それ以外target+(width/sd)(old−target)。rank1/zero sdは仕様として保持。raw targetと±2制約後を両保存。
- [x] 9→32→32→2 tanh、float64 CPU、U1 call=0。train-only scaler、local RNG、oldholding BPTT、全attempt/最後finite weights/更新数/capと失敗を保存。
- [x] scoped tests/ruff/format、索引、commit。

### Task5: Complete runner / statistical decision / candidate pilot

**Files:** Create _dynamic_hedging_study.py、deep tests/test_dynamic_hedging_study.py、research/run_reference.py、candidate.json、pilot receipts。Task5内部をTorch-free _dynamic_hedging_statistics.py＋hullkit testsと、_dynamic_hedging_protocol.py＋deep testsへ分割し、study orchestratorがconsumeする。Modify MODEL_INDEX.md/README.md/ROADMAP.md。

**Produces:** CLI --phase tiny/pilot/main/check；saved-check入力JSON+NPZ、phase別typed original IDs/status/expense keyset。mainはfrozen.jsonがないと拒否。policy/action/market/rawscoreをG/M/U/seed/level別に保存。

- [x] 統計helper：original perpath d/r、保存bootstrap/個別ES、数値envelope付きstrict閾値、全3init IUTを実装・独立レビュー承認。
- [x] protocol helper：候補12fits/44cells/用途別seed、receipt同一性、全費用・immutable I/Oを実装・独立レビュー承認。M1の不正inclusive flagを修正。runnerの金融semantic checkerと正式pilotは未実装。

- [ ] failing tests：test開封前のfit選択、original denominator保持、candidate/frozen mismatch、expense消去/二重加算拒否、改善閾値のboundary反例、64path block bootstrap、saved-only RNG guard。

~~~python
def test_relative_improvement_includes_baseline_uncertainty():
    base_sq = np.tile([1., 3.], 512)
    nn_sq = base_sq-.1
    scores = improvement_scores(base_sq, nn_sq, relative_improvement=.05)
    absolute_score = scores["absolute"]
    relative_score = scores["relative"]
    assert np.mean(absolute_score) == pytest.approx(-.1)
    assert np.mean(relative_score) == pytest.approx(0., abs=1e-14)
    assert np.std(relative_score, ddof=1) > 0
    assert np.std(absolute_score, ddof=1) == pytest.approx(0., abs=1e-14)
    assert relative_score[:2] == pytest.approx([-.05, .05], abs=1e-14)
~~~

- [ ] 44cells（G2×U2×11policy）、trainG2×U2×init3=12fits、別train/validation/test/oracle streams、3test seeds/192-384-768を実装。重いdriverはchunk、state/Greekを全policy共用。
- [ ] pilotはtoy→37quote→selected state→teacher/position/P&L refinement→tiny全44cell→4tinyNNの順。予算はCONDITIONAL_FEASIBILITYの構造的見積りを使い、actual時間/byte/SEを測る。各job≤10億path-step、NPZ≤256MiB uncompressedで分割し、全candidate直積を自動実行しない。旧CM2 scratch SEは選定に使わない。
- [ ] candidate gates：priceSE .03、hSSE .002/hQSE .005、独立Asian価格 .05/positions .01、call .001。Nprefix1024/4096/16384/65536、coarse/fine nodes、内部SDE/teacher/gridを検証し、24/48取引頻度は別診断する。未達は教師/source revisionへ戻り、達成を偽装しない。
- [ ] testN候補8192/16384/32768×3seedをpilot varianceから決める。width候補0/.01/.02/.05/.1/.2はvalidation-only selection。premiumは独立Heston direct MC（65536 IID、1536step/year）のpilot値/SEを固定。
- [ ] 主判定はpaired d=LNN²−LB²、r=LNN²−.95 LB²、各upperCI+独立numerical envelopeがUd+ud<−.001 AND Ur+ur<0。8familiesの名目α=.05/8、全3initのIUT。random baselineをdeltaCI外の閾値へ置かない。
- [ ] perpath mean/MSEのIID SEと、64path blocks・seed内stratified2000 bootstrap CIを保存。全methods/Gで同indices。ES95は個別lossのempirical tail/countを表示、blockmean ESと呼ばない。ES CI未評価は明記可。
- [ ] 全original Nにunknownがあれば全体支持判定unknown。finite-only表示はdescriptive。Pdrift optionalは別receipt。
- [ ] scoped tests/ruff/format・独立math/code/pilot review。source/候補/pilot/費用の変更が必要なら旧費用/失敗を残してrevision。README/ROADMAP現在地を同commitで更新。

### Task6: Frozen main / saved replay / fresh / full costs

**Files:** research/frozen.json、reference.json+ignored reference.npz、run_fresh.py、fresh receipts、CAS records、results assessment。

- [ ] registry全金融sourceとprotocolを列挙し、pilot/独立reviewにbindしてfreeze。全seed/slot/N/axes/grid/criteria/expense scopesを固定。
- [ ] train/validation生成→全12fits/全band候補→checkpoint選択完了→test開封。全3seeds/3levels/44cellsを完走又は理由付き失敗、resumeはsource/primitive binding一致のみ。
- [ ] 原始market states/monthly memory/call prices/holding/fee/claim/P&L、label blocks、rawscore、bootstrap indicesを保存。teacher earlier-SDE全replayとprimitive-boundary checkerを区別。
- [ ] 全cache-to-price/Greeks/IFT/holding/cash/statistic/expenseのsaved-only checker。reserved selected restartは独立future draws/別実装/1536stepでfresh再評価し、raw recordは変更しない。
- [ ] 両CASコピーを別々に復元し同じsemantic checkerを実行。archive/fresh/cold/interpreter/validation/pilot/sourcefreezeなど全費用を測り、inclusive親と子を二重加算しない。
- [ ] accuracy未達やunknownならspeedup/paybackは不採用/未定義。教育保持と実運用採用を分離する。

### Task7: 3図・最終受入・main integration

**Files:** build_notebook.py、dynamic_hedging.ipynb、RESULTS.md、REVIEW.json/.md、validation.json、MODEL_INDEX.md、ROADMAP.md、plan checklist。

- [ ] 図1 common面/selected quote risk/支持・原分母、図2 G×Uのnet P&L/全seed/費用、図3 cross-G/数値誤差/全費用/unknown・採否。
- [ ] guarded artifact-only notebookを実行し3PNG/0errorsを確認、実図を目視。研究計算を表示buildで再実行しない。
- [ ] 関連3suiteを1回実行、変更Pythonruff/format、tracked release。失敗ならbaseline比較とscoped修正/再検査、全suiteを無理由に再実行しない。
- [ ] 最終独立review、original/fresh/CAS/実図/費用/source bindingを確認して受入assessmentを作る。NN勝利を完了条件にしない。
- [ ] 既承認のGit方針でbranch push/main ff integration/push。main実pathでartifact復元/数値replay/release、別project変更維持を確認。全体ROADMAP・索引・integration receiptを更新。

## Execution / validation commands

WSL Linux path、既存shared .venvを用いる。worktree内で新uv syncを行わない。

~~~bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/deep_hedge_price/src" \
  /home/kazumasa/projects/.venv/bin/python -m pytest -q \
  johnhull/hullkit/tests/test_dynamic_hedging_core.py
/home/kazumasa/projects/.venv/bin/ruff check johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py \
  johnhull/hullkit/tests/test_dynamic_hedging_core.py
/home/kazumasa/projects/.venv/bin/ruff format --check johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py \
  johnhull/hullkit/tests/test_dynamic_hedging_core.py
~~~

Task2–5は各taskに記載したtest/source fileを同じcommandへ渡す。最終全suiteは以下一回。

~~~bash
PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/deep_hedge_price/src" \
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/kazumasa/projects/.venv/bin/python -m pytest -q \
  johnhull/hullkit/tests johnhull/report/tests deep_hedge_price/tests
/home/kazumasa/projects/.venv/bin/python johnhull/scripts/verify_release.py --require-tracked
~~~

## Self-review / status

全spec要件をTasks1–7へ割当。主claim/quote fit/limited local closure/原分母/CF/終端費用/有限四次/paired relative score/phase費用/3図を含む。候補の精度・所要時間は正式pilotで確定し、現時点で達成値を主張しない。Tasks1–4のprivate source実装・独立レビューを完了し、開発branchの整合したソースcommitにまとめる。Task5の統計/protocol helperも実装・独立レビューを完了した。Task5 runner/金融checker/pilot、Tasks6–7の主実験・最終受入・main統合は未実施。

実装は既存の「研究ロードマップ完遂」指示の範囲で進める。新依存/API昇格/実データ利用権が必要になった場合だけ、その具体差分を別判断とする。

## Source checkpoint（2026-10-09）

Tasks1–4の詳細・レビュー対象・5件のImportant修正・最新指紋は[ソース記録](../../../research/RB-F04/dynamic_hedging/implementation/README.md)を参照。変更範囲＋索引/docstring1193 tests、11Python ruff/check/format PASS。関連全3suiteは最終gateで1回実行する。Tasks1–4は共有索引の参照を同時に解決するため一つのcommitにする（各taskのRED/GREENと独立レビューは別記録）。元d71b25f3の設計レビューは歴史的記録で、最新ソース承認と区別する。

Task5で必須：call/Asian state-support交差、NaN/unmeasured誤差の不適格化、独立CFのquad収束・cutoff・bumpの別誤差、共通乱数cluster covarianceとCtheta誤差のIFT伝播、全original N／raw failure／cap超過／費用の保存。solver-okだけで精度承認しない。正式pilot・freeze・main/phase acceptanceは未完了。

Task5実装分担：統計helperはoriginal shape(3,N)、保存済みint16 bootstrap indices、paired d/rと全3initのIUTを扱う。protocol helperは44cell/12fit roster、seed namespaces、source/候補/pilot/review binding、test開封前選択、全費用、immutable JSON+non-object NPZを扱う。freeze helperはreceipt同一性の境界であり、pilot raw arraysの数学/数値再算出は研究checkerの責務。両helperの実装だけでrunner/pilot完了とはしない。

Task5 helperの[ソース確認](../../../research/RB-F04/dynamic_hedging/implementation/TASK5_HELPERS.md)：M1解消・独立再レビュー未解決0、変更範囲＋索引/docstring1200 tests、5Python ruff/check/format PASS。候補/rosterはsourceから保存、formal freezeは未実施。以前の1193件と重複するguard件数を足し合わせない。
