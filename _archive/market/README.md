# 旧市場研究プロジェクト

現行の統合入口は [market-research](../../market-research/README.md) です。
旧コードは比較と復元のために保管します。ここにある README の起動例は
退避前のパスを示すため、そのまま実行しないでください。

| 旧プロジェクト | 退避理由 | 後継と残す機能 | 実行可能性・復元 |
|---|---|---|---|
| [autostock](autostock/README.md) | Mag7の固定研究例を統合先で比較可能にしたため（2026-09-28） | market-researchの因果的なprefix評価。自律編集ループと当時の報告・画像は旧成果として保持 | 退避前の旧5件は410 passed/13 skipped。移動後のautostock testsは17 passed。旧自律起動と価格取得は未検証。必要なら退避前commitで専用worktreeを作り、READMEの旧パスで実行 |

退避先の report.py / plot.py は同じディレクトリの results.tsv を参照します。
各cloneで追跡外の旧 autostock/results.tsv が残っている場合は、内容を公開Gitへ追加せず、
_archive/market/autostock/results.tsv へローカルで移してから再生成します。
旧パスもルート .gitignore で除外し、移行前に誤って追跡しないようにします。
保存済み report.html と progress.png はそのまま保管します。
