# RB-F08 full pilot 独立レビュー

更新日: 2026-10-09。**判定: approved。候補条件・配分・capを変更せずfreeze可能。未解決Critical/Importantなし。**
対象source commitは `850c4d44a20ea190ae410155c75a1b4c9ec3ae50`。主結果は見ておらず、価格性能・速度採用・4図・F08研究完了を承認したものではない。

## 固定した証拠

- protocol: `1918739bcccd8a29cdef1cddfab29b5721df2058381273b3ed94c332839d95cd`
- source/dependency fingerprint: `d14e7b141275a6f988c309da1bedcfee579932addb910599ac0f2ee47660a004`
- pilot JSON canonical digest: `0efc23f768fe1c11a887ce595d8c9ec2b7fe70b66845973c60feeca44f416788`
- pilot typed arrays digest: `a6aabfbc80064f4e4c9a829ed52da08c34be6aa851061dc033df86ff398248e7`
- pilot NPZ SHA256: `4d50f5be5b41d7f86e5fc849b0c7dc97bd482f39c52d2e68c361e5e87b093be2`（5,071,444 bytes、allow_pickle=False）
- final seed typed digest: `e3c264ebc4fb93b7c82e6ba3464243a04d4881981cab23ce698acbbadcebdb16`
- 全条件・全配分・固定betaの承認内容は [pilot_review.json](pilot_review.json) にexact copyした。レビューは実装者と独立したagentによる。初回指示の通りfull pilot完了通知前はソース読解だけを行い、以後に数値検査した。

## 全pilotの独立再計算

3 streams × 16,384 paths × 9 levels、Euler全216 block/442,368 pathsと独立exact/CV全24 block/49,152 pathsを確認した。hullkit再生・moments・pilot merge関数を期待式へ使わず、自前のEuler乗算recurrence、隣接normal和/sqrt(2)、Brownian終端のexact式から**全blockを再生成**した。平均・M2・cross M2・負state/path・元分母・operation countが一致した。最大絶対差はmean `1.95e-14`、M2 `1.16e-9`、cross M2 `8.73e-10`（相対1e-10・絶対1e-10以内）。

poolは `mean=sum(n_b mean_b)/sum(n_b)` と `M2=sum(M2_b+n_b(mean_b-mean)^2)` を使い、paired covarianceも同様に再計算した。各levelのn=49,152を使ったSE/df49,151、`abs(mean(Euler-exact))+t(.995,df)*SE` がJSONと一致した。Euler price単独SEをbias SEへ流用していない。

| level | 元n | Var(Y) | paired bias mean | paired bias SE | 99%経験的bound | 負path |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 49152 | 187.024047 | -0.00286664915 | 0.00520507774 | 0.0162745616 | 0 |
| 1 | 49152 | 0.631693693 | -0.00145153093 | 0.00370313193 | 0.0109905371 | 0 |
| 2 | 49152 | 0.325673959 | 0.00425871784 | 0.00265021889 | 0.0110854944 | 0 |
| 3 | 49152 | 0.168792236 | -0.00220783025 | 0.00187325015 | 0.00703319027 | 0 |
| 4 | 49152 | 0.0856633839 | 0.00239346411 | 0.00131829706 | 0.00578930418 | 0 |
| 5 | 49152 | 0.0441853965 | -0.000586233766 | 0.000939466063 | 0.00300623196 | 0 |
| 6 | 49152 | 0.0216623933 | -0.000368441891 | 0.000664411532 | 0.00207991905 | 0 |
| 7 | 49152 | 0.0108961339 | -0.000152005404 | 0.000473228998 | 0.00137100986 | 0 |
| 8 | 49152 | 0.00544779994 | -0.000438799254 | 0.000334557875 | 0.0013005967 | 0 |

全元分母を維持し、fine/coarse state分母はそれぞれn×M_l/n×M_l/2（level0 coarseは0）。負状態0はこの観測の結果で、真の確率0という承認ではない。非finiteを除去していない。差分平均のsign変更を保持し、連続3levelの3SE信号条件を満たさないため**alpha unresolved**を承認した。隣接差分varianceのbetaは診断であり、理論計算量改善を宣言しない。

## L・N・capの採用

候補L=2..8を全保持し、全epsilonで最小合格L=2。bound `0.01108549443571483` は最小bias target `.1/sqrt(2)=.07071067811865477` にも合格する。negative率は0、variance floor使用levelはなし。

isolated median C、pilot V、target=epsilon²/2から
`N_l=max(32,ceil(sqrt(V_l/C_l)*sum(sqrt(V_j C_j))/target))`
を自前で再計算した。plain/exact/CVも各pilot variance/targetのceilと一致。step proxy配分は診断として再計算し、主配分へ選び直していない。

| epsilon | L | MLMC N_0..N_L | plain Euler N | exact plain N | fixed CV N | predicted sampling variance | MLMC updates/run |
|---|---:|---|---:|---:|---:|---:|---:|
| 0.40 | 2 | [2670, 118, 71] | 2403 | 2533 | 425 | 0.07998675322 | 13800 |
| 0.20 | 2 | [10680, 472, 284] | 9611 | 10131 | 1699 | 0.01999668831 | 55200 |
| 0.10 | 2 | [42720, 1888, 1133] | 38442 | 40521 | 6793 | 0.004999931171 | 220728 |

全12 method/epsilon cellがready、未支持budget cell0。最大MLMC paths/runは `sum([42720,1888,1133])=45741` でpath cap2,000,000以下、最大MLMC updates220,728とplain Euler615,072はstep cap100,000,000以下。候補capを維持する予算余裕があり、主観測を用いたcap変更・不利なcell削除を認めない。sampling推定はpilot条件付きであり、mainの実測RMSE達成を保証しない。

## CV・clip・費用

独立exact/control pilotよりVar(payoff)=202.6007027513441、Var(control)=412.75194433445006、Cov=263.82817902724497、
`beta=0.6391930617132764`、fixed-beta Var(CV)=33.963561232680945を再計算した。controlはdiscounted S_T、期待値はS0 exp(-qT)=100。sourceのq drift/期待値を確認し、基礎レビューのq=.02独立期待値98.01986733067554も維持する。betaはmainでfitしない。

clip専用seed3739489220・power10の全1,024 uniforms/payoffsを自前Sobol生成と終端式で再生した。K80/100/120の同一uniform比較はclipされた点0・endpoint0でsample差0。一方、endpoint massを含むz領域の独立quad積分ではpublic−private真値差は各 `約−1.08307e-9`。観測差0をclip真値同一と呼ばない。

329 expense_idは一意。全Euler candidate9levelsの216 blockをMLMC/plain双方の必要pilot費用に保持し、exact/control24 blockをexact plain/CVに対応させた。calibrationは9levels×(warmup1+measured7)=72観測、各4096pair。medianはwarmupを除外し、warmupを含む全秒数を研究費用へ算入する。14 allocation項目、RNG/engine/summary、diagnostic exact/control費用区分と元の整数operation countを確認した。

保存measured subtotalは21.7376072909683秒（pilot2.18197263777256、calibration1.6367423553019762、allocation.004019985964987427、setup8.361806567991152、validation9.526336593960878、clip.026729149976745248）。共有費用は研究総費用ではunique IDで一度だけ数える。cold/amortizedのmethod別選択も確認した。freeze費用はpendingのまま別receipt、fresh/serialization等の研究全体費用も最終会計へ残す。

## seed・主roster・freeze

全181,729 seedを候補から再生成し、typed ledgerと全fieldが一致、物理seed全一意。pilot31/main9,216/coverage172,032/fresh372/timing72/method_order3/bootstrap3を確認した。2衝突のraw/generated/retry/spawn auditは保存値と一致。pilot/timingの全実使用seed、mainのlevel0..8予約、coverageの全18cell/512 outer/R8,16,32/power8,10を維持する。未使用fine slotはmainで別seedに置き換えない。

全条件を承認JSONへbindingしたうえで、**実numerical checkerを使うfreeze_protocolをin-memoryだけで実行しPASS**。candidateと保存protocolは変更していない。実freeze・freeze費用receipt保存とmain実行はrootが行う。

## 記録上の制限

pilot時のBLAS backend直接記録はなかった。[pilot_backend_review.json](pilot_backend_review.json) は同一source/Python3.12.3/NumPy2.4.6/SciPy1.17.1のレビュー時捕捉で、原計時の直接観測を置き換えない。UTC `2026-10-09T05:14:27.621703+00:00`、semantic digest `9b20c67b5d77ada3e76f5bfcdd28e56c214630fbd4cbb254d7ba634e5a84bb19`、file SHA256 `116af6ff4c8b9e070c53d22ee08963b92900839e0270623a650f59f46d989fbe`。runtimeはOpenBLAS0.3.31.188.0/pthreads/Haswell、実1thread。rootのmain直前preflightでも同一runtime確認が報告された。

finite pilotの99% t boundは経験的診断であり、保証付き停止定理ではない。RQMC Studentは独立scramble Rを標本単位とする近似区間、512反復のcoverage SEは95%付近で約.0096。m/Rの採用や速度改善はmain結果を用いて再レビューする。Heston Asianは後続revisionのまま。保存JSONフラグ・SHAだけを金融検証の根拠にしていない。
