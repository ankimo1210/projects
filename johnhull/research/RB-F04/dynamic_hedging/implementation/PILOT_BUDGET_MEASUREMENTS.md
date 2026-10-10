# 正式pilot予算のための測定

修正版fresh正式pilotは12:34:56 UTCに終了（外側7,930.370秒、約2時間12分）。214件目のHeston/N1024/coarse stage gateで引数bindingの不一致を検出し、status=unclosed_source_or_solver_defect・qualification unknownのpartialを保存した。行政資源停止はなく、source81/入力/priorは不変。原失敗・費用・元3,138 jobs/121 cases/51義務を保持し、原因修復・再検証・原rawのsaved数値検算・freeze/mainは未完了。 [終了証跡](pilot-execution-evidence/task-5-formal-pilot-root-terminal-readonly-summary-v1.json).

2026-10-10。修正版正式金融pilotは214件目の引数binding不一致でpartial停止、mainは未実行。以下の先行測定は**部品の実測と、歴史的教師計算からの外挿**であり、全phaseの実測時間・精度資格ではない。現在の実起動は末尾に記録。

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

各volumeの観測空きはC314,778,112,000 B/F185,710,804,992 B/WSL595,309,969,408 B。両保管庫は同じcorpusをそれぞれ保持するので空きを合算しない。whole物理容量と復元ピークは未確定。原N65536/highの真正一節点は下記で生成・保存と全N保存検算を測定した。正式pilot/freeze/main・金融qualification・研究9受入は未完了。


## 事前予算の元契約確認

[契約照合](pilot-execution-evidence/task-5-fullmixed-prior-budget-independent-contract-gap-v2-review.md)で、元DESIGNが要求するのは予定保存byte・実測/明示推計・元job/phase work/cost priorであり、圧縮後の全体物理容量の保証上界やwhole-storage source capは追加必須条件ではないことを確認した。全3,138 jobsのbudget/expanded chunk/rate出所、元121/51のcap options・実親費用・10外部費用、source81/原入力の再結合を次のroot configで行う。

容量はvolumeごとの明示推計と実空き/RSS/wall監視で扱う。監視停止は原義務/費用/partialを保存し、金融case/A cap合格へ投影しない。未知の増加速度からディスク枯渇防止を保証しない。原N/全case/閾値、main/fresh・両保管庫の数値復元・3図/notebook・最終関連suite条件を維持する。unknown/不支持は研究成果に許容されるが、未完attemptや未閉鎖source/integrityは完了と数えない。

候補組立で、選択Nが変わるcase/attemptのcap optionをparent jobだけで選ぶconsumer境界に未解決の接続を確認した。正式callerは実selector hashをrow証跡へ分ける既存処理を持つ。4N候補の先頭を無条件に使わず、元template＋選択Nの静的branchと実親費用/事前decisionを照合する必要がある。[最小案](pilot-execution-evidence/task-5-conditional-n-prior-cap-consumer-minimal-proposal-v1.md)はparent＋plan一致を選択条件へ追加し、既存SHA検査と複数親の順序を保つ。元N固定やcap合格への置換は行わない。最大N部品測定後、原入力・数学を保つ限定修正を完了した。
## 真正最大Nの一節点と保存検算

元local/high・N65536・date0/spot100/state1・node17・65thresholds・16blocks・seed1345225788を保持した。元mother jobは1,344節点のままで、一節点の測定を全母jobの完了や全域の金融精度とは数えない。共用bankの全256chunksと元N1024 prefixを照合した。

生成・full raw保存・native readまで完了したが、最初の保存検算は個別child RSS4,310,867,968 Bで事前4 GiB上限を超えて停止した。[旧外側実費](pilot-execution-evidence/task-5-maximum-original-node-root-enclosing-cost-v1.json)はwall83.231006秒/child tree CPU83.450557秒。元未検算義務・原raw・bank・停止・費用を保持している。生成worker区間33.329730秒は内側の一部で、外側へ加算しない。

[保存専用の新事前予算](pilot-execution-evidence/task-5-maximum-original-node-saved-budget-root-fixed-v1.json)を300秒/親子各8 GiBで固定し、原rawを一コピーだけ読んで再検算した。新RNG・bank生成・teacher生成は実行禁止。全Nの保存SDE、全11標本、元16blocks/covarianceの比較とbounded reportの保存読込が完了した。[外側実費](pilot-execution-evidence/task-5-maximum-original-node-saved-root-enclosing-cost-v1.json)はwall39.413927秒/child tree CPU39.511260秒、sampled child peak RSS3,721,838,592 B、kernel peak3,721,367,552 B、実capなし。内部39.379452秒と旧83.231006秒は別区間・履歴として保持し、今回の費用へ重複加算しない。

[rootの限定確認](pilot-execution-evidence/task-5-maximum-original-node-saved-root-component-review-v1.json)は全N/元geometry/検算完了・生成0・source81不変を確認した。真正raw物理6,280,626 B/保存primitive展開94,658,320 B、共用bank物理807,061,160 B/展開806,354,944 B、新bounded report物理19,035 B。返却された全標本の論理配列469,524,240 Bとは区別する。単一節点の圧縮率や39秒を全1,344節点・全日付の保証へ転用せず、保存検算の予算はN/格子別の明示推計で検討する。金融qualification・全mother/phase完了はunknownのまま。

## Conditional Nのprior cap消費を限定修復

親IDだけで先頭のcap optionを選ぶ条件へ、capを除いた具体化plan全欄の一致を追加した。他Nの枝を通過し、元option順で最初の互換親を選ぶ。元複数親/全費用binding・metric/limit・decision/plan SHAの検査、正式callerの実selector証跡分離は保持する。金融solver・元N・公開APIは変更していない。

[実装記録](pilot-execution-evidence/task-5-conditional-n-prior-cap-consumer-author-v2-report.md)は修復前8 failed/14 passed、追加22 passed・関連既存16 passed、2Python Ruff/format PASS。[独立限定判断](pilot-execution-evidence/task-5-fullmixed-prior-budget-independent-v2-source-decision.json)で4N/複数親順・actual cap guardsを確認した。実closure81/dynamic0の変更はcheckerのみ、他80 sourceは不変。現identityはdc7631fe…、元N測定/false予算候補の408f2bc2…は原由来として保持する。

全3,138-job prior候補は未承認。全20 teacher_domain_selectionは元N/格子別の保存検算を明示推計し、local high/N65536は52,972秒・3倍余裕の159,000秒を候補とした。16 teacher_candidate_gate・2 teacher_selectionと最初のactivationにも保存SDE再検算が含まれるため、単なるmetadataの600秒候補を実測にもとづく見積へ補足中。元required rosterの反復は省かず、金融精度・正式lock・freeze・main・phaseの承認へ広げない。

## 全stage実行時の再検算反復と工程見積り

[原required rosterに基づく未承認補足v4](pilot-execution-evidence/task-5-fullmixed-prior-budget-candidate-author-gate-selector-supplement-v4.md)は、16gate・2selector・初回activationの保存SDE再検算を費用見積へ追加した。最大local-high stageのrequired213件には4教師rawと4domain-selectionの全検算が含まれ、selectorは各modelの最大8 executed gatesを再検算する。activationは14 cache unitsの最大1回を予測に含め、2332 eligible jobsへ配る保守予算の総和を実時間へ加えていない。

全stageが必要な初期phaseの既知部分外挿は、ordinary174157.908秒＋20domain163210.857秒＋16gate700138.342秒＋2selector700138.342秒＋activation447126.751秒＝2184772.200秒（606.881時間、約25.3日）。未観測kernel/IO/外部10費用/resumeは含まない。実際の終了時間や確定した仕事量ではなく、qualified prefixで短縮され得る一方、数日以内の完了を裏付けない。

数日の工程見積りを取り下げ、同じ不変source/input/job/raw/driverの全N検算結果をphase内で安全に再利用できるか、既存context境界を調査する。元N/全case/閾値/数学・初回の全SDE/11labels/16blocks/covariance検算と原失敗/unknownは維持する。fresh・独立検証・両保管庫semanticは別contextで実施する。再利用案は下記の限定source確認と部品実測まで完了した。v1–v4の原費用見積を履歴として保持し、正式全phase予算・lockは未承認。

独立の[変更検知・保持範囲の読取調査](pilot-execution-evidence/task-5-phase-local-saved-check-memo-independent-tamper-review-v1.md)では、同一実行contextのbounded teacher-grid検算結果に限る条件付き案を確認した。各利用で実入力・全node/driverの物理証跡を再結合し、fresh・独立検証・保管庫復元では空contextから検算する。入力読取・hash費用と短縮後の所要時間は未測定で、現在source・金融計算は変更していない。

## 同じphase内の検算結果再利用（2026-10-10）

[固定v2](pilot-execution-evidence/task-5-phase-verified-raw-memo-fixed-v2-results.json)をrootが適用し、[関連既存240tests・Ruff/format](pilot-execution-evidence/task-5-phase-local-reuse-root-regression-v1-results.json) PASS。[独立source判断](pilot-execution-evidence/task-5-phase-local-reuse-independent-decision-v1.json)は18実probeで限定承認。初回は元の全N/SDE・全11label・16blocks・共分散・cacheを検算し、同一producer/operation/計算引数の次回だけ小さな検算結果を再利用する。hitにも現在のsource・入力・元node/driver全ファイル内容の確認とcopy費用がある。failed/capped/partialは登録せず、元unknownを保持する。fresh/resume/review/保管庫復元は新しい空contextから検算する。

真正M6 Heston-coarse、原N1024・108節点・12日付・全33閾値を[実事前180秒/8GiB予算](pilot-execution-evidence/task-5-phase-local-memo-resource-root-approved-v1.json)へ結び、一回のsaved-only部品計測を実行した。

| 呼出し | 実wall秒 | 実CPU秒 | 元全grid checkerの新規呼出し |
|---|---:|---:|---:|
| 初回・空context | 23.670931 | 23.651921 | 1 |
| 同じcontextで再利用 | 0.222289 | 0.222287 | 0 |
| 別の空context | 23.796868 | 23.780474 | 1 |

[実親receipt](pilot-execution-evidence/task-5-phase-local-memo-observation-root-v1__parent-cost-and-decision.json)はcapなし・最大観測child RSS696,823,808 B。[root外側時計](pilot-execution-evidence/task-5-phase-local-memo-resource-root-enclosing-v1.json)はwall52.226233秒、全子CPU50.627967秒。金融生成/RNG 0、原701入力とsourceの終了時再照合PASS、元金融資格unknownを保持。各返却reportの全108節点/全N検算記述は初回証跡を表し、当該呼出しでの実SDE実行有無は別のmemo eventとchecker呼出しcounterで区別する。

この一例の再利用部分は初回比106.5倍。hitでもPython binary read 49,985,348 B・SHA入力70,677,598 Bを観測した（OS device IOやC/mmapは未計測）。全体速度への一般化はしない。大N/別gridでのhit費用、初回検算、非teacher gate、生成、独立fresh/両復元の費用を含む新全phase予算は次に確認する。旧606.881時間は旧方式の既知部分外挿であり、残時間の確定値ではない。

v2のsource81/dynamic0のplain canonical identityは959f879a…（runner._digest）、native job/memo payload identityは0df11d81…（runner.payload_digest）。同じ81 sourcebytesの別符号化であり、旧generation4e8f8b…・旧saved checker408f2b…を置き換えない。独立probeの初期hash算式誤認とNaNセルへの無効な改変probe、author接続時の元失敗・実費用は各manifestに保持する。正式pilot/freeze/main・金融受入は未実施。

[現v2の未承認予算補足v5](pilot-execution-evidence/task-5-fullmixed-phase-local-reuse-budget-supplement-author-v5.json)は、全stageが実行される仮定で初回40 cold/840 hit、110 gate・非teacher 22,550 rowsを数えた。旧部品rateだけの更新小計は初回139.050時間、各full saved/fresh/restore contextの60 cold部分は136.009時間。新wall capの承認や全体ETAではなく、hot guard・非teacher kernel・IO・外部費用等は未観測。full savedの余分20 keysが行政引数wall/work-directory差だけに由来する点を確認し、限定修正v3を適用した（次段落）。v5はv2時点の未承認候補として原byteを保持する。元3,138jobs/121cases/51obligations/全4N/全capsを保持する。


### 計算に無関係な引数差の重複検算（v3）

[固定v3](pilot-execution-evidence/task-5-phase-verified-raw-memo-fixed-v3-manifest.json)はproof keyからトップレベルのwall_cap_seconds/work_directoryだけを除く。全引数SHAと外側のtyped input・cap監査は保持し、producer/operation・seed・driver・金融入力・物理byteが異なる証拠へは転用しない。他80 runtime sourceと元数学は不変。

[独立判断](pilot-execution-evidence/task-5-phase-local-admin-proof-key-independent-decision-v1.json)は元N16/Hcoarse108節点を用いた9境界を確認（保存432節点の全N検算）。別contextと別producer、driver差は全検算、seed/金融入力改変は拒否した。[root適用検証](pilot-execution-evidence/task-5-phase-local-admin-proof-key-root-v2-results.json)は関連phase_memo14tests・2Python Ruff/format PASS。初回root検証scriptのimport誤りは金融実行前に修正し、元scriptと失敗を保存した。

現source81/dynamic0はplain canonical 1cc16cf7… / native payload be858ced…（異なる符号化）。前節の23.671/0.222/23.797秒はv2時点の同一M6ケースの実測として保持し、v3全体のrateやETAへ転用しない。新sourceの全仕事key件数に基づく予算更新は別途確認し、正式pilot/main・金融資格は未承認。


### 現v3の全仕事キーと正式prior準備（v6）

[未承認v6候補](pilot-execution-evidence/task-5-fullmixed-phase-local-reuse-budget-supplement-author-v6.json)を、[独立697件のmetadata照合](pilot-execution-evidence/task-5-fullmixed-phase-local-reuse-budget-independent-v6-decision.json)で確認した。元3,138jobs/121cases/51obligations/全4N/573,122 cap optionsは不変。全stage実行の仮定では初回110 gate・40 cold/840 hit、別full saved contextは96 gate・40 cold/768 hit。raw20とdomain20は別producerのまま、行政引数差による余分20 coldだけを解消した。

旧部品rateでの初回既知小計139.050h（5.79日）と、別contextのcold部分90.673h（3.78日）は限定外挿。再利用guard・非teacher kernel・IO・外部10費用等が未測定なので、合計ETA・保証上限ではない。v2の一例106倍を全体へ適用していない。

[実root運用prior](pilot-execution-evidence/task-5-formal-pilot-root-operational-resource-prior-v2.json)は行政wall allowance30日・個別process RSS16GiB・WSL/C/F各10GiB reserve・poll1秒を固定した。30日は所要時間の予測ではない。停止はpartial/unclosedとして残し、金融cap PASSや受入へ置換しない。作成時MemAvailable約48.7GB、空きWSL約594.1GB/C約323.2GB/F約185.7GBを確認した。起動前に実容量とsource/inputを再確認する。

全3,138jobの予算と元2332 potential-first activation allowances、元全cap recipeを独立確認する候補・現source対応materializer/monitorを準備中。v6の件数確認は正式全prior承認に代用しない。正式lock/金融pilot/freeze/mainは未実施。

## 正式prior固定と実起動（2026-10-10）

[全3,138資源priorの独立判断v2](pilot-execution-evidence/task-5-fullmixed-prior-budget-independent-final-decision-v2.json)は既存18bindings・元121cases/51obligations・4N・全573,122 cap optionsを限定承認。12行の歴史的実測と3,126行＋16 conditional branchesの明示見積りを区別し、全runtime/物理容量/外部費用のunknownを保持した。元v1不承認はmonitorの実fieldと異なるtokenを使ったレビューprobe誤りとして保存し、実SOURCE_IDENTITY/financial_A_cap_projection_approved/volume_probesの機構で最終47件PASSを確認。source限定承認だけを全budget承認へ転用していない。

[root実prior承認の結合](pilot-execution-evidence/task-5-formal-prior-actual-root-binding-receipt-v1.json)で、各budget.review_sha256へ実独立decision3cf74462…を結合。[元APIによる実metadata生成](pilot-execution-evidence/task-5-formal-prior-lock-materialized-root-v2__materialization-progress.json)は原3,138/121/51/20teachers/10driversと全573,122 literal options、source81/dynamic0の不変を確認。全計画metadata648,421,785 Bを元native writerで保存し、locked artifact69fc5288…を生成した。金融RNG/SDE/solverは0。[実保存計画とguardの限定独立確認](pilot-execution-evidence/task-5-formal-prior-materialized-and-guard-independent-decision-v1.json)はroot承認3,170・実plan577,045・guard32項目PASS。全literal optionsを原parent順・4N・各branch/cap planSHA・実decisionへ照合し、金融資格はunknownを保持した。

[最外側の実費](pilot-execution-evidence/task-5-formal-prior-lock-materialization-root-observation-v1__parent-cost-and-status.json)はwall66.171689秒、child CPU64.630352秒、kernel peak RSS3,884,457,984 B、capなし。内側64.396329秒を重複加算しない。外側receipt尾部費用はunknown。

[別root実起動許可](pilot-execution-evidence/task-5-formal-pilot-root-launch-binding-receipt-v1.json)で、現source・生成済みplan全tree・原typed inputs全tree・実full prior・monitor SHAを結合。起動直前空きはWSL約593.4 GB/C約322.1 GB/F約185.7 GB、MemAvailable約48.4 GB。全物理容量は保証していない。

初回正式pilotを2026-10-10 09:16:40 UTCに起動。実native child PID287118/monitor287117を確認し、同09:26:20 UTCに終了した。root行政30日・各process RSS16GiB・各volume reserve10GiBの元選択で監視し、停止はpartial/unclosedとして保持する。これらはETA/金融A cap/精度受入ではない。[実進捗観察](pilot-execution-evidence/task-5-formal-pilot-live-root-observation-v1.json)では初期field/premium・両call cache・両modelのN1024/coarse rawとdomain artifactを保存し、N4096/Heston coarse生成へ進んだ。jobの保存数・nodeディレクトリ数を精度PASSや工数割合とは扱わない。完走・保存金融結果のsemantic検算・freeze/main・研究9受入は未完了。[実sessionの引継ぎ](pilot-execution-evidence/task-5-formal-pilot-actual-root-exec-handle-v1.json)は起動時点の履歴。session15463/PID287118/287117はterminalで、同じ観察timeoutを理由に再起動しない。EXIT0だけで実結果を完了と数えない。

次は原正式pilotの実結果保存検算、実教師選択とfreeze、原774-job main・独立fresh・両保管庫の数値復元・3図/notebook・最終3suite。後続の多曲線risk/P&Lと増分XVA＋IM/資本も残す。

### 初回pilotのsourcefaultと限定修復

[終端snapshot](pilot-execution-evidence/task-5-formal-pilot-terminal-root-summary-v1.json)は69件executed・1件unclosed_source_or_solver_defect。最初の日付gate stage:Heston:N1024:coarse:date-gate:Heston:0 が KeyError N を保存して停止し、後続3,068 jobsは未実行。raw None・金融qualification unknown・元未閉鎖義務を保持する。資源capによる停止ではない。[最外側費用](pilot-execution-evidence/task-5-formal-pilot-root-enclosing-observation-v1__parent-cost-and-status.json)はwall580.028628秒・child CPU578.566955秒・kernel peak RSS5,610,414,080 B。内側phase555.031004秒はその一部で、重複加算しない。

[独立原因確認](pilot-execution-evidence/task-5-formal-date-gate-N-contract-independent-decision-v1.json)で、native teacher/domain-selected/stateの3cacheがoriginal_N=1024のみを保持し、日付gateだけが存在しないNを読んでいたことを確認。run_date_gate_jobの返却fieldをasian_cache["original_N"]へ1行修正した。cache schema・checker・数学・元N/seed/grid/threshold・公開APIは変更していない。

[修復前の回帰](pilot-execution-evidence/task-5-formal-date-gate-N-root-RED-v1__receipt.json)は2件とも同じKeyError NでFAIL。[修復後](pilot-execution-evidence/task-5-formal-date-gate-N-root-GREEN-v1__receipt.json)は関連2test files全246件PASS（pytest135.06秒、親136.124262秒）、変更2Python Ruff/format PASS。実source-unitのnative cacheを日付gate→writer/read→実saved checkerへ通し、原N16、unknown/no_root、16block SEの許容差、原N改変拒否を確認した。source-unit testは正式金融精度や全3suiteの検査に数えない。

[修正版の独立source判断](pilot-execution-evidence/task-5-formal-date-gate-N-source-fix-independent-decision-v1.json)は96静的項目を確認し、run_pilotの1行以外のruntime80sourceを保持した。[rootの再確認](pilot-execution-evidence/task-5-formal-date-gate-N-root-source-confirmation-v1.json)も81実file bytes・RED/GREEN・独立manifestを照合。新source identityはplain5d059dc9…/native56815c0b…で、初回prior/計画/旧rawの1cc16cf7…/be858ced…を置き換えない。全予算の新source結合・金融精度・main/phaseは限定source判断に含まれない。

[再開契約の読取](pilot-execution-evidence/task-5-date-gate-source-fix-resume-contract-review-v1.md)で、新sourceと旧checkpointは既存--resumeのsource/plan一致条件を満たさず、旧sourceのままでも保存済みfaultで停止することを確認。旧69件の由来を保持して新sourceへ付け替えず、新sourceのprior/monitorを結合してfresh実行する。新continuation APIは作らない。現在の初回prior/lock/launch許可は旧sourceの履歴で、修正版の起動許可に転用しない。

[閉じた事前metadataの両保管庫保存](pilot-execution-evidence/task-5-formal-prior-metadata-cas-root-receipt-v1.json)は183 unique blobs/186 paths、両copy PASS。原648MB plan・旧source81・root承認と独立レビューを保持した。wall67.486184秒・CPU4.690202秒は保存区間の費用。終端金融raw/checkpointはこのmetadata packetに含まれず、別packetで保管する。

残時間は暫定で数週間規模、1か月以上になる余地があり、上限は未確定。元v6は別空contextとしてfinal_saved / fresh_independent_review / CAS_primary_restore / CAS_mirror_restoreの4つを明示する。全stageと元40 cold keysを各contextで検算する同じ仮定なら、既知部品は初回139.050h＋4×90.673h＝501.742h（約20.9日）。初回139.050hは初回coldを含み、初回の90.673hを再加算しない。これは旧部品rateの条件付き成分小計で、保証下限・上限・全体ETAではない。選択が早く閉じれば短縮する一方、再利用guard・非teacher・IO・外部10費用・main/fresh追加生成・図/review等は未測定。新source pilotの実選択と実費で更新し、今回580秒や69件から全完了へ比例計算しない。後続の多曲線risk/P&Lと増分XVA＋IM/資本は調査案までで、正式設計・実装・実測rateは未完了。

### 修正版sourceのprior再結合とfresh再開

[新保存計画とguardの追加独立確認](pilot-execution-evidence/task-5-formal-prior-materialized-and-guard-independent-decision-v2.json)は3447件PASS。原typed inputs/current81・全3138の実review SHA・実ef4→cd77→manifest6e355/artifact206b/metadata1809→guard a36eを照合し、既承認の予算数学を再審査していない。金融実行0、数値精度・main/phaseの承認ではない。live起動後にfresh-directory条件を再評価したreaderの時点誤用は元trace/unknown費用として保持し、source/guard欠陥へ読み替えず、root起動前の実PASS receiptを基準にした。

[限定prior追加判断v4](pilot-execution-evidence/task-5-formal-prior-lock-rebind-independent-decision-v4.json)は、旧3cfの全予算値・rows02da・元3138/121/51/4N/573122を維持し、新source5d/568への6bindingsだけを再確認した。差分151件PASS、数学予算の新規再審査ではない。元v3の268PASS/1FAILを保持し、同じrunner SHAがfilesとprotocol_sourceの2箇所に現れることを正しく扱うD materializer修復だけを確認。その他protocol/env/identityは不変で、3改変を拒否した。金融精度・main/phaseの承認ではない。

[root実追加priorの結合](pilot-execution-evidence/task-5-formal-prior-actual-root-binding-receipt-v3.json)は各budgetへ実decision ef4b8cbe…を結合。[新native計画生成](pilot-execution-evidence/task-5-formal-prior-lock-materialized-root-v3__materialization-progress.json)は実lock API/source binding PASS、source81安定、3138jobs/121cases/51obligations/20teachers/10drivers/573122 optionsを保持。新artifact206b2c86…/metadata1809cfeb…を生成。金融worker0。[最外側metadata費用](pilot-execution-evidence/task-5-formal-prior-lock-materialization-root-observation-v2__parent-cost-and-status.json)は67.172874秒、child CPU65.466859秒、kernel peak RSS3,882,967,040 B、capなし。内側65.800522秒は同区間に含み、重複加算しない。

[別rootの実起動許可](pilot-execution-evidence/task-5-formal-pilot-root-launch-binding-receipt-v3.json)は実a36ec860…guard、新plan全tree/元typed inputs/current81/実ef4 prior/monitor94dd…を結合し、既存load_guardで起動前PASS。観測空きはWSL590.2GB/C316.4GB/F182.8GB、MemAvailable48.3GB。行政30日・各process16GiB・各volume reserve10GiBは精度条件やETAではない。

修正版fresh正式pilotを2026-10-10 10:22:45 UTCに起動。root PID316326、monitor PID316327、実session21286。[起動sessionの引継ぎ](pilot-execution-evidence/task-5-formal-pilot-actual-root-exec-handle-v2.json)と[初期実観測](pilot-execution-evidence/task-5-formal-pilot-live-root-observation-v2.json)を保存した。新native root-v2と旧69executed＋1sourcefaultのroot-v1は別に保持し、旧rawを新sourceへ読み替えていない。同じhandleで観察を継続し、完走・数値saved検算・freeze/main・全研究受入は未完了。

[旧終端pilotの両保管庫保存](pilot-execution-evidence/task-5-formal-pilot-terminal-cas-root-receipt-v1.json)は6245paths/4358 unique blobs、両vault4172new＋186existing、原byte/closed roster不変でPASS。保存区間wall1226.188257秒・CPU52.484495秒。旧failed原raw/checkpointとsource/plan/費用を保持するbyte保管で、数値semantic復元の承認ではない。別の[読み取り診断](pilot-execution-evidence/task-5-formal-pilot-terminal-cas-readonly-process-diagnosis-v1.json)で既存Windows fallback publicationの逐次処理を観察した。新正式pilotのlive rawはこのpacketに含めない。


### 派生結果の保存量と原byte共有（2026-10-10）

[修正版prior metadataの両保管庫保存](pilot-execution-evidence/task-5-formal-prior-metadata-cas-root-receipt-v2.json)は326paths/235 unique blobs、両copy PASS。manifest2dae5d8d…、wall42.140秒・CPU7.021秒。旧0c/34a packetと実source/plan/承認を保持し、live金融rawは含めない。[旧停止点の実保存観察](pilot-execution-evidence/task-5-formal-date-gate-closed-metadata-observation-v2.json)では日付gate status=executed、original_n/embedded/native cache original_Nが全1024。metadata境界の確認であり、NPZの全金融saved検算・正式pilotの完走は未完了。

[独立stat診断](pilot-execution-evidence/task-5-live-capacity-independent-v1-review.md)は10:47 UTCのnative73.260GB、最初のHeston N1024/coarseだけで71.258GBを確認。[source/NPZ診断](pilot-execution-evidence/task-5-formal-pilot-storage-amplification-diagnosis-v2.json)は、上流raw/market/risk/chunks/variantsの再内包、配列出現別ID、非teacher ZIP_STOREDを原因として特定した。[metadata切分け](pilot-execution-evidence/task-5-formal-pilot-storage-metadata-paths-addendum-v1.json)ではbump root JSON549.5MB、position566.5MB、同10:56 UTCのfirst-prefix89dirsにJSON/receipt床12.978GB。live非atomic観察であり完了job数ではない。旧364GB整理は他3088派生jobsを除外しており、教師圧縮率や全phase容量へ外挿しない。

[静的契約確認](pilot-execution-evidence/task-5-closed-npz-hardlink-independent-contract-v1-review.md)を踏まえ、runtime sourceを変えずD-onlyの[closed leaf共有ツール](pilot-execution-evidence/task-5-stage-npz-hardlink-v1.py.txt)を準備した。原NPZの両実SHA・metadata/receipt・size/dev/uid/gid/mode/mtimeを確認し、native外の同FS stagingでrollback可能なatomic hardlink置換を行う。byte/SHAは保存provenanceだけに使用する。ROOTの実1組trial、bounded v1/v2で合計2124 filesの旧別inode割当53,243,871,232 B（10進53.244GB）を削減。[実postcheck](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-postcheck-v1.json)は全共有先inode・原receipt/metadata、source81不変、11合成tests/Ruff/format PASS。数学/N/cases/unknown/原失敗/原金融費用に変更はない。原JSON/NPZの値は残り、saved金融検査は省略しない。

[独立コードレビュー](pilot-execution-evidence/task-5-stage-npz-hardlink-independent-code-review-v1.md)で、helper v1のrollback自体がI/Oエラーになった場合にbackupが消え、通常rejectedへ吸収されるP2を確認した。既存2124件の成功/postcheckは維持し、v1は今後の操作に使用しない。[helper v2](pilot-execution-evidence/task-5-stage-npz-hardlink-v2.py.txt)は元backupを保持しeffect unknown/tool_exceptionを専用例外で伝播する最小修復。旧v1で新回帰FAIL、新v2は既存11＋新回帰12PASS、rootのRuff/format・元source81不変もPASS。[限定独立再確認](pilot-execution-evidence/task-5-stage-npz-hardlink-independent-code-review-v2.md)は元I/O反例・正常共有・正常rollbackの3境界PASS。この限定sourceレビュー時点ではv2の実操作0。以後のroot実適用は次段落で区別する。

[v1処理の原呼出し側失敗](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-batch-v1-wrapper-failure.json)は、180GiB読取上限の実停止を旧例外名で捕捉したためAttributeErrorとなった。648 successful links/36.873GBの原journalを保持し、[別reconciliation](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-batch-v1-reconciliation.json)で行政partialと原失敗を明示する。元finished行のcompletedはwrapper全体の完了に使わない。v2は実固定AdministrativeLimitErrorを扱い、1475links/16.284GB、90秒行政上限を正常に記録した。これは収納操作の制限であり、金融A capや精度判断ではない。

[trial](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-trial-v1.json)の外側費用は1.599秒/CPU0.222秒、v1の内側87.928秒/CPU77.756秒（外側尾部/peakはunknown）、[v2](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-batch-v2.json)は外側90.018秒/CPU75.281秒・peak35.226MB。これらwallはlive正式pilotと重なり、phase wallへ加算しない。原金融expenseファイルは変更しない。[closed操作証跡の両保管庫保存](pilot-execution-evidence/task-5-stage-npz-hardlink-closed-proof-cas-root-receipt-v1.json)は29paths/29 unique blobs incl manifest、8.029MB、両PASS（manifest3c568845…、wall7.883秒/CPU0.139秒）。全catalog/原journal/fixture/費用を保管し、live金融rawとsemantic復元はこのpacketへ含めない。

本対策の対象は同一filesystemで閉じたNPZの物理共有のみ。Windows C:の空きが直ちに戻るとは主張しない。既存restoreはentryごと別実体へ書くので、native節約を両保管庫復元容量へ外挿しない。大きいJSON・元unique原始値・復元/検算RAMは残り、全phase容量は引き続きunknown。[後続transportの読取候補](pilot-execution-evidence/task-5-generic-saved-transport-options-readonly-v1.md)は未実装・未承認。decoded objectを単純共有するとbump mask/study covarianceのinplace操作で元の独立性が変わるため、候補でも各logical occurrenceの独立性・元payload_digestを維持する。正式pilotは同じhandleで観察を継続し、実選択/saved検算/freeze/main/fresh/両semantic復元/3図・教材/最終3suiteを残す。

修復後helper v2をroot bounded wrappers v3–v7で実適用した。追加2854 links / 90,403,504,128 B（90.403GB）、累計4978 links / 143,647,375,360 B（143.647GB）。5区間は読取120GiB/60秒の行政上限で終了し、金融A capや精度判定に使用しない。外側wall合計288.543秒・CPU250.682秒は正式pilotと重なり、金融phase wallへ加算しない。[全原記録の実postcheck](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-postcheck-v2.json)は8journals・最新5248pathsのphysical stat/原receipt/metadata/source81をPASS。NPZ実bytesは各実操作のfull before/after SHAを根拠とし、数値比較や金融qualificationへ代用しない。正常rollback2件も原inode/byteを保持した。[新catalogのstat候補](pilot-execution-evidence/task-5-formal-closed-pack-root-dedup-catalog-summary-v2.json)は11:46 UTCの24681 files・追加共有候補111.483GBであり、wholephase容量ではない。[closed証跡の両保管庫保存](pilot-execution-evidence/task-5-stage-npz-hardlink-closed-proof-cas-root-receipt-v2.json)は55paths/52 unique blobs incl manifest・16.790MB、両PASS（manifest c6e955c1…、wall14.194秒/CPU0.271秒）。live金融raw・金融semantic復元は含めない。

### 保存形式候補の小合成試作（2026-10-10）

[変更境界の読取追補](pilot-execution-evidence/task-5-generic-saved-transport-boundaries-addendum-v1.md)と[throwaway試作](pilot-execution-evidence/task-5-typed-dag-transport-spike-report-v1.md)を固定した。artifact内typed DAG/unique array/圧縮metadataを小fixtureで比較し、原referenceのlogical値/payload_digest、元全array出現数、復元後の独立writable dict/list/array・Parametersを確認。5tests/Ruff/formatはrootでもPASS、[独立確認](pilot-execution-evidence/task-5-typed-dag-transport-spike-independent-review-v1.md)は別2tests＋別fixture12項目PASS。2MiB（全64出現の論理合計）の反復array例は代表physical511480→7951B、unique64例は446011→324707B。DAG/圧縮の共同効果であり、実production形式の測定ではない。反復metadataとunique例でencode/readが増える場合もあり、全容量・速度・ETAへ外挿しない。

次の限定実装候補はrun_pilotの非teacher writer/new-schema reader分岐とprivate helper。million tiny arraysをそのままNPZ memberに残さず、元NPY header/bodyをuint8 blob pagesへpoolしdescriptor/DAG/offset表も圧縮する。旧PART/PACK/teacher/CLOSURE読取、各logical edgeの独立展開、原payload_digest、closure/checker、数学/N/cases/status/fault/costを維持する。静的importでhelperはsource closureへ自動捕捉され、欠落をrequired-source errorにする位置も確認した。新schema/writer version・source identityが必要で、旧liveplanのsource exact条件により現pilotへのresume適用はできない。source/metadata/rootの扱いを別に検証し、旧結果・原失敗を保持する。production page/receipt・bounded decompression/RSS・malformed入力・legacy/restore互換・実capacity/rateは未検証、returned RAMと全digest traversal費用も残る。実source変更・実業務大JSON/NPZ読取・追加金融実行0。


追加のbounded v8では1,391 links / 1,891,946,496 B（1.892GB）を共有し、累計6,369 links / 145,539,321,856 B（145.539GB）となった。外側wall60.020秒・CPU46.237秒、行政60秒で正常終了。直前intent1件はreplace前に停止し、2件の過去rollbackと元byteを保持。[全9journalのpostcheck](pilot-execution-evidence/task-5-stage-npz-hardlink-actual-root-postcheck-v3.json)は最新6767paths・原receipt/metadata/source81をPASS。[追加証跡の両保管庫保存](pilot-execution-evidence/task-5-stage-npz-hardlink-closed-proof-cas-root-receipt-v3.json)は4paths/5 unique blobs incl manifest・3.152MB、両PASS（wall1.481秒/CPU0.033秒）。Windows VHD/host volumeの実空き返却は未測定・未保証。金融数値・全phase容量・完了予定日は認定しない。
