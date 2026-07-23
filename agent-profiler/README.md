# Agent Profiler / Agenttop

Codex CLIとClaude Codeの非対話実行を、`htop`のようなローカルTUIで観測する
Python 3.12+のツールです。`agenttop`は実行とリアルタイム表示、
`agent-profiler`は正規化・保存・集計・レポートを担当します。

Phase 1は公式の構造化出力を使う非対話実行とreplayを正式対象にしています。
対話型CLIのPTY wrap、クラウド送信、モデル内部reasoningの取得は対象外です。

## インストール

このworkspaceではrootから実行します。

```bash
cd ~/projects
uv sync --all-packages
uv run --no-sync agenttop --help
uv run --no-sync agent-profiler --help
```

独立したコマンドとしてインストールする場合:

```bash
uv tool install ~/projects/agent-profiler
agenttop --help
```

runtime dependencyは
[Textual](https://textual.textualize.io/)と
[platformdirs](https://platformdirs.readthedocs.io/)だけです。Textualを採用した理由は、
非同期worker、DataTable、RichLog、test pilotが一つのframeworkに揃い、イベント取込みと
250 msの画面更新を分離しやすいためです。

## 初回実行

最初は匿名fixtureのreplayで画面と保存先を確認してください。

```bash
uv run --no-sync agenttop replay \
  agent-profiler/tests/fixtures/codex-session.jsonl --speed 4
```

実行中は`m`でmetrics、`l`で元JSONLのイベントログ、`q`で終了または子processへ
interruptを送ります。TUIを使わない場合は`--no-tui`を付けると、redact済みの
イベントstreamと終了summaryを表示します。

Codex:

```bash
agenttop run codex -- "テストを実行して失敗を修正"
```

Claude Code:

```bash
agenttop run claude -- "このリポジトリをレビュー"
```

内部ではそれぞれ`codex exec --json`と
`claude -p --verbose --output-format stream-json --forward-subagent-text`を使います。
CodexのJSONL event familyは
[OpenAI公式の非対話mode資料](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)、
Claudeのflagは
[Anthropic公式CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage)
に基づきます。sandbox・approval・tool設定はprovider CLIの既存設定を上書きしません。

## Codexの自動TUI起動

通常の`codex exec ...`から毎回`agenttop`を明示せずにTUIを起動できます。最初に一度だけ、
独立commandをinstallしてshell連携を有効にします。

```bash
cd ~/projects
uv tool install --force --reinstall ./agent-profiler
agenttop install-shell-hook
source ~/.bashrc  # zshの場合は ~/.zshrc
```

以後は普段どおり実行します。

```bash
codex exec "テストを実行して失敗を修正"
```

shell関数が`agenttop wrap codex`へ引数をそのまま渡し、内部で`--json`だけを追加します。
`codex exec`の終了code、sandbox、approval、modelなどのoptionは維持します。連携対象は
先頭subcommandが`exec`または`e`の非対話実行です。次は意図的に元のCodexへ直通します。

- 対話型の`codex`
- `--help`、`--version`、明示的な`--json`
- stdinをpipeする実行、promptとして`-`を使う実行
- `exec`より前にglobal optionを置く特殊な呼び方

一回だけ無効化する場合:

```bash
AGENTTOP_AUTO_WRAP=0 codex exec "task"
```

連携の解除:

```bash
agenttop uninstall-shell-hook
source ~/.bashrc
```

対応shellはbashとzshです。installerはマーカーで囲んだblockだけをrc fileへ追記・更新し、
既存内容とfile modeを維持します。

## 画面と録画

画面上部にprovider/model、status、elapsed、actual token、カテゴリ時間を表示します。
context windowの公式capacityをeventから得られない場合は、もっともらしい値を推測せず
`unavailable`と表示します。timelineとraw event logはtabで切り替えられます。

録画例:

```bash
asciinema rec agenttop.cast --command \
  "agenttop replay agent-profiler/tests/fixtures/claude-session.jsonl --speed 2"
agg agenttop.cast agenttop.gif
```

`asciinema`と`agg`は任意の外部ツールであり、このprojectのdependencyではありません。

## 保存とレポート

セッションごとに次を保存します。

```text
sessions/<session-id>/
├── metadata.json
├── events.normalized.jsonl
├── events.raw.jsonl       # --no-raw-logでは作らない
├── summary.json
└── report.md
```

Linuxのdefaultは`~/.local/share/agent-profiler/sessions`、macOSは
`~/Library/Application Support/agent-profiler/sessions`です。
`--data-dir`または`AGENT_PROFILER_DATA_DIR`で上書きできます。

```bash
agent-profiler sessions
agent-profiler show <session-id>
agent-profiler report <session-id>
agent-profiler export <session-id> --format json
agent-profiler compare <session-a> <session-b>
```

## Actual、Reconciled、Estimated

| 表示 | 意味 |
|---|---|
| `actual` | provider eventが直接報告したusage/duration、またはstart/endの観測時刻差 |
| `reconciled` | installed済み`ccusage`のJSON outputで同一sessionを照合した値 |
| `estimated` / `~` | providerがspanを出さないmodel待ち時間や、output byteからの寄与推定 |

ツール出力の次turn寄与は

\[
\widehat{T}=\left\lceil \frac{\text{UTF-8 bytes}}{4} \right\rceil
\]

という粗いheuristicです。billing tokenでもactual usageでもありません。日本語、code、
tokenizer、provider側の切詰めで誤差が大きくなります。詳細は
[token accounting](docs/token-accounting.md)を参照してください。

`ccusage`連携はterminal tableをscrapeしません。PATHに`ccusage` executableがある場合だけ
`<provider> session --json --offline`を呼びます。自動で`npx` downloadやnetwork accessは
行いません。

## Privacy

telemetryはなく、外部serverへsession dataを送りません。保存fileは可能な範囲で`0600`、
directoryは`0700`です。Authorization、API key、token、passwordと既知のsecret形式を
best-effortでredactします。

ただしraw eventにはprompt、source code、個人情報、tool outputが含まれ得ます。
redactionは完全なDLPではありません。機密性が高い作業では:

```bash
agenttop run codex --no-raw-log --redact -- "task"
```

defaultはraw保存あり・redactionあり・30日retentionです。`--no-redact`は意図的に
機密情報を平文保存し得るため、信頼できるlocal環境だけで使ってください。
[security](docs/security.md)も確認してください。

## 設定

Linuxは`~/.config/agent-profiler/config.toml`、macOSはplatformdirsの標準config directoryを
読みます。

```toml
[display]
refresh_ms = 250
show_estimates = true
max_timeline_rows = 20

[storage]
save_raw_events = true
retention_days = 30
max_event_bytes = 2097152

[privacy]
redact_secrets = true

[providers.codex]
enabled = true

[providers.claude]
enabled = true

[ccusage]
enabled = true
executable = "ccusage"
```

主要な環境変数:

```text
AGENT_PROFILER_CONFIG
AGENT_PROFILER_DATA_DIR
AGENT_PROFILER_REFRESH_MS
AGENT_PROFILER_SAVE_RAW_EVENTS
AGENT_PROFILER_RETENTION_DAYS
AGENT_PROFILER_REDACT_SECRETS
```

CLI optionが環境変数、環境変数がTOML、TOMLがdefaultを上書きします。

## 開発と検証

```bash
cd ~/projects
uv sync --all-packages
uv run --no-sync ruff check agent-profiler
uv run --no-sync ruff format --check agent-profiler
uv run --no-sync mypy agent-profiler/src/agent_profiler
uv run --no-sync pytest agent-profiler/tests
uv run --no-sync python agent-profiler/benchmarks/ingest.py --events 100000
uv run --no-sync python agent-profiler/benchmarks/overhead.py --events 100000
```

参考値（2026-07-23、この開発machine）では100,000 input eventに対して、
normalize+metricsの増分は0.734秒、約7.34 µs/eventでした。これはin-process ingestionの
計測で、model/network latency、disk性能、TUI renderは含みません。環境ごとに上のcommandで
再計測してください。

匿名化した実測probeは`tests/fixtures/probes/`、正常・異常・並列・sub-agent・巨大event用の
fixtureは`tests/fixtures/`にあります。

## 対応versionと既知の制約

2026-07-23に以下を調査しました。

| Component | 実測version | 状態 |
|---|---:|---|
| Codex CLI | 0.145.0 | 最小応答とcommand executionをE2E実測 |
| Claude Code | 2.1.218 | init、rate limit、resultを実測。正常runはsession limitで未完 |
| ccusage | 20.0.18 | provider別session JSONを実測 |

parserは未知eventを`other`として保存し、欠損fieldや不完全JSONLでprocess全体を落としません。
一方、upstream CLIはschemaを変更できます。特にClaude CLIのstream-json envelope全体には
固定schemaの保証を確認できていないため、upgrade後はfixture probeを更新してください。

主な制約:

- Codex 0.145.0 eventにtimestampがなく、受信時刻を使う。
- Codexのmodel/API spanは明示されないため、inter-event gapは`estimated`。
- Claudeの`result.duration_api_ms`はactualだが、個々のmodel call分解はできない。
- reasoning tokenはCodexの`reasoning_output_tokens`だけをactual表示する。Claudeのthinking
  textからtoken数を逆算しない。
- context window capacityは現行の観測eventから取得できず、ゲージはunavailable。
- Codexのsub-agent固有eventは確認できたtypeだけを分類し、未知typeは保持する。
- interactive PTY wrapとWindows nativeはPhase 1対象外。

詳しい調査表は[provider compatibility](docs/provider-compatibility.md)、
設計は[architecture](docs/architecture.md)にあります。
