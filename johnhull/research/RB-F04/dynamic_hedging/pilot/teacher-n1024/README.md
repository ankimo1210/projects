# Actual N1024 teacher preflight

2026-10-10。**原selected36slots、35実行/1fitunknownを保持した事前測定。正式pilot未承認。全qualification unknown。**

| SE条件 | 満たした原slots |
|---|---:|
| priceSE≤.03 | 18/36 |
| hS 16blockSE≤.002 | 10/36 |
| hQ 16blockSE≤.005 | 9/36 |
| 3条件同時 | 6/36 |

underresolved5は極小SEでも合格にしない。state15.Hestonは低Q識別不良で未実行、観測Qを実varianceで置換しない。元分母36を保持。

[原metadata](preflight.json)・[詳細](REPORT.md)・[実probe source](probe-source.txt)。固定seed/768global IID driver/N1024、月次12fixing、Qのfit状態からbaseとCRN±S/±stateを実行。175calls、82,247,680pathsteps、whole child process45.117秒/CPU45.063秒。raw240,626,504B≤256MiB、NPZ48,764,846B。peakRSS未測定。

[saved-check](saved-check.json)は全175callsのCE/control・calendar/fixing・元N/driver slice・CRN derivative/IFT/16block covarianceを許容差で再計算。65source/input bindings不変。[元checker](saved-check-source.txt)は先行SDE/RNGを実行しない。直接教師bumpはproduction cubic cache微分の精度認定ではない。

Git外の `reference.npz` は[manifest](evidence-manifest.json)から各C/F CASを別directoryへ復元。元checkerの入力directoryのみ変更＋RNG禁止guardで再検算。[recovery](recovery.json)に各費用・実行source・チェック境界を保存。原reportを上書きしない。

有限bump bias、SDE/格子/分母/CS/独立Asian参照/補間誤差は未測定。N増加前にstate感応度分散とunderresolutionを検討し、正式pilotを別receiptで実施する。
