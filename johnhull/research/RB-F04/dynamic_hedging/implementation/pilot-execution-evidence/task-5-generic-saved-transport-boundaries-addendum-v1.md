# Generic transport: 変更境界と互換契約の追補

2026-10-10 / D-only読取。元候補 task-5-generic-saved-transport-options-readonly-v1.md (a0f2c46e…) は固定のまま。実装・容量測定・承認はしていない。

## 判断

数学・公開API・全原payloadを変えずに、artifact内部の保存重複だけを除く設計は **可能**。最小のsource範囲は run_pilot.py のwrite/read分岐とprivate codec helper。currentfinancialsource81、livepilot、原artifactへ適用しない。全体容量が足りるという判断は、元形状の実測前にはできない。

| 変更候補の位置 | 変更の内容 | 保持するもの |
|---|---|---|
| run_pilot.py write_pilot_artifact:1818–1821 | teacher prepare がdescriptor無しのgenericにだけ新private writerを分岐 | 函数署名/返却root receipt、root teacher recipeと旧literal writer |
| 同 read_pilot_artifact:1952–1961 | 新generic schemaを判定して完全logical payloadを返す | PART_SCHEMA v1、PACK_SCHEMA v2＋teacher_storage、CLOSURE_SCHEMAの現読取 |
| private helper（名称/実source inventoryは実装時固定） | typed DAG、array/part pool、圧縮metadata pages、独立copyで再展開 | solver/RNG/SDE/数式/N/ケース/入力/status/failure/cost |
| protocol.write_artifact/read_artifact:645–746 | **変更不要**。既存JSON+nonobject NPZとexact receiptを下層に使う | immutable新directory、NPY expanded256MiB、shape/dtype、no-pickle |
| run_reference.py _encode_tree/_decode_tree:526–559、payload_digest:562–574 | **変更不要**。論理正規化と既存由来digestを維持 | 原check_pilot/closure/resume/typed input監査 |

新root format marker（例 rb-f04-pilot-generic-dag-v1）と明示writer versionは必要。新DAGを旧PACK_SCHEMA v2と偽って保存すると、旧 _read_packed_pilot の「各part entryは一度だけ使用」「tree array IDは全使用」の契約と衝突する。下層 rb-f04-array-chunk-v1 / receipt schemaを変更する必要はない。旧sourceは新formatを読めないことを明示し、新sourceは旧formatを読み続ける。新形式の導入はreader先の準備＋source/prior固定後のwriter変更という順で扱い、既存rawを自動変換/上書きしない。

## 物理表現を限定する

- DAGはartifact **内部** に閉じ、key/sequence順、scalar型、元fit/claim全path、空roots、NaN/Inf、status/reason、16blocks/covariance/SE、primitive/seed/source/input/expenseを保存する。外部producerへの依存resolverは追加しない。
- ndarrayだけinternし、残るtreeと全descriptorをliteral JSONで持つ案では約214–217MBのtreeが残る。DAGとdescriptor/offset表もlossless圧縮byte pagesへ移す。
- uniqueな小arrayを個別NPZ memberで百万件残すと、下層metadata/ZIP member/header反復が残る。元row-part境界を維持した **NPY partのheader+body** をuint8 blob pagesへpoolし、offset/coverageを圧縮表に置く案が必要。各物理packのNPZ member数は少なくできる。NPY headerも保持するため、dtype.strだけでは失われるstructured dtype等の型情報も捨てない。object dtype/pickleは禁止のまま。
- internはtyped header/shape/実bytesがexactに同じ場合だけ行う。SHAは候補検索/receipt由来であり、衝突候補の実一致を確認する。float丸め・approx dedup・statusの統合は行わない。
- 既存128MiB row-part / 256MiB expanded chunkを全N縮小やglobal容量/RSS capへ変えない。metadata pageには元byte数・参照coverageを結び、decompressionもpage単位で必要量までにする。巨大な単一dictを一部だけ保存して済ませない。

## alias と論理digest

現writerは同objectでも出現別IDを作り、現readerは別IDを別配列/containersへ復元する。新readerは物理poolを内部に隠し、**論理edgeごとに** 新dict/list/HestonParameters、writable ndarray.copyを返す。DAG nodeの展開結果を共有して返さない。異なるnp.ndarrayが同値でも、片方の変更が他方へ波及しない。

根拠: _resolve:2012–2045 はrawを直渡しする。bump:2453のdeepcopyは既にあるaliasを維持し、2477–2478のmask &= はinplace。study:353–355/447–457もblock/covarianceを書き換える。read-only arrayだけにする、copy-on-writeがないviewを返す、deepcopyへ任せる対応は互換ではない。全payload展開後のRAMは減らない。

正規化は既存runnerのdict key順、tuple→list、numpy scalar→Python scalar、非有限sentinel/parameters markerと同じにする。再展開payloadの配列shape/dtype/bytesとscalar型・値が同じなら runner.payload_digest は同じ。これは保存由来の条件であり、価格/Greekの金融一致は既存 tolerance 数値checkを維持する。

## receipt / saved checker / source の契約

- 新root indexは全blob/page/offset/shape/型/参照とcodec/source bindingを物理receiptへ結ぶ。欠落/余剰page、循環/不正参照、array範囲のgap/overlap、型/shape/原counts、変更されたphysical bytesを拒否する。root receiptだけの一致で全page検証を省かない。
- check_pilot:5039–5056 は checkpointを読み、各元jobをreadし、**logical** runner.payload_digest(row)==raw_job_payload_sha256を確認して従来の金融checkerへ渡す。この経路を変えずに新formatを使える。
- closure:1638–1645 は境界partのlogical payload digestを確認するため、境界childが新formatでも元全値を復元すれば契約は維持できる。CLOSUREの外側tree/part pathは変更不要。
- teacher raw_binding:1872–1895と既存teacher physical recipeは触らない。native teacherは現formatのままとし、generic transportをteacher label再生成の代わりにしない。
- phase memo physical guard:2784–2799は全filesのbyte inventoryなので新pageも対象になる。新codecだけを理由にphysical guardや初回金融checkを省略しない。
- **backward read可能はresume許可ではない。** check_job_envelope:753–756とrun_pilot:4079–4122はplan/source/inputをexactに照合する。新helper/read/write変更は実source closure/identityを変えるので、既存liveplanに旧sourceSHAを付け直して継続することはできない。source/priorの限定再bindと承認は別工程で、現源固定は維持する。
- 原status/fault/unknown/全費用をlogical payloadへ保持する。codec時間/CPU/RSSは親inclusive時計と別保存工程の範囲を明示し、旧測定費用を再加算しない。物理codec headerの追加を元金融rowへの新field追加にしない。

## 実装前に残る確認（新mandatory pipelineは作らない）

旧literal/teacher/CLOSURE roundtrip、新formatの原logicaldigestとtolerance値、同値別arrayのmutation隔離、全元N/順序/空/NaN/failure/16blockを含む元shapeの保存、page/参照tamper、復元rootのself-contained read、encode/decode RSS/実bytes/CPU。新source inventory数は実closureで固定する。元jobのdecoded RAMとpayload_digest全再帰費用は残り、artifact間コピーもこの案だけでは消えないため、全3138jobの容量充足/ETAは未確定。

今回: source読取＋このD追補のみ。production/source/tests/docs/Git/CAS/live/raw変更、金融/RNG/SDE/solver、巨大JSON全read、hardlink=0。
