# Prefreeze teacher precision diagnostic (saved N1024)

## 判定

現行β=1教師の精度確定を進める条件は満たさない。原36 slotsのqualificationはunknown、元N1024測定と証跡は不変。追加N・正式pilot・freeze・ソース変更は行っていない。

- 原36 slots = 実行35 + Heston fitunknown未実行1。30 ready + underresolved5。
- N65536のSEをN1024のSE/8で参考外挿すると、ready30中24 slotsが価格/hS/hQの3閾値内。Heston hS5件、hQ1件は閾値外。
- 外挿は同じ推定量・有限分散・平方根収束を仮定する参考値。N65536実行、Greek moment保証、SE推定自体の不確かさ、oracle/bias確認を含まない。
- 既存productionはHeston同次式を使用。直接教師微分とproduction tensor cubic微分は別の推定量であり、この外挿でproduction精度を認定/否定しない。

## 全36 slots

価格SEは元CV推定器のIID SE、hS/hQは同じ16block covarianceからのSE。予測は各1/8。

| slot | t | S | status | Ctheta | N1024 SE: price / hS / hQ | N65536参考: price / hS / hQ |
|---|---:|---:|---|---:|---|---|
| state00.heston | 0 | 99.95 | ready | 41.7528 | 0.0852813 / 0.0311692 / 0.0347233 | 0.0106602 / 0.00389615 / 0.00434041 |
| state00.local | 0 | 99.95 | ready | 4.61829 | 0.0412134 / 0.00842722 / 0.00930276 | 0.00515168 / 0.0010534 / 0.00116284 |
| state01.heston | 0 | 100 | ready | 38.1135 | 0.0823702 / 0.0208898 / 0.0255279 | 0.0102963 / 0.00261123 / 0.00319099 |
| state01.local | 0 | 100 | ready | 4.19127 | 0.0486206 / 0.00965998 / 0.00952352 | 0.00607757 / 0.0012075 / 0.00119044 |
| state02.heston | 0 | 100.05 | ready | 32.8985 | 0.0868263 / 0.0174614 / 0.0210507 | 0.0108533 / 0.00218268 / 0.00263134 |
| state02.local | 0 | 100.05 | ready | 3.57856 | 0.0623645 / 0.0123385 / 0.0103108 | 0.00779557 / 0.00154231 / 0.00128885 |
| state03.heston | 0.0833333 | 80 | ready | 19.7879 | 0.0214982 / 0.00167444 / 0.028845 | 0.00268728 / 0.000209305 / 0.00360562 |
| state03.local | 0.0833333 | 80 | ready | 3.35859 | 0.0189628 / 0.00175449 / 0.0235461 | 0.00237034 / 0.000219311 / 0.00294327 |
| state04.heston | 0.0833333 | 100 | ready | 38.9898 | 0.0677652 / 0.0153872 / 0.0203905 | 0.00847065 / 0.0019234 / 0.00254881 |
| state04.local | 0.0833333 | 100 | ready | 4.05281 | 0.0402187 / 0.0104686 / 0.00711554 | 0.00502734 / 0.00130857 / 0.000889443 |
| state05.heston | 0.0833333 | 120 | ready | 25.2481 | 0.0958202 / 0.0238185 / 0.0270522 | 0.0119775 / 0.00297731 / 0.00338152 |
| state05.local | 0.0833333 | 120 | ready | 1.98809 | 0.0285591 / 0.0122208 / 0.0120823 | 0.00356989 / 0.0015276 / 0.00151029 |
| state06.heston | 0.25 | 80 | ready | 16.4863 | 0.0109277 / 0.00108928 / 0.0411479 | 0.00136596 / 0.000136159 / 0.00514348 |
| state06.local | 0.25 | 80 | ready | 2.50784 | 0.006632 / 0.000515405 / 0.0149326 | 0.000829 / 6.44256e-05 / 0.00186657 |
| state07.heston | 0.25 | 100 | ready | 40.7248 | 0.0472812 / 0.015795 / 0.0198371 | 0.00591015 / 0.00197438 / 0.00247964 |
| state07.local | 0.25 | 100 | ready | 3.77059 | 0.0229786 / 0.00718787 / 0.00628515 | 0.00287233 / 0.000898484 / 0.000785644 |
| state08.heston | 0.25 | 120 | ready | 25.1827 | 0.0676701 / 0.032804 / 0.0353124 | 0.00845876 / 0.0041005 / 0.00441405 |
| state08.local | 0.25 | 120 | ready | 1.76421 | 0.0197268 / 0.0091298 / 0.0072085 | 0.00246585 / 0.00114123 / 0.000901063 |
| state09.heston | 0.5 | 80 | unknown_underresolved | 9.53019 | 1.0305e-18 / 1.3997e-20 / 0 | 1.28812e-19 / 1.74962e-21 / 0 |
| state09.local | 0.5 | 80 | unknown_underresolved | 1.25884 | 3.66097e-19 / 3.49925e-21 / 8.95807e-19 | 4.57621e-20 / 4.37406e-22 / 1.11976e-19 |
| state10.heston | 0.5 | 100 | ready | 42.9526 | 0.0211937 / 0.00481979 / 0.00720552 | 0.00264921 / 0.000602473 / 0.00090069 |
| state10.local | 0.5 | 100 | ready | 3.29988 | 0.00969262 / 0.00258202 / 0.00303592 | 0.00121158 / 0.000322753 / 0.00037949 |
| state11.heston | 0.5 | 120 | ready | 24.1201 | 0.0322225 / 0.0131294 / 0.0138233 | 0.00402781 / 0.00164118 / 0.00172791 |
| state11.local | 0.5 | 120 | ready | 1.42899 | 0.0116643 / 0.00648097 / 0.00546642 | 0.00145804 / 0.000810121 / 0.000683303 |
| state12.heston | 0.75 | 80 | unknown_underresolved | 2.5085 | 5.72027e-21 / 0 / 0 | 7.15033e-22 / 0 / 0 |
| state12.local | 0.75 | 80 | unknown_underresolved | 0.305929 | 1.3771e-21 / 0 / 2.7994e-20 | 1.72138e-22 / 0 / 3.49925e-21 |
| state13.heston | 0.75 | 100 | ready | 43.5563 | 0.00810197 / 0.00150361 / 0.00194649 | 0.00101275 / 0.000187951 / 0.000243311 |
| state13.local | 0.75 | 100 | ready | 2.72244 | 0.00279798 / 0.000493282 / 0.000882998 | 0.000349747 / 6.16603e-05 / 0.000110375 |
| state14.heston | 0.75 | 120 | ready | 20.827 | 0.0114734 / 0.00465618 / 0.00463879 | 0.00143417 / 0.000582022 / 0.000579849 |
| state14.local | 0.75 | 120 | ready | 1.03957 | 0.00457728 / 0.00235564 / 0.00207877 | 0.000572159 / 0.000294456 / 0.000259847 |
| state15.heston | 0.916667 | 80 | fitunknown: ill_conditioned | — | — | — |
| state15.local | 0.916667 | 80 | unknown_underresolved | 0.0472235 | 3.49137e-25 / 1.33486e-26 / 1.64027e-22 | 4.36422e-26 / 1.66857e-27 / 2.05034e-23 |
| state16.heston | 0.916667 | 100 | ready | 41.4993 | 0.00147202 / 0.000288457 / 0.000146504 | 0.000184003 / 3.60572e-05 / 1.8313e-05 |
| state16.local | 0.916667 | 100 | ready | 2.23471 | 0.000555888 / 0.00010264 / 0.000211603 | 6.9486e-05 / 1.283e-05 / 2.64504e-05 |
| state17.heston | 0.916667 | 120 | ready | 16.188 | 0.0023234 / 0.00175673 / 0.00170279 | 0.000290425 / 0.000219592 / 0.000212848 |
| state17.local | 0.916667 | 120 | ready | 0.713874 | 0.00121306 / 0.00100133 / 0.000943905 | 0.000151632 / 0.000125167 / 0.000117988 |

## varianceの内訳

共有16blockで Var(hS)=Var(VS)+CS²Var(hQ)−2CS Cov(VS,hQ) を再計算。割合は相殺を含み負/100%超になり得る。

| 状態 | VS項 | CS²Var(hQ)項 | 共分散項 | 意味 |
|---|---:|---:|---:|---|
| state08.heston | 1.30% | 85.94% | 12.76% | worst hS。state/quote Greek側が支配 |
| state05.heston | 4.26% | 94.83% | 0.91% | 最大価格SE。hSもstate側が支配 |
| state06.heston | 1411.68% | 1956.48% | -3268.16% | worst hQ。hSは共有相殺で小さい |
| state02.local | 51.04% | 18.85% | 30.11% | local最大価格/hS SE。VS/state/負相関の寄与 |
| state03.local | 225.26% | 220.66% | -345.92% | local最大hQ SE。hSの相殺を独立SE合成で壊さない |

- state08.H: Vtheta CE blockSE2.00467、aux1.40216、CV0.889261。Ctheta25.1827は極小ではないがhQ SE0.0353124 → hS SE0.0328040となる。
- state06.H: raw正値1/1024、CE正値6/1024。Vtheta varianceはCE15.2%、aux91.1%、共分散−6.2%。固定β1補助がrare-tailでnoiseを増やす。
- state06.H CE-only(固定β0)は価格SE0.000563757 / hQ blockSE0.0160225、元β1は0.0109277 / 0.0411479。別推定量の診断で、tail精度/採用認定ではない。
- β1 CV価格が負となるstate06.H(-0.00655327)もそのまま保存。価格/個票をclipしない。

## Heston同次式の独立確認

\[
 V=DSf(x)/12,\quad x=(1200-A)/S,\quad V_S=D(f-xf_x)/12.
\]

固定v・A・calendar・同一driverで正規化primitiveとaux分散はSに依存しない。別agentの式チェックも条件を確認。条件付き和Y=b+c exp(mu+sigma Z)のtruncated first momentを独立式で計算：

\[
 E[Y1_{Y>x}]=c e^{\mu+\sigma^2/2}\Phi(d_1)+b\Phi(d_2),\quad
 d_2=(\log c+\mu-\log(x-b))/\sigma,\quad d_1=d_2+\sigma.
\]

linear/deterministic枝は別処理。model CE、aux CE、既知aux平均のmomentを同じβ1で合成した解析VSを、保存f−xfxと標本/blockごとに許容誤差で照合PASS。spot±.02のHeston正規化primitive不変も照合。localへの流用なし。

state08.Hで解析VS−CRN VSのmean7.24e-7（差blockSE1.28e-6）。hS blockSEは0.03280398→0.03280425で改善なし。価格/価格SEも不変。式はspot差分bias/costを除く参照になるがstate Greek noiseを解決しない。

既存 `_dynamic_hedging_surfaces.py:306` は既に同次式を実装している。production改修候補は式追加ではなく、f_x/state微分の補間/教師精度。

## underresolution / IFT分母

全5 underresolved slotsはraw payoff0/1024。state09.H/L、state12.H/LはCEも全0。state15.LはCE正値191個でもmax8.61e-81、aux max1.47e-48に対しknown aux meanが大きく、CV全標本が浮動小数点で同値になる。

CVは事実上known auxiliary expectationだけの値となる。小SEはモデルのrare-tail再現を意味しない。既知auxは別GBMの期待値でHeston/local Asian価格やtail boundの代用にできない。

- state15.L: Ctheta0.0472235、1/|Ctheta|21.1759。fit condition0.211759が元gate内でも、未測定分母誤差とrare numeratorでhQを認定できない。
- state15.H: saved fit condition0.807825>0.25でunknown/ill_conditioned。state/CS/Ctheta未取得。latent v=.02で救済しない。
- deterministic denominator誤差はMC SEと別に伝播する。良好なfit residualだけでCthetaを認定しない。

## grid境界 / 最小revision案

`build_asian_cache` はunknown labelをNaN化(401–405行)、`evaluate_asian` はexact dateのCartesian全体にNaN1個でも `nonfinite_nodes` (515–517行)。遠いpositive-threshold tailのunknownがATM照会まで止める構造。実full Cartesian cacheは今回未実行。

1. **現行operatorの限定probeを先に**：worst Heston state00/01/02/05/08とtail state06について、同original driver/blockで状態9→13nodes、threshold33→65nodesを必要なdateだけ測る。production固定tensor cubicのVS/Vtheta/IFT SEと今回の直接微分を比較し、noise/補間biasを分ける。全12dates×全N直積は先に回さない。
2. **有効補間domainを決める**：未知tailを0や既知auxで補完せず、資格ある連続patchだけを同じ価格関数/C1導関数/block operatorで評価、patch外はunknownを保つ案。現行global not-a-knot/range[0,24]の変更でprefreeze revisionが必要。missing-nodeを単に無視する局所多項式はC1/共有operator/誤差gate確認なしに採用しない。
3. **β1を保つ分散選択案でも限定効果**：aux定数分散をfixing-weighted E[v]へ変える独立probeを保存標本で実施。重みはremaining_fixing_count²。aux prefix/loadingを線形変換、両state bumpと既知期待値chainを再計算。state08.H hS N65536参考SE0.0041005→0.0035287で未達。ready H15中3条件参考通過9→10、hQ失敗がstate06からstate03へ移る。単独解として採用できない。
4. **必要なら小さい推定量revisionを別案として評価**：rare-tailで補助が悪化する領域を独立pilotで確認し、事前固定CE-only/β1 branch、またはstate-Greekに強い補助を比較。DESIGN §7.3はβ最適化/QMCをv1対象外とするため最適βの事後fit/無断切替は未実施。価格/Greeksの同じ推定量、stencil/chain、未解決tail/分母/SE uncertaintyを維持する。

## 証跡・未測定

- `task-5-teacher-prefreeze-diagnostic.{py,json,npz,txt}`: 全36 slots、35計算の価格/Greeks/共分散分解/N外挿/Heston独立式。derived raw3.42MB、saved計算約0.50秒。
- `task-5-teacher-prefreeze-control-probe.{py,json,npz,txt}`: CE-only/fixing-weighted β1 auxの別案。derived raw2.13MB、saved計算約0.23秒。
- `task-5-teacher-prefreeze-homogeneity-independent.md`: 別agentの独立導出。
- source/input65bindingsと元preflight py/json/npz/txt全て不変。
- SDE格子、finite-state-bump bias、call denominator/spot Greek誤差、独立Asian oracle、production補間、SE推定の不確かさ、Greek moment条件は未測定/未認定。全qualification unknown。
