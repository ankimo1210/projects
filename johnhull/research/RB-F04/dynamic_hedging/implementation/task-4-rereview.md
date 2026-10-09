# Task4 修正差分の独立再レビュー

2026-10-09。元の Important T14-R1/T14-R2 と、修正が生む具体的リスクだけを対象とする。`task-4-fix-review-package.diff`、`task-4-fix-source.json`、`task-4-fix-report.md` を確認した。reviewer による source/tests/Git 変更なし。

**仕様適合 PASS、品質 PASS。元2件は解消、新たな Critical/Important/Minor 指摘なし。Task4 source は統合へ進める。Task1 core/source/tests は original digest のままであり、前回の Task1 統合可判定を維持する。** phase 全体の受入ではない。

## 元指摘の再確認

- **T14-R1 解消** — `_dynamic_hedging_risk.py:152–169,189–192`。負の quadratic は有限で、PSD gate 済みで、`16ε Σ|δ_i Σ_ij δ_j|` の明示 arithmetic bound 内の場合だけ sd0 とする。raw quadratic、bound、flag/count を保存。元の CS=.6/月次 fixture は raw `-1.7763568394002505e-15`、bound `1.7053025658242404e-13`、valid=True、old `[0,0]` 保持、補正count1。CS=.3/.7/.9 も保持した。不正な `[[1,2],[2,1]]` は依然 ValueError、nonfinite covariance は NaN/unknown のまま。ridge や無条件の負値 floor は入っていない。2asset の有限和に対する roundoff qualification として妥当であり、null 無取引契約に整合する。
- **T14-R2 解消** — `_dynamic_hedging_policy.py:324–338`。final diagnostics と thread restore 後に elapsed を判定し、cap 超過した completed を time_cap に下げる。元 clock `[0,.1,.2,2]` / cap1 fixture は `status=time_cap,complete=False,updates=1,updates_complete=True,elapsed=2,overrun=1`。last finite weights と更新実績は残る。既存 nonfinite の status を cap が上書きしない点も妥当。

## 証拠と残工程

4ファイルの現物 digest は fix manifest と全一致。preserved before source と diff hunks から復元した修正後ファイルも全一致。元 Task1 2ファイルの digest は unchanged。小 probe は `/tmp/dynamic_task4_fix_rereview_probe.py` に保存した。green suite は再実行していない。root の報告は risk22/policy10 green、ruff check/formatcheck PASS であり、reviewer の suite 再認証とは区別する。

runner は追加の raw quadratic/bound/roundoff診断と updates_complete/status/complete/overrun を全 attempt と共に保存する。元 review の caller 義務（dataset rejection の全 N 保存、fit/teacher qualification、固定契約・roster・selection）も残る。whole-suite、正式 pilot、source/candidate/pilot/review に結び付けた freeze、main、phase/研究受入は Tasks5–7 の未完了事項であり、今回の task source approval と混同しない。

## 修正後 source digests

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py`: `585ea869a96a6076fedd7749d88824dde5ebbbd99d0ca60a646ac829e39be50e`
- `johnhull/hullkit/tests/test_dynamic_hedging_risk.py`: `1a8ed43b97fdc9b229f5db4fa6ef8c794d6f78c01130f7be96bdb457e4cfbc22`
- `deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_policy.py`: `c233ba0cf6d736401c4f2a4d92dc803810c8066ebf7960534730299759142fca`
- `deep_hedge_price/tests/test_dynamic_hedging_policy.py`: `0b5929aeda2d044b3b70bc13c7d07c315a9a9166153479877a2daa3c3ff156cb`

Fix package SHA256: `25531b409ac2c2323ce727ad290115bc68f8448368570a9dc69977df1e888b96`。Fix manifest SHA256: `9528709147ad7363af9aa24a7003368f7f14766c088130a78d18fe3e28aa2cdb`。
