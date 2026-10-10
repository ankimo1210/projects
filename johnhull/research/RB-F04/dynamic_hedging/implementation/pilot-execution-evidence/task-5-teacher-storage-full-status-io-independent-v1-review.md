# Full-status native teacher I/O：保存済み合成部品の独立レビュー

## 判断

**元全形状を保つ単一合成教師の native 保存・読戻し部品観測を限定承認する。** 金融資格・genuine 全教師圧縮率/速度・正式容量予算・pilot/main/phase の受入は unknown / 未承認。

root の実行は事前に固定された 4 GiB RSS / 180 s の行政部品予算に結合される。候補 false 段階の probe は未実行で保持し、事前承認・source81・input/probe SHA を持つ別 root-fixed budget を原 receipt と照合した。

## 独立に再検算したこと

- 元 **N65536、全65元high-grid date0閾値、16 blocks**、full path/cluster order、全769 calendar/12 fixing を保持。
- 全 **65536×768 uint8 stepstatus**、**U128** failure reasons、**U7** primitive status、9 full float64 vectors を原保存値から検査。
- 全11 sample fields は各65536×65 float64、全 finite。f_samples は cv_samples alias。全 N を用いた raw/aux payoff と raw threshold derivative を独立式で再計算した。
- 全 original sample mean/SE、4096経路×16 blocks の price/derivative block means、全390×390 joint covariance を独立 NumPy で原保存 summary と許容差比較。全42原 summary/status fields は reader 後も物理原値を保持。
- root＋全 pack の receipt/由来 binding、全46 NPY の公開 header reader で shape/dtype/byte 検算。root pack payload 0 B / NPZ22 B、唯一の data pack **93,602,864 B payload**、**93,608,752 B expanded**（NPY headers込み）、**1,704,762 B compressed NPZ**。128 MiB payload /256 MiB expanded の各上限内。
- source81 と原保存10files は独立検査前後不変。金融 worker / RNG は 0。

最初の静的 preflight で metadata 包装の参照ミスを指摘した。root が metadata.json の metadata.teacher_storage 経由へ修正し、実観測は修正後の固定 probe SHA baed09d155d8d2476329bcf5bd7d6b5cd5bb07fdcdddc506a7cf9dffd590c9db に結合される。checkpoint が欠落した exit0 を完了扱いすることも隔離 AST 反例で拒否確認し、実 parent は最終 full-returned 復元 checkpoint を必須にする。

## 費用と cap

| 範囲 | wall | CPU | RSS |
|---|---:|---:|---:|
| root 外側（事前検証・起動・全子工程・終了後 source/progress/inner receipt） | 10.928016223 s | 内側 parent＋child 11.138593 s | root child peak 3,466,457,088 B |
| root 内側 | 10.886324132 s | child 10.842933 s | 上と同じ観測対象 |
| 独立 saved-only 再検算外側 | 5.471254653 s | child 5.120084 s | sampled peak 3,126,276,096 B |

root 外側は内側を包含し、外側 tail は 0.041692091 s。内側・外側の時間/CPUを加算しない。root RSS peak と内側/外側 wall は 4 GiB/180 s に届かず、原 overrun は 0。RSS は process RSS であり address-space cap ではない。独立読取でも同じ安全上限を監視し、cap なし。外側 observer 自身の CPU と最終 receipt 保存、レビュー準備・報告保存の費用は unknown。

## 推論を広げない境界

この primitive は合成 b/c/mu/sigma/last-state を持ち、driver は None、chunks は空。モデル path-law は認証していない。全ステータスが ready/空理由であり、高圧縮率はこの値分布の観測である。**実際の 4 whole teacher grids、異なる経路値/failed statuses、金融 job の RSS/速度/精度へ外挿しない。** 10.93 s はこの単一合成 I/O 部品だけの実費。これにより正式全容量や移行日程が成立したとは判断しない。

証跡：task-5-teacher-storage-full-status-io-independent-v1-probe.py/log/results.json/parent-cost.json。原 root evidence は observation-root-v1 と root-enclosing-cost-v1.json。preflight v1/v2失敗/v2/v3 も保持。
