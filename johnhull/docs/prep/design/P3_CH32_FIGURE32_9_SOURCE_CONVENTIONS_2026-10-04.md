# Ch32 Figure32.9 — DG201 に基づく独立再計算

更新:2026-10-04。read-only scratch。repo/Git/public API/product tests/browser/D1は変更・実行していない。

## 結果

**図32.9の25ノードにあるcash bond/option/dt-period rateの全75項目を、各フィールドの印刷半単位内に再現した。** 四捨五入の桁は印刷文字列から決め、価格に合わせたパラメータ調整も許容差拡大も行っていない。印刷ゼロのoptionは計算でも厳密にゼロ。

- 4step American call=0.6719332602576578; root印刷0.671933との差+2.60258e-7 <=5e-7。本文0.672とも一致。
- 100step American call=0.7025814093620565; 本文0.703との差-4.18591e-4 <=5e-4。
- curve fit最大絶対残差は両方1.11e-16。
- 全horizonの最終分枝確率が正。最小は4step=0.0024416666661376、100step=0.0186416666661067。負確率/代替fallbackは0件。
- 一次moment最大誤差8.88e-16、variance最大誤差2.09e-17。
- Figure75項目のhalfunitに対する誤差比の最大はbond=.94447、option=.99744、rate=.99863。一部が丸め境界に近いので印刷値自体を演算入力にしない。

## 原典入力

option expiry1.5年、bond maturity10年、face100、coupon5%年率/半年ごと2.5、quoted strike105、flat5% continuous zero curve、Black-Karasinski a=.05/sigma_log=.20。American exerciseは0..1.5の各user node。

粗い4step meshは0,.375,.75,1.125,1.5。100stepではDelta=.015。満期を日数ノットに置換せず、モデル・coupon schedule・quoted/cashの意味も保持した。

## DG201 の再現手順

1. `HW_TreeBondOption`が全coupon start/endを元のTermStructへ追加する。`DataSetUp(IsEqualSteps=True)`がexpiry以前のrate datesを最も近いuser stepへ移動する。4stepでは.5→.375、1.0→1.125、1.5→1.5。usermesh自体は変更しない。
2. expiry後のcoupon dates2,2.5,...,10は残す。`DataSetUp`の金利計算用dt1=.125、`i=Int(gap/dt1)+1`により.5year gapを5分割し、.1year間隔とする。よって1.5以後の最初のstepは1.6。
3. log-rate中心状態のgeometryを全horizonへ作る。mean=x*(1-a*dt)、variance=sigma_log^2*dt、次row spacing=sigma_log sqrt(3dt)。nearest expected child centerにkを選び、上下端では1つ内側のcenterを試す。候補確率が負ならnearest centerへ戻す。これはDG201のgeometry選択であり、負確率を実際の価格計算へ入れない。
4. discounted state-price propagationで全stepのalphaをfitし、R=exp(alpha+jh)、discount=exp(-R*dt)。終端user row1.5のspacingは前の粗いstepによるが、alphaを決める割引期間は次の.1year。
5. `BuildRates`のとおり、全rate-date ZCBを10年までのtreeからrollbackする。BKにHWのanalytic ZCBを代用しない。各option rowでZCBのlogからcontinuously compounded node yieldsを得る。
6. `TreeBondOption`はlocal node term structureへ次のstep dateのRを追加する。その後`ForwardBondPrice`は各coupon dateにzero rateを線形補間し、tより後のcashflowsだけをdiscountしてcash bond priceを得る。tで支払われたcouponは含めない。
7. quoted strikeのintrinsicはmax(cash bond−105−accrual,0)。accrualは0,1.875,1.25,.625,0。American backward inductionはこのintrinsicとparent-node discountによるcontinuationの最大値。

必要なpricing intervalsは4stepで89(4+85)、100stepで185(100+85)、maximum row widthは75/201 nodes。DG201 sourceは10年maturityの先にさらにsynthetic stepを置くが、最終ZCBは10年で1として満期終了するため、pricingに使わないその余分なstepだけをscratchでは省略した。option/bond値へ影響しない。

初期のflat curveに余分なnon-coupon maturityを入れると、BKの金利計算用meshを変える可能性がある。このfixtureでは原典のflat5%とcoupon datesで構成し、印刷全75値との一致でこの構成を検証した。

## ノード別の再計算

bond/option/rate_percentは計算結果。照合に使った元の印刷文字列・半単位・残差はJSONにすべて保存。

| time | j | cash bond | option | rate (%) | early exercise |
|---:|---:|---:|---:|---:|---|
| 0.000 | 0 | 99.5102126228 | 0.6719332603 | 5.00000000 |  |
| 0.375 | 1 | 94.6899952237 | 0.0582271965 | 6.13623667 |  |
| 0.375 | 0 | 101.4979026339 | 0.4716544860 | 4.96334347 |  |
| 0.375 | -1 | 107.6801715823 | 2.1630600426 | 4.01463954 |  |
| 0.750 | 2 | 87.0691951847 | 0.0000000000 | 7.53484774 |  |
| 0.750 | 1 | 94.3258832463 | 0.0170634451 | 6.09462107 |  |
| 0.750 | 0 | 100.9786862261 | 0.2735992376 | 4.92968236 |  |
| 0.750 | -1 | 107.0004207487 | 1.7716318788 | 3.98741249 |  |
| 0.750 | -2 | 112.3921775013 | 6.1421775013 | 3.22525007 | yes |
| 1.125 | 3 | 79.1939333364 | 0.0000000000 | 9.25715372 |  |
| 1.125 | 2 | 86.8573734838 | 0.0000000000 | 7.48772186 |  |
| 1.125 | 1 | 93.9624167195 | 0.0000000000 | 6.05650293 |  |
| 1.125 | 0 | 100.4531874962 | 0.0990703136 | 4.89885020 |  |
| 1.125 | -1 | 106.3087401918 | 1.2759434503 | 3.96247365 |  |
| 1.125 | -2 | 111.5353229198 | 5.9103229198 | 3.20507809 | yes |
| 1.125 | -3 | 116.1587165679 | 10.5337165679 | 2.59245271 | yes |
| 1.500 | 4 | 71.1316455843 | 0.0000000000 | 11.37437485 |  |
| 1.500 | 3 | 79.1364335937 | 0.0000000000 | 9.20025288 |  |
| 1.500 | 2 | 86.6557652885 | 0.0000000000 | 7.44169717 |  |
| 1.500 | 1 | 93.6005252777 | 0.0000000000 | 6.01927549 |  |
| 1.500 | 0 | 99.9219628119 | 0.0000000000 | 4.86873850 |  |
| 1.500 | -1 | 105.6054427412 | 0.6054427412 | 3.93811756 |  |
| 1.500 | -2 | 110.6623065802 | 5.6623065802 | 3.18537748 |  |
| 1.500 | -3 | 115.1222444167 | 10.1222444167 | 2.57651772 |  |
| 1.500 | -4 | 119.0263203363 | 14.0263203363 | 2.08403669 |  |


early exerciseは(t=.75,j=-2)、(t=1.125,j=-2/-3)の3node。終端expiryの正のpayoffはearly exerciseとして数えない。

## 原典ソフトの数値処理とfallback

DG201の`TreeAdvance`は、端nodeで内側centerを試し、負確率なら元のnearest centerへ戻す。この候補拒否は4stepで33回、100stepで100回ある。最終的に採用した分枝では全確率が正で、momentsも一致する。

DG400に追加されている負確率時のpu=1,pd=0 fallbackを本再計算は呼んでいない。DG201にないfallbackを仮定して価格一致させていない。

DG201 `TreeAdvance`の到達確率Pを保存するhousekeepingにはPDをpuから読む箇所がある。しかしcurve-fittingは別のArrow-Debreu Qのforward inductionで正しいPDを使い、`PV_Rates`/option rollbackも正しいPDを読む。scratchはその未使用Pをpricing根拠にしない。このsource上の問題を広い実装修正へ持ち込まない。

curve fitはsourceのNewtonを単調なscalar rootのbrentqへ置換して解いた。これはsolverの精度変更だけで入力/geometry/payoffを変更しない。上記残差がequationを独立に満たす証拠。

## 一次資料と位置証拠

[Author DG201 functions.xls](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/DerivaGem%20Software/Earlier%20releases%20and%20corrections/2.01/DG201%20functions.xls)

固定commit `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`。SHA-256 `273ebb1a0814724e962bd4e10bd643c73742f121b7703f813638204e3dee4493`。ローカルbinary `/tmp/p3-ch32-DG201-functions.xls`、抽出VBA `/tmp/p3-ch32-DG201-functions-vba.txt`。


VBA位置は結合抽出ファイルの1-based line。

- `Calc_IR_Options.HW_TreeBondOption`:4693、GetBondDates/TermStructへのcashflow-date追加:4738 onward、MakeHW_Tree call:4762。
- `Calc_IR_Tree.DataSetUp`:6524、nearest user rate-date移動:6588 onward、post-exercise interval数:6647。
- `Calc_IR_Tree.BuildHWTree`:6729、stepとspacing:6758-6764。
- `Calc_IR_Tree.TreeAdvance`:6773、variance/Euler mean:6800/6805、boundary candidate:6810 onward、採用確率とsymmetry:6829 onward。
- `Calc_IR_Tree.TreeAdjust`:6902; `BuildRates`:6985。
- `Calc_IR_Tree.PV_Rates`:7214; `discountfactor`:7201。
- `Calc_IR_Options.TreeBondOption`:5089、次のstep rate追加:5156 onward、ForwardBondPrice/quoted-strike adjustment:5170 onward、American max:5200 onward。
- `Calc_FixedInc.ForwardBondPrice`:3637; `BondAccrual`:3753; `GetBondDates`:3841。
- `Calc_FixedInc.Interp_Value`:4378; `DF`:4416。

Licensed original `johnhull/options, futures and other derivatives 11th.pdf` pp749-750の入力/図/price labelsを確認。付属ソフトのマクロは実行せず、sourceを読み mathematical scratchへ転記した。remote変更・送信なし。

## 成果物と限界

- `/tmp/p3-ch32-figure329.py`: geometry、curve fit、full-maturity conditional ZCB、local cash bond、American rollback、印刷文字列ごとの照合。
- `/tmp/p3-ch32-figure329.json`:全75フィールドの計算/原典値/半単位/残差、全25nodeでintrinsic/continuation/early exercise、100step価格、moment/curve/確率記録。
- `/tmp/p3-ch32-figure329-notes.md`:この報告。
- 再実行: `/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch32-figure329.py`。

**Figure32.9 の原典数値pin blockerは解決。** これは原典fixtureの再現であり、P3 product実装/portal表示、一般event tree、独立PDE受入などが完了した意味ではない。repoへ何も変更していない。
