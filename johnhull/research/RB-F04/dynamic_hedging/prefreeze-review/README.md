# Prefreeze revision design reviews

2026-10-10。**A/Bの限定設計を独立レビュー承認。source実装中。正式pilot/金融precision/readiness freeze/main/研究受入は未承認。**

- [A/B全体の独立レビュー](task-5-prefreeze-revision-review.md)／[decision](task-5-prefreeze-revision-review.json)：Critical0・Important0。原閾値・case・N・unknown、全396評価枠/12fits、費用/fresh/両CAS/3図/最終受入を保持する設計を承認。
- [Bの独立設計レビュー](task-5-fixed-domain-design-review.md)／[decision](task-5-fixed-domain-design-review.json)：blocking0。旧default、全元nodeと16blocks、full call roots後のpatch拒否、local fz/t0/linear、固定operatorとgeneration/replay/freeze bindingを必須契約にする。
- [独立反例](task-5-fixed-domain-design-review-probes.json)：call root domainをpatchへ狭めると元nonuniqueを隠す。元full root検査を維持する。
- [原byte一覧](archive-files.json)：10原ファイルをそのまま保存。source probeは `.py.txt` として保管。旧レビューも保持。

レビュー対象は [当初の候補snapshot](../PREFREEZE_REVISION.md)、SHA256 `3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b`。そのsnapshotの「レビュー待ち」は作成当時の状態。本ページが現在の設計レビュー状態を示す。

具体boxの金融精度・新source・本物pilot・実行可能freezeの承認ではない。旧strict v1 candidate/guardは保持し、source TDD/独立レビュー、全必要pilot attempt/refinement/費用を閉じた後に実行可能freezeを評価する。主実験は未開封。
