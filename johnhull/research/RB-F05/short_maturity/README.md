# RB-F05 短期・0DTE

2026-10-09。状態：事前実装/独立レビュー完了、対象1275 tests・16Python ruff/format・tracked release PASS。正式84×3 pilotの保存数値checkerと両341MB保管庫の独立復元/数値再検査PASS。N=1048576だけが全slot ready。正式pilot独立レビュー中、freeze・主6fits・正式教材/採否・mainは未完了。

[設計](../../../docs/superpowers/specs/2026-10-09-short-maturity-dml-design.md)／[実施計画](../../../docs/superpowers/plans/2026-10-09-short-maturity-dml.md)。

合成同日cash call、ACT365 carry・252日分散時計・Poisson pulse、C/spot Delta/spot Gamma。教師のSEとrare count、6paired price-only/DML、独立級数/密度参照、強Hermite、全費用・保存3図・独立採否まで実施する。本編・既存digital/discrete成果は変更しない。Bates/PIDE/roughと動的ヘッジの完了は意味しない。

## 基礎検証（2026-10-09）

[基礎実装/検証](FOUNDATION_VALIDATION.md)・[独立参照84条件](INDEPENDENT_REFERENCE_PREFLIGHT.json)・[接続smoke](FOUNDATION_SMOKE.json)。主実験・freeze・採否・main統合は未完了。

## 正式pilot

[保存数値検査](pilot_validation.json)／[N選択](pilot_selection_summary.json)／[全CLI原価](pilot_process_cost.json)／[保管庫manifest](pilot_manifest.json)／[両コピー数値復元](pilot_cas_validation.json)。84条件×3streamの元分母と全raw/CRN unsupported・inconclusiveを保持。N2^18は235/252 ready、価格SE最大.00216235で規定.002を超える。N2^20は252/252 ready、event active最低905、価格SE最大.00106944。raw診断はcoverageや手法不偏性の承認ではない。正式pilot独立レビュー後にN/source/条件をfreezeする。
