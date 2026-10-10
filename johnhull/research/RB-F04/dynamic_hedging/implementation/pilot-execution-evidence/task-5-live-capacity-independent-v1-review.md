# 稼働中保存容量の独立診断

対象は正式pilotの保存表現と資源前提です。金融資格・phase受入・全体容量保証は未承認のままです。2026-10-10 UTC、実験を止めずに stat・ZIP/NPY小header・実sourceだけを読みました。数値は decimal GB、容量guardは GiB です。

## 結果

- 10:47:13 UTC の native は **73.260 GB**、実allocatedは **73.308 GB**。jobsは136件、**最初の Heston / N1024 / coarse の81件だけで71.258 GB**です。走行中の非原子的scanであり、完成量や増加速度の推計ではありません。
- 同stageの内訳は NPZ **64.555 GB**、root metadata **4.987 GB**、その他 **1.715 GB**。width0単体は **2.946 GB**、そのroot JSONだけで **566.474 MB**、bump単体は **1.964 GB**です。
- paired・width0・bump の先頭NPZを小headerだけで確認しました。いずれも4096 members、**ZIP_STORED、stored bytes = expanded bytes**。normal cube の (256,1536,2) float64 や (1024,12,16,3) float64、path statusのUnicode配列などを保存しています。

## 保存契約との対応

run_pilot.write_pilot_artifact のpack圧縮は storage_descriptor がある場合だけです（run_pilot.py:1867）。_teacher_storage.prepare_teacher は完了した最上位 kind=teacher だけを対象とします（_teacher_storage.py:243）。paired / bump / refinement の入れ子のteacher・driver・cacheは通常のliteral表現になり、_encode_tree は配列の各出現へ新しい名前を付けます。shared Python objectが保存上で反復する構造があります。**今回、実binaryの同一性は検証していません。** 同receipt候補とhardlink契約は別のsource診断です。

paired は base/refined のdataset・rollout・risk・shared_market、bump はdataset・caches・base_risk・各variantを保持しています。原primitive、全node、original N、failed/unknownの保持を減らす変更は本診断の対象外です。checkpointは raw を除き由来digestを保存しており、checkpointが全rawを再複写するという主張はしません。

## 現在の容量・費用前提への影響

既存 static-v1 の **364.186 GB** は teacher / driver / domain / report の限定logical subtotalです。元3138jobsのうち **残3088jobsを明示的に対象外**としており、今回大きいcell_pair・bump等もその外側です。teacher用codecの圧縮率をこの領域へ外挿できません。これは旧subtotalの算術誤りではなく、wholephase physical容量が未確定というcoverageの限界です。progressive graphの全候補stageが実行される保証もありません。

DESIGN §7のNPZ分割上限256 MiBは **packごとのexpanded bound** です。width0の2.946 GB／root JSON566 MBが、これをwholejob・root JSON・RSS上限と扱えない具体例です。各process16 GiB／各volume10 GiB reserveの実monitorは行政停止とpartial保全の境界であり、全corpusの完成容量や金融case cap PASSを保証しません。独立保管庫は各々にcorpus・履歴・一時領域が必要です。

個別jobのdispatch時計は保存前に閉じ、writerはrun_pilot.py:4399でその後に実行されます。rootの外側phase費用には保存が含まれますが、serializationの大きいこの形式ではdispatch-only時間をwholejob保存込みの速度へ使えません。現時点のwholephysical上界・complete runtimeはともに unknown です。

## 範囲と証跡

原3138jobs・121cases・51obligations・4N・20teachers・10drivers・source5d/568・全unknownを保持。新金融生成、RNG、SDE再検算、solver、worker/Popen、巨大JSONparse、live全SHA、停止、production/Git/CAS変更は0です。詳細の値と小headerは同prefix results.json、既に実行したstat/header readerの原sourceは stat-header-probe.py に保存しました。元実験のrawは書換えていません。

scan内のstat時計は0.566702秒です。ZIPheader・import・他source読取・報告保存を含む総費用は未測定。失敗したreaderのsyntax／PowerShell引用／旧DESIGN-path照会もtool原記録に保持し、source欠陥や金融capへ読み替えていません。
