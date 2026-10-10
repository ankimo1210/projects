# 正式pilot予算のための測定

2026-10-10。正式金融pilot/mainは未実行。以下は**部品の実測と、歴史的教師計算からの外挿**であり、全phaseの実測時間・精度資格ではない。

## 実際に測った再較正

元selected18のS/Q・日付を使い、同じscalar not-a-knotの全call domainで2,304回fitした。受入済みfield257×321を読み、call cacheは元selectedの6日付・S65・Heston v33/local ell7。正式49日付cache・Asian教師・16block Greek・全path FD・政策は実行していない。

| 部品 | Heston | local |
|---|---:|---:|
| 実cache構築wall | 5.475秒 | 3.076秒 |
| 実fit件数 | 1,152 | 1,152 |
| 実fit合計wall | 0.339秒 | 0.300秒 |
| 1query中央値 / 95%点 | 0.285 / 0.346 ms | 0.253 / 0.300 ms |
| 状態 | ok1,088・unknown64 | ok1,152 |

元Hestonの1入力がunknownとなるため、64回の反復でもその理由を保持した。全体wall9.596秒。実測wall/CPU、原入力SHA、原fit/root/残差、実装SHAは原JSONに保存。診断の事前上限300秒内に完了した。unknownを金融PASSへ変更していない。

## Asian価格・16block Greeksと13回の再較正

原coarse/high軸・12月次日・local t0 spot5を保ったevaluate_asianを6,912回、元18入力の13回再較正を幅1/.5/2で計936query・72group測定した。実call cacheを使い、Asian格子は解析的な価格proxyと決定論的16block offset。金融価格・IID標準誤差・教師資格を認証する測定ではない。

| 格子 / モデル | Asian成功平均 ms/query | fit＋Asian平均 ms/query | 13query group中央値 ms |
|---|---:|---:|---:|
| coarse / Heston | 0.185 | 0.466 | 6.151 |
| coarse / local | 0.288 | 0.583 | 7.659 |
| high / Heston | 0.210 | 0.511 | 6.757 |
| high / local | 0.714 | 0.953 | 12.846 |

表はfull fixed boxの実処理。historical global mode、失敗query、全日付・状態・clock・raw root・残差・16block/covarianceも保存した。fit-onlyの936回は別計時し、価格queryの時間に加算していない。全体wall12.715秒/CPU12.700秒はcache構築と別fit-onlyを含み、最終JSON書込/stdoutを含まない。診断の事前上限300秒内で、使用source7件のbefore/afterは一致。

この診断のbumpはhS=.05/hQ=.01、正式producerはhS=.02/hQ=1e-4である。memoryも既往n−1個のfixing100＋current Sという説明済fixtureであり、正式入力の過去経路ではない。同じアルゴリズムの部品時間だけを予算審査へ使い、support/conditioning分布や金融Greek精度を正式入力へ転用しない。元Heston unknownはNaNのまま保持した。

[原測定の範囲と相違](runtime-evidence/task-5-asian-query-cost-summary.md)。

## 元の正式入力を準備

元selected18のS/Q・日付・診断fit状態を保持し、過去の原teacher memory n/100nを結び付けた。各モデル12月次診断query、1/24・1/48の追加teacher例、元seed namespaceを保存した。production CFで得た診断Qは合成benchmark観測であり、独立oracle/実市場観測の証明ではない。

準備wall4.233秒/CPU4.231秒、金融RNG未実行、formal_plan_locked=false。local追加例は受入済み旧field257×321でfitしているため、現正式fieldでの同一Qとfitの確認がlock前に必要。global driver IDとstream receiptは実market jobのrawから組み立て、入力準備だけで捏造しない。準備JSONの計時はelapsedだけでinterval endpointsを持たないため、正式費用のinterval認証には使わない。

## 主実験の保存量と計時

main実行器のsource-unitは、高格子の全原軸・12日付・解析的16block教師、実field、説明済affine QのN256を使用した。RNG/正式main/金融資格は未実行。実risk3.019秒、saved checker3.030秒、最大packed chunk30,273,655 B（うちarray30,243,088 B）は256MiB内だった。

原N32768・18riskへ線形に外挿すると、raw chunks約69.751 GB、測定時のfullmerged wrapper重複を含むexpanded量約140.896 GB、risk生成＋そのsaved検算だけで約3.87時間となる。いずれもfixtureに基づく参考推計であり、正式圧縮disk/RAM/wallの実測ではない。原raw/16block/rootをchunksに保持する必要最小policy viewと、resumeの追加load/replay/check費用receiptは正式main前のsource確認事項。

## 両保管庫からの復元と算術

10,707,062 Bの測定raw・元入力JSONを既存primary/mirrorへ保存し、両者それぞれを新しいdirectoryへ復元した。全6,912queryと936再較正のwall/CPU interval、件数、平均・中央値・95%点、status count、13query group合計を許容誤差付きで再計算し、両者PASS。保存と復元・検算の成功実行wall0.363秒/CPU0.179秒を別記録した。

[CAS manifest](runtime-evidence/task-5-component-cost-manifest.json)・[両復元と算術検査](runtime-evidence/task-5-component-cost-cas-check.json)。SHAはimmutable原byte・由来の照合に使い、計時算術はiscloseで検算する。最初の補助検査は入力JSONのclock schemaを誤認して失敗したため、原script/logを保存し修正した。失敗時費用は未測定であり、正式all-costs完了を主張しない。このCAS確認は部品測定の保存で、正式pilot/main/freshの金融semantic受入ではない。

## 教師計算の規模

旧実教師preflightは82,247,680 path steps、全child wall45.117秒（起動・import・保存込み）。この速度と当時のteacher_axesから、local high N65536は34,703,671,296 conditional path steps・約5.29時間となる。composition、source、保存/再計算費用が異なるので正式jobのwallとは扱わない。N ladder各項目は候補・attemptであり、全N×全gridの実行指示ではない。

workload JSONのraw_two_factor_driver_bytes_without_dedupは、fine normalsを各teacher nodeに複製保存した仮定の容量。従来の完成teacher rawはprimitiveとdriver SHAを保存し、全normalを保存していなかった。仮定上の大容量を既存実保存量と誤記しない。

正式実行では同じstream/N/calendarの不変fine driverを共有し、coarse/high・node/dateの同じSDEを保存normalから再計算する。oracle/premium/train/testのstreamは独立させる。driver保存・復元のsource確認と実際の費用計測は別の完了条件である。

## 予算を固定する前の残り

- 正式教師生成・訪問する全path/dateのsupport分布・限定patch・実serializer/savedcheck/CASを測定または別費用で明示する。部品fixtureの時間を正式wallへ読み替えない。
- 事前job/phase budgetとcap scopeを独立確認し、chunk境界のsoft deadline・実overrun・元未実行Nを保存する。
- source/solver欠陥を予算capとして閉じない。failed/unknownも全費用へ残す。
- 正式pilotの全121case/51obligationを実jobと結ぶ。4段階N/higher-N oracleのprogressive資格選択、未使用later-prefix理由、execution Aの原N/first_failure/verification/cap-planとdistinct inclusive expenseの写像を完成し、独立確認する。正式freezeは実結果の保存再検算後に行う。

[原測定・計算・由来](runtime-evidence/files.json)。SHAは由来の照合だけに使い、金融数値は許容誤差/標準誤差で検算する。

## 原サイズlabelのメモリ・保存部品を実測（2026-10-10）

[事前4GiB RSS/180秒の部品予算](pilot-execution-evidence/task-5-formal-controls-review-allocation-root-budget-v3.json)を固定し、決定論的な合成primitiveで原N65536・high/date0の全65thresholds・16blocksを保持してnative label生成と実writer/readerを測った。金融RNG・SDE・教師生成・価格精度の認証は実行していない。

[親込み実測](pilot-execution-evidence/task-5-formal-controls-review-allocation-observation-root-v3__parent-cost-and-decision.json)はwall5.711958秒/CPU5.696560秒・peak process RSS2,938,032,128 bytes。10個の別label配列とaliasを全サイズで保存復元し、4packsの総expanded380,125,208 bytes・最大chunk103,591,984 bytesをNPY header込みで独立照合した。256MiBのchunk上限はRSS上限ではない。この部品値には実金融driver・teacher・sourceチェック全体の負荷を含まず、全jobのRSS/時間へ転用しない。

先行v2はlabel生成と保存後にnumpy private header APIのAttributeErrorで失敗した。元script/log・wall4.491934秒/CPU4.473477秒・peakRSS2,937,831,424 bytesを保持し、v3はpublic NPY version readerへの最小変更だけで再実行した。正式pilot/main・金融資格はunknownのまま。

## 現fieldのdomainと全体保存予算（2026-10-10）

[原計測と候補レビュー](pilot-execution-evidence/task-5-formal-controls-review-report.md)は元37quote・8group・field257×321を保持し、同dx0.00075でPDE幅1.8（4801×3840）から2.4（6401×3840）へ広げた。全37値は有限・supported、最大価格誤差0.000104128828、幅による最大差2.23821e-13。rootの親込みwall38.325237秒/CPU38.740571秒・peakRSS755,789,824 bytesで、保存結果を独立に再計算済み。CF/RNGを追加せず、独立コール表の幅2.25・全倍率の精度へ転用しない。

全20teachergridが実行される最大経路のsample保存下限は、現encoderの11 entriesで1,587,356,762,112 bytes（約1.44TiB）。現volumeの空き602,157,051,904 bytes（約560.8GiB）を超え、primitives/driver等は別に加わる。既存1e9 path-step capはfinancial child単位で、全20gridが範囲内。aggregateをglobalcapへ読み替えて候補を除外できない。元N/roster/possible jobsを保ち、全体保存予算・真正capまたはrevisionの判断が正式pilot前に必要。全体storage capは現sourceに未実装で、予算は未承認。

## 現行全コール表と独立参照表の実測（2026-10-10）

固定v56のsource80と現field257×321、元入力を事前予算へ結合してから実native workerを実行し、返却rawを検査より先に保存した。初期全NaN/未処理、原失敗、reference unknownを保持。次の値は生成・保存・native read/check・親起動を含む実測であり、金融精度の認定ではない。

| 部品 | 元の形状・全枠 | 親込みwall秒 | CPU秒 | 個別process peak RSS bytes |
|---|---|---:|---:|---:|
| M2 Heston全49日付call cache | 49×65×33 = 105,105 | 55.631470 | 56.356544 | 854,126,592 |
| M3 local全49日付call cache | 49×65×7 = 22,295 | 7.666767 | 7.735771 | 854,421,504 |
| M4 Heston独立call table | 3levels×1×7×33 = 693 | 5.467673 | 5.250679 | 853,876,736 |
| M5 local独立call table | 4levels×1×7×7 = 196 | 35.560856 | 36.269271 | 854,016,000 |

全返却価格は有限。M2/M3のreferenceは未測定のまま、M5のprice-unit error196件は元NaNのまま保存した。Heston第3独立levelのupper500/limit1600/epsabs1e-13/epsrel1e-12、localの原domain幅2.25を保持。M4/M5の元controls={}と、事前に固定したupper250/space2401/time1920/width1.8のcontrols差を3種類の引数bindingで区別した。M1の同dx幅2.4とは別条件である。

[全cacheの独立判断](pilot-execution-evidence/task-5-current-whole-call-cache-independent-v3-decision.json)は元127,400枠、[独立表の判断](pilot-execution-evidence/task-5-current-independent-call-table-independent-v3-decision.json)は保存CF1,386積分とPDE28曲線から元693/196価格を再構成してPASS。source80/入力/保存34files不変、capなし、新solver/RNGなし。保存検査の計時はM2/M3が9.388497秒、M4/M5は先行import失敗3.216240秒＋成功3.328490秒を別保存し、未測定の準備/報告費用はunknown。正式全state精度・storage budget・pilot/main・phase受入は未承認。

原始全経路/診断/元統計を保持する教師専用保存形式の限定実装と、原N65536・全65threshold・全768stepstatusのI/O測定を準備中。全体storage削減率は未確定。次は同じ原driverを使うgenuine N1024の4教師classを生成＋保存SDE再計算まで測り、全job予算を固定する。
