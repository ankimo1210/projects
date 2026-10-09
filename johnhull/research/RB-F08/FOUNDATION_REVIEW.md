# RB-F08 基礎実装 独立レビュー

更新日: 2026-10-09。対象: Task 1/2/3/5、`e55e8569..4942ef35`。

**最終判定: basis品質・仕様適合とも基礎範囲で承認。未解決Critical 0、Important 0、Minor 0。**
初回のImportant3件とMinor1件は`4942ef35`で修正され、元の再現例と追加境界を独立再検査した。Euler/統計/参照価格/seed台帳も独立検算に合格した。実pilotの金融検証、主実験・4図・F08受入を認定するレビューではない。

## 対象の固定

- 最終commit: `4942ef35e6041e49facc632147d9c24873f6000d`。
- 初回range: `e55e8569..2334c54e`。初回patch SHA256: `ee4c5574d1b439bde3d0bf7ce0ab5c958d16b5684c379d5772db33e5e787bb4e`。
- 修正range: `2334c54e..4942ef35`。fix patch SHA256: `5b4a6fa01a9f87608628f1cd4088df49d3e8849c11e18928029884292f4622af`。
- 最終変更16fileのcanonical path→SHA256辞書をhashしたreview source fingerprint: `4f0358b42744fcc5aa5859411bd1238d1e6b8fc4c1cdb9e78ce6822f9c81a5bf`。各SHA・初回判定・再検査は[foundation_review.json](foundation_review.json)へ保存。これはreview対象の来歴であり、金融数値の承認フラグではない。
- 最初に `johnhull/AGENTS.md` と実施計画のGlobal Constraints / Review Focus / Task 1/2/3/5を読んだ。Task 4/6の並行未コミット実装は対象外。実装ソースを変更せず、指定review2fileだけを作成した。

## 指摘と修正確認

| ID | 初回の具体例 | 修正と再検査 |
|---|---|---|
| F08-FR-01 / Important | `analytics.py:231–234`、epsilon=.4の同一cell・同じ4run配列を3回複製するとsupported count3・速度採用true | 最終`:235–240`で有限正・降順一意を要求。旧例はValueError。distinct .4/.2/.1でratio .5は採用、1.2は不採用を維持 |
| F08-FR-02 / Important | 原価がexact_cv専用1件だけでもMLMCのoffline0・cold=mainで成功。decisionのoffline台帳欠落も成功 | 最終`:154–155`でmethod適用原価なしを拒否、`:241–242`でdecision台帳欠落/空を拒否。3境界すべてValueError |
| F08-FR-03 / Important | exact plain/CVのRMSE990でも速い秒数だけでstandard却下の速度理由を記録 | 最終`:288–296`でRMSE<=epsilonのexact法へ限定。全精度未達はaccuracy unresolvedのみ。片方だけ精度合格時も速い不正確法を除外することを確認 |
| F08-FR-M01 / Minor | protocolはconfidence=.9を許容するがRQMC wrapperが.95固定 | `_rqmc_ci.py:75,129`でconfidenceを渡す。.9のCIを自前t(df3)半幅で再計算し、.95とのscramble estimates一致も確認 |

## 独立数値検算

Blackはhullkit式を参照せず、lognormal payoffを正規密度に対してquad積分した。K80/100/120、q0/.02、sigma0/.2/.7の18条件で最大差`2.13e-14`、ATM/q0 price=`9.413403383853016`。one-step EulerはGaussian positive-part積分を別に計算し、q=.02でK80/100/120のprice=`21.848225116166475 / 8.237934627901378 / 1.7769971106801166`を確認した。

clip参照は`lower*g(lower)+(1-upper)*g(upper)`とz領域の直接quad積分を使った。sigma=.7/K120でclip .001/.999、.1/.9、nextafterの最大差`1.78e-14`。実装のpartial-lognormal式を期待式へコピーしていない。

配分V=[4,1], C=[1,4], sampling variance=.5、minimum2、floor0はN=[16,4]。異なるlevel n=[4,7,10]で手計算variance=`.453952380952381`、Satterthwaite df=`3.548861478674173`、CI=`[.40172056693440106,4.338279433065599]`と一致した。fine normalの隣接和/sqrt(2)、qを含むEuler drift、exact終端を別診断にする分離も確認した。

sigma1、fine[-4,-4]で途中負→満期正となるEuler pathのpayoff=`234.31457505076202`を保持し、3元試行を分母に使う。負path2、updates9、normals6、payoffs6、coarse aggregation3の原価件数も一致した。NaN入力とexact終端overflowは全runを拒否した。

RQMCはR=4でdf3、SE=`1.2909944487358056`。別のSciPy Sobol生成と自前GBM終端式でchild seeds41/43/47/53を直接照合し、4×16点すべてを含むことを確認した。q=.02のdiscounted-stock期待値は独立積分で`98.01986733067554=S0*exp(-qT)`。RMSE=sqrt(1.5)、Wilson2/4=`[.15003898915214947,.8499610108478506]`、inclusive endpointと退化trial分母を確認した。

## seed・typed保管・freezeの確認

最終181729slotを独立に再生成し、物理seed181729個の一意性、pilot31、coverage172032、main9216、fresh372、typed列のpack/unpack/hydrateを確認した。2衝突のraw/generated/retry/spawn keyはコミット済み[seed_audit.json](seed_audit.json)と一致。typed digest=`e3c264ebc4fb93b7c82e6ba3464243a04d4881981cab23ce698acbbadcebdb16`。

旧commitから181728行を別に再生成し、追加slot以外の全行について全fieldと物理seedが不変と確認した。新slotは`pilot.0.0.0.clip_diagnostic.-1.-1`、seed=`3739489220`、retry0。power10/public clip=[1e-10,1-1e-10]の条件はJSONとcandidateに一致し、frozen power改変、承認condition不一致、public clip変更を拒否する。一意seedは同初期化の偶発的再利用を防ぐ条件であり、数学的独立性の証明ではない。

freezeはtiny fixtureと**numerical checkerのstub**で承認配線だけを検査した。condition、allocation、beta、pilot record/array hash、source改変、numerical validator=Falseをすべて拒否しcandidateを保存した。実pilotの金融検証を認定した結果ではない。

## 検証範囲と次の条件

作者reported evidenceは修正対象69PASS、基礎/protocol/index/docstrings1108PASS、ruff/format PASS。今回は全suiteを繰り返さず、独立手計算と狭い境界probeを実施した。

費用primitiveの算術・適用先・欠落拒否を確認した。実験に必要な全expense_id/金額/計測receiptの完全性はTask 4/6のpilot・保存checkerで確認する。実pilotの配分/bias/負Euler率、mainの固定roster・全run/費用/被覆率、4図、独立最終レビューとF08採否は未検査。保存JSONフラグやSHA一致から金融検証・研究成績・研究完了を認定しない。
