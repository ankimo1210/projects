# Fable / high セッション

- 実際の会話ID: `68de4adc-db0a-4644-a3a5-9be5012127a3`
- バックグラウンドID: `68de4adc`
- 名前: `sauna-3d-fable-high`
- モデル指定: `fable`、effort: `high`
- 実メッセージで確認したモデル: `claude-fable-5-2`
- 会話原本の存在確認: `True`
- バックアップ: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\sauna-design\sessions\68de4adc-db0a-4644-a3a5-9be5012127a3.jsonl`
- 制作ソース: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\sauna-design`
- 削除・purge・cleanup禁止。進行中のバックアップは作業中スナップショット。

WSLのこのプロジェクト内から再開:

```bash
claude attach 68de4adc
```

背景実行で同じ会話を継続:

```bash
claude --bg --resume 68de4adc-db0a-4644-a3a5-9be5012127a3
```

背景継続ではモデル等の追加フラグを付けない。保存済みの fable / high 設定を使う。
このCLIでは背景継続にフラグを足すと別コピーになるため、元の会話を継続する時は上記を使う。

実行中に同じIDを重複起動しない。状態確認と最新会話のバックアップ:

```bash
python3 scripts/monitor_fable.py
```

ネイティブの背景実行は会話IDを管理するため、初期起動で要求したIDとは異なる。
原本を保持したまま、実IDで管理・再開する。
