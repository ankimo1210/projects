# Tiny source-connected experiment

2026-10-10。**constant-volの原N32、1updateという接続試験。正式pilot/main・OOS性能ではない。**

最新 `source-f96d768f5f47-n32-update1/` は12fit/12weights・56validation候補・44cells、Heston/local各32paths、teacher48/196groupsを保存。全44cells unknown。coarse call/grid、共有train/validation fixture、未測定精度を認定しない。

実CLI whole wall6.5156秒/CPU6.4425秒。immutable JSON+nonobject NPZ48,897,658B、expanded45,735,944B。[原実行](../../implementation/task-5-runner-report.json)に38required expenses（complete30/pending8）。store/restore/check費用はrecoveryへ別記録し、元ledgerを変更しない。

最新[manifest](source-f96d768f5f47-n32-update1/evidence-manifest.json)／[recovery](source-f96d768f5f47-n32-update1/recovery.json)で各C/Fを別restoreし現行 `run_reference.py --phase check --input <restored-dir>` を実行。原12fits/44cells/全N/teacher groupsを保持してPASS。独立reviewはRNG/train/先行SDE/CF/PDEの26操作を禁止して同artifactを再検算。

旧 `source-c7347038a574-n32-u1/` は元byte・旧source時点のCLI tiny/check・費用を保持し両CASへ保存。registryが異なるため現行sourceで旧artifactを再認定していない。

保存境界の再計算は実training→weights、train-only scaler、loss/update/capの原履歴、先行SDE、独立金融精度、正式freeze/main統計を認定しない。[残り](../../implementation/TASK5_CONNECTORS.md)。
