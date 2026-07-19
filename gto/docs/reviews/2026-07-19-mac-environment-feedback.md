# Mac / iOS Development Environment Feedback

Date: 2026-07-19

Status: **Pending — Macで記入後、H0判定を更新する**

Environment contract: [`../development-environments.md`](../development-environments.md)

> Secret、credential、token、証明書、provisioning profileの内容は貼らない。
> Apple accountやTeamの確認は可否だけを記録する。

## 1. Machine

| Item | Result |
|---|---|
| Mac model | Pending |
| CPU / architecture | Pending |
| RAM | Pending |
| macOS | Pending |
| Free disk | Pending |
| Physical iPhone / iOS | Pending |

## 2. Toolchain output

MacのTerminalで実行し、必要な範囲だけ結果を貼る。

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
Pending
```

## 3. Manual checks

- [ ] Xcodeを起動でき、license/初期component installが完了している
- [ ] iOS Simulatorを1台以上起動できる
- [ ] Apple Developer Programにアクセスできる
- [ ] App Store Connectにアクセスできる
- [ ] Xcodeがsigning teamを認識する（識別子は記載不要）
- [ ] 物理iPhoneを接続またはwireless pairingでき、Developer Modeを利用できる
- [ ] Gitでこのbranchをpullし、同じcommit SHAを確認できる
- [ ] R2/CDNの一般的なHTTPS downloadを阻害するnetwork policyがない

## 4. Findings

### Blockers

- Pending

### Warnings

- Pending

### Version decisions for P1

- Pending — macOS / Xcode / iOS / Node.js / pnpm / Expo SDKの固定候補

## 5. H0 verdict

- [ ] **GO** — P1のExpo scaffoldとiOS native検証を開始できる
- [ ] **CONDITIONAL GO** — 下記条件を解消しながら開始できる
- [ ] **NO-GO** — P1開始前にblocker解消が必要

Rationale / required actions:

- Pending
