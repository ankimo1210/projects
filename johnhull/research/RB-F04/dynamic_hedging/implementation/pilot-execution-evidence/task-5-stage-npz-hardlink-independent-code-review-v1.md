# stage NPZ hardlink helper：限定独立code review

2026-10-10。対象は固定 D/task-5-stage-npz-hardlink-v1.py、SHA **934f5337c45c6d0e9243477476effdd20155a44cfcf0127401a899f556b2587b**（27,284 B）。実native・金融・RNG・SDE・production/source・CAS・Gitには操作していません。既存作者11 PASSは作者証拠として保持し、独立PASSに数えません。

## 結果：rollback失敗時の記録・backup保全に1件（P2）

link() の postcheckが行政read cap等で失敗し、rollbackの os.replace(backup,target) も OSError になると、449–457行の finally が元backupを削除します。このOSErrorは run() の480–481行で通常の rejected として吸収されます。**実際にはtargetが共有済みなのに、成功にもrollback済みにも記録されず、元inodeへ戻すbackupも残りません。**

Dだけの合成反例では、既存 selftest の正常な同一NPZ pairを使い、置換直後にread上限を設定し、続く .original → target のrollback replacementへI/Oエラーを注入しました。source/targetの元bytesは同一のままですが、targetはsource inodeを共有し続け、backupは消え、journalは start / before_link / rejected / finished です。失敗済み操作を通常の候補拒否へ落とす境界が問題です。これは既存root 2124件の正常終了・原receipt/metadata postcheckを否定する証拠ではありません。

最小修正範囲は、**rollback失敗時にbackupを保持し、実操作結果unknown/tool_exceptionを上位へ伝播して通常rejectedへ落とさないこと**。既存成功時と行政capによる正常rollbackは維持してください。production金融sourceや値/N/thresholdの変更は不要です。

## そのほかの確認

native外staging、固定CLI root、direct stage/pack arrays.npz限定、symlink拒否、sameFS/dev/uid/gid/mode、canonical receiptとmetadata/NPZ現bytesSHA・ZIP expanded bound、前後stat安定、fsync journal intent後のatomic replace、原metadata/receipt不変更、外部hardlink存在時の解放量0はsourceで確認しました。正常な共有・detach・postcheck cap rollbackは以下の独立合成3件がPASSでした。CLI wrapperの旧exception名問題はroot wrapper履歴であり、このhelperの問題へ読み替えません。

## 独立合成原結果

```json
{
  "independent_selected_tests": 3,
  "pass": true,
  "test_log": "test_exact_duplicate_link_and_receipt_byte_preservation (synthetic_hardlink_review.SyntheticDedupTests.test_exact_duplicate_link_and_receipt_byte_preservation) ... ok\ntest_postcheck_read_cap_rolls_back_original_inode (synthetic_hardlink_review.SyntheticDedupTests.test_postcheck_read_cap_rolls_back_original_inode) ... ok\ntest_already_shared_inode_skips_and_detach_restores_independence (synthetic_hardlink_review.SyntheticDedupTests.test_already_shared_inode_skips_and_detach_restores_independence) ... ok\n\n----------------------------------------------------------------------\nRan 3 tests in 0.093s\n\nOK\n",
  "rollback_IO_error_probe": {
    "original_bytes_preserved": true,
    "target_remains_shared": true,
    "rollback_backup_retained": false,
    "journal_events": [
      "start",
      "before_link",
      "rejected",
      "finished"
    ]
  },
  "helper_sha256": "934f5337c45c6d0e9243477476effdd20155a44cfcf0127401a899f556b2587b",
  "wall_seconds": 0.1281795369941392,
  "cpu_seconds": 0.043222317999999996,
  "scope": "D-only synthetic byte transport; actual native untouched"
}
```

上記counterexampleは原bytes保全を確認しており、数値入力削減や金融資格を示しません。合成probe費用は wall 0.128179537秒 / CPU 0.043222318秒。source読取・import外側・文書固定を含む全review費用はunknownです。実native link・実CAS・金融実行は0。wholephase容量・金融precision・main/phase受入の承認はありません。
