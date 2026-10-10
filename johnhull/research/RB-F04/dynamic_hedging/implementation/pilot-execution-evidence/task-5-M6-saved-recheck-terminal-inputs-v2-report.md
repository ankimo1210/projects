# M6 terminal 入力固定 v2（2026-10-10）

完成した最終manifestは task-5-M6-saved-recheck-terminal-inputs-v2-manifest.json。
SHA256: 511191b8a3147c03ddebbafd4989e8f51cfd72428e8296338484fd3d15ecfbf8。

v1の全入力・証跡を保持し、旧prior budgetのprobe_source_sha256に結合する実生成observer measurement-v2.pyと、outer receiptのroot_log_sha256に結合するroot-v2.logをshared mapへ追加した。2ファイルのbytes/SHAは原receiptと一致する。元M6 directory外の由来参照の漏れをこれで閉じた。

最終13157ファイル、5437753447bytes。元全N1024・2128node（108/156/520/1344）・2driver・field・initial obligations・全旧checker/費用/cap履歴と4339 physical receiptsはv1認証結果をそのまま保持。全class map、全以前shared SHA、元history/cap/state/identityの不変も保存再読で確認した。

主検証はv1の行政12case/Ruff2/format2。v2は旧manifest exactSHA→2外部由来SHA→保存再読の限定検証とRuff1/format1がPASS。補完の親込みwall0.097775822秒、childCPU0.103546秒、RSS37404672bytes。v1の成功・失敗・行政中断費用は全て別保存済み。元金融費用を新検査に再加算しない。

candidateはfalse・new checker approvalはnullのまま（元candidate SHAも不変）。金融配列decode/RNG/solver/SDE replayは実行していない。production source/tests/docs/Git/CASは無変更。金融qualification、formal pilot/main/phase承認はunknown／未承認。

次はrootによる新bounded checkerの独立承認・source closure固定と、別名prior budgetによるsaved-only recheck。原generator source81 identityと新checker approvalは別に認証する。

詳細: task-5-M6-saved-recheck-terminal-inputs-v1-report.md。
