# M6 原形状・保存資源の独立レビュー

**判断：保存済み資源観測を限定承認。Heston-coarse のみ部品完了、他3クラスの実 RSS cap は未完了のまま保持する。金融資格・正式 pilot/main・予算 lock・phase 完了・全正式容量／速度予測は承認しない。**

固定 source 81 件・入力 26 件は独立 probe の前後で一致。identity 4e8f8b7bad48b9f6bf89b655cd115de835a9a486d89dd6d9ffafcad2b3cb64b0。事前予算 SHA 57314ddcadb722fea8cb54496f2ba586e39a877dbb0e9ba93e383fe1d57b0992 と最終 root receipt が一致。旧 source は 7d929800 commit／D snapshot に固定。本 probe 後、root が freeze を解除して開始する意図的な bounded checker 編集は別作業で、旧測定の source fault にしない。このレビューでは source/tests/docs/Git/CAS は変更していない。

## 原形状・資格・実費

| クラス | 元 N / dates / K | 元節点 | 部品結果 | class wall 秒 | grid child 実 RSS B | unknown_underresolved |
|---|---:|---:|---|---:|---:|---:|
| Heston-coarse | 1024 / 12 / 33 | 108 | completed | 72.053259 | 1926557696 | 1304 |
| Heston-high | 1024 / 12 / 65 | 156 | actual RSS cap / unknown | 114.619496 | 4326535168 | 4022 |
| local-coarse | 1024 / 12 / 33 | 520 | actual RSS cap / unknown | 383.121392 | 4361334784 | 6733 |
| local-high | 1024 / 12 / 65 | 1344 | actual RSS cap / unknown | 831.816587 | 4298833920 | 35123 |

全 2,128 節点が生成・native 書出し・full-teacher 読戻しまで保存済み。未実行 0。元 dates/state/spot/t0-spot/date別threshold axes・N・seeds・全 path ID／16 clusters・driver共有・field/source/input は維持。計画引数と実 typed 引数の input_identity を再計算し、差分は事前許可済みの work_directory と行政 wall_cap_seconds のみ。threshold axes は 12×K、planned_nodes は元節点リスト。

全 primitive path は ready／valid（2,179,072 個）だが、原ラベルには unknown_underresolved 47,182 個が残る。元 NaN f/f_x・unprocessed 全節点義務も保持。Heston-coarse の saved checker にも independent_accuracy と global_driver_generation の未検証が残り、金融資格は unknown。native expense の内部 scope 名を正式実験承認へ読み替えていない。

root 外側 wall 1401.807423751 秒、内側親子 CPU 1406.361056 秒。class 包含和 wall 1401.610734841 秒／CPU 1406.239385943 秒、外側との差 wall 0.196688910 秒。元 fine driver 2本（各 1024×768×2、12,582,912 B）を保存から全 chunks 認証し、coarse owner 生成費用だけに計上、高 grid へ二重加算なし。driver/grid/class/outer の包含区間を検算。工具外側 exit 1 と実計測 exit 3 の区別を保持。外側観測者 CPU と最終 receipt 書込みは unknown。

cap は個別 child RSS 4,294,967,296 B の実観測で、時間超過ではない。全 class は行政 wall 上限 300/300/600/900 秒以内。RSS はサンプリング値。Heston-coarse には読取 unknown 1件、progress kernel RSS は最終 checkpoint 時点の値。親子合算 RSS や厳密時刻間最大値を認定していない。

## 実保存量（全 native node のみ）

| クラス | 物理 NPZ B | ndarray payload B | 展開 NPY（header込み）B | metadata+receipt B |
|---|---:|---:|---:|---:|
| Heston-coarse | 32862385 | 178031088 | 178708464 | 2693943 |
| Heston-high | 137347851 | 479200176 | 480178608 | 3894768 |
| local-coarse | 154528323 | 849936752 | 853198192 | 12968611 |
| local-high | 1192068216 | 4097911504 | 4106341072 | 33556673 |

genuine 元 N1024・原4形状の観測値。全原始9 vector・path mask/status/failure・full N×残存step uint8 status・元 summary/block/covariance を保持。11 sample fields は固定 recipe による全 N 復元。full-teacher cache/container、初期義務、共有 driver、saved checker は別量で、上表へ含めていない。results.json に各量を分離。合成圧縮や他 N／全正式 grid の容量・速度へ外挿しない。

全 physical root/packs の canonical receipts／元圧縮byte SHA／ZIP central directory／NPY header・shape・dtype・coverage・256 MiB expanded 上限を bounded に検算。node binding は全 root+packs へ結合。SHA は由来と保存 byte 認証だけに用い、金融比較は rtol=2e-9／atol=2e-10。96 節点（各 date先頭／末尾、24/class）は保存 primitive から全11 sample field を復元し、raw payoff・価格平均／SE・16 block価格共分散を別計算で確認。全 node Greek や新 SDE／solver／金融 RNG は実行していない。

## cap 後の保存検査の境界

| クラス | checker NPZ B | checker 展開 NPY B | 物理 receipt/header認証 | 最終完了checkpoint |
|---|---:|---:|---|---|
| Heston-coarse | 388738446 | 388002644 | 確認済 | あり |
| Heston-high | 1242905016 | 1241842468 | 確認済 | なし |
| local-coarse | 1872151420 | 1868611580 | 確認済 | なし |
| local-high | 保存なし | 保存なし | 保存なし | なし |

Heston-high/local-coarse に整合した checker root/packs は保存され、ソース順序上 checker 関数返却後の writer/read へ進んだことは分かる。ただし最終保存・読戻し完了 checkpoint が無く部品完了にしない。local-high は full-teacher 読戻し後、checker artifact 保存前の cap。巨大 checker 全 payload は全 decode せず、これを金融検査 PASS としていない。

## 独立検査の費用・失敗

成功 probe 外側 26.013323975 秒／child CPU 25.918483000 秒／kernel peak RSS 804,323,328 B。4,331 physical artifacts を検査。初期 reviewer schema 誤解2件（planned_nodes を件数、date別thresholdを1次元と誤認）は script/log/cost を attempt1/2 として保持。測定済み3回の外側和 30.244078082 秒／CPU 30.126610000 秒。引数probe初期の canonical SHA 仮定の失敗を保存し、文書化済み input_identity に訂正した。引数probe import、探索、レビュー保存のその他費用は unknown。

原 M6 cap／partial／unknown、v56 baseline、合成 I/O baseline は保持。次の bounded saved checker 修正は別の差分・独立検査が必要。本資源レビューの source 編集待ち gate は解除できる。

詳細証跡：task-5-current-full-teacher-independent-m6-v2-results.json、task-5-current-full-teacher-independent-m6-v2-arguments.json、task-5-current-full-teacher-independent-m6-v2-parent-cost.json、task-5-current-full-teacher-independent-m6-v2-decision.json。
