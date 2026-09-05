# 実行ログの索引

- `E0_baseline_tests.log` と `E0_baseline_cli.log` は、原本ではなく `audit/baseline_workspace` の再現実行であり、いずれも成功した。
- `E1_unit_and_bidask_audit.log` は生入力と初回コピーの監査出力の独立突合であり、成功した。
- `E2_long_end_multiplier.log` は市場データのパスを一段浅く指定して `FileNotFoundError` で終了した失敗ログである。次の `E2_long_end_multiplier_retry.log` は正しい公開パスで成功した。失敗結果をモデルの数値結果として使っていない。
- `E3_output_schema_and_numeric_validation.log` はHTML見出しを文字列集合との集合演算で検査したため、存在する見出しを誤って未検出と表示した診断スクリプトの失敗である。提出コード・出力は変更せず、部分文字列検査へ訂正した `E3_final_schema_validation.log` が成功している。
- `E3_final_cli.log`、`E3_final_schema_validation.log`、`E3_original_manifest_check.log` が最終採用版のCLI、数値・スキーマ、原本マニフェスト照合ログである。
- `removed_copied_build_metadata/` は提出コピーから可逆的に移した初回コピー由来のegg-infoビルドメタデータであり、提出物の実行や数値結果には使わない。
