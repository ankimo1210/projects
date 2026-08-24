# agentic-setup

ローカルの AI エージェント CLI（Claude Code / Codex CLI）の設定を、この
リポジトリに退避したもの。マシン再構築時の復元元であり、設定変更の履歴を
git で追うための場所。

**これはバックアップであって、動作中の設定そのものではない。**
実際に使われているのは `~/.claude/` と `~/.codex/`。ここを編集しても
何も起きない。変更したら下の「同期」に従って手で反映する。

## 中身

| パス | 実体の位置 | 役割 |
|---|---|---|
| `AGENTS.md` | 下記「シンボリックリンクの連鎖」参照 | 両ツール共通のグローバル指示 |
| `claude/settings.json` | `~/.claude/settings.json` | 権限・プラグイン・statusLine・effort 等 |
| `claude/keybindings.json` | `~/.claude/keybindings.json` | キーバインド |
| `claude/statusline-command.sh` | `~/.claude/statusline-command.sh` | ステータスライン生成スクリプト |
| `claude/project-settings.local.json` | `~/projects/.claude/settings.local.json` | このワークスペース固有の permission allow 蓄積（**下記の注意**） |
| `claude/gitignore` | `~/.claude/.gitignore` | ホワイトリスト方式の除外設定（**下記の注意**） |
| `claude/skills/repo-survey/` | `~/.claude/skills/repo-survey/` | 自作スキル：リポジトリ概観 |
| `claude/skills/hull-derivatives/` | `~/.claude/skills/hull-derivatives/` | 自作スキル：デリバティブ参照（自分で書いた要約ノート） |
| `codex/config.toml` | `~/.codex/config.toml` | モデル・reasoning effort・trust level・MCP |
| `codex/gitignore` | `~/.codex/.gitignore` | 同上 |

### 注意：`gitignore` のファイル名

`claude/gitignore` と `codex/gitignore` は、実体では `.gitignore` という名前。
**ここでドットを外しているのは意図的**で、`.gitignore` のまま置くと中身の
`*`（全部無視）がこのリポジトリで発動して、同じディレクトリのファイルが
まるごと追跡対象から外れてしまう。復元時にドットを付け直すこと。

### 注意：`project-settings.local.json` のファイル名

実体は `~/projects/.claude/settings.local.json`。Claude Code の規約では
`*.local.json` は「マシンローカルの個人上書き」であり、このリポジトリの
ルート `.gitignore` でも意図的に除外されている。

ただし中身は許可ドメインなどの**積み上げた設定**で、失うと許可ダイアログを
一から踏み直すことになるため、バックアップとしてここに置く。`.claude/` 配下
ではなく `agentic-setup/claude/` に、頭に `project-` を付けた別名で置くこと
で、ルートの除外ルール（`.claude/settings.local.json`）に一致させずに追跡
している。**実体の除外設定はそのまま**で、二重管理になっている点に注意。

## シンボリックリンクの連鎖

グローバル指示は実体が1つで、両ツールがそれを共有している。

```
~/.claude/CLAUDE.md  ->  ../.codex/AGENTS.md
~/.codex/AGENTS.md   ->  /mnt/c/Users/Kazumasa/.codex/AGENTS.md   <- 実体（Windows 側）
```

WSL 側からも Windows 側からも同じ内容が見えるようにするための構成。
`git` はシンボリックリンクをリンクのまま記録するため、`~/.claude` や
`~/.codex` のローカル git 履歴には**中身が入っていない**。この
リポジトリの `AGENTS.md` は `cp -L` で実体を解決してコピーしたもので、
実質ここが唯一の内容バックアップになっている。

## 意図的に含めていないもの

秘密情報とローカル状態は入れない。

- `~/.claude/.credentials.json`、`~/.codex/auth.json` — 認証トークン
- `~/.claude/history.jsonl`、`~/.codex/history.jsonl` — 入力履歴
- `~/.claude/projects/` — 会話トランスクリプトと auto memory
- `~/.codex/logs_2.sqlite` — 実行ログ（70MB超）
- `~/.claude/plugins/` — マーケットプレースのクローン。再取得可能で、
  どれを有効にしているかは `claude/settings.json` の `enabledPlugins` と
  `extraKnownMarketplaces` に記録されている
- `session-env/`、`shell-snapshots/`、`tasks/`、`cache/` 等のランタイム状態

## 復元

```bash
cd ~/projects/agentic-setup

# Claude Code
mkdir -p ~/.claude/skills
cp claude/settings.json          ~/.claude/settings.json
cp claude/keybindings.json       ~/.claude/keybindings.json
cp claude/statusline-command.sh  ~/.claude/statusline-command.sh
cp claude/gitignore              ~/.claude/.gitignore
cp -r claude/skills/*            ~/.claude/skills/

# このワークスペース固有の permission（リポジトリのルートで実行）
cp claude/project-settings.local.json ~/projects/.claude/settings.local.json

# Codex CLI
mkdir -p ~/.codex
cp codex/config.toml             ~/.codex/config.toml
cp codex/gitignore               ~/.codex/.gitignore

# 共通のグローバル指示（WSL + Windows 併用の場合）
cp AGENTS.md /mnt/c/Users/Kazumasa/.codex/AGENTS.md
ln -sf /mnt/c/Users/Kazumasa/.codex/AGENTS.md ~/.codex/AGENTS.md
ln -sf ../.codex/AGENTS.md                    ~/.claude/CLAUDE.md

# 単一 OS のマシンなら、リンクを張らず実体を直接置く
# cp AGENTS.md ~/.codex/AGENTS.md && ln -sf ../.codex/AGENTS.md ~/.claude/CLAUDE.md
```

復元後に手で直す必要があるもの:

- `claude/settings.json` の `statusLine.command` は
  `/home/kazumasa/.claude/statusline-command.sh` を**絶対パスで直書き**して
  いる。ユーザー名やホームが違うマシンでは書き換える。
- `codex/config.toml` の `[projects."..."]` の `trust_level` も絶対パス。
- 認証は復元しない。`claude` と `codex` を起動して各自ログインし直す。

## 同期

`~/.claude` と `~/.codex` はそれぞれ**リモートなしのローカル git リポジトリ**
にもなっていて、ホワイトリスト方式の `.gitignore` で設定ファイルだけを
追跡している。日々の変更はそちらでコミットし、区切りのいいところで
このディレクトリへコピーして `~/projects` 側にコミットする。

```bash
# 差分の確認（コピーする前に）
diff -u ~/projects/agentic-setup/claude/settings.json ~/.claude/settings.json
diff -u ~/projects/agentic-setup/codex/config.toml    ~/.codex/config.toml
diff -u ~/projects/agentic-setup/AGENTS.md            ~/.claude/CLAUDE.md
diff -u ~/projects/agentic-setup/claude/project-settings.local.json \
        ~/projects/.claude/settings.local.json
```
