# M29 HW Q-state correction: caller / saved-artifact impact

日付2026-10-04。対象 /home/kazumasa/worktrees/m29/johnhull。
依頼は読み取り専用。リポジトリ/Gitは変更していない。
root が並行して実装している修正は本調査の変更ではない。

## 結論

documented stateをQ下のzero-mean OU xとして保持し、bond exponentへ−B c(t)を追加すると、
同じxを指定したfuture conditional bondの価格は正しく変わる。
一方、既存のJamshidianのrootは−c(t)だけ移動し、各strikeとtime0欧州swaption価格は数学的に不変。
ZCB option formulaとcalibration objectiveも数学的に不変。
独立root/erfc/直接Gaussian求積と凍結旧式/補正式の実関数比較で確認した。

保存vol26では浮動小数点root solverの丸めが変わり、hw_swaption_priceの3要素が約1e−16動く。
現行artifact gateはSHA256/array_equalなので保存NPZ/JSONとnotebookのdigest表示をrefreshする必要がある。
価格の数式や表示の意味が変わったわけではない。
さらにD1のstatic import closureはpackage initializerを含むため、
既受入28節すべてにhull_white.pyの変更が波及する。

## 1. Baselineとprobeの分離

旧版はWSLで以下のread-only Git読出しから凍結:
git show 88e03d3f:johnhull/hullkit/src/hullkit/hull_white.py
→ /tmp/m29-hw-main88e03d3f.py。

/tmp/m29-hw-caller-probe-20261004.py はこの旧ソースから2つのscratch moduleを作成:
hullkit._m29_old_88e03d3f、
hullkit._m29_corrected_copy。
後者は旧return expressionを1回だけPold(x+c)へ置換。
rootが修正したcurrent functionへ追加補正を掛けていない。
hullkit.hull_whiteのmonkeypatchもしていない。
PYTHONDONTWRITEBYTECODE=1で実行し、ソースへのpycache書込みを避けた。

独立oracleはproduction root/price関数を呼ばず、
scalar二分法、kernel積分によるq/c、独自linear-zero interpolationとDF、math.erfc、
rootで積分区間を分けたGaussian求積を用いた。
実API比較側は凍結旧ソース/補正scratchソースのbrentq/ndtr/calibrationを実行した。

保存artifact probeはroot修正後の実current sourceでvol26だけを/tmpへ生成した:
 /tmp/m29-hw-reference-probe/26_inflation_jgbi/reference/metrics.json
 /tmp/m29-hw-reference-probe/26_inflation_jgbi/reference/inflation_scenarios.npz
生成先はrepositoryではない。

## 2. 座標移動の証明

expiry E固定、a>0、sigma≥0、初期curve共通。
B_i=(1−exp[−a(U_i−E)])/a、
q(E)=sigma²(1−exp[−2aE])/(2a)、
c(E)=sigma²(1−exp[−aE])²/(2a²)。

旧bond:
Pold(E,U_i;y)=P0Ui/P0E exp[−B_i y−B_i²q/2]。

documented Q-stateを修正したbond:
Pnew(E,U_i;x)=P0Ui/P0E exp[−B_i(x+c(E))−B_i²q/2]
=Pold(E,U_i;x+c(E))。

positive cashflows C_i（既存HullWhiteSwaptionのvalidateが要求）に対し
ΣC_i Pold(E,U_i;y*)=1のunique rootがあれば、
x*=y*−c(E)が補正版のroot。
全maturityに同じc(E)なので
K_i,new=Pnew(E,U_i;x*)=Pold(E,U_i;y*)=K_i,old。
既存hw_zcb_optionは初期DFとB_i sqrt(q)を使うのでそのK_iへのpriceも同じ。
receiverはcalls、payerはputsのcashflow-weighted sumとして不変。

正しいQ^E分布はx_E~Normal(−c(E),q(E))。
y=x+c(E)はQ^E下でmean0になる。
したがって旧中心座標での欧州求積と、補正Q stateでの求積は同じ積分。
このcoordinationがあるため、旧Jamshidianのtime0 pricesは正しかった。
同じQ xへのconditional bondが誤っていたことと両立する。

同じxを固定する一般callerはPnew/Pold=exp(−B c)。
t=0、sigma=0、U=tでは補正がゼロ。
Q OU transition、hw_phi、initial curve、total bond-option volは変わらない。

## 3. 全johnhull runtime callers / 関連資産

rgでjohnhull内のPython/ipynb/JSON/Markdownを検索した。
source数値callerは下記。generated Bookは元notebookのsymlinkとして分類した。
新M29 tests/lessonの追加はrootによるconcurrent workなので、既存baselineとは別に記載する。

| 場所（現行パス、caller lineは変更されていない箇所） | 使用内容 | 修正影響 |
|---|---|---|
| hullkit/src/hullkit/hull_white.py:217 hw_jamshidian_swaption | root関数と各strikeでhw_discount_bondを使用。旧line209。 | root Q coordinateが−c移動。strikes/欧州価格は数学的に不変。brentq丸め差はあり得る。 |
| hullkit/src/hullkit/hull_white.py:257 calibrate_hw1f | Jamshidian price residualでleast_squares。旧line249。 | objective数学的に同じ。fitの最終bitに丸め差、repricing残差は同水準。 |
| hullkit/src/hullkit/hull_white.py:193 hw_zcb_option | DFとtotal volのみ。旧line185。 | hw_discount_bondを呼ばないので完全に不変。Table32.3 analytic pinの入力/式も不変。 |
| hullkit/src/hullkit/frontier_reference.py:2012–2029 volume26_reference | a=.10,sigma=.009固定。t=0,state=0のmodel DF、expiry1/2/3 receiver option ladder。 | DFはbit一致。swaption ladderは約1e−16のroundoff。vol26はcalibrate_hw1f自体を呼ばない。 |
| hullkit/tests/test_hull_white.py:28,75,106–108 | initial fit、Jamshidian vs direct forward求積、synthetic校正。 | initial fitは不変。求積のzero-mean y表現は正しくそのまま使える。校正許容差は十分小さいままで通る見込み。probeでsame inputsを確認。 |
| hullkit/tests/test_hull_pins_exotics_ir.py:163–187 | Table32.2 curveによるhw_zcb_option put、Table32.3 1.8093/1.809294。 | bond-option関数は変更なし。許容差拡大/印刷pin改変は不要。 |
| hullkit/tests/test_jarrow_yildirim.py:261–295 | Q nominal factors、t=1 bond maturing2、nominal bankで経路割引してmartingale検査。 | 同じQ stateを使う正しいcallerなのでbond path valuesをexp(−Bc)倍に修正する効果。テストは残す。旧SEがbiasを隠せるため新独立towerテストが必要だった。 |
| hullkit/src/hullkit/jarrow_yildirim.py:21,462–489 | HullWhiteParams/hw_b/hw_phiのみをimport。Q zero-mean nominal OUとshort-rate accounts。 | hw_discount_bondを呼ばない。JY path/analytic/forward-level reference自体は不変。 |
| hullkit/src/hullkit/__init__.py:17,69 | hull_white re-export/import。 | signatures/symbolは不変。ただしD1 source closure全体へのfingerprint波及あり。 |
| hullkit/tests/test_frontier_reference.py:556–575、scripts/frontier_acceptance.py:1773–1791 | vol26 initial curveとinflation identities。 | metricsは不変。bit再生成gateとは別のsemantic検査。 |
| report/tests/test_frontier_acceptance_tamper.py:249–251 | hw_model_discount_factorの改変検出。 | baseline DF不変、改変検出は維持。 |
| hullkit/tests/test_numeraire_hw_state.py | rootの新M29 RED→GREEN独立state/tower tests。 | root concurrent change。今回の調査が作成したファイルではない。 |

その他の参照:
- interest_rate_models/build_ir_models_notebook.py は独自inline HWモデル/MC/較正を持ち、
  hullkit.hull_whiteをimportしない。ir_models.ipynbもその保存出力なので、この関数の修正によるnumeric changeなし。
  MODEL_INDEX.md:87にもlegacy IR notebook does not import hullkitと明記されている。
- vol11 ir_options.ipynb のBlack APIsもhw_discount_bondを呼ばない。
- frontier_reference volume21–25/27–28にhw_discount_bond/Jamshidian callsなし。
  共有モジュールimportはあるが、今回のfunction body修正だけで各reference値を変えない。
- docs/prep ch28/29/31/32/33/34、P3_DESIGN、source design、MODEL_INDEX、
  RESEARCH_HANDOFF、PROJECT_RESEARCH_BRIEF、SECTION_AUDITは説明上のsymbol参照。
  signature/symbol/zero-mean Q state契約は保持される。過去の候補/監査を現在の新実行成績に書き換えない。
- scripts/paper_corpus/implementation_gold.py はhw_b/phi/discount/transition/simulate/calibrateとoption symbolsの
  AST存在を確認する。body hashやline positionsを保存しない。関数名は同じため、
  references/gold/gold_implementation_evidence.json / gold_implementation_metrics.jsonの生成内容はこの修正で変わらない。
  paper source tables/regressionの値もこのHW APIから生成されていない。
  ソース修正を理由にpaper Goldのpinを更新する必要はない。

## 4. 独立root / price / calibration 数値

全fixture入力はsynthetic。
existing test curveはhullkit/tests/test_hull_white.pyのCURVE、
vol26 curveはfrontier_reference.pyのnominal_curveを使う。
negative curveとzero-volは補助fixture。

| fixture | E | c(E) | old root y* | new root x* | 最大strike差 | 最大payer/receiver価格差 |
|---|---:|---:|---:|---:|---:|---:|
| existing test a=.12,s=.01 | 1.5 | .00009422188627946882 | −.0050538742263389475 | −.005148096112618416 | 0 | 0 |
| vol26 a=.1,s=.009 | 1 | .00003667646387455398 | .005317924162125003 | .005281247698250450 | 1.11e−16 | 1.2143e−16 |
| vol26 | 2 | .0001330770865126861 | .0038139709894402683 | .003680893902927582 | 1.11e−16 | 3.47e−18 |
| vol26 | 3 | .0002720595386588923 | .002264519028673007 | .0019924594900141155 | 1.11e−16 | 6.25e−17 |
| negative flat−1%,a=.05,s=.035 | 3 | .0047535556187425524 | .016278643648811132 | .011525088030068582 | 1.11e−16 | 5.55e−17 |
| zero volatility | 1.5 | 0 | −.004822230250855916 | 同値 | 0 | 0 |

root_new−(root_old−c)の最大absは3.47e−18。

existing testのprice:
receiver old/new=.008536961235263534、
独立decomposition=.008536961235263351、
独立Q^E求積=.008536961235263332。
payer old/new=.025182458622650068、
独立decomposition=.025182458622650325、
独立Q^E求積=.025182458622650300。

ZCB option（任意test curve例）はold/newでbit一致:
E2,U6,K.88,a.12,s.01:
call .014277748041457539、put .012729320260585264。
sigma0/expiry0例もbit一致。
Table32.3原典pinのactual curveはここで再実行していないが、当該function body/DF/volは変更されない。
親の既存suiteでそのpinを検証できる。

既存calibration fixture（expiry/maturity=1/5,2/7,3/8,4/10、fixed2.8%、truth=.12/.01、
initial=.06/.015）:
old fit=(.12000000000000144,.010000000000000049)、
new fit=(.11999999999999915,.010000000000000004)。
truthでsurface最大差6.2450e−17、
old最大price残差6.2450e−17、new最大price残差6.4185e−17。
公開APIの新機能、追加market fit、parameter contract変更は不要。

## 5. JY caller の実際のSE挙動

既存testと同じparams/24000paths/seed29/grid0..2 by .025でsimulate_jy_pathsを実行した。
t=1,U=2,a=.08,s=.01:
補正factor exp(−B c)=.9999556194738902、
target P0(2)=.9607894391523232。

old sample mean=.9607942390563803、SE=.00008924499617832786、z=.05378345。
new sample mean=.9607515985025676、SE=.00008924103543844480、z=−.42402746。
両方とも既存4SE条件を満たす。
一つの標本でoldのzが小さいことを旧式の正しさの根拠にしない。
補正で理論towerは成立し、標本ばらつき/台形short-rate積分誤差は別に残る。
このprobeはtest全体のpytest実行ではなく、bond expectation部分のsame-seed評価である。

## 6. 保存reference/notebookへの正確な影響

current root corrected sourceからvol26の53配列を/tmpへ再生成し、保存NPZとarray_equalで比較した。
変わる配列は **hw_swaption_priceだけ**。他52配列はbit一致。

old:
(.021573339235236084,.021450528062320166,.020592220163892887)
new:
(.021573339235236206,.021450528062320163,.02059222016389295)
最大abs=1.214306433183765e−16。

保存値変更対象:
1. volumes/26_inflation_jgbi/reference/inflation_scenarios.npz
   hw_swaption_price double[3]。
   old SHA256=629f79997a413c7630a797b6fb1f53160bae758742ac7d92f3b1defbe70b6f5f。
   new scratch SHA256=7967ceb1ac3c00e0e6e39498c8fb54adb6b11ff492467d4a7f5c795605ac3365。
2. volumes/26_inflation_jgbi/reference/metrics.json
   JSON比較で変わるtop-levelはcompanionsのみ。
   metrics、acceptance、schema、semantic_sources/tests、limitationsは同じ。
   old JSON SHA=05a5f579adb5fe8324491370cc297a55dedf20150b03a2d44c4424ea40b46789、
   new scratch SHA=81bcdfcc927f04478ec436f87cdebd20ac4e7c962537dac3a7845511cc699f7e。
3. volumes/26_inflation_jgbi/inflation_jgbi.ipynb
   zero-based cell4（code、ipynb本文line60のsaved output）は
   schema=1 volume=26 digest=629f79997a413c76 arrays=53を表示。
   new refならdigest=7967ceb1ac3c00e0へ変わるので、fresh execution/rebuildが必要。
   cell15 markdown / cell16 codeはHW initial-curve fit（line363のhw_model_discount_factor）で値は不変。
   cell17 markdown / cell18 codeはHull--White option ladder
   （heading line375、plot line407）で3点のinputがroundoff分だけ変わる。
   画像bytesの変化は未検査。見えるplotの意味/表示精度は不変。
   cell34のgeneric finite/unit/hash検査stdoutは同じtext。
4. book/notebooks/26_inflation_jgbi.ipynb は
   ../../volumes/26_inflation_jgbi/inflation_jgbi.ipynbへのsymlink。
   別copyを編集せず、元notebookを更新してBook buildを実行する。
5. volumes/26_inflation_jgbi/VALIDATION.md:
   metrics/acceptanceの表示であってcompanion hash/ladder pricesは載せない。
   再生成の期待内容は不変（ここではmarkdownを実際に書き直していない）。

関連gate:
- scripts/verify_frontier_artifacts.py:86–100 はvol26 JSON/NPZのSHA比較なので
  economic priceが不変でも旧saved artifactsではFAILになる。
- scripts/verify_frontier_notebooks.py:stale_output_cells はstdout/text結果をcell単位で比較する。
  referenceを更新してnotebookをfresh実行しなければcell4がstaleとなる。
  figures bytes自体はこのgateの比較対象外。
- release_manifest.json:234–264 はsource/test/referenceのpathを宣言。値hashを埋めていないのでpathは不変。
- report/report_builder/frontier_figures.py:353–413 のportal vol26 4図は
  nominal/real DF、ZCIS、JGBi floor、BEIを読む。
  hw_swaption_price/initial HW fitを直接表示しないため、portal図の数値はbit不変。
  portalの「option ladderを更新する必要がある」と誤報しない。Bookのnotebookにはladderがある。

このscratch hashは、rootが同じ補正式で同じreferenceを再生成した時の値。
他のconcurrent changesでvolume26の他API/inputも変わった場合はrootの新生成を優先する。

## 7. D1 evidenceへの全28節波及

scripts/evidence_fingerprint.py:272–332 python_closure:
module全file hashに加え、imported package initializerとstatic importsを含める。
hullkit.__init__:17がhull_whiteをimportするので、
直接HWを呼ばない各lessonのclosureにもhull_white.pyが含まれる。

実際にcurrent scripts/evidence_dependencies.jsonの全sectionsのclosureを計算:
28/28にhullkit/src/hullkit/hull_white.pyが含まれた。
対象は§26.1–26.17（17）、§27.1–27.8（8）、§28.1–28.3（3）。
closure source数は55–58。/tmp/m29-hw-caller-inventory-20261004.jsonに各節を保存した。

したがって本修正で全28節のPython source fingerprintが変わり、
M28 baseline画像の通常の再利用条件を満たさない。
現行D1 driverで再検証/再描画した証跡を作る必要がある。
これは数値callerの影響が28節に広がったという意味ではなく、現行指紋規約による検査範囲。
署名を手で合わせたり、許容差/画像再利用規約を本修正のために変えたりしない。

## 8. 最小の対応提案と未検証

rootの修正本体:
documented Q zero-mean state/signatureを保持し−Bcを追加。
Jamshidianの導出/price formulaやZCB option formulaを変更する必要はない。
roundoff差は既存source/価格許容差より遥かに小さい。

必要な追随:
- rootの独立state/tower RED→GREENと既存HW/JY/pin/calibration tests。
- vol26 reference NPZ/JSONとnotebook fresh出力のrefresh（上記3点）。
- Book rebuild、全accepted28節のD1再検証/新指紋証跡。
- artifact/notebook/releaseの既存gate。
元のeconomicsを変えずbyte snapshotをcurrent implementationに合わせることを説明する。

本調査で行ったもの:
baseline読取り、scoped caller search、独立root/strikes/price/calibration probes、
既存JY callerのsame-seed expectation、全D1 static closures、
vol26のみ/tmpへのactual corrected-source reference再生成。

本調査では未実施:
full pytest、Table32.3のactual curve再実行、notebook fresh execution、
Book/portal render/browser、D1 actual capture、全volume artifact/release gate。
親のrootが実施する。未実施項目を本probeのPASSとして報告しない。

## Scratch成果物

- /tmp/m29-hw-main88e03d3f.py
- /tmp/m29-hw-caller-probe-20261004.py / .json
- /tmp/m29-hw-caller-inventory-20261004.py / .json
- /tmp/m29-hw-reference-impact-20261004.py / .json
- /tmp/m29-hw-reference-probe/26_inflation_jgbi/reference/metrics.json
- /tmp/m29-hw-reference-probe/26_inflation_jgbi/reference/inflation_scenarios.npz

