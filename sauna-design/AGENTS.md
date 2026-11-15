# Sauna Design — project rules

- v3〜v6の主実装者はユーザーが指定した Fable / high。v7は同じ会話で公式資料を照合後、利用上限で停止したため親が製品反映を引き継ぐ。v8はユーザーの継続指定に合わせ同じFable/highが主実装を再開する。既存の簡易Web描画への追記を前提にしない。
- 作成・編集するソースはこのプロジェクト内に限定する。
- バイナリ、参考画像、描画結果、セッションバックアップは共有側の canonical data root（`/home/kazumasa/projects/_data/sauna-design/`）内。worktree内に生成物を作らない。
- `reference-v2/` は読み取り専用の参考資料。旧版のモデルや画像を上書き・削除しない。
- 制作中v8の生成データは canonical data root の `fable-v8/` の1ルートに集約する。受入済みv3・v4・v5・v6・v7と参考画像は上書き・削除しない。
- 内装画像の貼り付けや画像ビューアを、実3Dやレンダリング成果として扱わない。
- 座標を持つモデル、再生成用ソース、同じモデルから描画した画像を納品する。
- Fableセッションは保存必須。`--no-session-persistence`、session削除、purge、cleanupは禁止。
- 未確認の安全性、法適合、席数、費用成立を確定扱いにしない。
- この専用worktreeはすでに隔離済み。新しいEnterWorktree/ExitWorktreeは不要。ソース編集はここで通常のWrite/Editを使い、隔離ガード拒否をBashで回避しない。
- ブラウザ操作と画面確認は親が mcp__cua_repl で行う。子はPlaywright/headless Chrome等を実行しない。
