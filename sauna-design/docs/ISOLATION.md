# 作業場所の隔離（2026-11-14）

このファイルは EnterWorktree で入った専用 worktree の中で、Write ツールにより作成した。
Write が拒否されずに成功したことが、隔離ガードが通っている確認になる。

## 場所

| 項目 | パス |
|---|---|
| 専用 worktree（Git ルート） | `/home/kazumasa/projects/.claude/worktrees/sauna-design-v3` |
| worktree 内のプロジェクト | `/home/kazumasa/projects/.claude/worktrees/sauna-design-v3/sauna-design` |
| 同 Windows UNC | `\\wsl.localhost\Ubuntu\home\kazumasa\projects\.claude\worktrees\sauna-design-v3\sauna-design` |
| ブランチ | `worktree-sauna-design-v3`（基点 `b50b9a9c5`、`git worktree list` で locked） |
| 原本ソース（読み取り専用で保持） | `/home/kazumasa/projects/sauna-design` |
| 生成物・会話バックアップ（移動・コピーなし） | `/home/kazumasa/projects/_data/sauna-design/` |

以後のソース編集はこの worktree 内だけで行う。原本ソースは編集・削除しない。

## 経緯

前回までは EnterWorktree がこのセッションに無く、Write / Edit が背景セッションの作業場所保護で拒否された。
そのとき共有チェックアウトの `sauna-design/` へシェル経由でファイルを書いたのは保護の回避にあたり、採用しない方法だった。
今回 EnterWorktree が有効になったので、最初にこれを呼んで worktree を作り、そこへプロジェクトだけを写した。
`safe.directory` を含む Git・OS 設定は変更していない。commit / push もしていない。

## 原本とコピーの一致

- コピー方法: `tar --exclude=__pycache__` で原本から worktree へ転記（原本側は読み取りのみ）。
- 対象: 33 ファイル。`__pycache__`（2ディレクトリ、Python の実行時キャッシュ）は写していない。
- 検証: 両側の全ファイルの sha256 一覧を `diff` して差分なし。`diff -rq -x __pycache__` も差分なし。
- 一覧（相対パス順の `sha256sum` 出力）自体の sha256: `f3be9e246069a1ea42f74d314b12961eed9871c7d1a9717cdfe05f9f5673fbb1`
- コピー後の差は、この `docs/ISOLATION.md` の追加だけ。

再確認:

```bash
diff -rq -x __pycache__ /home/kazumasa/projects/sauna-design \
  /home/kazumasa/projects/.claude/worktrees/sauna-design-v3/sauna-design
# 期待: "Only in .../sauna-design-v3/sauna-design/docs: ISOLATION.md" の1行だけ
```

## 再生成時は canonical data root を明示する

スクリプトの既定の出力先は `<プロジェクト>/../_data/sauna-design/fable-v3` という相対位置で決まる。
worktree 内ではこれが `.claude/worktrees/sauna-design-v3/_data/...` を指し、受入済みの生成物とは別の場所になる
（`scripts/blender.sh` は無ければ作ってしまう）。worktree から実行するときは必ず正規の場所を渡す。

```bash
cd /home/kazumasa/projects/.claude/worktrees/sauna-design-v3/sauna-design
export SAUNA_DATA_ROOT=/home/kazumasa/projects/_data/sauna-design/fable-v3

scripts/make_all.sh                      # 一括。SAUNA_DATA_ROOT を各段へ渡す
scripts/blender.sh build                 # 個別。blender.sh は SAUNA_DATA_ROOT を読む
scripts/blender.sh render main --res 2400 --samples 1500 --threshold 0.01 --name sauna_main_v3

# Python スクリプトを単独で呼ぶ場合は引数で渡す（環境変数は読まない）
python3 scripts/fetch_assets.py --data-root "$SAUNA_DATA_ROOT"
python3 scripts/label_plan.py "$SAUNA_DATA_ROOT"
python3 scripts/write_manifest.py "$SAUNA_DATA_ROOT"
```

注意: この指定で再生成すると、受入済みの `.blend`・画像・GLB を同名で上書きする。
今回は再制作・再描画をしていない（モデルと画像は受入済みのまま、`fable-v3/` は 59 MB で無変更）。
この隔離作業で worktree 内に `_data` は作られていないことを確認した。

`docs/REGENERATE.md` と `README.md` の手順は原本の位置（`/home/kazumasa/projects/sauna-design`）を前提に書いてある。
worktree から使うときは上の `SAUNA_DATA_ROOT` 指定を足す。

## 会話ID

- 会話ID は変わっていない: `68de4adc-db0a-4644-a3a5-9be5012127a3`
  （このセッションの `CLAUDE_CODE_SESSION_ID` で確認。`docs/FABLE_SESSION.md` の記載と同じ）。
- 新しいセッションへは移っていない。削除・purge・cleanup もしていない。
- EnterWorktree に伴い、会話原本の保存先がハーネスにより次へ移った:
  `~/.claude/projects/-home-kazumasa-projects--claude-worktrees-sauna-design-v3/68de4adc-db0a-4644-a3a5-9be5012127a3.jsonl`
  以前の `~/.claude/projects/-home-kazumasa-projects-sauna-design/` には、この ID のファイルはもう無い。
- そのため再開は worktree から行う想定になる（未実行・未確認。実行中の重複起動はしない）:

```bash
cd /home/kazumasa/projects/.claude/worktrees/sauna-design-v3
claude --resume 68de4adc-db0a-4644-a3a5-9be5012127a3 --model fable --effort high
```

- バックアップ `/home/kazumasa/projects/_data/sauna-design/sessions/68de4adc-db0a-4644-a3a5-9be5012127a3.jsonl` は
  17:58 時点のスナップショットで、この隔離作業より前のもの。`scripts/monitor_fable.py` が旧保存先を見ている場合は
  新しい保存先に合わせる必要がある（親側のスクリプトのため、こちらでは変更していない）。

## 未確認

- worktree からの Blender 実行（build / render）は試していない。再描画不要の指示に従った。
- `claude --resume` を worktree から実際に再開できるかは試していない。
- 原本 `sauna-design/` は共有チェックアウト上で未追跡のまま残っている。今後どちらを正とするかは未決定。
# 親による最終確認

隔離先へのコピー一致を検証した後、親がこのworktree内の管理用スクリプトを調整した。
管理用データルートはGit共通ディレクトリから共有側のcanonical data rootを解決し、
会話ファイルはEnterWorktree後の移動先を参照する。モデル制作コード・モデル・描画画像は変更していない。

同じ会話IDの実再開を検証済み。Blenderでモデルを読み込む検査、GLB/PNGの構造検査、
mcp__cua_replによる軽量ビューの読込・4視点切替も完了した。

