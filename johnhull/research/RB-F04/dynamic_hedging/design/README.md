# 設計検証の保存証拠

2026-10-09。決定的な数式検査・反例・試作の記録。正式pilot/mainの精度達成ではない。

| 原レビューに記録された /tmp file | 正本のコピー |
|---|---|
| rbf04_dynamic_design_probes.py | [数式probe source](design_probes_source.txt) |
| rbf04-dynamic-design-probes.json | [probe結果](design_probes.json) |
| rbf04_dynamic_moment_recheck.py | [24条件再計算source](moment_recheck_source.txt) |
| rbf04-dynamic-moment-recheck.json | [24条件再計算](moment_recheck.json) |
| rbf04-implicit-cir-moment-bound.json | [初期moment certificate](implicit_cir_moment_bound.json) |
| rbf04-dynamic-design-review.json | [独立レビュー](../DESIGN_REVIEW.json) |

[exact source proof](design_source_proof.json)は原記録のpath/hashを保持する。コピーは原byteを変えていない。sourceの.txtは記録保存用で、既存Pythonで実行できる。新依存・学習・乱数生成は不要。

旧 [CM2-LN auxiliary probe](rejected_ln_auxiliary_probe.json) / [source](rejected_ln_auxiliary_probe_source.txt) と [最初の実現性probe](old_feasibility_probe.json) / [source](old_feasibility_probe_source.txt) は試作履歴。旧Heston schemeのpopulation moment欠陥があり、そのsample SEを正式N選定やCI認証に使わない。[実現性メモ](../CONDITIONAL_FEASIBILITY.md)の範囲を参照。

数式/設計の独立レビューは[DESIGN_REVIEW.md](../DESIGN_REVIEW.md)。新implicit CIR/actual local fieldの正式pilot精度は未検証。
