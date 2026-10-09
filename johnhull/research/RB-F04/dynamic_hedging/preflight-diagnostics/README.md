# Prefreeze alternatives / feasibility evidence

2026-10-10。**scratch原証跡。正式pilot/source変更/新protocol承認ではない。**

- [教師SE](task-5-teacher-prefreeze-report.md)：原36slots/16block covariance、state微分が最大hS分散を支配。N65536外挿は参考・未実行。
- [call/put](task-5-teacher-prefreeze-parity-report.md)：β1両版を全35slots無条件比較。put全面採用は根拠なし。
- [cache domain](task-5-cache-domain-report.md)：全108groups/3564nodes/N1024、full-ready curve0/108。固定boxはATM候補を持つが精度未認定。query毎4点cubicはC1不連続。
- [freeze監査](task-5-freeze-feasibility-audit.md)：元state15.Hは非ゼロCv/収束solverでもκ≈.808>.25。元quote-risk契約の拒否でありIFT不存在ではない。

[原file対応](archive-files.json)は同定用。rawは[manifest](evidence-manifest.json)から各C/Fへ保存・別復元。[recovery](recovery.json)はbyte境界のみ。元numeric runsを保持し、代替案の金融精度を独立認定していない。初回Cartesian保存失敗のsource/output/raw/未測定追加費用も保持。

[revision案](../PREFREEZE_REVISION.md)は独立設計レビュー待ち。
