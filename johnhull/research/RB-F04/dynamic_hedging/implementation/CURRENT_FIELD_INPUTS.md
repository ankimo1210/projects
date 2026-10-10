# 現行fieldと元pilot入力の再照合

2026-10-10。正式pilot/main/freezeは未実施。本書は正式入力の準備と部品測定の証跡であり、金融精度・研究受入の承認ではない。

## 発見と修復

保存済みfield257×321は order1024、frequency_scale512、各時点のcutoff=512/√t、density_floor1e-10で作られていた。旧正式graph案はorder2048/cutoff1024固定を指定していたため、最短t=1/4096の中心がunsupportedになりfieldを生成できなかった。v2の失敗raw/全宣言shape/clockを残した。

元の現行build_surfaceで作り直したv3と、修正したrun_field_jobの実adapterを使ったv4は、82,497点の値を保存原典とrtol1e-10/atol1e-12で照合し、support/wing境界も一致した。入力18statesのQ・24monthly diagnostic queries・元stream namespaceは保持。1/24・1/48の追加local状態も元値と許容誤差内で一致した。run_field_jobのfrequency_scale指定とその保存再検算はpilot sourceの独立確認対象であり、この部品再現を全pilot source承認に広げない。

## 実測範囲

| 試行 | 結果 | 専用childの実wall/CPU秒 |
|---|---|---|
| v2 固定cutoff | unsupported中心、失敗保持 | 1.313325 / 1.304562 |
| v3 元build_surface | 全fieldと元入力の再現 | 9.814656 / 9.803271 |
| v4 修正adapter | 全fieldと元入力の再現 | 8.137211 / 8.126260 |

parent費用はcold start/import、field、入力組立、raw/JSON保存までを含む。内側のfield/入力時計はその一部なので加算しない。v4のfield計算は3.536480秒、raw保存は0.050343秒。元18Qを変更せず、追加CF観測14本とlocal追加2日付の再fitを行った。固定シードMC/教師/正式市場経路は開いていない。入力作成中の数式/コード編集時間は未計測であり、正式全費用が判明したとはしない。

## 保管と保存後の照合

[元byteの小証跡一覧](field-input-evidence/files.json)、[rawの保管庫manifest](field-input-evidence/task-5-field-input-manifest.json)、[保存後の照合](field-input-evidence/task-5-field-input-cas-check.json)を保存した。大きなfield配列はGitではなく既存C/F両保管庫へ格納した。

- rawは32 entries / 17,216,162 bytes。primary/mirrorから別の新規directoryへ復元。
- 両copyで全field値/support/wing、18/24/4入力、元namespaces、各clock差分と保存費用を再照合しPASS。
- v2は期待したunavailable/全257×321宣言shapeとして保存。成功値へ書き換えていない。
- 最初のCAS検査はreaderのtuple返却schemaの扱いを誤り停止。script/logを保存、費用はunmeasuredのまま。修正試行の専用childは2.313973秒（内側CAS/復元/照合1.026551秒を含む）。
- SHAはprovenance/immutable bytes照合用。金融の比較は上の許容差を使用。

## 正式実験へ残す条件

正式controlsへ元time-scaled cutoff/density設定を結合する。全121cases/51obligations、progressive全N/格子、日付固定domain選択、A原N/実費用写像、独立prior budget/source/inputレビューが済んでからplanをlockする。今回のfieldが再現できたことだけで、teacher/Greek/P&Lの精度や正式全phaseの実行時間を保証しない。
