# Conditional Asian cache：原失敗を保った supported domain の調査

2026-10-10。read-only / ignored scratch。production source・DESIGN・公開API・依存・Gitは変更していない。
正式pilot、全Cartesian領域、教師精度、hS/hQ、NN mainの受入ではない。

## 結論

正式pilot前の最小revisionは、**日付ごとに固定した、全nodeが利用可能なCartesian subdomainへ従来not-a-knot tensor cubicを構築する方式**が最も小さい。
[0,24]の主claim threshold範囲、全原node・status・原N・全16blocks・失敗は原artifactへ保持し、外部queryは全Nを保持したunknownにする。
選んだboxに含めないnodeを「解決済み」としない。これは計算domainの局所化で、元teacher failureを除外した資格拡張ではない。

ただし、一つのboxでは支持domainが狭い。全state/threshold支持の約束にも、SE精度不足にも、悪条件callの解決にもならない。
pilotで最小の固定boxを選び、元18states / 全経路をそのまま照会してunknown数と元分母を報告する。精度gateは変更しない。
支持範囲を広げるため複数boxを使う場合、overlap / seamで価格面とGreeksが一意に決まる追加設計が必要。
安易にqueryごとに「近くのfinite 4点」を選んではいけない。

第二案として**幾何だけで決まる共有node jetsからのtensor Hermite**は有効。C1を保った局所cellに拡張できるが、
補間method・stencil・block SE・精度の再reviewが必要で、今回scratchの四点jet方式もlate local ATMをまだ支持できない。

## 1. 原因と actual 数値証拠

source `_dynamic_hedging_surfaces.py` の `build_asian_cache` はunknown nodeをNaNへ移し、
`evaluate_asian` はdateのCartesian表に1NaNでも `nonfinite_nodes`。
現在の `CubicSpline(axis, identity)` はglobal not-a-knot operatorなので、この拒否は現methodでは保守的に正しい。
遠方NaNをmaskして0として積を取る実装へ変えると、別の補間器になる。

- m1 / v=.04 / x=1 のanalytic lognormal fixtureで、x=24の遠方1nodeをNaNにするだけでATM価格照会がunknown / nonfinite_nodes。
- x=1.02のglobal basisのx24 price weightは−1.4478e−22、derivative weightは7.8345e−21。
  影響はこの例では極小だが数学的に0ではなく、「local stencilだけ参照した従来cubic」とは呼べない。
- 保存済みactual N1024の35教師primitiveを正式候補33thresholdへ再評価：
  all33readyは0/35。原selected queryが4点以上の連続ready区間に入るのは30/36。
  残りは既知underresolved5とfit unknown1。これはcurve単独の支持で、state/spot Cartesian全体の支持ではない。
- 格子生成ではsinh丸めによりx0が±1e−15、x24が24+1e−14になり得る。
  仕様は0/m/24を含むので、axis生成時にその3nodeを仕様値で直接構成する。
  教師・価格のclipや成功へのrepairとは別。original rounded scratch版も保存した。

### actual coarse Cartesian 2 dates

N1024、同じ保存済みcandidate teacher drivers、actual local field257×321 / T1.25。
H9state、local S9×ell5、33threshold、16IID blocks。t=.5と11/12で全108groups / 3564nodes。
原driver identity・global slice・全原node・unknown・raw primitiveを保存。各job最大393216 path steps、総24772608。

| date / model | ready raw nodes / original | all33ready groups | 原全cubic支持 | raw price boundsも満たすanchor box例 |
|---|---:|---:|---|---|
| .5 Heston |187/297|0/9|なし|v[1e−5,.5]、x[4.71967,6.72596]、9×15 nodes|
| .5 local |875/1485|0/45|なし|S[50,200]、ell[.25,4]、x[5.51553,6.51962]、9×5×10|
| 11/12 Heston |118/297|0/9|なし|v[.02,.5]、x[.829806,1.19380]、6×10|
| 11/12 local |591/1485|0/45|なし|S[50,200]、ell[.25,4]、x[.924075,1.05483]、9×5×5|

表のboxはscratchの最大node-volume候補。採用・freezeしていない。全axis4node以上、x=mとstate anchorが内部にある連続boxのみを調べた。
元S[50,200]／state支持／threshold[0,24]を改変したartifactではない。
late localにはCV finite-sample価格が負の23nodeを確認（rawのまま保持）。
たとえばS118.92 / ell.5 / x1.11676でf=−2.7870e−6、SE=5.9880e−6、primitive statusはready。
readyだけでは価格boundもGreek-readyも保証しない。
同nodeを0へclipせず、bound failを別のraw記録として残し、採用計算boxへの利用を止める。

## 2. 比較した3案

### A. 固定Cartesian subdomain + 従来cubic（推奨する最小revision）

各dateにfixed geometry の一つの完全finite boxをmanifestで保存。
cache本体にはfull axes / f / blocks / status / primitive / original_N をそのまま持たせ、
追加のevaluation domainとそのindexだけを持つ。query時に同じboxのnot-a-knot価格surfaceからf/fx/fs/fzを計算。
全16block curveにも同じfixed linear operatorを適用。

利点：

- 従来method、C2、same-price Greeks、local f_z を維持する。既存Torch/public API依存不要。
- 教師費用・原全node費用は全て計上する。計算box選択をNの削減や失敗解決として数えない。
- 全array保存を変えず、saved checkerでbox indexの再検査と数値再計算を追加できる。

限界：

- threshold domainが狭い。late Heston例はv<.02でunknown。
- box boundaryを跨ぐqueryはunknownで、linear x<=0 branchとの間に未評価gapを許す。
  支持域の各component内部でC1以上。gap越しの全domain C1や滑らかなextensionは主張しない。
- source price boundsとcurrent reference/SE/holding precisionは別gate。
- 元global cubicとの差は補間revision誤差として保存。far-tail削除なら小さいことがあるが一般保証はない。
- データからqueryごとにboxを選ぶことは禁止。
  pilotの別streamでgeometryと選択規則を固定し、mainに入る前にfreezeする。
  以後statusを見てboxを変えない。後のfresh教師にunknown nodeがあればpatch unavailableを記録する。
- raw fit roots / residual / original boundsを保持。call inversionの解をpatchへclipしない。
  唯一call rootが選んだAsian support外ならunknown / asian_outside_patch。
  dateごとの支持boundsの扱いを正式revisionに書き、全元rootsを消して「一意」を作らない。

### B. 共有node jetsの局所tensor Hermite（次候補）

各axisのnode iに、固定された4node polynomial derivative operator D_iを一度だけ定義する。
Dは幾何のみで決まり、finite nodeが足りないとき近傍探索・fallback stencilは使わない。
多次元jetはtensor D operatorsで求め、混合微分も同じ共有node値から作る。
各cellのcorner values / first + mixed jetsをtensor Hermiteの同じ価格式へ入れる。

- 隣接valid cellsは同じcorner jetsを共有するのでfaceを挟んで価格と全first derivativesが一致する。
- needed corner/stencil tensorの1nodeでもunknown/nonfinite/price-bound failなら、そのcellはunknown。
  不要な遠方nodeをrepairしない。原全node/失敗は保持。
- 2D Hestonはv/x、3D localはlogS/logell/x。local価格Deltaは必ずf_z項を含む。
- 同じlinear operatorを16block curvesへ適用してcross-node clustered covarianceを保つ。
- 今回の4node jetsではcell当たり一axis最多5元node、Hestonは25、localは最大125の依存元nodeがある。
  cell jetをprecomputeすればhot queryは4^d（2D16、3D64）coefficient演算に縮約可能。
  この演算数はwall benchmarkではない。cold jet生成、必要node照合、artifact保存、checker費用は別途実測する。

probe：

- 2D fixtureのshared faceでf / f_v / f_xの左右差は数値許容差内。
- 3D local fixtureはS・ell・xの3種類faceを検査し、価格＋全first derivativesの最大差3.5e−18。
- finite differenceとordinary surface derivativesも同じ表から照合。nodeのC2は保証しないので
  first derivativeのFD biasはO(h)になり得る。source Greek精度の根拠とは別の機械的一致。
- shared16blocksのmeanとmean-tableに対するoperatorが許容差で一致。
  covarianceはcross-componentsが非0。nodeごと独立SEを足す方式へ変えない。
- m1 deterministic-variance Blackで、H9/v=.04/x1：
  normalized f_vのoracle=.287882、従来cubic=.282151、4node Hermite=.298221。
  C1は数値精度の保証ではなく、Hermiteのstate Greek誤差がこの例では大きい。
- local frozen power-variance one-step analytic fixtureのS103/ell1.1：
  proper Delta=.0589714、f_z省略=.0594820、oracle=.0589625。
  f_z省略の差−.00051054。actual Heston-marginal local月次教師の精度達成ではない。
- actual coarsegrid anchorのgeometry-only jet dependenciesは .5両M / late Hで利用可能。
  late localはunknown3node（xindex19）に加えreadyだがprice-bound fail3nodeへ依存し、ATMでもunknown。
  したがってこのB案だけで現在の全失敗は解決しない。

必要な正式accuracy gate：

1. analytic polynomial / Black / nonlinear local chain ruleとprice FD。
2. 全axis faceのC1、mask holeとboundary、4+node nonuniform geometry。
3. same16block operator / full clustered covariance / original_N同一。
4. coarse/fine state/spot/xのsame-price hS/hQ、再較正bump、oracle、SDE refine。
5. 元18statesの失敗・費用・SE分母を保持。成功subsetで採否を作らない。
6. 新method identity・stencil indices・必要原node・jet係数・sourceを保存してsaved/fresh/CAS検査。

### C. rigorous tail boundで区間資格を付ける（今回は非推奨）

B=残future normalized stock sum>0、p>1なら、
f(x)=E[(B−x)+] <= E[B^p]/x^(p−1)、−f_x=P(B>x) <= E[B^p]/x^p。
p4 finite-moment確認は価格/threshold derivativeの上限に使えるが、state derivative / local f_z / quote-risk ratioの上限は別途必要。

- m1 GBM、x24、v.04、remaining1/12のp4 price boundは.0006196通貨、tail probability bound3.106e−6。
- m12 GBM、同x24のMinkowski p4 price boundは14.7622通貨で、.05の価格予算に役立たない。
- actual Heston CIR mgf定数やlocal bounded-wing定数が有限でもtightである保証はない。
- lower tailのlinear近似誤差にもsmall-B bound / negative moments等が別途必要。
- 価格上限だけを根拠にf=0、f_v=0、f_z=0を作るのは禁止。
- certified interval / risk誤差budgetを持つ別のqualified-tail treatmentを設計しない限りunknownのまま。

## 3. 避ける案

queryごと4node cubicを切り替える方式は、node上の価格が合ってもordinary first derivativeが跳ぶ。
smooth exp(.4x) / nonuniform 6nodes fixtureでprice jump0、first derivative jump−.00177211。
overlapで「近いpatch」を選ぶ場合も同じ問題がある。
NaNを0/nearest/linear-neighborへ置換する、localでHeston homogeneityを流用する、
tail失敗nodeや経路を削除する、元分母をready subsetへ変える、mainを見てdomainを広げる方式は採用しない。

## 4. 証跡・費用・未実施

- `task-5-cache-domain-probe.py/.json/.npz/.txt`：
  actual35教師の33threshold saved-only replay、analytic/Hermite/face/block/tail-bound probes。
- `task-5-cache-cartesian-probe.py/.json/.npz/.txt`：
  actual2date全108groups / 3564threshold nodes / raw primitives / all original statuses。
- `task-5-cache-cartesian-probe-run.json`：
  成功した子process全体 wall11.484s / CPU11.475s、import・全計算・serialization込み。
  finance engine内timerはwall10.570s / CPU10.570s、最終NPZ/JSON保存前まで。
- raw Cartesian expanded100757420 B、1chunk256MiB内。元global driversは保存preflight NPZから読む。
- 初回Cartesian runはJSONでNaN metadata serialization失敗。source/output/raw NPZを
  `task-5-cache-cartesian-probe-first-failure.*`へ保存。raw財務計算は実行済み。
  初回runの全process費用は未測定でunknown、成功runの費用だけを総費用と主張しない。
- 最初のHermite拡張scratchで変数名collisionによる出力失敗も `task-5-cache-domain-probe-first-extended-failure.txt`に保存。
- source/input SHAはprovenance。金融数値は許容差・手計算・同じprice式のFDで確認し、bit一致をgateにしていない。
- 未実施：full12dates、高N、独立actual Asian oracle、price/Greeks precision資格、Q drift、全経路P&L、
  cold/hot benchmark、production source、formalpilot/main/freeze、reviewed正式revision、Git。

実読一次資料：
- [SciPy CubicSpline](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.CubicSpline.html)：finite values、C2、not-a-knot。
- [SciPy CubicHermiteSpline](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.CubicHermiteSpline.html)：shared first derivativesによるC1。
  現venv SciPy1.17.1。webは現1.18 docsで、API実挙動はlocal probeで確認した。
- ローカル DESIGN §7.1/7.4/7.5、CONDITIONAL_FEASIBILITY §2/3/8、surfaces/conditional source/tests。
