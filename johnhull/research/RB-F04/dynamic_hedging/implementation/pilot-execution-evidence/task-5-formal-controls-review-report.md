# 正式 solver controls・rate・資源予算の独立候補レビュー

2026-10-10 / reviewer: progressive_graph_review

**結論：現在fieldの初期37価格に使う設定候補と資源量の根拠を整理した。正式pilot・main・全sourceの金融承認は行っていない。**
最新候補は [candidate-v2.json](task-5-formal-controls-review-candidate-v2.json)。元121ケース・51attempts、18状態、24query、4追加teacherケース、49コール日付、全stream、元N/格子を保持する。

## 1. solver設定の接続

| 用途 | 設定候補 | 根拠・未決 |
|---|---|---|
| field | 257×321、t=1/4096..1.25、z=±5、order1024、scale512、density_floor1e-10 | 元fieldを固定。旧129×161、early、wing6は履歴であり代用品にしない |
| 初期37価格・base | 2401×1920、幅1.8 | 同じ現在fieldの実測最大誤差0.0001306441、計算wall6.8905秒 |
| 初期37価格・space | 4801×1920、幅1.8 | 最大誤差0.0001040825、計算wall13.1727秒 |
| 初期37価格・time | 4801×3840、幅1.8 | 最大誤差0.0001041288、計算wall26.5850秒 |
| 初期37価格・domain | 6401×3840、幅2.4 | root追加計測：同dx0.00075、37/8group全有限・supported。幅差2.23821e-13、価格誤差0.0001041288 |
| 独立コール表・Heston | upper250のみを明示 | 250/500、800/800/1600、eps(1e-12/1e-11)→(1e-13/1e-12)の3levelを保持。flat eps/limitで全levelを上書きしない |
| 独立コール表・local | base2401×1920/1.8 → space4801、time3840、domain幅2.25 | sourceがdomainを1.25倍、nodesを同数にするのでdxが25%広がる。全state倍率0.25..4/価格/Greeks/rateは未測定 |
| production cache | 実sourceのHeston order1024、local1201×960/1.8 | build_call_cacheにPDE-controls引数はない。APIを変更する提案ではない |

初期wrapperの pde_stages=[] は実行時に拒否される。候補の4stageは全て現在fieldの初期37価格のcomponent根拠を持つ。
独立表の independent_call_controls は別設定である。初期37価格の同dx幅2.4が通っても、独立表の幅2.25・全状態倍率・取引日・Greeksを承認したことにはならない。

追加PDEのroot観測は parent wall38.3252秒 / CPU38.7406秒 / peak RSS755,789,824B。新CF・RNG・MCなし。
本reviewerは保存gridから元37価格のqueryを独立に再計算し、8group・価格誤差・domain差・solver前の37NaN原形保存を確認した。
[保存算術検査](task-5-formal-controls-review-domain37-saved-arithmetic.json)。新solverは実行していない。

## 2. 256MiBは保存chunk、RSSは別

- DESIGN.md:390は **NPZ 256MiB uncompressed**。protocol.write_artifact:650–670は各chunkのNPY header込み展開byteを検査する。
- write_pilot_artifact:1820–1863は128MiB配列payloadごとにpackする。_job_identity / locked_planのbyte検査はlive RSSを制限しない。
- 元N65536・65thresholdsでは samples / derivative_samples / joint の同時float配列だけで390MiB。conditional_tailの2枚のU40 statusだけでさらに1,300MiB。これは静的下限である。
- rootの原形allocation v3：65536/65/16blocks、10distinct label＋aliasを実保存・復元。parent5.71196秒 / CPU5.69656秒 / peak RSS2,938,032,128B。全展開380,125,208B、最大chunk103,591,984B（5chunks、うち4packs）。
- v2のheader private API失敗と実費wall4.49193秒/CPU4.473477秒は原形のまま残す。v3はpublic NPY header readerだけに変更した。
- 4GiB RSS / 180秒はrootの事前component予算。RLIMIT_AS・所要時間予測ではない。このsynthetic部品実測は、実教師/driver/全node replay/field/cacheを合わせたRAMや金融精度の証明にはならない。

## 3. 元の計算上限を適用した結果

[全20gridの表](task-5-formal-controls-review-existing-path-cap-table.json)

元capは path_steps/job=1e9。現契約ではoriginal_teacher_nodeがfinancial childであり、prediction.path_stepsはN×768（最大50,331,648）、実pathchunkは最大196,608。**20/20が既存cap内、事前未実行になるgridは0件**。
15/20のaggregate totalが1e9を超えるが、_job_identity:3695がtotal/count/child_boundaryを認証し、locked_plan:3866が子計算のpath_stepsを検査する。aggregateをglobalcapへ読み替えて除外してはいけない。

全最大経路が実行された場合の構造量：

- 20 teacher：条件付き遷移129,482,096,640、10共有driver234,356,736は別。
- 108 oracle：全13query・元768/1536のpayoff遷移上限54,103,375,872、driver2,774,532,096は別。
- production Heston：615,615 scalar CF / 630,389,760 frequency pairs。local161 PDE solve。
- 独立コール：12,474 scalar CF / 24,948 probability integral、local504 PDE solve。

109件の宣言totalと実ループ量の差は保守的包絡の違いであり、109件のsource defectではない。元predictionを変更しない。
旧teacherの1.823million path-step/sは混合した古い部品実測。oracleや全workerのrate、ETAとして扱わない。

## 4. whole storageは正式予算判断の未決

現在sourceは各nodeで全labels＋primitivesを保存し、保存時にcv/f_samples aliasも別entryとなる。

| 保存量の下限（全20gridを実行する経路） | byte |
|---|---:|
| 10distinct sample配列のみ | 1,443,051,601,920 |
| 現encoderの11sample entriesのみ | 1,587,356,762,112（約1.44TiB） |
| 単一local high N65536・11entries | 503,819,796,480（約469.22GiB） |
| principal全4grid N1024・11entries | 10,653,597,696 |

ここにprimitives/status、共有driver一回分、headers、cache・その他raw・receiptsが加わる。完了検査とcache再構築はさらに各nodeを全読込する。
rootが確認した空きは602,157,051,904B（約560.8GiB）、全容量約1.08TB。**全最大経路は現在のvolumeに収まらない。既存1e9 cap適用後もこの量は変わらない。**

2TiBのwhole storage候補はこのvolumeでは不可能で、完全な上限証明でもない。
128GiB等の有限administrative ceilingは元N/roster/possible jobsを保った予算revision候補として提示する。ただし現sourceにglobal storagecap実装はなく、本subtaskでは追加・実行していない。
256MiBをwhole disk capへ読み替えない。元aggregateを消さず、実際の低N qualificationによるunused、真正capによる停止、予算revisionを別の理由で残す。

A cap_optionsへの結合は真正のper-child path cap・既存parent wall capの原scope/実費の候補を作ることはできる。しかし今回path capを超える予定childはなく、aggregate超過によるA rejection候補は作れない。global storagecapはrootの次のbudget/revision判断が必要。

## 5. 正式pilot前に残る必須項目

1. 原49date/fullstateコールcache・独立表（local幅2.25を含む）の誤差とwhole job work/byte/rate。測定済みの初期37componentを全域証明へ広げない。
2. 実teacher/driver/replay/serializer、独立oracle、quote_riskと残りworker群に、実測または独立レビューした非zero費用見積と最大保存boundaryを付ける。全3138jobの現draftはrate/bytes/事前wall budget未固定。
3. 10本の実inclusive external receipts、121＋51実alias、phase parent interval/overrun、費用forest、元failure/unknownを保持する。欠落を0で補わず、source defectをcapへ変えない。
4. 全保存量・空き/headroom・実RAMを含むroot予算revisionを決める。高Nの未実行は実lower gateまたは適切なcap/revisionの証拠で説明する。
5. 指名source reviewerの現source closure、正式混合graph・budget lock・全数値受入は別工程。

このreviewの編集はD固有prefixの候補・独立証跡のみ。金融source、Git、公開API、主docs、formal/mainは変更していない。
