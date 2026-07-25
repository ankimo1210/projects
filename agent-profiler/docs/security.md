# Security and privacy

## Threat model

provider eventとtool outputは次を含み得る。

- user prompt、system instruction、source code
- command lineとtest log
- API key、Authorization header、cookie、credential
- path、username、email、顧客/個人情報
- sub-agent messageとMCP result

Agent Profilerはlocal observability toolであり、DLP productではない。

## Defaults

| Control | Default |
|---|---|
| External telemetry/upload | disabled / implementedなし |
| Raw event storage | enabled |
| Secret redaction | enabled |
| Retention | 30 days |
| File mode | `0600` |
| Directory mode | `0700` |
| Prompt in metadata | never |
| Environment values in metadata | never |

redactionはsensitive keyと既知patternをrecursiveに処理する。Authorization、API key、
access/refresh token、password、cookie、`sk-`, GitHub token、Slack token、AWS access key、
`*_TOKEN=value`形式が対象である。

## Raw logs

`events.raw.jsonl`はprovider JSON objectを保持する。redaction有効時は保存前にcopyを
redactする。stderrは`{"_stream":"stderr","text":"..."}` envelopeで同じfileへ保存する。

redactionは誤検知と見逃しがあり得る。secretでないtoken-like文字列を隠す場合も、
未知形式のsecretを残す場合もある。raw logを共有、commit、issue添付する前に人手で確認する。

もっとも安全な設定:

```bash
agenttop run codex --no-raw-log --redact -- "task"
```

`--no-redact`を使うとnormalized command/file previewにも機密値が残り得る。

## Environment and child process

子processはprovider CLIの通常動作のためparent environmentを継承するが、Agent Profilerは
environment変数の名前/値をmetadataへ列挙・保存しない。provider CLIへ独自のcredentialや
Authorization headerを注入しない。

Agent Profilerはproviderのsandbox/approval modeを緩めない。対象repo自体が悪意ある場合、
provider CLIの既存security境界が必要である。

## Oversized data

default 2 MiBを超える単一JSONL行はcontentを保持・表示・保存せず、discarded byte countだけを
記録する。streaming redactionが不完全な状態で巨大secretをraw logへ書かないためである。

## Retention

起動時にmetadataの`started_at`がretention日数より古いsession directoryだけを削除する。
session IDにpath separatorを許さず、configured `sessions/`直下以外を削除しない。
`retention_days=0`は自動削除を無効にする。

## Incident response

secretがraw logへ保存された疑いがある場合:

1. provider credentialをrotate/revokeする。
2. session保存先を確認し、該当directoryを安全に削除する。
3. shared backup、terminal capture、issue attachmentにもcopyがないか確認する。
4. patternが一般化可能ならredaction regression testを追加する。

