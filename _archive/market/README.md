# 旧市場研究プロジェクト

現行の統合入口は [market-research](../../market-research/README.md) です。
旧コードは比較と復元のために保管します。ここにある README の起動例は
退避前のパスを示すため、そのまま実行しないでください。

| 旧プロジェクト | 退避理由 | 後継と残す機能 | 実行可能性・復元 |
|---|---|---|---|
| [stock](stock/README.md) | 価格・財務・バスケット等の初版対応を統合先で実装・合成検証し、旧Dash入口を退避（2026-09-28） | F16のAIチャット・コード実行と8画面は旧成果として保持 | 退避前のstock/market-viz合計56 tests成功。ライブAPIと旧画面の再起動は未検証。退避前commitから専用worktreeを作り、当時のuv環境で再実行 |
| [market-viz](market-viz/README.md) | 日足・市場概要・品質・アラート表示の対応を統合先で実装・合成検証し、旧UIを退避（2026-09-28） | 暗号資産イントラデイ更新、FastAPI、Next.js scaffoldは旧成果として保持 | 退避前のstock/market-viz合計56 tests成功。旧フルスタック起動は未検証。退避前commitから専用worktreeを作って再実行 |
| [autostock](autostock/README.md) | Mag7の固定研究例を統合先で比較可能にしたため（2026-09-28） | market-researchの因果的なprefix評価。自律編集ループと当時の報告・画像は旧成果として保持 | 退避前の旧5件は410 passed/13 skipped。移動後のautostock testsは17 passed。旧自律起動と価格取得は未検証。必要なら退避前commitで専用worktreeを作り、READMEの旧パスで実行 |

退避先の report.py / plot.py は同じディレクトリの results.tsv を参照します。
各cloneで追跡外の旧 autostock/results.tsv が残っている場合は、内容を公開Gitへ追加せず、
_archive/market/autostock/results.tsv へローカルで移してから再生成します。
旧パスもルート .gitignore で除外し、移行前に誤って追跡しないようにします。
保存済み report.html と progress.png はそのまま保管します。

stockとmarket-vizの追跡外ローカルデータ・設定・生成物は公開Gitに含めません。
各cloneで旧パスに残ったものは、内容を確認し、同じプロジェクトの退避先へ
ローカルで移します。退避前の全環境を再現する場合はmainの移動前commit
6fbd93caから別worktreeを作り、当時の依存をインストールします。
stockのキャッシュはSTOCKKIT_DATA_DIRで退避先を指定できます。market-vizの旧画面は
旧worktree内の data/ を参照するため、再実行時だけローカルDBをその場所へ
コピーしてください。公開Gitへ追加しないでください。
