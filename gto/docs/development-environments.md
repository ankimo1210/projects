# Development Environments and Workstreams

Date: 2026-07-19
Status: **Active development contract**

GTO製品開発は、ハードウェア依存を混ぜないため次の2レーンに分ける。
ソルバー生成はWindows 11機、iOSネイティブ開発はMacで行い、両者は
バージョン付きpack契約と小さなgolden fixtureで接続する。

## 1. レーン定義

| レーン | 主環境 | 担当範囲 | 主な成果物 | 実行しないもの |
|---|---|---|---|---|
| **W: Solver / Content** | Windows 11ホスト + WSL2 Ubuntu + RTX 5080 | `crates/`, `src/gto/`, solver audit、pack生成、FastAPI | ベンチマークJSON、監査レポート、pack、manifest、golden fixture | Xcode、署名、TestFlight、iOS実機検証 |
| **M: App / Release** | Mac + Xcode + iPhone | `mobile/`, `packages/`, Expo/RN、IAP、TestFlight、App Store | iOSアプリ、TS reader、実機QA結果、リリース設定 | CUDAビルド、GPUコンテンツ生成 |

`packages/` の純粋なTypeScriptコードは両環境でテストできる。ただし、pack writerの
正本はWレーン、iOSネイティブ動作とリリース判定の正本はMレーンとする。

## 2. 必要環境

### Wレーン — Windows 11 / WSL2 / GPU

- Windows 11、WSL2、Ubuntu 22.04以降
- RTX 5080（Blackwell `sm_120`）と互換CUDA driver/toolkit
- Rust、Python 3.12、uv、Node.js、pnpm
- 長時間計算に必要なRAM、空きディスク、安定した電源
- リポジトリとcheckpointはWSLのLinux filesystemに置く。高負荷I/Oを
  `/mnt/c` 配下で行わない
- 15分を超えるsolver runは
  `_data/gto/checkpoints/` の世代付きsnapshotから復帰可能にする

### Mレーン — Mac / iOS

- 現行XcodeがサポートするmacOS（Apple Silicon推奨）
- XcodeとCommand Line Tools、利用可能なiOS Simulator
- Node.js、pnpm。Expo/EASはP1で固定するproject script経由を原則とする
- Apple Developer Program / App Store Connectへのアクセス
- 署名確認と性能・offline検証に使う物理iPhone
- Xcode、macOS、iOS、Node.js等の正確な対応版はP1開始時に固定する。
  それまでは実機の調査結果をMac feedbackに記録する

## 3. ソースと成果物の境界

| 搬送手段 | 含めるもの | 含めないもの |
|---|---|---|
| Git | コード、schema、小さなgolden fixture、manifest、監査/QAレポート | checkpoint、実pack、証明書、provisioning profile、token、実 `.env` |
| R2/CDN | SHA-256付きの大容量・versioned pack | source code、secret |
| 各マシンのlocal storage | build cache、checkpoint、署名情報、開発用secret | 共有すべき契約の唯一のコピー |

- 受け渡し時は両マシンで同一commit SHAをcheckoutする。
- Wレーンはpack schema version、SHA-256、`min_app_version`をmanifestに記録する。
- Mレーンは取得後のfingerprint検証、atomic install、破損時の再取得、offline読込を検証する。
- Rust writerとTS readerの最小golden fixtureはP0b/P1の契約タスクで
  `gto/fixtures/packs/` に作成する。実packをfixtureとしてcommitしない。
- R2へのpublishは明示承認を得たリリース操作とし、通常のテストではlocal fixtureを使う。

## 4. 所有境界と変更ルール

| 対象 | 主担当レーン | 共同ゲート |
|---|---|---|
| Rust solver / Python pipeline / pack writer | W | 数値品質、schema、golden fixture |
| `@gto/domain` / `@gto/packs` / `@gto/api-client` | M | Rust fixtureとのround-trip |
| Expo/RN、iOS native config、IAP、TestFlight | M | entitlement APIとmanifest契約 |
| FastAPI、entitlement verification、signed URL | W | Mのsandbox/実機flow |

pack schemaの破壊的変更はwriterとreaderを同じ変更単位で更新し、unknown majorを
fail-loudで拒否する。どちらか片方だけを先にreleaseしない。

## 5. 環境間handoff gates

| Gate | 完了条件 | 主環境 |
|---|---|---|
| **H0 Mac ready** | Mac feedbackを記録し、Xcode/Simulator/署名/実機のblockerを判定済み | M |
| **H1 Contract** | Rust writer → TS readerのgolden round-tripと破損拒否がCIで成功 | W + M |
| **H2 Preflop** | preflop packをSimulatorと物理iPhoneで表示・検証 | M |
| **H3 Blueprint** | 実機でresume download、SHA検証、atomic install、offline gradingが成功 | W + M |
| **H4 Commerce** | IAP sandbox、purchase restore、entitlement、TestFlightが成功 | M + cloud |
| **H5 Release** | release gates、privacy、17+表記、App Store提出条件を満たす | M |

P0aはWレーンだけで完結し、Macを待たない。P1 scaffoldはH0後、P0aと並行して
fixtureベースで開始できる。P2以降とmass generationはP0a/P0bの品質ゲートを待つ。

## 6. Mac feedbackの実行

Macでこのbranchをpullし、次を実行して環境情報を採取する。

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

結果と手動確認事項は
[`reviews/2026-07-19-mac-environment-feedback.md`](./reviews/2026-07-19-mac-environment-feedback.md)
に記入する。`mobile/` はP1で作るため、H0ではExpo buildを要求しない。
credential、token、証明書、provisioning profileの内容は記録しない。
