# 非公開APIキーをDriveで共有する

更新: 2026-11-01

公開リポジトリには汎用コードと空のサンプルだけを置く。実キーはGoogle Driveの
`Repo/secrets/` に保存し、各端末のレポ外コピーから起動するプロセスへ渡す。
Drive上では通常のテキストファイルであり、今回確認したRepoフォルダの共有先は所有者だけ。

| サービス | Drive内のファイル | 渡す環境変数 |
|---|---|---|
| OpenAI | `secrets/openai.env` | `OPENAI_API_KEY` |
| Anthropic | `secrets/anthropic.env` | `ANTHROPIC_API_KEY` |
| 不動産情報ライブラリ | `secrets/reinfolib.env` | `REINFOLIB_API_KEY` |

Windowsの保存先は `G:\マイドライブ\Repo`。
キーはチャット、コマンド引数、公開の設定ファイルへ貼らない。
空欄の登録は既存値を保持する。各ファイルには上表の環境変数1個だけを保存する。
`secrets/retired/` は退避済みの旧キーで、起動には使用しない。

## Windows・WSLで使う

WindowsのPowerShellには `%USERPROFILE%\.local\bin\api-keys.ps1` と
`api-key-setup.ps1` を設置済み。後者を `api-key-setup` で呼ぶと
マスク付き入力画面を開き、Driveへ保存する。
PowerShell 7と既存のWindows版Pythonを使用する。通常のCLI実行例:

```text
api-keys status
api-keys sync
api-keys run --provider openai -- <起動したいコマンド>
api-keys run --provider anthropic -- <起動したいコマンド>
api-keys run --provider reinfolib -- <起動したいコマンド>
```

複数必要なら `--provider openai --provider anthropic` と列挙する。
指定したキーだけを子プロセスへ渡し、シェル全体やOSの環境変数には常設しない。
実行コマンド自身のログ出力は、そのコマンド側で管理する。

Windows設定は `%USERPROFILE%\.config\repo-secrets\config.json`、
ローカルコピーと起動補助は `%USERPROFILE%\.local\share\repo-secrets\` にある。
設定JSONにはパスだけを保存する。
cmd.exe向けに `api-keys.cmd` もあるが、UNC上のリポジトリからはPowerShell版かWSLを使う。

WSLには `~/.local/bin/api-keys` を設置済み。同じコマンド名で利用できる。
起動前にWindows側のDrive同期元を読み、その後Linuxプロセスへキーを渡す。
GドライブをWSLへ直接マウントする必要はない。
WSL用設定は `~/.config/repo-secrets/wsl.json` で、Windows側コピーを
`/mnt/c/Users/Kazumasa/.local/share/repo-secrets` 経由で読む。

Drive未接続時は保存済みのローカルコピーを使う。
キー未登録や不正な設定の場合は、対象コマンドを起動せず値なしのエラーにする。
Driveに接続できているのに対象ファイルがない場合は、古いコピーを無効にして起動を拒否する。
旧キーの使用禁止記録はDriveと端末の両方から読み、別端末の記録も保持する。
Driveを編集した直後は、Driveデスクトップアプリの同期完了後に起動する。

## Macの初回設定

この手順は用意済みだが実Macでは未検証。Driveデスクトップアプリで同じRepoを
同期し、Finderで確認した実在する `Repo/secrets` のパスを使う。
Googleアカウント名や「マイドライブ／My Drive」の表記を決め打ちしない。

リポジトリのルートで実行する:

```bash
read -r -p 'Repo/secrets の実パス: ' drive_source
python3 agentic-setup/api_keys.py init \
  --source "$drive_source" --cache "$HOME/.local/share/repo-secrets"
mkdir -p "$HOME/.local/share/repo-secrets/tools" "$HOME/.local/bin"
cp agentic-setup/api_keys.py "$HOME/.local/share/repo-secrets/tools/api_keys.py"
cat > "$HOME/.local/bin/api-keys" <<'SH'
#!/bin/sh
exec python3 "$HOME/.local/share/repo-secrets/tools/api_keys.py" "$@"
SH
chmod 700 "$HOME/.local/bin/api-keys"
"$HOME/.local/bin/api-keys" status
```

Python 3.12以降を使う。上の入力例はbash向けなので、Macのzshからは先に
`bash` を起動して実行する。以後はWindowsと同じ `api-keys run` を使う。
`~/.local/bin` がPATHにない端末では `"$HOME/.local/bin/api-keys"` で指定する。
新しいキーを登録する場合は `api-keys set --provider openai` などを使い、
非表示入力に貼り付ける。公開リポジトリのパスを保存先に指定すると拒否する。

## 今回の状態と確認範囲

- OpenAI・Anthropic: ユーザー入力を保存し、Driveとローカルの一致を確認。
- 不動産情報ライブラリ: 公開ノートブックの直書きを環境変数へ変更。
  旧キーは非公開へ退避し、再登録を拒否する。新キーは未登録。
  旧キーのサービス側停止・新規発行は未実施。
- 実APIへのリクエスト・課金を伴う検証は行っていない。
- 通常のcommit/pushで公開側を反映しても、過去のGit履歴や公開済みコピーは除去されない。
- 実ポジション・残高・取引履歴の14ファイルは移管済み。
  [資産データの保存先と端末設定](../../portfolio-analyzer/docs/private-data.md)を参照。
  住宅比較は運用利回りを残高と誤認していたため、変更していない。

秘密検査は `agentic-setup/check_api_secrets.py` とpre-commitで行う。
このWSLチェックアウトにはpre-commit 4.7.0のフックを設置済み。
既知のキー形式と実envファイルを検査する補助であり、すべての機密情報を検出するものではない。
公開済みのキーはコードから除去するだけでは失効しない。
