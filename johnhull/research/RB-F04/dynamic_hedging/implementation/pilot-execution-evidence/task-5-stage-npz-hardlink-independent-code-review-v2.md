# stage NPZ hardlink v2：P2限定独立再確認

**判断：P2の最小修復を限定承認。** 実操作・金融資格・phase容量の承認ではありません。

対象固定SHA：v2 **010fb31dd02be6e7be937d1c9923ba8f80abeac2bbb03f05725850be430adf58**（28,505 B）。元v1 SHA **934f5337c45c6d0e9243477476effdd20155a44cfcf0127401a899f556b2587b** と独立P2メモ-v1は不変です。既存関数のAST差分は **Deduplicator.linkだけ**、新規 RollbackFailureError は RuntimeError 派生なので通常候補rejectedのexcept(ValueError,OSError,BadZipFile)へ入りません。

2026-10-10、元反例と正常共有・正常rollbackだけをD合成fixtureで再確認しました。**3境界PASS**。作者全12PASSを独立件数へ加算していません。

元の「置換直後readcap→rollback replaceもI/Oエラー」反例では、RollbackFailureErrorが上位へ伝播、元inodeと元bytesのbackup1件を保全し、mutation_effect=unknown / termination=tool_exception / 解放量0になりました。journalに rollback_failed / tool_exception が残り、通常 rejected はありません。targetは共有状態としてunknownを保持し、rollback成功と偽りません。正常byte共有と正常caprollbackも独立PASSです。

## 原probe結果

```json
{
  "independent_normal_tests": 2,
  "normal_pass": true,
  "test_log": "test_exact_duplicate_link_and_receipt_byte_preservation (synthetic_hardlink_review_v2.SyntheticDedupTests.test_exact_duplicate_link_and_receipt_byte_preservation) ... ok\ntest_postcheck_read_cap_rolls_back_original_inode (synthetic_hardlink_review_v2.SyntheticDedupTests.test_postcheck_read_cap_rolls_back_original_inode) ... ok\n\n----------------------------------------------------------------------\nRan 2 tests in 0.042s\n\nOK\n",
  "original_rollback_IO_error_counterexample": {
    "raised_type": "RollbackFailureError",
    "original_bytes_preserved": true,
    "receipt_preserved": true,
    "target_remains_shared": true,
    "backup_count": 1,
    "backup_original_inode_preserved": true,
    "backup_original_bytes_preserved": true,
    "termination": "tool_exception",
    "mutation_effect": "unknown",
    "linked": 0,
    "certain_released_allocated_bytes": 0,
    "journal_events": [
      "start",
      "before_link",
      "rollback_failed",
      "tool_exception",
      "finished"
    ],
    "pass": true
  },
  "changed_existing_functions": [
    "Deduplicator.link"
  ],
  "v1_sha256": "934f5337c45c6d0e9243477476effdd20155a44cfcf0127401a899f556b2587b",
  "v2_sha256": "010fb31dd02be6e7be937d1c9923ba8f80abeac2bbb03f05725850be430adf58",
  "wall_seconds": 0.09349525500147138,
  "cpu_seconds": 0.044185497000000004,
  "actual_native_financial_CAS_source_mutations": 0
}
```

合成probe費用 wall0.093495255秒 / CPU0.044185497秒。source読取・外側import・メモ固定込み総費用はunknown。金融生成/RNG/SDE/solver・実native操作・production/source編集・CAS/Git操作は0。旧root trial/batchの実費・状態は本probeで再審査していません。v1失敗と既存原履歴を保持します。
