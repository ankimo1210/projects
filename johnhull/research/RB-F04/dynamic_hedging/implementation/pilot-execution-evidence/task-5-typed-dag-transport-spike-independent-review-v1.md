# typed-DAG transport Spike：限定独立確認

2026-10-10。**判断：指定した小合成payloadの論理値・既存digest・mutation隔離はPASS。production採用は未承認。**

固定source SHA **16768870e07b602d610cbd1f24af5b41fbe4ff81c7bc7f52fa40423f18f5ef52**、selftest SHA **7afadc52170499ac6ca0c3ff688b83d303532fee6dbed49a036bae43e02b6781**。原run_reference.pyの _encode_tree / _decode_tree / payload_digest と HestonParameters は実sourceの指定ASTだけを抽出し、金融moduleをimportしていません。

独立実行は既存合成 **2 tests PASS** と別小fixtureの **12項目PASS**。同じdict/arrayを左右へ反復したpayloadを、原literal保存読出とも比較しました。原normalized payload_digest一致、tuple→list、NumPy scalar→Python scalar、bool/int/floatの区別、signedzero、非finite、実Unicode、Parameters別instance、dtype/shape/endian/NaN/0d/empty/strided/Fortranの論理値と由来bytesを確認しました。数値はequal_nan付きallclose、実bytes比較は保存由来の保持として扱い、金融精度へ昇格していません。

unique2配列からlogical3出現を戻す小fixtureでは、各dict/list/arrayの出現が別object、arrayはwritableでshares_memory=Falseです。片側array、nested original_N、textを書換えても隣edgeと原inputは変わりません。共有intern後の読出は各edgeごとに完全展開しており、logical occurrenceの省略はありません。

## 独立原probe

```json
{
  "scope": "synthetic logical/alias compatibility only",
  "independent_existing_tests": 2,
  "tests_pass": true,
  "test_log": "test_repeated_objects_decode_as_independent_writable_occurrences (dag_spike_independent.SyntheticDagTests.test_repeated_objects_decode_as_independent_writable_occurrences) ... ok\ntest_dtype_shape_empty_zero_dim_nan_bits_and_signed_zero (dag_spike_independent.SyntheticDagTests.test_dtype_shape_empty_zero_dim_nan_bits_and_signed_zero) ... ok\n\n----------------------------------------------------------------------\nRan 2 tests in 0.016s\n\nOK\n",
  "additional_reference_and_alias_checks": {
    "original_reference_digest_equal": true,
    "tuple_normalized_to_list": true,
    "bool_int_float_types_distinct": true,
    "signed_zero_preserved": true,
    "numpy_scalar_normalized": true,
    "actual_unicode_values": true,
    "Parameters_instances": true,
    "dtype_shape_and_logical_values": true,
    "array_actualbytes_provenance_equal": true,
    "all_edges_independent": true,
    "writable": true,
    "mutation_isolation": true
  },
  "all_additional_pass": true,
  "unique_array_count": 2,
  "logical_array_occurrences": 3,
  "source_sha256": "16768870e07b602d610cbd1f24af5b41fbe4ff81c7bc7f52fa40423f18f5ef52",
  "reference_bindings": {
    "runner": {
      "path": "/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F04/dynamic_hedging/run_reference.py",
      "source_sha256": "cc7183df08f8d4b7942929ccc44cbcc5899be5df74128016c7c6521bac2909b9",
      "selected_ast_sha256": "fd4356ada0b9e9c1d86c15ff24c340880d6d0d6869bf8a5c1d88e7ce032584e1"
    },
    "parameters": {
      "path": "/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/_heston_local_surface.py",
      "source_sha256": "b343578fd31b48457680b4da2e34fedf41f9724af77b5010929141cd74e2a622",
      "selected_ast_sha256": "5d49b18426b0369fdf45969219243d479c9b7d8d57f2ccecfd41e608a436ef62"
    }
  },
  "wall_seconds": 0.019588525996368844,
  "cpu_seconds": 0.020395710999999928,
  "physical_rate_or_speed_extrapolation": false,
  "financial_RNG_native_CAS_source_Git_changes": 0
}
```

作者5 tests・4測定は作者証拠として保持し、独立件数へ足しません。測定圧縮率・速度をproduction容量や全phase ETAへ外挿していません。DAG読出は全logical arrayをcopyし、既存digestも全出現を走査するので、戻りpayload/RSSを減らす証明ではありません。

prototypeの明示範囲はstring-keyed通常payload／非object・非structured array。旧reserved marker衝突は再定義しません。bounded metadata decompression、256MiB pages、既存receipt/保存形式・両復元互換、malformed型拒否、実大規模RSSは未検証のままです。ここで新しいproduction承認条件を追加したのではなく、合成Spikeをこれらの承認へ転用しない境界です。

probe内部（NumPy import後）wall0.019588526秒 / CPU0.020395711秒。起動・外側読取・メモ固定込み総費用はunknown。金融生成/RNG/SDE/solver・実native読取/操作・production/source・CAS/Git変更は0。本メモのみDに追加しました。
