# Fable / high セッション

- 実際の会話ID: `68de4adc-db0a-4644-a3a5-9be5012127a3`
- 元バックグラウンドID: `68de4adc`（停止済み。会話は専用worktreeで継続）
- 名前: `sauna-3d-fable-high`
- モデル指定: `fable`、effort: `high`
- 実メッセージで確認したモデル: `claude-fable-5-2`
- 会話原本の存在確認: `True`
- バックアップ: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\sauna-design\sessions\68de4adc-db0a-4644-a3a5-9be5012127a3.jsonl`
- 制作ソース: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\.claude\worktrees\sauna-design-v3\sauna-design`
- 直近の実行状態: `completed` / `complete`（v10の新規配置/モデル2本/設計メモ、同一会話・正常終了。実モデルの修正/GPU描画/GLBと表示UIは親側）
- 削除・purge・cleanup禁止。進行中のバックアップは作業中スナップショット。

2026-11-15：GPU/Fable再開をユーザーが許可。同じUUIDで資料をReadしたがBashと一部Readに権限拒否があり、拒否された操作を再実行せず、Read/Write専用で許可済み資料/ソースからV9の独立生成ソースを保存した。原本とV9最終控え・上記標準バックアップはSHA一致。会話を新規作成/削除していない。[V9の実行・検証](V9_BUILDING_STUDY.md)。

WSLの専用worktree内の制作ソースから再開:

```bash
cd /home/kazumasa/projects/.claude/worktrees/sauna-design-v3/sauna-design
/home/kazumasa/.local/bin/claude --resume 68de4adc-db0a-4644-a3a5-9be5012127a3 --model fable --effort high
```

専用worktree: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\.claude\worktrees\sauna-design-v3`
元の背景タスクのcwdは共有側なので、今後は上記の専用worktreeから再開する。
背景実行の継続にモデル等のフラグを加えると別コピーになるCLI仕様にも注意する。
出力フォルダを参照するときもBashのcwdをworktree外へ移さず、絶対パスを指定する。

実行中に同じIDを重複起動しない。状態確認と最新会話のバックアップ:

```bash
python3 scripts/monitor_fable.py
```

EnterWorktreeに伴い会話原本は専用worktree用のClaudeプロジェクト保存先へ移動された。
会話IDは同じであり、最新の原本を外部データルートへバックアップしている。

2026-11-16：同じ会話をhighで再開し、V10比較版の新規4ソースを作成して正常終了。Read/Write/Editの許可内、今回permission denialsなし。親が実測レビューから修正・本番9点/GLB/表示を確認。原本と標準バックアップのSHA一致をdelivery_manifest/verification/session_preserved.jsonへ記録。V10のソース実行結果はsessions/v10-result.jsonにも保存し、monitorの完了判定に対応。[V10レビュー](V10_PARENT_REVIEW.md)。
