# Genuine M6 Heston-coarse memo 資源計測の保存結果レビュー

**限定承認**：N1024・108節点・12日付・全33threshold の資源／由来／保存転送観測。金融資格は unknown、正式 pilot/main・精度・最大N・全体予算・ETA は承認しない。

- 全701原ファイル（64,420,530B）と81 runtime source のSHAを由来として照合し、108 native root＋全packのbindingを確認。
- cold/hit/fresh の全検算呼出し数は **1/0/1**、今回のSDEフラグは **true/false/true**。hit のレポートは初回に完了した証跡を保持する。
- 3レポートと元cacheを rtol=1e-11, atol=1e-12, equal_nan=True で比較。最大有限差0。全Nの11sample descriptor、16block、共分散、NaN、unknown 1,304 threshold、全108節点の未資格を保持。
- cold **23.670931s**、hit **0.222289s**、fresh **23.796868s**。約106.49倍はこの同一入力だけの観測。全体ETAへ一般化しない。
- 外側wall **52.226233s**、root＋子孫CPU **54.741425s** を一度計上。RSS peak **696,823,808B**、capなし、RSSの不明サンプル1件を保持。内側費用・以前の生成費用を加算しない。
- producer 4e8…／旧saved checker 408… を維持。新runtime canonical _digest は 959…、envelope payload_digest は 0df…。
- 初回レビューprobeの scalar status 仮定の誤りとFAIL費用を保存し、33threshold配列としてv2で訂正。計測sourceの欠陥ではない。追加SDE/RNG/solver/生成は0。

詳細・許容差・費用原本のbindingは task-5-phase-local-memo-resource-independent-results-v2.json、判断は task-5-phase-local-memo-resource-independent-decision-v1.json。
