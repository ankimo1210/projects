# RB-F04 Heston・local volatility比較 Implementation Plan

> For agentic workers: superpowers:executing-plansを使い、独立部品はsubagentへ分担する。

Goal: 同じバニラ面へ数値誤差内で適合したHestonとlocal volatilityについて、月次Asianと二時点分布の差を測る。
Architecture: torch-free private面・経路計算、研究用独立PDE/積分、固定pilot→protocol freeze→主比較、保存配列checkerと3図。
Tech Stack: 既存numpy/scipy、CPU、既存uv環境。依存/公開APIは変更しない。
Spec: ../../prep/design/RB-F04_DESIGN.md

## 前提・契約

- F05離散v1はe803e00bでmain統合・push、独立採否済み。
- D1-preflightは過去に本編受入で完了。今回変更するのはprivate研究部品で、既存CF/COS/Asian/台帳/教材は変更しない。実装前に既存依存・保管庫の指紋と適用範囲を確認する。
- 候補Heston: S0=100,r=.03,q=0,v0=.04,kappa=2,theta=.04,xi=.3,rho=-.7。Feller .16>.09。固定パラメータ、較正性能は主張しない。
- 満期1年、Asian strike100、観測{i/12,i=1,...,12}、時点0を平均へ含めず満期払。fine/coarseの内部stepを観測平均に含めない。
- 理論の単一時点marginalと数値quote再価格の確認を区別する。全部の価格面一致を有限test群のPASSから主張しない。
- density/local varianceのclip、面外pathの除外、負variance状態の隠蔽は禁止。明示したwing/early-time拡張と訪問数、full-truncationの負variance数を保存する。

## Review Focus

1. 短期/wingのFourier打切りと次数を別比較。低密度や負値は未支持とする。
2. t0はS0のv0だけが定義された初期状態。全spotへ同じ初期local volという理論を置かない。
3. 配当/固定strike/固定月次観測を両モデルで一致させる。
4. coarse/fineはfine Brownianの和で結合し、各modelのbiasとmodel差のpaired SEを区別する。
5. 条件付きbin確率は各model固有の分母を用い、比のinfluence functionからpaired SEを求める。低件数は未支持。

## Task 1: Heston面とlocal variance格子

Create hullkit/src/hullkit/_heston_local_surface.py、tests/test_heston_local_surface.py。
Interfaces:
- HestonParameters(spot,rate,dividend_yield,v0,kappa,theta,xi,rho)
- fourier_surface(strikes,T,parameters,order=...,max_frequency=...,density_floor=...) -> price,ck,ckk,ct,density,weighted_density,local_variance,supported。
- LocalVarianceGrid(times,z_nodes,values,parameters).evaluate(t,spots) -> variance/status。
- 格子zはlog(S/S0)からdriftを引き、expected integrated varianceのsqrtで標準化する。t/zの線形補間、明示したconstant-edge wing、最小time proxyのflags。
- CFのRiccati時間微分からE[v_T exp(iu log-return)]を得る。Dupire価格微分の値とconditional varianceの比を照合。

- [x] 解析GBM/決定論的variance極限と、既存COS価格・CFの独立比較testを先に書く。
- [x] 未存在moduleでRED、面/格子を実装、pytest.approxでGREEN。
- [x] CT/CK/CKKを2幅の差分で検算し、次数/頻度上限・低密度・t0/wing/不正gridのtestを通す。
- [x] MODEL_INDEX登録と対象ruffを実行。commitはrootが依存module登録と一緒に行う。

## Task 2: 固定月次・共通乱数の経路

Create hullkit/src/hullkit/_model_dynamics.py、tests/test_model_dynamics.py。
Interfaces:
- aggregate_normals(z[N,steps,2],factor) -> coarse standardized normals。
- heston_monthly(parameters,z,expiry=1) -> observations[N,13],negative_variance_counts,failures。
- local_monthly(parameters,surface,z,expiry=1) -> observations[N,13],status_counts,failures。
- 同じfirst shockでHeston stockとlocal volを結合。Heston variance shock=rho*z1+sqrt(1-rho²)*z2。
- full-truncation/log Euler、local log Euler。月次観測はstepsが12の倍数の時点だけ。失敗pathはNaNと理由を保持。

- [x] xi=0とconstant local volのGBMは同じBrownianで一致するtest、qのmartingale、13観測、aggregationのRED→GREEN。
- [x] 集約normalの粗細結合、negativevariance件数・未支持surfaceを保持するtestを通す。
- [x] 対象ruffを実行。rootがMODEL_INDEXと一緒にcommitする。

## Task 3: 独立PDE・価格積分

Create research/RB-F04/reference_methods.py、hullkit/tests/test_model_dynamics_reference.py。
Interfaces:
- pde_call(spot,strikes,T,variance,rate,q,space_nodes=...,time_steps=...,log_half_width=...) -> price/grid/status counts。
- variance(t,spots)はvariance/status dict。hullkitをimportしない。
- independent_heston_call(strikes,T,parameters,upper=...) -> own-CF Gil-Pelaez価格。
- calendar timeを使うbackward log-PDE、CN/Rannacher、call Dirichlet境界、space/time/domain refinements。

- [x] 独立Black式・time-dependent varianceでPDEをRED→GREEN、q/boundaryと不支持を検査する。
- [x] own-CF積分とCOS/Fourierを対照、上限250/500の差を保存する。
- [x] PDEの時間/空間倍増を独立に比較する。

## Task 4: 数値pilotとfreeze

Create research/RB-F04/protocol.json、pilot.py、pilot.json/npz、tests/test_model_dynamics_pilot.py。
候補surface: t_min1/4096→1、65 geom-times、z81。z範囲±4/±5/±6、time/space格子倍増、Fourier次数/上限を比較。
候補path: pilot8192、steps192/384/768、共通fine driver。主paths65536×3独立seedsはpilotで予算/精度を確認してから確定。
quotes: T.25/.5/.75/1、K80/90/100/110/120、別holdout K85/95/105/115,T1/3,2/3。
PDE spatial/time/domain、MC各modelのcoarse/fine、wing/early flags、Asiandifferenceを保存する。
- [x] pilotで数値・sampling誤差を分離し、候補設定の妥当性を独立レビューする。
- [x] 全主比較前に精度設定・t0/wing・model差識別基準・seed/bins/予算をfreezeする。
- [x] 精度不足は失敗/未識別と記録し、numerical precisionを上げてpilotを再検討する。別の簡単なmodelへ置換しない。

## Task 5: 主比較・保存checker・3図

Create build_reference.py、analytics.py、build_notebook.pyと対応test。
- [x] 独立3seedで固定protocolを実行。各seedの粗細経路、vanilla/Asianpayoffs、conditional/joint bin countsを保存する。
- [x] model差はpairedpayoff差のmean/SE。各modelの格子差・surface/grid/wing変化は別成分として残す。
- [x] Asian差が誤差予算を超えない場合「差を識別できず」と採否記録する。勝利を研究完了条件にしない。
- [x] checkerは保存配列から数値/件数/SE/採否を再計算し、freshは固定seedから再生成する。SHAはblob来歴だけ。
- [x] 20MB超は既存C/Fの両保管庫へ置き、各copyから復元する。
- [x] artifact-only3図: vanilla残差/面、二時点分布、Asian差と誤差内訳。実行・目視。
- [x] 対象test/ruff、索引guard、独立最終レビュー、関連suite/release、ROADMAP更新、main統合/push。

## 実装時の設計判断（2026-10-09）

- 行ごとのinclusive index支持境界を追加する。初期81点の±6格子では118セル/34行が未支持だった。包括pilotの97点±6格子では133セルが未支持となった。NaNを保持し、各bracketing rowの支持端を定数延長してから時間補間し、その訪問を明示する。これによりwing感度を比較できるが、域外真値の証明には使えない。
- joint cellのsampling SEは記述量。空/疎なcellのSE0を確率0の証明や全bin同時の信頼区間と解釈しない。条件付きratioは最低件数を満たす各modelの独自分母とpaired influenceで評価する。
- 初期診断は包括pilotへ統合した。pilot8,192 pathsの7面・Fourier/PDE/各model収束を独立review後、主実験前に129×161面・65,536×3seed・精度予算を固定した。主196,608 pathsではAsian差0.00367288/paired SE0.00438743が経験的閾値0.01153142を超えず、未識別とする。
