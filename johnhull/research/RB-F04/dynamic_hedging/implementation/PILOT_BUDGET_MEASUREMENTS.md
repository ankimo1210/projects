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

原始全経路/診断/元統計を保持する教師専用保存形式を限定実装し、原N65536・全65threshold・全768stepstatusの合成I/O測定を完了。全体storage削減率は未確定。原N1024四classの生成・保存を実測したが、保存checkerの3classが実RSS capで停止した。下記M6の停止/実費を保持し、検査レポートのbounded化と元rawのsaved再検算後に全job予算を判断する。

## 教師専用保存と全status付き最大Nの検査（2026-10-10）

[限定実装記録](pilot-execution-evidence/task-5-teacher-storage-implementation-report-v1.md)：completed native root teacherだけに固定recipeを適用し、全primitive・元summary/status/16block/covarianceを物理保存する。重複する10種類の全N×threshold標本＋f_samples aliasを読み込み時に再構成する。writerは元全標本/統計を照合してから省略し、readerは独立保存した元統計と照合して元統計を保持する。金融数値は既存rtol=2e-9/atol=2e-10、shape/dtype/NaN/inf/statusは保持。source/input/driver/原物理receiptをSHAで結び、再構成金融標本のビット一致を合否へ用いない。

新nodeのphysical binding、旧literal/raw_sha256・cap/sourcefault/nestedとの互換を保持。private protocolのcompress=False既定を保ち、新teacher自身のpacksのみ圧縮する。public API・依存・金融計算・元N/casesは不変。storage46＋protocol54=100、pilot191、closure14、main transport/resume7のscoped testsと5Python Ruff/formatがPASS。現在の実runtime closureは81files/dynamic0（旧v56測定はsource80のまま保存）。[独立codec検査](pilot-execution-evidence/task-5-teacher-storage-independent-v1-results.json)は保存N32全key/元統計/全標本・旧形式15正例と60改変拒否を確認した。

原N65536・全65threshold・16blocks、9本のfloat64 primitive、65536×768 uint8 stepstatus、U128 failure reasons、U7 statusを含む合成単一nodeを、事前4GiB/180秒の行政上限で生成・保存・復元した。[外側実費](pilot-execution-evidence/task-5-teacher-storage-full-status-io-root-enclosing-cost-v1.json)はwall10.928016秒/CPU11.138593秒、個別peakRSS3,466,457,088 bytes。全11標本と全返却payloadの復元を確認、capなし・81source不変。外側CPUは内部parent+childを含みobserver自身のCPU/最終receipt書込はunknown、内側費用と加算しない。

[独立全N検査](pilot-execution-evidence/task-5-teacher-storage-full-status-io-independent-v1-results.json)は全46 NPY headers、physical payload93,602,864 bytes・expanded93,608,752 bytes・全status/shape/dtype、原raw/aux payoff全行、全N平均/SE・16block/joint covarianceを再計算した。独立検査wall5.471255秒・peakRSS3,126,276,096 bytes。原保存10files不変、新RNG/金融workerなし。

これは合成transportの検査であり、genuine教師の圧縮率・計算速度・金融精度を示さない。原全20gridの353,606,441,728 bytes以上のmandatory展開下限、各volumeの容量、main/oracle/復元の同時占有を保ち、genuine N1024四classの実測後に正式保存/実行予算を判断する。正式pilot/freeze/main・両保管庫の新金融semantic・研究受入は未完了。

## 原四教師class（M6）の実測

元N1024・12日付・全108/156/520/1344節点（計2,128）、元seed H138674072/local1345225788、共有driver2本を保持して実行した。4classとも元全節点の生成とfull raw保存まで完了、未生成節点0。行政上限はclass別300/300/600/900秒・個別process RSS4GiBで、所要時間予測ではない。

| 元class | 節点 | 親込みwall秒 | 検査工程の結果 | 実child peak RSS bytes |
|---|---:|---:|---|---:|
| Heston coarse | 108 | 72.053259 | 検査・保存読込まで完了 | 1,926,557,696 |
| Heston high | 156 | 114.619496 | 実RSS cap、金融資格unknown | 4,326,535,168 |
| local coarse | 520 | 383.121392 | 実RSS cap、金融資格unknown | 4,361,334,784 |
| local high | 1,344 | 831.816587 | 実RSS cap、金融資格unknown | 4,298,833,920 |

[最外側実費](pilot-execution-evidence/task-5-current-full-teacher-root-enclosing-cost-v2.json)はwall1,401.807424秒・内部parent/child CPU1,406.361056秒。各class合計wall1,401.610735秒と別に保持し、外側と内部を加算しない。driverの生成費用はcoarse ownerに一度だけ含む。全81sourceはbefore/after一致。外側observer自身のCPUと最終receipt書込費用はunknown、元失敗/部分artifactを保持する。

停止原因として、grid checkerが各節点の全label標本とcovariance/blockを検査結果にも複製する構造を確認した。local highの10種類N×65標本だけの論理量は7,156,531,200 bytes、covariance/blockだけでも約2.60GB。これらは実RSS予測とは区別する。元raw・統計・全N/閾値・全saved SDE/label/cache比較を保持し、検査レポートだけを原raw参照＋小要約にするprivate修正を完了。旧測定をPASSへ書き換えず、新sourceで元生成rawの保存再検算を完了した。新SDE生成/原乱数の再生成は行っていない。

本測定の保存geometry・物理bytes・費用/capは[独立レビュー](pilot-execution-evidence/task-5-current-full-teacher-independent-m6-v2-review.md)で限定承認された。全2,128節点のnative NPZは1,516,806,775 B、展開NPYは5,618,426,336 B（full-teacher/cache/driver/checkerは別計上）。全物理4,331 artifactsと96選択節点の原Nラベル/価格統計を確認し、原unknown_underresolved 47,182を保持。これは全節点Greek/SDEの独立再演算や全正式容量の保証ではない。金融精度・全phase容量/rate・正式pilot/main/研究受入は未承認。保存済みの原4classを全N検算する[再検査候補](pilot-execution-evidence/task-5-M6-saved-recheck-preparation-report-v1.md)は純行政30件/Ruff PASS。全terminal入力13,157 files/5,437,753,447 Bを固定し、原producer81と新checkerの由来を分離して、別のroot事前予算で全N保存再検算を完了した。M7の元state00/2model/N4096/13query/768–1536も、原controls={}と保存M4/M5明示controlsとの差を別root事前予算で結合した上で、部品計測を完了した。各結果と承認範囲は以下に分けて記録する。

## Bounded検査レポートの限定修正

全Nのsaved SDE・全11ラベル・元16block/covariance・全cache比較を終えてから、検査レポートのlabelsを原raw path/既存physical binding/shape/dtype参照へ置換した。元rawの全配列・費用・failure/unknownは保持し、既定fullとstandalone checkerは不変。cache=Noneは逐次消費し、正式grid/domain-selectionの2呼出だけboundedを明示する。runtime復元contextはレポートへ保存しない。

専用17件・影響する既存46件・2Python Ruff/format PASS。[独立source/transportレビュー](pilot-execution-evidence/task-5-teacher-check-report-bounded-independent-v1-review.md)は7正例/11改変拒否・元root不在のfull cached report保存/semantic比較で限定承認。実closure81/dynamic0、旧80ファイルは不変、正式identityはrun_reference._digestの408f2bc2…（payload_digestとの算式差の訂正を保持）。これは原M6/最大NのRSS・金融精度・正式予算lockの承認ではない。元N1024/2,128節点・元driver2本の保存再検算結果は別に記録する。


## 元rawの全N保存再検算（M6）

[root事前予算](pilot-execution-evidence/task-5-M6-saved-recheck-budget-root-fixed-v1.json)は原N1024・全2,128節点・元共有driver二本・全11標本/16blocks/covariance/cacheと、固定checker source81を結合した。原driverを読み、保存SDE/全ラベル/統計/cache比較を全節点で行い、bounded reportの保存読込まで完了。新RNG/教師生成なし、未検算節点0、実cap0。

| 元class | 元節点 | 親込みwall秒 | 親＋child CPU秒 | child kernel peak RSS bytes |
|---|---:|---:|---:|---:|
| Heston coarse | 108 | 31.008640 | 31.122087 | 703,631,360 |
| Heston high | 156 | 50.187349 | 50.395210 | 758,280,192 |
| local coarse | 520 | 186.486414 | 187.301769 | 829,755,392 |
| local high | 1,344 | 506.164096 | 508.509975 | 1,490,243,584 |

[最外側実費](pilot-execution-evidence/task-5-M6-saved-recheck-root-enclosing-cost-v1.json)はwall774.091347秒・child tree CPU777.573424秒。内側合計wall773.846499秒・親child CPU777.329041秒は部分区間として保持し、加算しない。外側自身の最終receipt/stdout費用はunknown。旧生成1,401.807秒と3実RSS capsは原履歴として保持し、再検査実費へ重複加算しない。原unknown_underresolved 47,182も変更していない。[独立saved-onlyレビュー](pilot-execution-evidence/task-5-M6-saved-recheck-independent-v1-review.md)では元raw由来・全23,408標本参照/件数・cacheの許容誤差比較を確認したが、新しいSDE再演算や金融精度の認定は含まない。

## 元state00の独立oracle部品（M7）

[root事前予算](pilot-execution-evidence/task-5-current-oracle-budget-root-fixed-v2.json)を固定して、元state00・N4096・全13query・coarse768/fine1536・seed3631740690・16chunks/16blocks・3差分幅を両modelで実行。各modelで26×4096=106,496 payoff枠が全有限、未処理0、実wall/RSS cap0。返却raw・初期NaN義務・元費用・driver mappingを保存してから、全saved payoff/Greek/block/covariance算術と保存読込を実施した。

| model | 親込みwall秒 | child CPU秒 | sampled child peak RSS bytes |
|---|---:|---:|---:|
| Heston | 13.744001 | 13.725373 | 847,294,464 |
| local | 90.384456 | 90.308574 | 853,979,136 |

[最外側実費](pilot-execution-evidence/task-5-current-oracle-root-enclosing-cost-v2.json)はwall104.215732秒・child tree CPU104.624358秒。inner合計104.128456秒は部分区間、元M4/M5表生成費用は既存履歴で再加算しない。実payoff transitionsは各122,683,392、driver steps6,291,456、保守的work宣言163,577,856とは区別する。

[独立saved-only検算](pilot-execution-evidence/task-5-current-oracle-saved-arithmetic-independent-v5-report.md)は34,149比較・1,692,611値（alias再照合込み）を確認、最大差7.1e-15。全433費用/modelと元clock、source81/input39/観測61ファイルの不変を確認した。今回のbaseline selected-call refinementはH0.040297秒/local59.122619秒で、親実費に含む。親wallを純path速度として外挿しない。監査v1–v4失敗を含む5child実費17.458261秒/CPU30.403173秒を別保存し、未測定準備等はunknown。

M4/M5の保存表を部品参照として使用し、graph原controls={}と明示controlsの差はroot priorに記録した。全stateでの同等性・金融精度・正式予算の承認ではない。nativeはnormalを保存しないため、新RNGなしで独立path generationを再演算したとは主張しない。原unverifiedのindependent_path_generation/full_common_domain_call_fitと金融qualification unknownを保持する。

## 全体容量の静的整理

[元metadata/headerに基づく整数計算](pilot-execution-evidence/task-5-whole-phase-capacity-static-v1-report.md)と[元M6/M7終端ファイル一覧](pilot-execution-evidence/task-5-M6-M7-terminal-observations-root-v2-manifest.json)を保存した。

全20教師候補の論理配列部分下限353,606,441,728 Bを元N/全grid/全status/16block/covarianceから再現した。現native項目のnode配列名目量は355,868,451,168 B、共用driver・grid/cache・bounded reportを加えた限定小計は364,185,768,816 B。圧縮後のCAS物理容量の上界・下界ではなく、他3,088 jobs・metadata・複写・旧失敗履歴・stagingは別。N1024の実圧縮率を最大Nへ保証付きで外挿しない。

各volumeの観測空きはC314,778,112,000 B/F185,710,804,992 B/WSL595,309,969,408 B。両保管庫は同じcorpusをそれぞれ保持するので空きを合算しない。whole物理容量と復元ピークは未確定、原N65536/highの真正一節点は次の限定資源測定候補。正式pilot/freeze/main・金融qualification・研究9受入は未完了。


## 事前予算の元契約確認

[契約照合](pilot-execution-evidence/task-5-fullmixed-prior-budget-independent-contract-gap-v2-review.md)で、元DESIGNが要求するのは予定保存byte・実測/明示推計・元job/phase work/cost priorであり、圧縮後の全体物理容量の保証上界やwhole-storage source capは追加必須条件ではないことを確認した。全3,138 jobsのbudget/expanded chunk/rate出所、元121/51のcap options・実親費用・10外部費用、source81/原入力の再結合を次のroot configで行う。

容量はvolumeごとの明示推計と実空き/RSS/wall監視で扱う。監視停止は原義務/費用/partialを保存し、金融case/A cap合格へ投影しない。未知の増加速度からディスク枯渇防止を保証しない。原N/全case/閾値、main/fresh・両保管庫の数値復元・3図/notebook・最終関連suite条件を維持する。unknown/不支持は研究成果に許容されるが、未完attemptや未閉鎖source/integrityは完了と数えない。

候補組立で、選択Nが変わるcase/attemptのcap optionをparent jobだけで選ぶconsumer境界に未解決の接続を確認した。正式callerは実selector hashをrow証跡へ分ける既存処理を持つ。4N候補の先頭を無条件に使わず、元template＋選択Nの静的branchと実親費用/事前decisionを照合する必要がある。[最小案](pilot-execution-evidence/task-5-conditional-n-prior-cap-consumer-minimal-proposal-v1.md)はparent＋plan一致を選択条件へ追加し、既存SHA検査と複数親の順序を保つ。元N固定やcap合格への置換は行わない。最大N部品測定後、原入力・数学を保つ限定修正を検討する。
