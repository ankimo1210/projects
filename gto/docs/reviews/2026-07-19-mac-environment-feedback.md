# Mac / iOS Development Environment Feedback

Date: 2026-07-19

Status: **Recorded — H0 verdict below**

Environment contract: [`../development-environments.md`](../development-environments.md)

> Secret、credential、token、証明書、provisioning profileの内容は貼らない。
> Apple accountやTeamの確認は可否だけを記録する。

## 1. Machine

| Item | Result |
|---|---|
| Mac model | MacBook Pro (Mac17,2) |
| CPU / architecture | Apple M5, arm64, 10コア (4 Super + 6 Efficiency) |
| RAM | 32 GB |
| macOS | 26.5.2 (Build 25F84) |
| Free disk | 142Gi / 460Gi (8% used) |
| Physical iPhone / iOS | Kazumasa's iPhone 16 Pro — ペアリング済みだが本チェック時点では未接続（Offline） |

## 2. Toolchain output

```bash
sw_vers
uname -m
system_profiler SPHardwareDataType
df -h /
xcodebuild -version
xcode-select -p
xcrun simctl list devices available
node --version
pnpm --version
git --version
git branch --show-current
git rev-parse HEAD
```

```text
$ sw_vers
ProductName:    macOS
ProductVersion: 26.5.2
BuildVersion:   25F84

$ uname -m
arm64

$ system_profiler SPHardwareDataType
Model Name: MacBook Pro
Model Identifier: Mac17,2
Chip: Apple M5
Total Number of Cores: 10 (4 Super and 6 Efficiency)
Memory: 32 GB

$ df -h /
Filesystem      Size  Used  Avail Capacity  Mounted on
/dev/disk3s1s1  460Gi  12Gi  142Gi  8%       /

$ xcodebuild -version
Xcode 26.6
Build version 17F113

$ xcode-select -p
/Applications/Xcode.app/Contents/Developer

$ xcrun simctl list devices available
== Devices ==
-- iOS 26.5 --
    iPhone 17 Pro (Shutdown)
    iPhone 17 Pro Max (Shutdown)
    iPhone 17e (Shutdown)
    iPhone Air (Shutdown)
    iPhone 17 (Shutdown)
    iPad Pro 13-inch (M5) (Shutdown)
    iPad Pro 11-inch (M5) (Shutdown)
    iPad mini (A17 Pro) (Shutdown)
    iPad Air 13-inch (M4) (Shutdown)
    iPad Air 11-inch (M4) (Shutdown)
    iPad (A16) (Shutdown)

$ node --version
v22.23.1

$ pnpm --version
command not found: pnpm
(corepack 0.34.6 is present and bundled with this Node; pnpm is not yet
activated via `corepack enable`)

$ git --version
git version 2.55.0

$ git branch --show-current
claude/gto-p0a-audit

$ git rev-parse HEAD
bcb04f0a4e0d9ab2b45136047972d602cbe9e8da
```

Additional check not in the original list — R2/CDN HTTPS reachability
(§3, no restrictive network policy expected to be found):

```text
$ curl -sS -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" https://www.cloudflare.com/cdn-cgi/trace
HTTP 200 in 0.028s

$ curl -sS -o /dev/null -w "HTTP %{http_code}\n" https://r2.cloudflarestorage.com
HTTP 301
```

## 3. Manual checks

- [x] Xcodeを起動でき、license/初期component installが完了している
      （`xcodebuild -version` / `-showsdks` がlicenseプロンプトなしで成功。
      iOS 26.5 / macOS 26.5 / tvOS / DriverKit SDKインストール済み）
- [x] iOS Simulatorを1台以上起動できる（11台 available: iPhone 17系5台 + iPad系6台）
- [ ] Apple Developer Programにアクセスできる — 未確認（Apple ID未サインイン、CLIでは判定不可、ブラウザ/Xcode GUIでの確認が必要）
- [ ] App Store Connectにアクセスできる — 未確認（同上）
- [ ] Xcodeがsigning teamを認識する（識別子は記載不要） — 未認識。
      `defaults read com.apple.dt.Xcode IDEProvisioningTeams` が
      「domain/default pair does not exist」を返す = Xcodeに
      Apple IDが未登録の状態
- [ ] 物理iPhoneを接続またはwireless pairingでき、Developer Modeを利用できる —
      `xcrun devicectl list devices` / `xctrace list devices` は
      ペアリング済み端末（iPhone 16 Pro）を認識しているが、本チェック時点では
      unavailable/Offline。実機接続してのDeveloper Mode確認は未実施
- [x] Gitでこのbranchをpullし、同じcommit SHAを確認できる —
      `claude/gto-p0a-audit` を worktree でcheckoutし
      `bcb04f0a4e0d9ab2b45136047972d602cbe9e8da` で一致確認
- [x] R2/CDNの一般的なHTTPS downloadを阻害するnetwork policyがない
      （Cloudflare / R2ドメインとも到達、ブロッキングプロキシなし）

## 4. Findings

### Blockers

- なし（ハード的な不足はゼロ）。ただし下記2点は「P1着手前に解消が必要」な軽微な項目:
  1. **pnpm未導入**。`corepack enable && corepack use pnpm@<固定バージョン>`
     （またはP1のproject scriptで指定される方法）で解消可能、1分程度の作業。
  2. **Xcodeに Apple ID / signing team 未登録**。Xcode → Settings → Accounts
     でApple IDを追加し、Developer Program / App Store Connectアクセスと
     teamの認識をあわせて確認する必要がある（credentialはこの文書に書かない）。

### Warnings

- 物理iPhone (16 Pro) は ペアリング済みだが本チェック時点で未接続。P1の実機検証
  （signing確認・パフォーマンス・offline動作検証）を行う際は接続 or wireless
  pairingの再アクティブ化が必要。
- 空きディスク142Giは現時点で問題ないが、Xcode CLTの追加コンポーネントや
  複数Simulatorランタイム、後続のblueprint bundle（目標 ≤300MB/端末側）を
  考慮しても妥当な余裕がある。P0b以降、home GPU側の生成物をこのMacに置く
  運用は想定していないため、当面は監視のみで良い。

### Version decisions for P1

- macOS: 26.5.2 (Apple Silicon) — 現行最新、固定候補として妥当
- Xcode: 26.6 (Build 17F113) — 現行最新、固定候補として妥当
- iOS Simulator runtime: 26.5 — 固定候補
- Node.js: v22.23.1 — Expo SDK要件（Node 18+）を満たす、固定候補
- pnpm: 未導入のため未固定。corepack経由でのバージョン固定をP1着手時に決定
- Expo SDK: 本チェックの対象外（P1で選定）

## 5. H0 verdict

- [x] **CONDITIONAL GO** — 下記条件を解消しながら開始できる
- [ ] GO
- [ ] NO-GO

Rationale / required actions:

- ハードウェア（Apple Silicon, 32GB RAM, 142GB空き）、Xcode/CLT/SDK、
  Simulator、Node.js、git、branch/SHA一致、R2/CDN疎通は全て問題なし。
  P1のExpo scaffoldとfixtureベースの開発は今すぐ開始できる。
- P1完了までに解消が必要な残タスク（いずれも軽微、所要時間は分〜数十分）:
  1. `corepack enable` でpnpmを有効化しバージョンを固定する。
  2. Xcodeに Apple ID を追加し、signing team / Developer Program /
     App Store Connect アクセスを確認する（実機ビルド・TestFlight配布の
     前提条件。P1のScaffold自体はSimulatorのみでも進行可能なため、
     この項目はP1の途中〜完了までに解消すればよく、着手のblockerではない）。
  3. 実機テストのタイミングでiPhone 16 Proを接続し、Developer Modeと
     Wireless pairingを確認する。
- 上記いずれもH0を「NO-GO」にする性質の問題ではなく、環境そのものは
  iOS開発に対応済みと判断する。
