# 次段階研究案 独立設計レビュー — 2026-10-09

多曲線risk/P&L、増分XVA＋IM・資本の両案は計画段階へ進めてよい。正式DESIGNへ必須修正2件を反映する。Critical0 / Important2 / Minor0。正式設計・実装・study acceptanceではない。

## Important I1 — 多曲線 §8、原稿144–150行

exactな旧curve ratioによるcalendar rollと、新t1 calibration instruments/tenor節点への表現移行を同じ状態として扱っている。旧knotsがt1から見て移動するため、zero/logDF splineは新節点に一般には厳密に載らず、quote move0でもVfとq_roll再較正値が異なる。その差をmarket Taylorへ混ぜると曲線依存・fixing・market shockの識別が崩れる。

独立例: old knots=[0,.5,1,2,3]、logDF=[0,-.005,-.04,-.07,-.10]、roll=.25。new knots=[0,.5,1,2]にexact rolled値をsampleして再補間し、旧.5期日のunit CFを評価すると、exact ratio DF=.9975031223974601、new-grid DF=.9900498337491681、差−.007453288648291978。これはtiny math反例で、主studyの結果ではない。

最小修正: shifted absolute old knotsを保持してexact rollを再現するか、regrid/rebootstrapのvalue差を独立bridge項として保存する。market Taylorは移行後のrepresentable calibrated stateとfixing-conditioned center quotesから開始する。zero-move反例を固定する。

## Important I2 — XVA §5、原稿90行

bundle(c)はhedgeをnetting不能な別setに置きながらIM低減を調べる。既存契約/thresholdを保持した独立setのIMでは、既存IMは変化せず新setのnonnegative posted IMが加わる。資金/資本poolの共通化はIMのcross-set相殺を許さない。同一法的netting agreement内だけでIM risk offsetsを認める国際基準とも整合が必要。[BCBS MGN20.14](https://www.bis.org/committees/bcbs/basel-framework/standard/mgn?allChapters=true)。

独立Gaussian anchor: 既存sd100、逆方向hedge sd80、z99=2.3263478740408408。before posted IM=232.63478740408408、別set after=418.74261732735135、同一set after=46.52695748081682。

最小修正: IM低減とcapital residualのmain bundleは同一setの異満期hedgeへ変更する。別setはIMが減らないvalidation対照にし、set別IMとbank capital/funding集計を分ける。期待する符号を結果選択へ使わない。

## 整合している設計とsource境界

ratesのexact block IFT、二次較正responseを含むdirectional Hessian、direct quote項、bp/bp²単位は整合する。非ゼロ残差LSのresidual Hessianとregularization、KKTのactive-set/LICQ/二次条件の境界も適切。D/pseudoDF projectionの区別、basis付加leg、fixing publication/as_of、known fixing保持、immutable coupon、CFをt1へ累積したnominal contractual P&Lとex-paymentは適切。bridgeの代数恒等式自体は正しい。

XVAは単独/増分/marginal/Eulerとhedge bundleを区別し、各bookをfull revalueする。first-to-default密度、stochastic discountとgap cashを同じcloseout時刻へ移す規約、settled VM/segregated posted/received IMの使い分けは整合する。F0 cash ledger、borrow/invest spread、IM専用(rbI−rI)、(rVM−rOIS)C、net excess capital charge、φの資金便益を重複控除しない設計も妥当。これは指定したinternal desk cost policyであり一般的funding fair-price解を主張しない。

現物のMODEL_INDEXと主要sourceで、singlecurve exact root、静的frozen contracts、diagonal-only P&L、単独credit/EE/funding教材、FlatHWのjoint state/discount Gaussianという再利用境界を確認した。dated leg/rfrの既存helperにもsyntheticcalendar・known fixing・projection/discountの区別がある。新multicurve calibration/full cross gamma/bilateral closeout ledger/IM/capital engineが既に完成したという記述はない。project全域の実装不在監査はしていない。

## 外部主張・証拠・計画へ引き継ぐ要件

MGNの99%/10day/stress比較基準、CRE52のsegregated posted IMをNICAへ入れない区別、MAR50 reduced BA-CVAのall-counterparty aggregation/0.65 scalarを公式章で確認した。詳細equation imagesの実装一致・管轄法適合・whole-bank capitalは未判定。[MGN](https://www.bis.org/committees/bcbs/basel-framework/standard/mgn?allChapters=true)、[CRE52](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05)、[MAR50](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08)。

SIMM2.8+2512の2026-06-12公表/2026-07-11発効は公式検索本文で確認した（direct openは失敗）。公開説明とcommercial methodology利用権を区別し、手製Gaussian proxyをSIMMと呼ばない範囲は適切。係数本文・利用許諾の監査はしていない。[ISDA公表](https://www.isda.org/?p=1243627)、[ISDA Licensing FAQ](https://www.isda.org/2021/04/08/isda-simm-licensing-faq/)。

計画ではdate/fixing公開状況を解決してから12quote rank/coverageを確認する。0×3m/0×6m term-forward anchorsはresetが未確定である条件かabstract forward quoteである条件を固定し、known fixingのzero-J rowを較正へ残さない。laggedVM/MPOR/coupon/reset履歴のGaussian求積dimensionは実際のstateから導出し、条件付き1D/2D anchorを全caseに一般化しない。closeout/IM返還/資金・資本のstop timesとOIS超過費用のcash照合は提案済みの小台帳gateで検証する。

原4quote scratch scriptは読んだが数値は再実行していない。今回実行したのは指摘2件のtiny counterexamplesだけ。source/Git/pytest/full-suiteは変更・実行していない。XVA studyの実測証拠はなく、12quote精度/rank/runtime、規制subset実装、pilot/main/refinement/artifact/checker/復元/性能はすべて提案gateである。2案・読取sourceのSHA256と出典範囲はJSONに保存した。新RB-IDは付与していない。
