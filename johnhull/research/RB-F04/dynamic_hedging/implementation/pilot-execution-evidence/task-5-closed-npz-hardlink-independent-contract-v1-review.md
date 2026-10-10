# 閉じたNPZのsame-FS hardlink共有：独立契約確認

2026-10-10。source静的読取のみ。実rawの置換・金融/RNG/SDE・process/CAS実行は0です。**同一bytesを保つ閉じたleaf NPZの共有は、現行のbyte/path認証と整合します。** 実共有の実装・本物の同一性・容量充足・金融資格は本確認では承認しません。

## 保持される契約

- protocol.write_artifact（645–695）はleafのmetadata → arrays → receiptを各 xb でcloseし、既存dirを拒否します。closed **pack** とcompleted **wholejob** は別です。rootreceiptの存在だけでは全pack完了を示しません。
- protocol.read_artifact（698–746）は exact metadata/NPZ/receipt bytes、expanded size、dtype/shape/配列集合を認証します。inode・mtimeを資格にしません。
- memoの _artifact_byte_guard（check_pilot.py:2784–2799）は相対file/dir inventoryと各fileの現bytes SHAを毎回読みます。_teacher_physical_guard（2802–2824）は原pathをresolve。teacher physical_artifact_binding（_teacher_storage.py:309–342）はroot/pack receiptとsourceを結合します。全pathとbytesが同じならlink数・inode変更でこれらの入力/N/11labels/全primitiveを省略しません。
- CAS evidence_store.py のmanifest（93–132）、read_verified（187–199）、restore（395–434）は path/refSHA/byte数で認証します。artifactのinode/mtimeは保存要件に含みません。CAS内部lockfileのinodeを保つコメント（312）はwriter排他のためであり、native NPZを変更する根拠ではありません。

## root実処理で必要な境界

1. 全closeした **leaf arrays.npzだけ**。現在writer中の別pack、metadata/receipt、native原path、node/array集合・status・unknownは変更しない。receipt候補だけで同一とはせず、現在の実byte比較・元receipt認証と前後安定照合を行う。
2. same filesystem/device、uid/gid/modeと読取権限を確認。guard対象nativeの外で一時linkを作り、atomic replace後も元file名・bytes・receiptsを再照合し、一時pathを残さない。旧FDが読む内容も同一bytesである。
3. source契約の write-once を運用でも維持する。**in-place再書込は共有先すべてを汚染**するため禁止。symlinkへの置換、別FSコピーを同じactionとして偽ること、原packの欠落をlinkで埋めて完了扱いすることは不可。
4. 実節約量はlink対象の確定同一性とfilesystem free-space又はdistinct (device,inode) のallocated量で記録する。pathごとのlogical sizeは変わらず、st_blocksのpath合計は共有blockを二重計上し得る。将来のunique数は未知のままにする。

## CAS・復元の容量は別

CASは各vault内でdigestごと既に共有し、verify_copies（446–468）は各vaultだけから別々に復元します。**_write_restored（370–392）はentryごとに別temporaryを作るため、同一digestが多数pathにある復元物は再び別実体になる**実装です。nativeのhardlink節約を両vault/復元/一時容量の保証に広げません。後続の両独立semantic再検査と実費記録も必要です。

結論はbyte保存方式の静的互換性です。source変更・計算入力削減・original N削減・金融資格の昇格はありません。rootの合成検証・本物exactbyte確認・actuallink処理の結果は別証拠として記録してください。読取/import/文書固定を含む本レビュー総費用はunknown、金融費用は0。
