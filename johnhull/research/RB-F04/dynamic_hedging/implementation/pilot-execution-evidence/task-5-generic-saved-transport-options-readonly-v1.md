# Generic saved transport の限定候補（読取調査）

日付: 2026-10-10。状態: 技術候補のみ、未実装・未承認。現financial source、live原raw、全N/queries/16blocks/費用は変更していない。

## 結論

最小の範囲は **artifact 内に閉じた private な lossless DAG + 配列表**。保存時だけ同一の配列・typed metadata の物理表現を共有し、read 時は従来どおり各論理出現を独立した writable object として展開する。外部producerの解決、新stage cache、金融計算の省略は不要。source-free hardlinkは別の暫定対策であり、この候補の承認にはしない。

現JSONの descriptor335.7/349.5MB、tree213.8/217.0MBという分割は既保存の storage-metadata-paths-addendum-v1.json に固定済み。配列だけinternしてtreeをliteral JSONのまま置く案では、残る約214–217MBと全pathのdict/list overheadが減らない。DAGと配列descriptor表も物理byte pagesへ lossless 圧縮して、root JSONは小さいindexとreceipt/source/format情報だけにする必要がある。縮小率・所要時間・wholephase容量は未計測。

## 確認した現在の境界

- run_reference.py:526–543 _encode_tree は ndarray **出現ごと** に新IDを付ける。dictはkey順、tupleはlist、numpy scalarはPython scalar、非有限floatはsentinel、HestonParametersはmarkerへ正規化する。repr fallbackや値の丸めはない。
- run_pilot.py:1898–1946 _read_packed_pilot は別IDの配列を別々に復元し、各part/shape/dtype/bytes/参照coverageを検査する。run_reference.py:546–559 _decode_tree はIDの配列を直接返すが、現writerが出現別IDを付けるため原objectのaliasは保存されない。
- run_reference.py:562–574 payload_digest は再帰treeと各出現のshape/dtype/実bytesで由来を結ぶ。新物理formatから同じ正規化payloadへ展開できれば、この **論理digest** は同じにできる。物理receipt SHAは新formatの値で別に結ぶ。いずれも金融精度の合否ではない。
- run_pilot.py:2012–2045 _resolve は結果のraw/pathを直接渡す。読出payloadを共有array/containersに変更すると、その別の利用先にも変更が波及し得る。
- run_pilot.py:2452–2453 はbase_riskをdeepcopyして3variantsを作り、2477–2478でmaskに &= を行う。Python deepcopyは入力に既にあるaliasを保持するため、読出時に作ったaliasの隔離手段にはならない。
- _dynamic_hedging_study.py:353–355/447–457 はoriginal linear branchのblock値/covariance/SEを書き換える。これ自体は現在の数式の一部であり、transport側がreadonly arrayを返す対応も互換ではない。
- protocol.write_artifact/read_artifact:645–746 は既存immutable NPZ、receipt、256MiB NPY expanded capを持つ。新候補はこれを下層で使い、旧literal/teacher formatはそのまま読む。旧current sourceへ今追加しない。

## 候補の具体的範囲

1. 非teacher generic artifact の write/read 境界にだけ private format marker/helper を置く。現teacher recipe、runner._encode_tree/_decode_tree、公開API、計算workerは変更しない。既存literalと旧receiptは変更しない。
2. 物理配列を dtype.str + full shape + 実bytes でinternする。SHAは候補検索/物理由来に使用し、write時の衝突候補はtyped bytesを確認する。float丸め、NaNの勝手な置換、ゼロ長rootsの省略、statusの統合はしない。異なるdtype/shapeは同じ物理blobでも論理descriptorを区別する。
3. metadataのDAGはscalar型/keys/順序/array参照を保存し、反復dict/list subtreeは一度だけ持つ。数式による再生成ではなく、全scalar fit/claim/16block/covarianceの元情報そのものの符号化。DAGとdescriptor表の反復文字列はlossless圧縮byte pagesへ保存する。unique配列も既存lossless compressed NPZを使用できる。
4. root indexは全page/packのexact physical binding、format/source binding、元countsとlogical payload bindingを持つ。partial/failure/unknown/NaNのまま保存できる。欠落・余剰・循環参照・誤shape/dtype・page改変を拒否する。page分割は全coverageを保持し、既存256MiB chunk capをglobal容量/RSS capへ読み替えない。
5. readで物理intern poolは内部に留め、**各論理edge/出現ごとに** 新dict/list/HestonParametersと ndarray.copy を生成する。DAG nodeの復元objectをそのままmemo返却しない。scalar正規化・tuple→list等も旧readと同じにする。0d、空array、NaN、符号付きzero、Unicode/status、原row順・query/date/path順を保持する。全重複を展開したreturned payloadのメモリ下限は減らない。
6. 論理payload_digestと現金融saved checksは従来どおり維持し、codec物理SHAをprice/Greek同一性の判定に置き換えない。snapshot/source inventory/priorの再bindingは新sourceを実装・独立検証した後の別工程。codec elapsed/CPU/RSS/write/read費用も既存親のinclusive時計と別工程の範囲で残し、既往費用を再加算・ゼロ補完しない。

## 選択肢と未確認点

| 選択肢 | 影響 | 未確認 |
|---|---|---|
| **artifact内 typed DAG＋unique配列＋圧縮metadata pages** | 保存byteとdescriptor/treeの反復を減らし、readで完全payload/出現別copyを返す。新private codec境界に限定できる | 元全形状のdedup率/圧縮比、encode/decode CPU、peak RSS、ページ/参照tamper、mutation isolation、logicaldigest、legacy/復元root互換 |
| 外部producer rawへの参照からfullpayloadを復元 | descendantごとの全上流コピーを減らす余地が大きい | restore/CAS依存閉鎖、source/input/producer/capのresolver追加、欠落原artifactとsource混在の扱い。今回の最小候補には含めない |

最小候補でもuniqueな319,488組のquerypath fit/claimを消すものではない。完全なreturned payloadを要求する限り、展開後のRAMと既存payload_digestの全再帰費用は残る。content internの実benefitと圧縮比は元Nで確認するまでunknown。aliasを作らず保存を共有できるという技術的可能性の読取判断であり、実装承認や正式pilot資格の判断ではない。

実施: source読取のみ。新RNG/SDE/solver/worker/大JSON全parse/CAS/hardlink/source edits/process control=0。
