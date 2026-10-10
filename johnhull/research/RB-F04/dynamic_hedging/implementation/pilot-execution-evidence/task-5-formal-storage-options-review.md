# 正式pilotの保存方法：限定候補2案
2026-10-10。読取と整数の構造算術のみ。source/tests/docs/Git、金融計算/RNG、CAS検査を変更・再実行していない。正式pilot・予算は未承認。

## 結論
全20teacher最大候補の現11 sample entriesだけで **1,587,356,762,112 B**、真正aliasを一回保存しても10 distinct samplesで **1,443,051,601,920 B**。root native teacherのprimitive-based再構成が有望だが、元primitive/状態/失敗理由/全16block/covariance等だけでも **353,606,441,728 B以上**。両案とも実圧縮とwhole-job保存予測が必要。

rootのactual dfはWSL **601,683,951,616 B**、C: **340,566,458,368 B**、F: **185,710,804,992 B**。各CASをC:/F:の別volumeに1copyずつとして計算する。削除・移設・追加容量は承認済としない。最も厳しいF:では1corpus <185,710,804,992 Bが絶対条件で、staging/metadata/増加分の余裕は別。

## 原契約・encoder
- DESIGN §7.4:214–220、§14:332–337は元CRN/N/全16blocks/相関/primitiveからの再計算と全failed nodes/referenceを保持する。元121 cases/51 attempts/20teacher candidates、N1024/4096/16384/65536と独立reserved N65536、全33/65thresholdsは変更しない。
- run_teacher_job:491–525はraw.primitivesとlabelsを返す。run_teacher_grid_job:1331–1333はnative node rawを保存しfull payload digestを付け、check_pilot:1191は再SHA比較する。
- run_reference._encode_tree:526–574は同一ndarrayも出現ごとに保存。decoderは同一array keyの複数tree参照に対応。native primitive_labels:539–549のcv_samples/f_samplesは真正alias。11→10の保証された節約は **9.09%だけ**。generic canonical payload_digestは変更しない。
- protocol.write_artifact:645–695はnp.savez（無圧縮）。256MiBはNPY header込み各NPZ chunkの展開量、pilot:1810–1864の128MiBはpack payload。圧縮後も展開capは維持する。既存1e9 path-stepはfinancial child境界であり、aggregate/global storage capではない。現行whole-storage capはない。
- 全nodeの完了status読込とcache再構築は少なくとも2回の全readを伴う。progressive選択で実際に未使用になった証拠なしに、全候補宣言最大を縮めない。

## 保持するprimitiveの展開byte算術
元全20teacherのpath×node records=324,681,728、step状態entries=129,482,096,640。native:215–226,342–378、pilot._PATH_KEYS/_merge_primitivesより次が現在dtypeの展開保持下限。

|配列|元全候補のbyte|
|---|---:|
|9本のfloat64 primitive vectors|23,377,084,416|
|primitive_status Unicode7|9,091,088,384|
|failure_reasons Unicode128|166,237,044,736|
|path_mask bool|324,681,728|
|全local_step_status uint8本体|129,482,096,640|
|**merged primitive小計**|**328,511,995,904**|
|path_ids＋cluster_ids int64|5,194,907,648|
|price/Greek/jointの3 covariance行列|15,166,206,720|
|全16block price/derivative/joint/f_x summaries|983,623,680|
|共有driver float64（10producer、一回分）|3,749,707,776|
|**この部分だけの保持下限**|**353,606,441,728**|

calendar/fixings/dictionary、thresholds/means/SE/status、labels内mask等の重複、headers、他job raw/cache、失敗raw・10 receiptsの履歴は別。Unicode失敗理由は空値も原N全部を保持する現dtypeの量で、lossless圧縮効果は期待できるが実測前に比率を主張しない。下限1copyはC:空きを13,039,983,360 B、F:空きを167,895,636,736 B超える。2copy合計707,212,883,456 Bは2volume全体の量であり、F単独の必要量とはしない。

最大原N65536/date0/high65 node：merged primitive/status主要配列 **90,505,216 B**＋3 covariance **1,825,200 B**＋全16block summaries **108,160 B**＝**92,438,576 B**。path/cluster IDs **1,048,576 B**や小配列等は別。このprimitiveの量はlive RSSの下限であり、chunks/merged共存、再構成/統計、reader packs/concatenateは別。

## 比較する2案（pending）
|候補|最小変更・保持内容|容量を支えるための追加作業|
|---|---|---|
|A：literal全rawのlossless圧縮＋真正alias|full raw/10 distinct samples/全primitive/統計を保存。当該pilot physical NPZだけcompressed、他artifact/defaultは不変。pack専用memoでcv/f_samplesだけ共用、generic serializer/digestは不変。receiptはcompressed actual bytesとexpanded bytesを別計上。一般protocol APIを変えない限定writer境界の互換性をレビューする。|alias後samplesだけでもF:で圧縮率≤.1287、C:≤.2360、WSL≤.4170が必要（余裕なし、その他raw未計上）。旧N1024/1threshold混合probe率.203は全65thresholdの根拠にならず、容量成立は未証明。genuine全65threshold nodeの圧縮/restore bytes・wall/RSS測定が必要。|
|B：root native teacher専用recipe＋当該物理NPZのlossless圧縮|成功したroot raw.kind=teacherだけ対象。nested診断/cap/source-defect/failed partialは旧literal。原primitive/thresholds/全N/path/cluster IDs/seed/driver/stream/source/case/failure/unknown、全means/SE/status/16blocks/covarianceを物理保存。10 distinct派生samples＋aliasのみnative primitive_labelsからfull returned payloadへ復元。一般型辞書/bitpackは追加しない。|保持下限353.606GBだけでもF:圧縮率≤.5252、C:≤.9631が必要（余裕なし）。状態/失敗文字列を含む最大node実測と全job量の合計が必要。保存量は大幅に減り得るが、まだ両vault収容の証明ではない。teacher専用writer/reader・new/old node binding/checker/saved cacheの限定変更と独立レビューが増える。|

Bの物理保存はlossless。NumPy/SciPy/runtimeに依存する派生float再構成は、跨環境の元sample全byte再現保証とは呼ばない。native source-bound式と許容差検算により同じfull returned payloadの定義を維持する。元sample byte完全可逆が必須なら、固定runtimeのbit replay又は本物lossless codecを別途証明する必要があり、この候補では未証明。

## Bのteacher専用境界と検証
1. writerはteacher-rootだけを認識し、recipe schema/version・closed kind・primitive dtype/shape・元分母/全thresholds/16blocksを検証。primitive/物理summary/recipe/source identity/case/driverをreceipt/SHAで認証する。欠損・source/type/object/recipe tamperは拒否し、未知値/失敗を0やfinite subsetへ置換しない。一般serializer/public APIは広く変更しない。
2. 新recipe nodeにphysical artifact receipt binding kindを明記。新nodeの再構成金融floatを既存full payload SHAの金融判定へ入れない。旧literal raw_sha256は互換維持。物理保存はhash、raw/conditioned/CV/Greek・全16block/covarianceの再計算はapprox、status/分母/case/shapeは厳密に照合。原保存summaryを再計算値で上書きせず返す。teacherが上書きするglobal_driver_id/date_indexも再現する。
3. full10 sample配列＋cv/f alias・keys/shapes/units、全N/16blocks、unknown/NaN/failureをread/check/cache両vault復元で検証。元source/driver stream/費用を保持。reconstructはnative primitive_labelsのみ、金融worker/RNG/CF/PDE/optimizerを呼ばない。再構成のread費用は新actual receiptの別scopeに記録する。
4. 旧allocation-v3は全N65536/65threshold/16blocksのsynthetic label/I/Oのみ（peak RSS2,938,032,128 B、wall5.711957768 s）。failure_reasons/local_step_status等のmandatory full primitiveは入っていないので、今回の容量/rate実測の代用にしない。金融teacher/fullgrid/driver/replay複合RSS/rateは未測定。

## 最小追加部品計測案とwhole予算
- source実装/レビュー後、元N65536・全65threshold・16blocksのdeterministic synthetic teacher fixtureに、9 float primitive vectors、calendar/fixings、原N mask/Unicode7 status/Unicode128 failure reasons、全65536×768 uint8 step状態＋dictionary、元path/cluster IDs、全summary/covarianceを含める。全ready＋有限failure/unknown fixtureを分け、kind=teacherをfinance qualifiedとせず、金融worker/RNGを禁止してwrite/read/approx再構成/tamperを測る。部品だけのroot事前候補はRSS4GiB・wall180s（runtime予測ではない）、実receipt/NaN/unknownを保存する。
- fixture物理配列のbyte roundtrip、原N/threshold/16block/alias、actual compressed/NPY-expanded bytes・全chunk256MiB・pack128MiB、RSS/wall/CPU/再構成費用を独立計数する。synthetic status圧縮率は金融全nodeへ外挿せず、既存の次のgenuine全shape teacher計測でstatus付き保存を共用する。codecだけのために追加金融MCを作らない。
- 全候補の他job raw/cache・失敗・費用履歴・driver・staging/restoreまでactual volumeごとに合計する。例として1corpus128GiBならC:余裕203,127,504,896 B、F:余裕48,271,851,520 B。WSLで原本＋逐次1復元なら274,877,906,944 B、原本＋同時2復元なら412,316,860,416 B（その他staging等は別）。これは**未測定の資源目標**であり、正式cap/完了条件ではない。復元NPZはcompressedを保ち、全展開配列を追加ファイル保存しない前提も確認する。
- 選択に効く追加開発はAの狭いcodec/alias互換検証、又はBのteacher recipe＋physical binding/checker互換検証。その後に最大node/status付きI/O部品、genuine raw、C:/F:両restoreの検証とwhole storage予算固定が必要。既存capをglobalへ転用せず、容量未達なら原N/rosterは保持して予算/source revisionへ戻る。capをruntimeや金融精度達成と数えない。

**次の判断材料**：Bの限定境界と物理保存予測を先に確定し、最大node/status付き部品を実測する。現容量のままAだけで正式全候補を開始できる根拠はない。source編集・正式実行はこのメモでは行っていない。
