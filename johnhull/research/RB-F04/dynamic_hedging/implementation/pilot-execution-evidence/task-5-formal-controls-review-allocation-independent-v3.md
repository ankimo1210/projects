# 全形状 allocation / artifact I/O v3 独立レビュー

2026-10-10。対象は task-5-formal-controls-review-allocation-observation-root-v3/、診断script v3、root事前budget v3。

**限定 component 記録は妥当。金融教師・実価格・全teacher jobの費用/最大RSS・formal plan資格は unknown のまま。**

## 点検結果

- script SHA 94cab631ba7ded72375ce9396ff9dc912f1bfb05de299cd49b9f4b5a313ec2b5、prepared input SHA、source4本の実SHAをroot prior budgetと照合。前後source同一。budget固定時刻02:55:50 UTCとmtimeが最初のrawより前。
- 元N65536、high/local/date0の非等間隔threshold65個、16blocks×4096本を保持。各labelは65536×65のfloat64。
- 異なる10 labelのpayloadは340,787,200B。f_samplesはcv_samplesの**値entry**として復元される。復元後のPython alias identity / shared memoryは保持されない。現行記録の「alias復元」は値を意味する。
- 独立に45 NPY headersをstdlibのmagic/length/ASTで読んだ。shape・dtype・payload・ZIP expanded size・receiptと元independent-chunk-bytesを全件照合した。
- 4 packsの最大payload103,590,448B <128MiB（134,217,728B）、最大expanded103,591,984B <256MiB（268,435,456B）。
- 全payload380,119,448B、NPY headers込み380,125,208B。空のroot NPZを含むartifact構造も一致。
- 元native readerで保存物を独立に再読込。全10 labelの形状、alias値、synthetic raw式、価格と微分のmean /16 block集計をrtol/atol1e-12で確認した。
- 元scriptは元10 labelとaliasを全値比較してから完了記録を書く。root exit0 /最後の復元checkpointを確認。本レビューでは原金融pathや教師を再生成していない。

## 時計とRSS

| 指標 | 原記録 |
|---|---:|
| parent wall | 5.711957768秒 |
| child CPU | 5.69656秒 |
| native labels部分 wall | 2.274154356秒 |
| artifact write wall | 0.854019737秒 |
| read + full-label比較 wall | 1.160380373秒 |
| 最大process RSS（/proc sampleとkernelの最大） | 2,938,032,128B（2.938GB、約2.736GiB） |
| kernel child peak | 2,937,769,984B |
| 事前RSS上限 | 4GiB |
| 事前wall上限 | 180秒 |

parent/child clockの包含、elapsed差分、overrun0、実RSSが上限内であることを確認した。
RSSは0.01秒の/proc監視とkernel ru_maxrssによる観測で、RLIMIT_ASではない。瞬間的な硬上限保証ではない。
parent wallはchild起動からwait完了まで。CPU値はRUSAGE_CHILDREN差分で、親監視CPUを含まない。事前fingerprint確認・事後receipt書込はこのwall区間の外。
この区間と、正式jobのenclosing expenseの範囲を同一視しない。

## 原失敗・限界

- v2の子exit1、completed_component=false、NPY private API _read_array_headerのAttributeError、途中までのraw/checkpoint/log/費用を保存したまま確認した。cap成功として扱わない。
- v3は公開NPY header readerへ変更しただけで、shape/N/label仕事を縮めていない。
- deterministic synthetic primitivesのnative allocationとI/Oを測った部品観測。MC driver、SDE、金融call/teacher精度の観測ではない。
- labelsのstatus/SEはsynthetic入力の計算結果。金融statistical qualificationへ昇格させない。
- 約2.938GBや5.712秒を、全teacher jobのpeak RSS、金融paths/second、原4Nの予算や精度へ転用しない。
- この独立読取は約2.1496秒。追加RNG・金融job・source/docs/Git変更なし。Dの本小reportだけを追加した。

原証跡: root prior budget v3、allocation-probe-v3.py、v3 observationのprogress/parent-cost/independent-chunk-bytes/full-original-shapes、
v2 observationの失敗記録。formal pilot/main/budget/phaseの受入は別作業。
