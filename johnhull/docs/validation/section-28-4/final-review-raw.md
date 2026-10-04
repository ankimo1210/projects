# M29 §28.4 最終コードレビュー（原文）

- Reviewer: fresh Senior Code Reviewer 1名。追加agent・再レビューは使用していない。
- 日付: 2026-10-04
- 対象: `/home/kazumasa/worktrees/m29`
- BASE: `88e03d3f7bb5e3a03237ab67ae0836442726af44`
- HEAD: `0e21d349c2766da8489d4c18bc5e9ef3026d7a01`
- 読み取り専用。Git/HEAD/index/branchとプロジェクトファイルの変更なし。scratchは `/tmp` のみ。確認後の `git status --porcelain` は空。

## 判定

**M29のマージを承認可能。Critical 0、Important 0、Minor 3。**

原典§28.4の数学、公開HW状態補正、通常の教材入力、独立参照、保存値消費、既存246セル維持、受入前ゲートにマージ阻害を認めなかった。以下のMinorは表示文の精度1件と、教材fixtureの外側にある極端な数値入力2件。通常のquarterly/semiannual金利、公開API変更、今回の受入価格に影響する不具合とは判定していない。必要なrulingを記録して後続で扱える。今回のレビューはmain統合/pushの実施完了を意味しない。

## 良い点・数理上の確認

1. 公開 `hw_discount_bond` の `-B*c(t)` はQ zero-mean OUという既存契約に整合する。`r=x+phi`、`phi=f0+c` からの条件付きintegralとの一致を、production bond式を使わないテストで確認している。Jamshidianの根は `x*=y*-c(E)` と平行移動し、各ZCB strikeとtime0欧州価格は数学的に不変。既存ZCB option、較正、JY callerの23テストも今回再実行してPASSした。
2. `joint_moments` のQ平均・共分散と、payment U測度への `cov @ [-B(T,U),-1,0]` tiltは、同じ将来Wiener増分からの `(X,I,W)` の定義に一致する。stockのQではpath discountが給付と同じ標本に掛かり、Tでは同じcall給付をtilted分布で平均する。raw RN重みの自己正規化は行われていない。
3. termはT固定/U支払、overnightはU実現/U支払として区別される。annuityはOIS bondの正の線形結合で、A測度はpayment Gaussianの有限混合。projectionの決定的加算simple-rate basisはVだけに入る。single Gaussian/lognormal swap rateを暗黙に仮定していない。
4. 原典pp.676–679をPDFから直接抽出し、式28.16–28.25・脚注5/6・N01–N12の説明との対応を照合した。原典に印刷価格例がないこと、合成市場であること、年・年率小数・simple複利の区別が明示されている。
5. 独立oracleはhullkitをimportせず、短期金利shiftの積分・正のOU kernel求積・Q条件付きdiscount/T直接密度・annuity混合を使う。保存oracleの再生成比較と実API変異を組み合わせ、単なる保存hashの一致に留めていない。
6. notebook検証はBASEの旧246 source/output/Plotlyを保護し、新4図をfresh共有図と比較する。consumerは保存結果のshape/finite値/独立値/MC統計を検査する。統合gateは全28 D1の必須source inventoryを現行宣言から再構成し、両保管庫の実ファイルとcurrent hashesを検証してから台帳更新に進む。updaterはgate失敗時に台帳を保存しない。

## 指摘

### Minor 1: portalの練習文が図に存在しない定数金利極限を案内する

- 場所: `johnhull/report/report_builder/figures.py:1481`（関連する表現は1476）。
- 再現: `martingale_numeraire_forward` cardのpracticeは「差の向きと定数金利極限を確認」と案内するが、図にある3群はすべて金利vol `eta=.02`、stock loading `+.25,-.25,0`。最後の `sigma_S=0` でもfutures=108.4152721949055、forward=108.32870676749582であり、定数金利極限ではない。
- 影響: portalだけを見る読者がstockのzero loadingをzero rate volatilityと取り違えたり、存在しない図の状態を探したりする。Book本文と保存eta=0 fixtureは正しいため、数理全体の受入阻害とはしない。
- 対応案: 現図に合わせて「stock loadingが0でも確率金利による差が残る」と案内するか、eta=0の明示的な図状態を追加する。1476の「QとTの価格差」も、実際には各MC価格から独立価格を引いた差なので、「Q/TそれぞれのMC価格と独立価格との差」とすると図の読み方が正確になる。

### Minor 2: 極小accrualでterm/forwardが桁落ちする

- 場所: `johnhull/hullkit/src/hullkit/_numeraire_choices.py:236` および252。
- 再現: `rate_statistics(0, 1, 1+1e-12, 0, FlatHW())`。実際のdeltaは1.000088900582341e-12年。flat curveの安定計算 `expm1(.04*delta)/delta` とovernight_paymentは約0.0400000000000008。一方forwardは0.03996447602131439、term_paymentは0.04002220818870255を返す。
- 原因: 小さなlog bondを一度expした後にlogへ戻すことと、ほぼ1のDF比から1を引いてdeltaで割ることが精度を失わせる。
- 影響/重大度: 有限かつ正の期間として入口は受理するが、期待金利の恒等式が公称rate toleranceを外れる。ただし約32マイクロ秒のaccrualで、今回の原典・教材の.25/.5年や通常の金利scheduleには影響しないためMinor。
- 対応案: log-bondの直接評価とその差へのexpm1、または精度保証できる期間範囲の明示/拒否。小さいa*hのmomentsが安定でも、DF比の差分は別に扱う必要がある。

### Minor 3: 極端な大a*hでexact samplerのX分散が消える

- 場所: `johnhull/hullkit/src/hullkit/_numeraire_choices.py:175–176`。
- 再現: `m=FlatHW(a=1e16, eta=.02, zero=0)`、`sample_joint(0,1,0,m,100000,77)`。`ou_moments(1,m)[0]` は2.0000000000000002e-20だが、sampleのX分散は1.0792449831452078e-35。理論分散は浮動小数点で表現可能。
- 原因: `vi-ciw**2/h` の桁落ちを0にclipした後、`eta*w-a*i`でもほぼ等しい値を差し引く。この入力ではrate noiseをほぼ決定的にしてしまう。
- 影響/重大度: finite a>0という現在の入口契約の非常に外側で、正の分散が黙って失われる。a=1e16/yearは実用的な金利モデル値ではなく、既存fixture/今回の表示価格への影響はないためMinor。
- 対応案: 大a*hでは(X,W)側から安定にfactorizeする分岐、または相対残差を検査して非対応領域を拒否する。tiny-a対策とは逆側の数値条件である。

## 今回レビューで実際に実行した検証

環境は `/tmp/m29-env.sh`、`PYTHONDONTWRITEBYTECODE=1`、pytestは `-p no:cacheprovider`。

- 新private/HW state/lesson/numerical/acceptance/updater/notebook/registry対象: **73 passed, 25.97s**。
- 既存 `test_hull_white.py`、`test_hull_pins_exotics_ir.py`、`test_jarrow_yildirim.py`: **23 passed, 1.46s**。
- 以下4本を **--checkで再実行してすべてPASS**:
  - `build_numeraire_reference.py`
  - `verify_numeraire_numerics.py`
  - `verify_numeraire_notebook.py`
  - `build_numeraire_acceptance_record.py`
- 上記notebook checkはin-memory fresh executionを行う。旧246セル保持・257セルのfresh保存出力比較・4共有Plotly照合を確認。統合checkは既存28 D1のcurrent hashes/両保管庫を再検査した。
- 独自scratch probe100ケース: a in approximately [1e-8,5]、eta in [0,.06]、zero in [-.04,.1]、複数時刻/状態/期間。独立積分とのbond最大差2.220446049250313e-16、term/forward最大差5.009881398621019e-15、overnight/forward最大差4.961309141293668e-15、Q/T stock最大差9.237055564881302e-14。
- 不正入力42回（bool/string/complex/NaN/Inf/datetime/timedeltaを時刻・state・schedule・basis・stock loadingへ投入）をすべてValueErrorで拒否。eta=0のsample、2×2状態配列、負V/負swap rateと正Aも確認。
- 保存1000px画像を目視: portal pricing、portal forward、Book payment、Book annuity。4つともラベル/凡例が読み取れ、選択した画像にクリップ・重なりを認めない。
- 独自probe: `/tmp/m29-review-probe.py`。原典抽出: `/tmp/m29-review-source.txt`。

## 実行者証跡として確認したもの（今回の独立再実行とは区別）

- 全hullkit+report **4125 passed / 6 skipped / 既存warnings2 / 213.52s**。
- 16browser states/16PNG、旧28 D1実ブラウザ・runtime probe・個別pytest計2157、462 images、両保管庫。
- ruff21対象、strict tracked release、保存vol26の3値のroundoff refresh。
- 台帳はbranch上29 accepted/277 pending、P3 4/37。mainはまだM28。この区別はP3_STATUS/受入記録に記載されている。

## Declined to judge（未判定の挙動と理由・全件）

1. **現在のブラウザ環境での全16状態および旧28節の再描画成功**: 今回は再描画を実行していない。既存producerはprojectのPNG/JSONを書き換えるためread-only条件と合わず、具体的な再描画不具合の証拠もない。4枚を目視し、全状態matrix/current hash/両保管庫をcheckした範囲で判断した。
2. **全4125テストの今回の独立再走行結果、全release/lint検査の独立再走行結果**: 全体再実行は依頼で重複回避を指定され、対象96テスト・4checks・追加probeが通った後に範囲拡大が必要な不具合はなかった。記載された全suite等の結果は実行者証跡として扱う。
3. **M30多因子設計、TN14/TN19/元XLS回収、LMM/flexicapの次節受入可否**: 新prep資料は準備専用と明示され、M29の実装・五軸受入に含まれない。境界とpending維持は読んだが、その全出典・132fixture・元回帰/全9fit点を今回再現していない。後続節の正式レビューが必要。
4. **main統合後のsource/成果物一致、remote push到達性**: 対象HEADは統合前の固定branchであり、read-onlyレビューではmain/remoteを変更しない。親実行者の後続統合検証対象。

これら以外に、M29 Review Focusの4領域について判定を留保した挙動はない。Minorの極端入力を全通常入力の不具合へ一般化せず、教材の合成モデルを一般多曲線市場・全実数域に対する数値保証へ一般化しない。
