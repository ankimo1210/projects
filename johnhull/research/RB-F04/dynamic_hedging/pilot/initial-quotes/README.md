# Initial37 quote preflight

2026-10-09。**T1.25を覆う実Heston-marginal local fieldで、原fit25+holdout12を測定・保存再計算。正式動的pilotは未承認。**

| 比較 | 原37値の最大差 |
|---|---:|
| 独立CF積分・Fourier order/cutoff + quad誤差 | 3.95927e-10 |
| field129×161 / PDE1201×960 | 0.000498730789 |
| field257×321 / PDE4801×1920 | 0.000104082529 |
| PDE時間1920→3840 | 7.02430e-8 |
| PDE領域1.8→2.4（同dx） | 9.59233e-14 |
| early tmin1/4096→1/16384（後段元time nodesを保持） | 6.04756e-8 |
| z±5→±6 | 1.60247e-5 |

単価の条件は元candidateの.001、CF差/誤差1e-8。全8 PDE attempt・7 refinement・37元IDを保存し、最小測定candidateの選定だけを表示。[raw metadata](initial-quotes.json)・[saved-check](saved-check.json)・[source](initial-probe-source.txt)/[refinement](refinement-probe-source.txt)へ詳細。

[checker](../../check_initial_quotes.py)は元積分receiptからCF価格/価格単位の誤差、PDE格子からS100のquery、37差、refinement pair差を再計算。別の時間順receiptもtime/strike identityから元ID順へ戻す。元stage配列の消去は拒否。元quad/PDE solveを再実行・証明したとは呼ばない。マスク内は正有限の連続支持とT1.25覆域を確認する。

原rawは487非object arrays、uncompressed33,375,237 bytes／NPZ30,535,323 bytes。Git外の `reference.npz` は[両保管庫manifest](evidence-manifest.json)から復元。[復元記録](recovery.json)でC/Fを別々にrestoreして同checkerを実行。SHAは同定のみ、金融算術は許容誤差で比較する。

元spikeのengine wall100.077011秒/CPU99.999686秒は、raw記録のtiming_scopeにある計算部分の測定。起動・import・最終保存などを含む完全なprocess費用は未測定であり、0とは扱わない。byte復元と金融checker再実行の費用は各receiptへ別保存した。

初期fitだけでconditional call CS/Ctheta・再較正state・Asian教師/position・Q drift・P&L・NN・main/fresh/研究受入をqualifiedへ昇格しない。次の[selected call preflight](../selected-calls/README.md)では18元状態のHeston識別不良1件をそのまま保持する。
