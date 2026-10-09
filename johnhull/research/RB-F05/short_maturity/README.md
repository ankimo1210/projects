# RB-F05 短期・0DTE

2026-10-09。状態：正式84×3 pilot承認・source10/N1048576固定後、640教師/主6fits/336点・追加raw12条件・両保管庫の独立数値復元・実3図・実測費用を完了。主数値review残Critical/Important0。v1受入済み。最終関連3suite7998 PASS/6 skip・19Python ruff/format・tracked release・最終独立208checks PASS。main統合済み。DML全3seedでDelta誤差改善、NN raw/safe全fit精度未達、Hermite336/336 PASS。詳細は[結果と採否](RESULTS.md)。

[設計](../../../docs/superpowers/specs/2026-10-09-short-maturity-dml-design.md)／[実施計画](../../../docs/superpowers/plans/2026-10-09-short-maturity-dml.md)。

合成同日cash call、ACT365 carry・252日分散時計・Poisson pulse、C/spot Delta/spot Gamma。教師のSEとrare count、6paired price-only/DML、独立級数/密度参照、強Hermite、全費用・保存3図・独立採否まで実施する。本編・既存digital/discrete成果は変更しない。Bates/PIDE/roughと動的ヘッジの完了は意味しない。

## 基礎検証（2026-10-09）

[基礎実装/検証](FOUNDATION_VALIDATION.md)・[独立参照84条件](INDEPENDENT_REFERENCE_PREFLIGHT.json)・[接続smoke](FOUNDATION_SMOKE.json)。基礎時点の記録。正式結果は[結果と採否](RESULTS.md)。

## 正式pilot

[保存数値検査](pilot_validation.json)／[N選択](pilot_selection_summary.json)／[全CLI原価](pilot_process_cost.json)／[保管庫manifest](pilot_manifest.json)／[両コピー数値復元](pilot_cas_validation.json)。84条件×3streamの元分母と全raw/CRN unsupported・inconclusiveを保持。N2^18は235/252 ready、価格SE最大.00216235で規定.002を超える。N2^20は252/252 ready、event active最低905、価格SE最大.00106944。raw診断はcoverageや手法不偏性の承認ではない。[独立承認](PILOT_REVIEW.md)／[条件固定の再検査](freeze_check.json)を完了しN/source/条件をfreezeした。主成果は別レビューで判定する。

## 主成果の証拠

[主独立レビュー](MAIN_REVIEW.md)・[外部assessment](assessment.json)・[主検算](main_validation.json)・[追加fresh](fresh_check.json)・[主両復元](main_cas_validation.json)・[fresh両復元](fresh_cas_validation.json)・[実notebook](short_maturity_dml.ipynb)。元recordのpending/acceptedと外部の採否を区別する。
