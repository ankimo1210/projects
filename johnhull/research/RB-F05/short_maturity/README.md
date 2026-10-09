# RB-F05 短期・0DTE

2026-10-09。状態：正式設計と実施計画を作成し、private教師・独立参照・CPU学習・C²補間/集計の基礎実装と接続smokeを完了。full pilot/runnerを実装中。pilot/main/freeze/受入は未完了。

[設計](../../../docs/superpowers/specs/2026-10-09-short-maturity-dml-design.md)／[実施計画](../../../docs/superpowers/plans/2026-10-09-short-maturity-dml.md)。

合成同日cash call、ACT365 carry・252日分散時計・Poisson pulse、C/spot Delta/spot Gamma。教師のSEとrare count、6paired price-only/DML、独立級数/密度参照、強Hermite、全費用・保存3図・独立採否まで実施する。本編・既存digital/discrete成果は変更しない。Bates/PIDE/roughと動的ヘッジの完了は意味しない。

## 基礎検証（2026-10-09）

[基礎実装/検証](FOUNDATION_VALIDATION.md)・[独立参照84条件](INDEPENDENT_REFERENCE_PREFLIGHT.json)・[接続smoke](FOUNDATION_SMOKE.json)。主実験・freeze・採否・main統合は未完了。
