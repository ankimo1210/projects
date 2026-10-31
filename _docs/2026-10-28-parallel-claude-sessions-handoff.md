# Claude Code の並行セッション運用の引き継ぎ（ChatGPT 向け、2026-10-28）

Claude Code（セッション名 win main2）が 2026-10-28 に書きました。ChatGPT に追加で調べてもらうための引き継ぎです。ChatGPT からは手元のファイルや端末が見えないので、判断に要る事実は本文に写しました。`_docs/` の一時メモです。

**お願いしたいこと：** §4 の提案に誤りや、もっと良いやり方がないかを見てください。§5 の未確認の点は、一次資料（Anthropic の Claude Code 公式ドキュメント、Windows Terminal と WSL の Microsoft のドキュメント）で確かめてください。Claude Code は更新が速いので、記憶ではなく、版 2.1.312 と §3 のヘルプの抜粋を基準にしてください。確かめた事実と推測は分けて書き、ユーザーへの返答は日本語でお願いします。

## 1. 困りごと

- PC を再起動するたびに Claude Code を複数起動して、`/rename` でセッション名を付け直している。これを自動にしたい。
- あわせて、多くの作業を同時に並行して進める人向けの、便利なオプション・設定・運用のやり方を知りたい。

## 2. 環境（2026-10-28 に確認）

- Windows ＋ WSL2 の Ubuntu（kernel 6.18.33.2-microsoft-standard-WSL2）。Claude Code は WSL の中で動かしている。
- Windows Terminal が入っている。WSL から `wt.exe`（`/mnt/c/Users/Kazumasa/AppData/Local/Microsoft/WindowsApps/wt.exe`）を呼べる。WSL の配布名は `Ubuntu`。
- tmux は `/usr/bin/tmux` にある（設定ファイルは無い）。
- Claude Code は 2.1.312。`/home/kazumasa/.local/bin/claude` にあり、`bash -lc` からも PATH で見える。
- ユーザー設定（`~/.claude/settings.json`）の主な値：
  - `model = opus`、`effortLevel = xhigh`、`permissions.defaultMode = auto`
  - `inputNeededNotifEnabled = true`、`agentPushNotifEnabled = true`、`remoteControlAtStartup = true`
  - `statusLine` は自作のスクリプト。`hooks` は空。`autoCompactWindow = 500000`
- 作業の中心は1つの git リポジトリ `/home/kazumasa/projects`（公開、多数のプロジェクトを含む）。別リポジトリもある（例 `/home/kazumasa/re_invest_os`）。
- いま動いているセッション（`claude agents --json`）は4つ。すべて interactive で、作業ディレクトリはすべて `/home/kazumasa/projects`（main ブランチ）。名前は `win main1`、`win main2`、`win main3`、`projects-e6`。
- 既存の git worktree は `/home/kazumasa/worktrees/` の下に4つある。

## 3. `claude --help` で確かめた事実（2.1.312）

- `-n, --name <name>`：セッションの表示名を付ける。プロンプト欄、`/resume` の選択画面、端末のタイトルに出る。
- `-r, --resume [value]`：セッション ID か名前で再開する。値を省くと選択画面が開く（検索語を付けられる）。
- `-c, --continue`：今のディレクトリの最新の会話を続ける。`--fork-session`：再開するとき新しいセッション ID にする。
- `--bg, --background`：セッションを裏で起動してすぐ戻る。表示される id を `claude attach`・`logs`・`stop`・`rm` に渡す。`claude agents` が一覧を出す。`--resume <session-id>` と一緒に使うと、同じ ID のまま裏で続ける（そのセッションがすでに動いていれば、コピーを作ってそう言う）。
- `claude agents`：background agents を管理する画面。`--json` は interactive と background の両方の一覧を JSON で出す。`--all` は終わったものも含める。`--model`・`--effort`・`--permission-mode` は、この画面から出すセッションの既定値。
- `claude attach <id|name>`：background セッションをこの端末で開く。名前の一部でもよい。
- `claude logs <id|name>`：background セッションの最近の出力を表示する。
- `claude stop|kill <id>`：background セッションを止める。会話は残り、`claude attach <id>` で開き直せる。止まったあとは `claude --resume` も使える。
- `claude rm <id>`：background セッションを消す。「安全なら」その worktree も消す。
- `claude respawn [--all]`：background セッションを、今の版の Claude Code で再起動する。
- `-w, --worktree [name]`：このセッション用に git worktree を作る。`--tmux`：worktree 用の tmux セッションを作る（`--worktree` が必要）。iTerm2 があればそのペインを使い、`--tmux=classic` で従来の tmux になる。
- そのほか：`--remote-control [name]`、`--model`、`--effort`、`--permission-mode`。セッションの中では `/rename` で名前を変えられる。

## 4. Claude が出した提案（どれもまだ実行していない）

### 4.1 起動スクリプト `cc-up`

置き場所の案は `/home/kazumasa/.local/bin/cc-up`。名前と作業ディレクトリの組ごとに Windows Terminal のタブを開き、`claude -n <名前>`（新規）か `claude -r <名前>`（前回の続き）を実行する。ファイルはまだ作っていない（実行するとウィンドウが開くため）。

```bash
#!/usr/bin/env bash
# Open one Windows Terminal tab per named Claude session.
set -euo pipefail
sessions=(                       # 名前:作業ディレクトリ
  "market:/home/kazumasa/projects/market-research"
  "johnhull:/home/kazumasa/projects/johnhull"
  "reos:/home/kazumasa/re_invest_os"
)
flag=-n; [[ ${1:-} == resume ]] && flag=-r   # 引数 resume で前回の続き
args=()
for s in "${sessions[@]}"; do
  name=${s%%:*} dir=${s#*:}
  args+=(new-tab --title "$name" wsl.exe -d Ubuntu --cd "$dir" -- bash -lc "claude $flag '$name'" ";")
done
unset 'args[${#args[@]}-1]'
wt.exe -w new "${args[@]}"
```

### 4.2 ログイン時の自動起動

Windows のスタートアップフォルダ（`shell:startup`）に、`wsl.exe -d Ubuntu -- /home/kazumasa/.local/bin/cc-up resume` を実行するショートカットを置く。

### 4.3 タブを並べず、background セッションでまとめて管理する

`claude --bg -n <名前> "最初の指示"` で裏で起動し、`claude agents` の一覧で状態を見て、`claude attach` で中に入る。再起動のあとは `claude --bg --resume <session-id>` で裏のまま再開する。cc-up をこの形に書き換えればタブは要らない。

### 4.4 セッションごとに worktree を分ける

いまの4セッションは、同じチェックアウト（main）で index と HEAD を共有している。あるセッションの `git add`・commit・checkout が、他のセッションの作業に混ざる。`claude -w <名前>` でセッションごとに worktree を作る。

注意点：worktree を消すと、git が無視しているファイルも一緒に消える。ユーザーは 2026-10-17 に、`git worktree remove` で約115GiB のデータを失った。`claude rm` も worktree を消すので、消す前に `git status --ignored` と `du` で中身を確認する。

### 4.5 モデルと effort を作業の重さで分ける

並行するセッションは、同じアカウントの利用枠（5時間の枠と週の枠）を使う。既定が `opus` と `xhigh` なので、単純な作業のセッションは `--model sonnet --effort medium` などで起動して枠をもたせる。

### 4.6 運用のコツ

- 1セッションに1タスク・1ブランチを割り当て、同じファイルを2つのセッションで触らない。
- セッション名はタスク名にする（`win main1` より `dsinc-review`）。`attach` や `-r` で名前を指定して呼べる。
- 長い作業は、最初に完了条件を書いて渡す。そうすると放っておける。
- 入力待ちの通知、プッシュ通知、Remote Control の自動起動、ステータスラインは、すでに有効（§2）。

## 5. 確かめてほしいこと

1. `claude -r <名前>`：同じ名前のセッションが複数あるとき、何が開くか（最新か、選択画面か）。名前は一意である必要があるか。`-r` で再開したとき名前は引き継がれるか。
2. `claude --bg --resume` に、session-id ではなく名前を渡せるか。
3. Windows を再起動（WSL が停止）したあと、background セッションはどう見えるか。`claude agents --all` に残るか、`claude respawn` や `--bg --resume` で戻せるか。
4. WSL から `wt.exe` を呼ぶときの引数：
   - `";"` を独立した引数で渡して、タブを区切れるか。
   - `wsl.exe -d Ubuntu --cd <Linux のパス> -- bash -lc "..."` の書き方で正しいか。
   - `-w new` の意味。Claude が端末のタイトルを書き換えるので、`--suppressApplicationTitle` が要るかどうか。
5. ログイン時の自動起動は、スタートアップフォルダ、タスク スケジューラ、Windows Terminal の `startupActions` や「ログイン時に起動」の設定のうち、どれが確実か。WSL の起動を待つ必要があるか。
6. `claude -w`：worktree がどこに作られ、ブランチ名がどうなるか。`claude rm` が「安全」と判断する基準。無視されたファイルを失わない後片付けの手順。
7. `--tmux`（`--tmux=classic`）は、WSL の Windows Terminal の中でどう動くか。
8. 並行セッションと利用枠：全セッションで同じ枠を共有するか。並行作業で枠を節約する公式の推奨はあるか。
9. ほかに、多くのセッションを並行して回す人向けの定番があるか。例：tmux でのセッション管理、`claude agents` の画面からのセッションの起動、hooks でセッションの状態を Windows に通知する方法。

## 6. 前提と制約

- ユーザーの決まり：破壊的な git 操作や、取り消せない操作には承認が要る。外部への送信や公開にも承認が要る。
- worktree を消す提案をするときは、§4.4 の確認手順を必ず添える。
- コマンドを提案するときは、それが効いたかを確かめる方法も添える。ChatGPT の返答はユーザーが Claude Code のセッションに戻し、Claude Code が実機で確かめる予定。
