# RB-F06 SABR識別可能性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development task-by-task. Root owns Git; independent financial and review work may run in parallel on disjoint files.

**Goal:** 固定betaのHagan IV写像について、fitの良さ・parameter識別・holdout価格安定性を分離し、教材としての採否を独立検算から記録する。
**Architecture:** privateの較正/感応度診断と、研究用の固定条件・保存結果・artifact-only教材を分離する。pilotの費用/収束/差分を確認して条件を固定し、主918 fitとprofileを全slot保存する。
**Tech Stack:** existing NumPy/SciPy/Matplotlib/nbformat/nbclient、CPU単一thread、Python3.12.3/NumPy2.4.6/SciPy1.17.1。
**Spec:** ../../prep/design/RB-F06_DESIGN.md。

## Global Constraints

- scopeはfixed beta=.5のHagan近似写像。exact SABR/dynamics/exotic・Heston・SBI・public API変更・production依存追加を含めない。
- 実装はhullkit private、研究はresearch/RB-F06。公開sabr.pyは変更しない。torch不要。
- notebookはartifact-only。主financial sourceと条件を本比較前に固定する。
- 数値は許容誤差で比較し、全失敗/境界/元分母を保存する。fingerprintは出典/成果のbindにのみ使う。
- 本編306節と既存依存指紋69件の状態を変えない。全関連suiteは章末相当の最終gateで1回。
- 本人の研究完遂・main反映/pushの継続指示に従い、計画から実行まで進める。既存research worktreeを再利用。

## Review Focus

1. sparse 2x3 Jacobianは第三零特異値とright nullspaceを保持する。有限condition値でfull rankと扱わない。
2. nu=0境界とHaganの小z分岐で、finite difference/弱方向精度を確認する。小非零値を構造的非識別と断定しない。
3. 全start失敗・profile不足・基準より良いprofileはdataset全体の区間判定をunsupportedとし、unknownを非被覆に混ぜない。
4. profileはnuisance再最適化。参考chi-square線はpointwiseで、3D同時支持域・保証CI・価格包絡と呼ばない。
5. noisy quote/holdout/原価を主比較前に固定し、全start・profile再最適化・差分価格評価費用を保存する。

## 固定候補と一次文献

# RB-F06 小規模実施計画草案

2026-10-09／準備のみ。F08の最終統合後に新branchでpilot→条件固定→本比較を行う候補。正本設計・金融source・Gitは変更していない。

## 1. 問い・境界・既存資産

固定βのHagan lognormal IV写像から、合成quoteに対してα/ρ/νがどこまで決まり、未使用strikeのvanilla価格がどれだけ変わるかを調べる。SDEは原著(2.15)、近似IVは(2.17)、ATMは(2.18)。近似式への自己生成データfitは、その写像の逆問題を検証する。[Hagan et al. (2002), 著者公開原著](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf)

exact SABRの一般価格・動学・exoticの受入は範囲外。Hagan式は漸近近似であり、低strikeで裁定を生じる場合がある。arbitrage-freeの一次元PDE版も原著要旨では同じ漸近精度とされる。[Hagan et al. (2014), 原著要旨](https://onlinelibrary.wiley.com/doi/abs/10.1002/wilm.10290)

確認済み資産：RB-F06_DESIGN.md、hullkit/sabr.py、test_sabr.py、test_stochastic_volatility_reference.py、MODEL_INDEX.md、既存Hagan原著抽出。公開calibrate_sabrは3quote以上・raw無重みresidual・ν下限1e-9で、最終3値だけを返す。研究用非公開runnerで診断と2quoteを扱い、公開APIは維持する。既存Hull式転記との一致は実装転記の検証で、独立exact SABR参照ではない。既存Euler SABR MCはforwardのzero吸収・時間離散誤差があるため、過去の成功を新条件の参照としない。

## 2. 凍結候補roster（小さな2真値×3quote群）

| 項目 | 候補 |
|---|---|
| 共通 | F=100、T=1年、β=.5、discount=1。a=α/F^(1−β)と定義 |
| 真値 | a=.20、ρ=−.30、ν=.40（通常）／.02（弱いvol-of-vol）。αはいずれも2 |
| full | x=log(K/F)=[−.20,−.10,−.01,0,.01,.10,.20]、7quote |
| ATM近傍 | x=[−.01,0,.01]、fullの3quote部分集合 |
| sparse | x=[−.10,.10]、fullの2quote部分集合。3parameterに対する不足を明示 |
| holdout | x=[−.15,−.05,.05,.15]（補間）／[−.25,.25]（外挿）。全fit/pilotから隔離 |
| noise | noiseless 1件＋known SD=.0005（5 vol bp）の独立Gaussian IV noiseを16反復 |
| seed | SeedSequence(2026100606)、spawn=(phase,truth,rep)、pilot phase=0／main phase=1。master7quoteのnoiseを生成し各群へ同じ成分をsubselect |
| 境界 | a∈[.05,.50]、ρ∈[−.95,.95]、ν∈[0,1.5]。ν=0境界を隠さない |
| starts | a∈{.12,.28}×ρ∈{−.60,.30}×ν∈{.08,.80}の8点＋(.20,0,.50)。真値startは入れない |

mainは6条件×17 dataset×9 starts＝918 fit。pilotは別seedの4反復で費用・収束・差分安定性だけ確認し、main noise/holdoutは見ない。noiseが非正/非finite IVを生んだouter slotは再drawやclipをせずinvalidとして元16分母に残す。恒等noiseは市場bid/askや相関構造を表すとの主張をしない。

別の解析fixtureだけβ=1、α=.20、ν=0、ρ∈{−.8,0,.8}、x∈{−.25,−.10,0,.10,.25}を使う。fixedβの本比較にβ探索を加えない。

## 3. 残差・scaled Jacobian・全失敗保存

研究runnerはscaled座標 u=(a/.20,ρ/.50,ν/.50)でbounded least_squares(method="trf", jac="3-point", loss="linear", x_scale=1)、ftol=xtol=gtol=1e-10、main max_nfev=400／profile nuisance max_nfev=250を候補にする。研究費用はresidual実呼出数とwall timeも数え、nfevだけで価格評価原価を代用しない。SciPyのcostは1/2 residual二乗和なので保存Q=2 costを明記する。[SciPy公式least_squares仕様](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)（本実装はlocal SciPy 1.17.1を固定、オンライン現行manualは1.18.0）

Q=Σ[(IV_H(K;θ)−y_K)/s_ref]^2、s_ref=.0005をnoiselessでも固定。noiselessでSD=0を割らず、このQを尤度とは呼ばない。noisyでは既知σ=s_refのGaussian尤度に対応。ATM/sparseで残差自由度からnoiseを推定しない。

J=∂IV/∂(α,ρ,ν)、D=diag(2,.50,.50)、W=I/.0005、J_scaled=W J D（無次元）。singular values・rank・右特異vector・弱方向のholdout price変化を保存する。2×3のcompact SVDは2値しか返さないため、第三零特異値と3次元のright null directionを明示する。

独立差分確認はscaled uでh={1e-4,3e-5,1e-5}、内部点は中央差分、境界は片側差分。相対J変化1e-5以下を候補gate、rank数値閾値1e-8·s_maxを候補とする。ただし小さい非零値を「構造的非識別」と断定しない。

各startに初期/最終θ、全IV/価格residual、Q、raw/scaled J、success/status/message、active_mask、optimality、nfev/njev/実呼出数/time、例外/非finiteを保存。全件の元slot数は維持。best convergedとbest finite（失敗を含む）を別表示し、全start失敗はunsupported。境界はactive_maskとscaled境界距離≤1e-6で記録。solver successは大域最適性や識別の証明ではない。

## 4. 真のprofile・区間と下流評価

profile_i(c)=min_{θ_-i} Q(c,θ_-i)。θ_-iを真値や推定値に固定するsliceとは別表示する。[Raue et al. (2009), §4 Eq.(10)、原著PDF](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)

費用を抑えるため、全curveは各条件のnoisy rep=0（事前指定）の3parameterのみ、noiselessはν profileのみ。a grid=[.05,.08,.10,.12,.15,.18,.20,.22,.25,.30,.35,.40,.50]、ρ grid=linspace(−.95,.95,17)＋真値、ν grid=[0,.002,.005,.01,.02,.04,.08,.12,.20,.30,.40,.60,.80,1,1.2,1.5]。各curveにbest値を追加。各点nuisanceは4固定start（残る2parameterの各low/high組合せ）で再最適化し、全4失敗も保持する。閾値crossingだけ最大6回/側の二分細分化。全dataset×密gridのsweepは行わない。

noisyではΔQ=3.841458820694124（χ²_1の.95）を参考支持域として表示。noiselessの同等fitはmax|IV residual|≤1e-9、かつΔQ≤1e-6の数値基準を候補にする。noisyの同等fit集合は上の参考域を使い、全start解＋converged profile点のholdout価格範囲を示す。有限採取集合の価格範囲は、連続支持域全体の保証包絡ではない。

profileで閾値に達する前に探索boundへ着いた側は「境界により打切り／端点未確認」。有限boundを識別性や有限confidence intervalの根拠にしない。profileがunconstrained best Qより1e-6超低ければ最適化不足を記録し、その曲線の区間判定は未支持にする。

全16 noisy反復は各parameterの真値固定profile点だけ4startで解き、参考域が真値を含む件数/元16とWilson区間を出す（curve全体を再作成しない）。16回の率は記述的で、95%被覆の認定はしない。ν=0・非識別・少数quoteでは通常χ²近似の正確さは未確認で、Self–Liangの特定混合χ²も自動適用しない。[Self & Liang (1987), §1/§3, 原著](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf)

holdoutは同じHagan IV→独立Black call（undiscounted、価格/Fも併記）。IV max/RMSE、価格max/RMSE、parameterのscaled距離、同程度fit内の価格幅を並記。参考の実用線はIV 10bp／価格/F 2e-4（F100で.02）を候補とし、採用用途が未定なので普遍的合格値とはしない。parameter回復だけで採否を決めない。β変更によるexotic/hedge差や学習器は追加しない。

## 5. 独立参照・小さな準備結果・残る未知

β=1/ν=0ではSDEから F_T=F exp(−α²T/2+α√T Z)。ρが価格法則から消え、IVは全strikeでα。これは原著(2.15)/(2.17)からの解析的帰結。独立正規密度quadでmax(F_T−K,0)を積分し、独立Black式と突合する（候補価格atol=1e-10、IV flat atol=1e-12）。同じSABR関数を二重呼出するだけの参照にしない。β=.5/ν=0はρ消失の参照には使えるが、Haganがexact CEV価格に等しいとは扱わない。

ATM1quoteならJ rank≤1、sparse2quoteならrank≤2を線形代数の対照にする。profile≤対応slice、同じ入力のpublic calibrate_sabr（full noiselessのみ）と研究fitのresidualを照合する。public関数との一致だけでは独立optimizer/価格モデルの認定にならない。

準備時にtruth地点だけ差分計算済み（本fit/noise/profile実験は未実施）。上記W,Dで通常ν=.40のcond(J_scaled)はfull44.46／ATM15623.7、弱ν=.02はfull10740.8／ATM約3.82e6。sparseはいずれも3parameterでrank不足。差分step間の相対J変化は全6点で6.1e-9未満。β=1/ν=0/ρ3値のflat IVを15点で確認した。これをmain受入や一般識別性の証拠とはしない。

未知：固定β・ν>0での一般/有限strike集合の大域単射性、上記bounds内での全大域最小値、今回noise/境界での正確なLR分布、exact SABRとHaganの当該条件での近似誤差、market noise/用途別許容差。pilot後に費用・停止予算・上記候補を固定し、source/条件/noise全配列をfingerprintでbindしてからmainへ。失敗・未支持条件を隠さず説明できることを教材採用の条件とする。

成果はtyped JSON+NPZ、3図（profileとslice／scaled SVDと弱方向／noise反復とholdout価格幅）、独立reviewと費用記録。必要性が出ない限りHeston/SBI/exact SABR Monte Carloの大きな追加sweepは行わない。


## 草案からの確定調整（2026-10-09）

- profileまたはtruth固定点がbaseline Qより1e-6超低いdatasetは全parameter支持判定をunsupported。良い点を黙って基準へ差替えない。
- 真値含有率はincluded/excluded/unknownを元16分母で保存し、確定率とunknown込みの上限を併記。Wilsonはknown outcomesの記述的区間であり、unknownを非被覆に混ぜない。
- profileは1parameterのpointwise参考域。対応するholdout価格範囲はprofile訪問点/全startの有限集合として表示し、3D joint confidence envelopeを主張しない。
- 格子全隣接区間の閾値crossingを保持し、最大6回二分/区間・全curveで追加12点まで。全crossingを昇順で処理し、未細分のbracketは幅つきで保持。非連結の支持域は連結区間へ潰さない。bound到達を真の識別性と扱わない。
- 差分はscaled J全体に加え、full rankの最小特異値比、sparse null projection residualをstep間で比較。弱い方向が不安定ならその診断をunsupported。
- referenceは独立Hagan転記＋Black/正規密度積分極限を分けて記録し、前者をexact SABR参照と呼ばない。
- profile候補集合は草案grid＋best値、nuisance4固定starts。representative noisy rep0全3軸・noiseless nu軸・全noisy反復のtruth点。pilotは代表1条件の費用も測り、main roster/sourceを固定してから全実施。

## Task 1: private較正と線形代数・独立参照

**Files:** hullkit/src/hullkit/_sabr_identifiability.py、hullkit/tests/test_sabr_identifiability.py、research/RB-F06/reference_methods.py、hullkit/tests/test_sabr_identifiability_reference.py、MODEL_INDEX.md。
**Interfaces:** sabr_vols(F,T,beta,theta,strikes)、scaled_jacobian(F,T,beta,theta,strikes,h=3e-5,noise_scale=.0005)、fit_smile(F,T,beta,strikes,quotes,start,fixed=None,max_nfev=400,noise_scale=.0005)。
theta=(a,rho,nu)、a=alpha/F**(1-beta)。fit返却は初期/最終theta,IV/residual,Q,success/status/message,active_mask,optimality,nfev/njev/residual_calls,seconds,raw/scaled J,SVD。
- [x] RED: importはgetattrで未実装をassertし、beta1/nu0 flat、2x3 null方向、noisy/notfinite、max_nfev=1失敗保持、profile固定軸を検査する。
```python
assert np.linalg.norm(J @ diagnostic["right_vectors"][-1]) < 1e-8
assert diagnostic["singular_values"].shape == (3,)
assert fitted["q"] == pytest.approx(np.dot(fitted["scaled_residual"], fitted["scaled_residual"]))
```
- [x] GREEN: 3point TRF、bounded scaled座標、正方/不足quoteどちらもfit、SVD full_matrices=Trueで欠損零特異値を補う。境界は片側差分。
- [x] 独立Black/quadのflat極限、原著Hagan転記と元public参照の役割を分け、対象tests/ruffと索引guardを実行。
- [x] rootがTask1をcommitする。全suiteはTask4だけ。

## Task 2: protocol・pilot・主実験前固定

**Files:** research/RB-F06/protocol.json、protocol.py、pilot.json、pilot_review.json、build_reference.py、hullkit/tests/test_sabr_identifiability_research.py。
**Interfaces:** run_study(protocol,phase,output)、check_record(record,arrays,fresh=False)。JSONはmetadata/slot、NPZはnon-object数値。source_registryはsabr.py/private module/reference/runner/protocol/analyticsを含む。
- [ ] RED: fixed seedsにより全群が同じmaster noiseをsubselectすること、fixture slot/失敗保持とraw array改変でcheckerが落ちることを検査。
```python
assert np.allclose(atm_noise, full_noise[atm_indices])
assert result["attempted_slots"] == len(result["fits"])
```
- [ ] GREEN: noiseless＋別pilot4 noisy反復、全9starts、代表profileの費用・差分安定性を保存。holdout/main noiseは見ない。
- [ ] 独立pilotレビュー後にstarts/grid/seed/予算/許容差/全financial sourceを固定し、固定前の成果をmainへ昇格しない。
- [ ] rootが条件固定・ROADMAP状態をcommitする。

## Task 3: 918 main fits・profile・独立数値検算

**Files:** research/RB-F06/reference.json/.npz、analytics.py、fresh_check.json、cost.json、hullkit/tests/test_sabr_identifiability_analytics.py。
**Interfaces:** summarize(record,arrays)、mainは6x17x9 fit、profile全attemptとcostを別計上。
- [ ] RED: best finiteとbest converged、negative ΔQのdataset伝播、unknown分離、nonconnected支持格子とbound打切りを固定する。
```python
assert support["included"] + support["excluded"] + support["unknown"] == 16
assert bad_profile_dataset["support_status"] == "unsupported"
```
- [ ] GREEN: 主fitと固定profileを全slot保存。Q,scaled J,SVD,holdout価格,失敗/境界,元分母を保存値から再計算。
- [ ] freshは指定した通常full/弱ATM/sparseの独立3start再較正、profile truth固定点/quadを再検算し、主推定にpoolしない。独立reviewは別差分と別optimizer/profileを確認。
- [ ] source freezeを守り、原価・数値結果・参考域の制限を保存。rootが主成果をcommitする。

## Task 4: artifact-only教材・最終受入・main反映

**Files:** research/RB-F06/build_notebook.py、sabr_identifiability.ipynb、README.md、REVIEW.md/review.json、validation.json、ROADMAP.md、MODEL_INDEX.md。
- [ ] 3図：profileとslice、scaled SVD/弱方向、全noisy反復/holdout価格幅。失敗/unknown/boundの数も表示し、固定代表repを変更しない。
- [ ] notebook実行時のoptimizer/RNGをguardして保存成果だけで描画。nbformatと3図を実行/目視する。
- [ ] 20MB超の成果は既存CAS契約で両保存/独立復元・数値検査。20MB以下はGit管理。
- [ ] 関連3suiteを1回実行：pytest -q johnhull/hullkit/tests johnhull/report/tests deep_hedge_price/tests。変更Python ruff/formatとtracked releaseを実行。
- [ ] 独立最終レビューで全データ/原価/採否を照合。Critical/Important未解決を受入済みと扱わない。
- [ ] rootがmainへfast-forward/pushし、mainのrelease/保存数値checkerを確認。ROADMAPを更新し、次の研究を保持する。

Nu=0の解析Jacobian列をprivate診断に使う（publicの小z/log取消しを修正しない）。rho=0/nu=0のrank1と弱方向を独立検算する。main918、代表profile最大1200、noiseless profile408、truth固定1152、細分化1152の最大4830 solver callsを本前固定し、重複省略も元rosterとの対応を保持する。
