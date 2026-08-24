# macOS のワークステーション設定

この Mac（Apple Silicon / macOS 26）固有の設定。親ディレクトリの
`agentic-setup/README.md` と同じくバックアップであって、動作中の設定
そのものではない。

**親ディレクトリの `claude/` `codex/` は WSL 機のもの。** この Mac の
エージェント CLI 設定は同名ファイルでも中身が違うので、上書きせずここに
分けてある。

| パス | 実体の位置 | 備考 |
| --- | --- | --- |
| `claude/settings.json` | `~/.claude/settings.json` | statusLine のパスが Mac 用。`swift-lsp` プラグイン、`modelSettings` の opus-5 xhigh を含む |
| `codex/config.toml` | `~/.codex/config.toml` | ollama プロファイル、marketplaces、computer-use の notify を含み WSL 版とはほぼ別物 |
| `karabiner/*.json` | `~/.config/karabiner/assets/complex_modifications/` | 下記「Karabiner-Elements」参照 |

`claude/statusline-command.sh` はマシン固有のパスを含まないため親ディレクトリの
ものをそのまま使える。`settings.json` の `statusLine.command` だけが
`/Users/ankimo1210/...` を直書きしているので、復元時はそこを書き換える。

## Karabiner-Elements：アプリ別の修飾キー

### 何をしているか

Caps Lock の役割を**フォアグラウンドのアプリによって切り替える**。

| アプリ | Caps Lock | 狙い |
| --- | --- | --- |
| Terminal.app | `left_control` | `⌃C` `⌃R` `⌃A` `⌃E` `⌃D` を左小指で押す |
| Citrix Viewer / Workspace | `left_control` | リモート Windows 側の `Ctrl+C` / `Ctrl+V` |
| それ以外すべて | `right_command` | macOS のコピペを左小指で押す（導入前と同じ） |

ルールは `karabiner/capslock-control-in-terminal-citrix.json`。
2件を上から順に評価し、条件付きの1件目が外れたら無条件の2件目が拾う。

### なぜ標準設定ではできないのか

macOS の システム設定 → キーボード → 修飾キー は**キーボード単位**であって
アプリ単位ではない。「ターミナルのときだけ」を実現する標準手段は存在しない。

Terminal.app 側での対処も不可能。設定 → プロファイル → キーボードのキー割り当ては
カーソル・ファンクション・Home/End など特殊キーしか対象にできず、英字キーを
選べない。加えて `⌘C` はメニュー（編集 → コピー）が先に横取りする。

そもそも端末に「Command」という修飾キーは存在しない。`⌃C` は修飾キーの
組み合わせではなく**1バイトの文字 `0x03`**（`⌃D` は `0x04`、`⌃R` は `0x12`）で、
端末はこれをバイト列としてプロセスへ流す。Command にはバイト表現がないため、
vim・tmux・less・readline は Command を永久に受け取れない。
エミュレータ側で1個ずつ翻訳するしかない。

### Karabiner は System Settings の修飾キー設定を無効化する

**2026-08-24 に実測で確認**（Terminal で Caps Lock+C → `^C` が出た）。

Karabiner は物理キーボードを seize し、仮想キーボード
（`vendor=1452 / product=591`）として再送出する。
`com.apple.keyboard.modifiermapping.<product>-<vendor>-<n>` はデバイス別に
記録されているので、物理デバイスのエントリが一致しなくなり素通りする。

**System Settings 側の `Caps Lock → 右⌘`（内蔵キーボード = `0-0-0`）は
意図的に残してある。** Karabiner を止めた・消したときに導入前の挙動へ
戻るフォールバックとして働く。消すと Caps Lock が素の Caps Lock に戻って
しまう。設定が2箇所に分かれる代わりに、安全に降りられる。

### 未移行：HHKB Studio2

System Settings に `⌃⇄⌘` を左右とも入れ替える設定が残っている
（`1278-22-0`、PFU 0x04FE）。上記の理由で **Karabiner 動作中は効かない**。
次に接続したときに `device_if` 条件付きルールとして Karabiner 側へ移すこと。

## 設定の在り処

| パス | 役割 |
| --- | --- |
| `~/.config/karabiner/karabiner.json` | 実際に読まれる設定。ここでルールを有効化する |
| `~/.config/karabiner/assets/complex_modifications/*.json` | ルール定義。UI の Complex Modifications 一覧に出る |
| `~/.local/share/karabiner/log/` | `console_user_server.log` / `core_service.log` |
| `/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli` | CLI |

## 復元手順

```bash
brew install --cask karabiner-elements   # .pkg なので sudo パスワードを聞かれる

mkdir -p ~/.config/karabiner/assets/complex_modifications
cp macos/karabiner/*.json ~/.config/karabiner/assets/complex_modifications/
```

Karabiner-Elements を起動し、**2段階**の許可を通す。1回で終わらない。

1. **バックグラウンドサービス / 入力監視** — アプリの案内に従う
2. **ドライバ機能拡張** — システム設定 → 一般 → ログイン項目と機能拡張 →
   **一番下までスクロールして「機能拡張」セクションの「ドライバ機能拡張」の ⓘ** →
   `Karabiner-DriverKit-VirtualHIDDevice` を ON

2 が分かりにくい。上部の起動項目リストにも Karabiner が並ぶので、そちらを
触って済んだつもりになりやすいが、別物。トグルが出ない・押しても戻る場合は
承認ダイアログを出し直す。

```bash
sudo '/Applications/.Karabiner-VirtualHIDDevice-Manager.app/Contents/MacOS/Karabiner-VirtualHIDDevice-Manager' forceActivate
```

許可が済んだら `~/.config/karabiner/karabiner.json` の選択中プロファイルへ
`complex_modifications.rules` としてルールを流し込む。GUI で
Complex Modifications → Add rule から有効化してもよい。

## 状態の確認コマンド

```bash
# ドライバ拡張が承認されたか（enabled 列に * が要る）
systemextensionsctl list

# 仮想キーボードが起きているか（空なら未稼働）
hidutil list | grep -i karabiner

# 現在の System Settings 側の修飾キー設定（デバイス別）
defaults read -g | grep -A20 modifiermapping

# キーボードの物理配列。40 = ANSI
plutil -p /Library/Preferences/com.apple.keyboardtype.plist
```

`defaults read -g` の値は `0x700000000` を引くと HID usage になる。
`0x39` Caps Lock / `0xE0` 左⌃ / `0xE3` 左⌘ / `0xE4` 右⌃ / `0xE7` 右⌘。

## この Mac の実測値

| 項目 | 値 |
| --- | --- |
| キーボード配列 | 全て ANSI（`keyboardtype.plist` が `40`）。入力ソースは ABC |
| 内蔵キーボードの HID ID | `vendor=0x0 / product=0x0` → 設定キーは `0-0-0` |
| Karabiner 仮想キーボード | `vendor=1452 / product=591` |
| Citrix（実際にキーが飛ぶ側） | `com.citrix.receiver.icaviewer.mac` — 実体は `/Library/Application Support/Citrix Receiver/Citrix Viewer.app` |
| Citrix（ランチャー） | `com.citrix.receiver.nomas` — `/Applications/Citrix Workspace.app` |

Citrix の bundle id が2つある点に注意。`/Applications` を見ただけだと
ランチャーしか見つからず、リモート画面側を取りこぼす。

## 元に戻す

Karabiner-Elements を終了するだけで導入前の挙動に戻る（System Settings 側の
設定が復活するため）。完全に消す場合は Karabiner の設定画面にある Uninstall を
使う。`brew uninstall` だけではドライバ機能拡張が残る。
