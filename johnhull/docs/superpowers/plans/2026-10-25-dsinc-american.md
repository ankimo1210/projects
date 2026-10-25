# DSINC American Put Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Subagentsを使う実行方法は、その時点のユーザー指示と利用可能なモデルに従う。

**Goal:** 市場データなしで公開Heston版を監査し、3/2モデルのAmerican put価格・EEP・行使境界を独立FDと照合して再現する。

**Architecture:** Heston公開コードを固定commitで研究用に保管し、統一入力adapterと監査を置く。新しい3/2 pricerはprivateな入力型・固定周波数伝播・節点境界の3単位に分ける。独立FDと研究runnerは `research/DSINC/` に置き、主要計算法を共有しない。

**Tech Stack:** WSL Ubuntu、Python >=3.12、既存NumPy >=2.0 / SciPy >=1.13、pytest、Matplotlib。float64/complex128、CPU 1 core。

**Spec:** [2026-10-25-dsinc-american-design.md](../specs/2026-10-25-dsinc-american-design.md)

**状態:** 2026-10-25、ユーザーの「進めて」により実装へ移行。Tasks 1–2完了、Task 3から継続。研究IDはDSINCで、既存RB-F*の計画を置換しない。Opus承認後、論文の印刷値（Table 3(b)のEuropean、Table 4のEEP・N=200）を照合対象に追加した（[レビュー記録](../reviews/2026-10-25-dsinc-american-opus.md)の「Opus承認後の追加照合と変更」）。

## Global Constraints

- private研究実装のみ。新production依存、既存公開API変更、本編/サイトへの組込み、市場データ取得は行わない。
- S,K>0、T>=0、rd>rf>=0、kappa,theta,v0,xi>0、|rho|<1。3/2はrho*xi<=kappa+xi**2/2の領域。T=0はexact payoff。
- 価格比較は価格/K、時間は年、v/thetaは分散率。chi=.5、正減衰の留数を含む。未定義入力や数値失敗をclip/代用値で隠さない。
- 主rosterは設計§6の3/2 6ケース。独立精度2e-5、referenceと個別細分の変化5e-6（価格/K）。文献gateはS0のspectral（Table 4の3/2 American 3spots、Table 3(b)の3/2 European 3spots、Table 9のT=1 ATM、6e-6）。Table 4のEEP列とN=200列は診断で、停止条件にしない。paper設定FDとの比較は診断で停止条件にしない。再現済みはspectral文献照合と独立gateの両方が必要。
- CPU 1 core、float64/complex128、1方式×1満期×1設定のsolver subprocess（3spotを一括）で180秒/peak RSS 2 GiB、pilot合計10分/main合計30分、保存目標50 MiB。反復計時はspectralだけ、FDは1回。
- untracked outputsは `_data/johnhull/DSINC/<run-id>/` の1root。再生成可能な大配列は保存しない。個別追加ファイル2 MB制限。
- 各タスクは適切な失敗テスト→実装→局所検証で進める。未達や全失敗も元の件数で記録する。コミットする場合は当該タスクのファイルだけをstageし、既存変更を含めない。
- 実装開始・段階完了・計画変更時に `johnhull/ROADMAP.md` を更新する。既存の完了・保留を維持する。

## Review Focus

1. SDE/契約入力が同じか。sigmaとxi、TとT2、varianceとvol、rd/rf、割引の二重適用をTask 1/2のテストで固定。
2. 0<chi<1の留数・反射周波数符号・端点半重みをTask 2/4で検査。偶然同じ符号誤りを持つ自己比較を避ける。
3. 符号変化のないroot、逆向き/多重root、内側contact点、非finite、反復上限をTask 1/4で検査し、成功価格へ変換しない。
4. 同じ誤差を共有したspectral/FD一致をTask 3の別導出・解析極限・領域細分とTask 5の全ケース会計で防ぐ。
5. キャッシュ混入・誤差のcancel・setup費用除外・失敗除外をTask 2/5で検査。同一精度を満たす方式だけで速度比較する。

## ファイルの配置と責任

| ファイル | 責任 |
|---|---|
| `johnhull/research/DSINC/upstream/{dsinc_pricer.py,fd_adi_pricer.py,benchmark.py,LICENSE}` | 固定commitの原本。改変しない |
| `johnhull/research/DSINC/upstream_manifest.json` | URL、commit、Git blobと取得byte列SHA-256、MIT出典 |
| `johnhull/research/DSINC/heston_baseline.py` | 統一入力adapter、上流fallback/penalty診断 |
| `johnhull/hullkit/src/hullkit/_dsinc_types.py` | frozen契約・モデル・格子・結果型、入力検証、構造化失敗 |
| `johnhull/hullkit/src/hullkit/_dsinc_spectral.py` | 周波数・作用素・伝播・European積分 |
| `johnhull/hullkit/src/hullkit/_dsinc_american.py` | EEP recursion、局所root、境界、American価格 |
| `johnhull/research/DSINC/reference_fd.py` | 独立3/2 FDと補完性診断 |
| `johnhull/research/DSINC/{cases.json,freeze_manifest.json,run.py,plot.py,README.md}` | 文献値/固定ケース、選択ladderと予算のfreeze、実験、保存結果3図、採否 |
| `johnhull/hullkit/tests/test_dsinc_{baseline,spectral,reference,american,runner}.py` | 各タスクの意味のある検算 |
| `johnhull/{MODEL_INDEX.md,ROADMAP.md}` | 実装索引と現在地。既存状態を保存 |

## Task 1: 型・上流固定・Heston基礎比較

**Files:** Create `_dsinc_types.py`、`research/DSINC/upstream/` の4原本、`upstream_manifest.json`、`heston_baseline.py`、`cases.json`、`test_dsinc_baseline.py`。Modify `MODEL_INDEX.md`、`ROADMAP.md`。

**Interfaces:**
- `PutContract(strike: float, expiry: float, domestic_rate: float, foreign_rate: float)`。
- `VarianceModel(kind: Literal['heston','three_halves'], kappa: float, theta: float, xi: float, rho: float, v0: float)`。
- `SpectralConfig(n_time: int, n_var: int, log_var_bounds: tuple[float,float], chi: float, panels: tuple[float,...], points_per_panel: int, root_width: float=.1, root_max_width: float=.3, root_x_tol: float=1e-10, root_residual_tol: float=1e-8, root_maxiter: int=60)`。
- `PricingFailure(code: str, message: str, details: dict)`。detailsに時刻、節点、bracket、residual、iterationを保持する。
- `PricingResult(european: ndarray, american: ndarray, early_exercise_premium: ndarray, times: ndarray, log_variances: ndarray, log_boundary: ndarray, diagnostics: dict)`。spot軸は入力順、boundaryは(n_time+1,n_var)。
- `run_heston_baseline(contract: PutContract, model: VarianceModel, spots: ndarray, *, dsinc_settings: dict, fd_settings: dict) -> dict`。結果はraw値、全実設定、fallback/非finite/penalty上限、初期化・EU・AM・query計時を含む。

- [x] RED: `test_baseline_parameter_mapping` で異なる入力キーの写像をassert、kappa=.5を両方式へ固定する。`test_source_hash_mismatch` はbyte改竄を拒否。`test_unknown_or_nonfinite_input` と `test_upstream_fallback_is_not_certified` で失敗を保持する。`test_upstream_raw_values_and_branches` は局所root/広域scan/min-residual、clip・非finite置換、EEP/価格の下限処理、penalty反復上限の各分岐を強制する。
- [x] Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_baseline.py`。新機能未実装のためFAILを確認する。
- [x] GREEN: 固定commitの4ファイルを取得して原文保持し、SHA-256/ライセンスを記録。実行時取得をしないadapterをimportlibで作り、benchmark.pyをimportしない。上流helperを研究サブクラスの観測版へ写して分岐・加工前後・penalty終了理由を記録し、同じ入力の無改変版と値が一致することをassertする。上流原本は変更しない。
- [x] 設計§5/6のpaper anchorをcases.jsonへ転記する。T=.5のAmerican { .107601,.048662,.019499 }、FD coarse { .107575,.048618,.019469 }、fine { .107593,.048648,.019490 }、T=1 ATM spectral .063668/FD fine .063658。Table 3(b)のT=.5 European { .102557,.047224,.019105 }（spectral＝閉形式Eq.(31)）、Table 4のEEP { .005044,.001438,.000394 }とDSINC N=200 { .107599,.048660,.019497 }も転記する。出典表、設定、丸め桁、not_availableも保存し、T=1全体を論文外と扱わない。
- [x] Run同コマンド、`test_docstrings.py` / `test_model_index.py`。PASS後、Hestonの最初の1ケースのみを予算付きpilotで実行し、上流印刷参照13.6633/13.6749等との差を記録する。精度未達でも原因を残してM0観測を完了できるが、受入済み価格器とは呼ばない。
- [x] 必要ならタスク単位でcommit。新private型をMODEL_INDEXに登録し、ROADMAPへ実装開始の事実を反映する。

## Task 2: 固定周波数伝播とEuropean価格

**Files:** Create `_dsinc_spectral.py`、`test_dsinc_spectral.py`。Modify `MODEL_INDEX.md`。

**Interfaces:**
- Consumes Task 1の型。`frequency_rule(config: SpectralConfig) -> tuple[ndarray,ndarray]`。
- `variance_grid(config: SpectralConfig) -> ndarray`（zeta節点）。
- `frequency_generator(contract: PutContract, model: VarianceModel, log_variances: ndarray, frequency: complex) -> ndarray`（設計§4の非割引作用素）。
- `build_propagators(contract: PutContract, model: VarianceModel, config: SpectralConfig) -> Propagators`。Propagatorsはcomplex128行列、周波数・重み・格子・dt・入力hash・setup secondsを持つprivate dataclass。
- `european_put(contract: PutContract, model: VarianceModel, spots: ndarray, config: SpectralConfig, *, propagators: Propagators | None=None) -> ndarray`。最終価格をzetaでnot-a-knot CubicSpline補間し、格子外なら拒否する。

- [x] RED: `test_constant_variance_fourier_mode` で定数分散fixtureの伝播を解析的なexpと比較（atol=1e-11）。`test_zero_frequency_preserves_one`、`test_reciprocal_variance_cir_mean` で3/2の独立CIR条件付平均を比較する。後者は160/240/320点の共通v0=.04、tau=.5、E[1/v_tau]=exp(-.8*tau)/.04+45*(1-exp(-.8*tau))、観測次数1.5〜2.5・最細相対誤差<=1e-4。
- [x] RED: `test_heston_european_against_existing_cf` はkappa2,theta=v0=.04,xi=.2,rho=-.5,rd=.05,rf=.02,T=.5、3spotで価格/K差<=2e-5。既存APIは `heston_price(spot,strike,rate,expiry,v0,reversion,long_run,vol_of_variance,rho,dividend_yield=0.0,*,kind='call',terms=1024,truncation=30.0)`、kind='put'とdividend_yield=rfを明示する。上流のFeller違反例をこの制御へ流用しない。
- [x] RED: `test_positive_damping_residue_and_sign` はBSM正規密度の独立数値積分fixtureを使い、留数なし・符号反転mutantをrejectする。`test_neumann_ghost_rows` は端の一次微分0/二次微分2倍、`test_common_generator_for_models` はa,b以外の共通経路を固定。`test_offset_and_cubic_interpolation` は解析曲線と±h/2の価格変化を比較する。
- [x] RED: `test_invalid_damping_or_grid` はchi∉(0,1)、非昇順panels、n_time<1、v0範囲外を拒否。`test_propagator_contract_mismatch` はrd/rf/T/model/gridのいずれかが違うcacheを拒否する。
- [x] Run `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_spectral.py`、FAIL確認後に実装する。n_varは節点数、中心差分＋ghost反射Neumann、`scipy.linalg.expm`、正周波数Gauss–Legendre、Eq.(61)。割引は価格側で一度だけ。Pe、exp(A_0*dt)の最小成分・行和を記録し、非単調なら独立検算/細分で影響を確認できるまで認定しない。
- [x] 同テストとTask 1をPASSにし、source/数学対応表を `research/DSINC/README.md` に加える。S0でT=.5のEuropean 3spotsを計算し、Table 3(b)とsmoke比較する（正式判定はTask 5のpaper_match）。setup/queryの計時を分離し、dense行列の同時保持量を計測する。必要ならcommit。

## Task 3: 独立3/2 finite-difference参照

**Files:** Create `research/DSINC/reference_fd.py`、`test_dsinc_reference.py`。

**Interfaces:**
- `FDConfig(n_x: int, n_var: int, n_time: int, log_spot_bounds: tuple[float,float], log_var_bounds: tuple[float,float], exercise: Literal['european','american'])`。
- `reference_put(contract: PutContract, model: VarianceModel, spots: ndarray, config: FDConfig) -> FDResult`。モデルはthree_halvesのみ。FDResultは価格、x/zeta格子、抽出境界brackets、最小payoff gap、補完性診断、計時・RSSを持つ。入力型だけ共有し、spectral/境界モジュールをimportしない。

- [x] RED: `test_fd_generator_from_three_halves_sde` は多項式/指数test functionへの作用を手計算式と比較し、混合項rho*xi*vの係数・割引符号を固定する。
- [x] RED: `test_fd_constant_variance_control` は独立定数分散fixtureを既存BSM/CRRと比較（European価格/K<=5e-6、American<=2e-5）。`test_fd_obstacle_and_complementarity` は接触・継続領域の相補性を確認する。
- [x] RED: `test_fd_refinement_and_domain_expansion` は小さな3/2ケースで軸別3解像度とh固定の領域拡大を比較し、未収束ならreferenceをunsupportedにする。`test_fd_geometry_mask_and_time_map` は整数indexの共通時刻、lambdaを用いた接触、FD bracketのzeta線形補間、x端4セルmask、90%coverageを固定する。`test_fd_time_budget_failure` は未計算点を成功値で埋めない。
- [x] Run `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_reference.py`、FAILを確認する。
- [x] GREEN: 設計§5の2D作用素を直接導出し、短い次元を内側に並べ、Rannacher 4 half-steps→CN＋Ikonen–Toivanen splitting。European左端はmax(K*exp(-rd*tau)-S_min*exp(-rf*tau),0)、American左端は有限領域近似payoff。lambda/gap/離散残差を返す。テスト用定数分散fixtureの生成はモデルSDEと分離する。
- [x] テストPASS後、T=.5の3spotsについてEuropeanをTask 2と比較する。paper設定FDのTable 4照合と、広い独立分散領域[log(1e-5),log8]の参照収束を分ける。軸別水準と領域拡大は設計§6に従い、3軸同時の巨大LUを作らない。価格補間もspot位置を変えて検査する。必要ならcommit。

## Task 4: EEP recursionと局所行使境界

**Files:** Create `_dsinc_american.py`、`test_dsinc_american.py`。Modify `MODEL_INDEX.md`。

**Interfaces:**
- Consumes Task 1/2。`payoff_transform(omega: ndarray, chi: float, boundary: ndarray, contract: PutContract) -> ndarray`。
- `local_boundary(residual: Callable[[ndarray],ndarray], predictor: ndarray, config: SpectralConfig) -> tuple[ndarray,dict]`。
- `american_put(contract: PutContract, model: VarianceModel, spots: ndarray, config: SpectralConfig, *, propagators: Propagators | None=None) -> PricingResult`。
- 境界/EEPの構造化失敗はPricingFailureとしてrunnerへ渡す。T=0はexact payoffと空の境界（shape=(0,0)）を返し、その例外形を明示する。

- [ ] RED: `test_time_quadrature_terminal_half_weight` と `test_boundary_endpoint_correction_only_at_root` は2段階の明示和を使い、dt半重み・dt*g/4の欠落/二重付与を検出する。`test_positive_strip_residue_in_eep` は独立な短時間fixtureで検算する。
- [ ] RED: `test_root_missing_sign_change_fails`、`test_root_nonfinite_fails`、`test_root_maxiter_fails`、`test_root_orientation_and_multiple_roots` は失敗codeと全node分母をassert。`test_contact_interior_not_selected` は平坦contact/ノイズ/逆向き/複数根のfixtureを使う。`test_failure_records_whole_time_slice` は失敗時刻の全node状態を埋め、より早い時刻をnot_runとし、Qを更新しない。
- [ ] RED: `test_maturity_exact_payoff`、`test_spot_order_and_strike_homogeneity`、`test_exercise_region_and_bounds`、`test_boundary_matches_independent_fd` を固定する。価格は設計の2e-5*K、境界はFDの細分に追随する隣接2cell基準。
- [ ] Run `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_american.py`、FAIL確認後にEq.(57),(58)を実装する。
- [ ] GREEN: RはEq.(58)左辺−右辺の価格/K残差。予測値pに対し[p-w,min(0,p+w)]、w=.1,.2,.3の順、R(lo)>0>R(hi)を必須にする。走査の零近傍はabs(R)<=root_residual_tol、設計のomega_maxに応じた走査点数で符号変化を数え、曖昧なcontactや多重根を拒否する。二分最大60回、x幅1e-10、abs(R)<=1e-8。失敗時刻の全node記録後に停止する。v0境界・値のzeta補間、初期行使領域判定とcontinuation評価を区別する。
- [ ] Run Tasks 1–4のテスト、T=.5の3ケースを初期設定と時間倍で比較する。ここでは文献値をsmokeとして確認し、正式な再現判定はTask 5のS0 paper_matchと独立gateで行う。必要ならcommit。

## Task 5: 予算付きpilot・固定main・費用/図・最終レビュー

**Files:** Create `research/DSINC/run.py`、`plot.py`、`README.md`、`test_dsinc_runner.py`、小さな採用結果/manifest。Modify `cases.json`、`MODEL_INDEX.md`、`ROADMAP.md`。

**Interfaces:**
- `run.py --phase pilot|main --output /home/kazumasa/projects/_data/johnhull/DSINC/<run-id>`。mainはpilotのfreeze manifestを必須入力にし、roster/source hash・閾値・job予算・ladder/選択規則の変更を拒否する。freezeはrepoとmain rootへ複製する。
- 各slotはcase_id、方式、全設定、状態、raw正規化/生価格、EEP、root diagnostics、setup/EU/AM/query/total seconds、RSS、source/input hash、失敗理由を持つ。JSONにNaNを出さず、失敗値はnullと理由。
- `plot.py --results <run-root>/results.json --output <run-root>/figures` は保存結果だけで3図を描く。

- [ ] RED: `test_every_original_slot_is_accounted`、`test_main_requires_frozen_pilot`、`test_timeout_and_memory_are_failures`、`test_setup_included_in_total_cost`、`test_hash_mismatch_rejected`、`test_result_replay_from_small_artifacts` を作る。`test_reproduction_requires_both_gates` はpaper_match（American・European・T=1 ATMの全anchor）とindependent_validatedの両方を必要とし、T=1非ATMのnot_availableを保持する。`test_frozen_ladder_no_posthoc_tuning` は未宣言設定と都合のよい段の選別を拒否する。費用テストは速度をassertしない。
- [ ] Run `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_runner.py`、FAIL確認後にbudget付きsubprocess runnerを実装する。
- [ ] pilotはHeston 1件と3/2 T=.5を使い、個別refinement・領域・damping・Delta bumpを調べる。T=1のFD fine American（3spots一括）も費用測定する。S0時間倍（cutoff固定）とTable 4のN=200列の差、EEPとTable 4のEEP列の差を診断列に残す（停止条件にしない）。10分合計/1process180秒・2GiBを超えたら中止。Heston全11件は予算内の場合のみ準備結果として保持する。
- [ ] 設定、source、閾値、roster、予算、S0/S1/S2とFD軸別ladder、採用候補Sjごとの個別感度ジョブ・最初の合格した隣接対の粗い側を選ぶ規則をfreeze。SjはS0またはS1、S2は検算用。同一満期の3spotsで最大差を判定する。設計§6のジョブ別予測式/係数を保存し、1job180秒超、合計30分超、係数未測定、reference未収束、spectral paper_mismatch、境界未成立ならmainへ進まない。FD文献差は診断だけ。許容差や予算を自動緩和しない。
- [ ] mainは各満期3spotsを一括で解き、ladderの全段と個別gateを保存する。採用候補Sj自身を起点に時間・分散・パネル点数・cutoff・chi・領域・offsetの各感度を調べ、全価格差/K<=5e-6を確認する。S0のpilotだけでS1を認定しない。cold setupとwarm queryを分け、spectralだけ1 warmup+3測定、FDは1回測定。FDの速度分布や統計的優位は主張しない。準備・収束探索費用も別会計にする。
- [ ] 価格誤差vs費用、境界、個別refinement/chiの3図を描いて目視する。境界比較mask・失敗件数・誤差の単位・探索費用を表示する。
- [ ] 保存は最終価格・境界・設定・hash・検算要約だけ。`du -sh <run-root>` とraw byte数を記録。中間伝播/全FD面を残さず、小artifactから再計算してhash/semanticを照合する。
- [ ] pytestには小さいfixtureだけを置き、DSINC単体suiteは60秒を目標にする。フル格子の収束・文献照合・費用検証はbudget付きrunnerで行う。Run局所suiteと `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests`（BLAS/OpenMP 1 thread）。ruff/formatは追加変更した自作Pythonのみでupstream/は除外。MODEL_INDEX/docstring guardを含める。既存由来の失敗とする前に基点比較する。本編の図全面再受入は行わない。
- [ ] fresh独立reviewを受け、重大/重要指摘を修正して再検証する。READMEへ達成/未達、全6件の結果、費用、採否、未検証範囲を記し、ROADMAPを証拠に整合させる。公開、push、deployはこの計画では承認されていない。

## 実装前レビューと次の判断

このプランと設計をOpusに渡し、数学の符号・境界選択・独立参照・許容差・メモリ見積もり・範囲の過不足をレビューする。指摘は証拠と突合して文書へ反映し、再レビュー結果とレビュー対象hashを記録する。

2026-10-25の後続指示「進めて」によりローカル実装は承認済み。公開・push・mergeの承認には含めない。
