# 保存済み Heston-coarse memo の最小資源計測（準備・未承認）

原genuine保存物を変更せず使用する。M6 generation source **4e8f8b7b…**、旧 bounded saved-check source **408f2bc2…**、新runtime checker source（root実snapshot指定待ち）を別々に記録する。原envelope/source SHAを新sourceへ書き換えない。

- 原N1024、108 nodes、12 dates、全33 thresholds、11 sample descriptors、16 blocks/covariance/status/NaNを維持する。
- 原grid metadataはcache構築済みdict、status executed、financial_qualification unknown、未実行0、cap null。metadata eligibilityは初回全integrity検算の代わりにならない。
- old input manifestを再利用し、原root/pack/driver/field等701ファイル・stat64,420,530 bytesへ結合。準備では468 JSONのSHA確認のみ。原binary SHAは実guardで全件照合し、その時間/読取/hash費用を含める。
- 単一child 180秒、個別RSS 8GiBの未承認候補。旧初回Hc費用31.008640309秒は履歴。予算値は行政上限で、速度保証ではない。
- 計測順は empty memo初回全検算 → 同memo immutable hit → 別empty memo全検算。実full checker呼出し差分 **1 / 0 / 1**、全N/108/11labels coverageとsource/physical binding再認証を記録する。
- root はsource ownerのfixed API/snapshotと実source closureを確認後、候補v2とは別の実事前承認JSONを作り、そのSHAを別root enclosing receiptへ記録する。候補false・API pending・source nullのままでは実行を拒否する。
- scriptは提案APIへ配線した暫定準備物。構文確認のみで、測定は未実行。fixed API到着後に適合させる。rootが実行するまでSDE再計算・RNG・solverは0。
- parent clock、child clock、各stage時計は包含関係がある。root実外側費用へ内側clockを再加算しない。最終root receipt自身の書込費用はunknown。
- IO計測はPython binary read呼出しのbytes。実デバイスI/O、C/mmap/text decode範囲はunknown。SHA計測はsource/metadata/入力由来など全SHA256入力bytesであり、物理ファイルhash bytesの明示guard項目と区別する。
- 元math/teacher/storage recipe bytesを変えない。新sourceではrun/checkのtransportのみ差分を許し、_teacher_storage.pyの元SHA 6a1ea6e5…を固定する。unknownを金融qualifiedへ昇格しない。

実source結合後のroot実行入口（今は実行しない）:

~~~text
.venv/bin/python -B task-5-phase-local-memo-measurement-v1.py \
  --budget <root実承認prior JSON> \
  --output <D/task-5-phase-local-memo-observation-root-v1>
~~~

原保存物をsyntheticに置換しない。eligibility外・失敗・実capはpartial/failedとして残し、資源完了にも金融PASSにも変換しない。旧v1入力/candidate、既往M6のcaps/費用/unknownは不変。
