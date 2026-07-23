# Provider compatibility and probe results

調査日: 2026-07-23、OS: Linux/WSL、Python: 3.12+。

## Commands and versions

```text
codex --version
codex-cli 0.145.0

claude --version
2.1.218 (Claude Code)

npx --yes ccusage@latest --version
ccusage 20.0.18
```

確認したhelp:

```bash
codex exec --help
claude --help
npx --yes ccusage@latest --help
npx --yes ccusage@latest codex session --help
npx --yes ccusage@latest claude session --help
```

## Official surfaces

Codex公式資料は`codex exec --json`がJSONLをstdoutへ出し、
`thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, `error`
およびcommand/file/MCP/web/reasoning itemを含むと説明している:

- [OpenAI: Non-interactive mode / machine-readable output](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)

Claude公式CLI referenceはprint modeの`text`, `json`, `stream-json`、
`--verbose`、sub-agent textをforwardするflagを説明する:

- [Anthropic: Claude Code CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage)
- [Anthropic: Tool call ID pairing](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Official Claude Agent SDK Python types](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/types.py)

Claude CLIのstream-json envelope全eventに対する固定versioned schemaは確認できなかった。
そのためSDKで公開されたmessage/content型を基準にし、CLI固有system/result envelopeは
実測とtolerant parsingで扱う。

## Probe matrix

| Capability | Codex 0.145.0 | Claude Code 2.1.218 |
|---|---|---|
| Session/model | thread IDあり、modelはprobe eventになし | `system:init`にsession/model/version |
| Event timestamp | なし | assistantにはあり。init/resultは欠損し得る |
| Input token | `turn.completed.usage` | assistant/result usage |
| Cached input | `cached_input_tokens` | `cache_read_input_tokens` |
| Cache write | `cache_write_input_tokens`を実測 | `cache_creation_input_tokens` |
| Output token | あり | あり |
| Reasoning token | `reasoning_output_tokens` | 独立field未確認 |
| Tool ID/pair | `item.id`, started/completed | `tool_use.id`, `tool_result.tool_use_id` |
| Shell output | `aggregated_output` | tool result content |
| Sub-agent | type名を保守的に分類 | task events、parent tool ID、forward flag |
| API duration | 明示spanなし | final `duration_api_ms` |
| Context capacity | 未確認 | stream eventでは未確認 |
| Unknown schema | `other`として保存 | `other`として保存 |

## Saved probes

実行promptとUUIDを匿名化した実測sample:

```text
tests/fixtures/probes/codex-0.145.0-minimal.jsonl
tests/fixtures/probes/codex-0.145.0-command.jsonl
tests/fixtures/probes/claude-2.1.218-rate-limit.jsonl
```

Codex command probeでは`item.started`と`item.completed`が同じIDを持ち、終了eventに
`aggregated_output`, `exit_code`, `status`が含まれた。event自体にtimestampはなかった。

Claude probeでは`system:init`からmodel/version/tools、assistantからtimestamp/error/usage、
resultからsession cumulative usage、`duration_ms`, `duration_api_ms`, `api_error_status`を
取得できた。ただし調査時にfive-hour session limitへ到達しており、正常tool callのlive probeは
完了できなかった。正常fixtureは公式SDK typeと匿名化したlocal schema形状から作ったsynthetic
dataであり、実測sampleと区別している。

## ccusage

`ccusage` 20.0.18はtop-levelとprovider別commandで`--json`を提供した。実測JSONは
`sessions`と`totals`を持ち、session rowにinput/cache read/cache creation/output/totalと
model breakdownが含まれた。

Agent ProfilerはこのJSONだけをoptional reconciliationへ使う。table outputはscrapeしない。

## Upgrade procedure

provider CLIをupgradeしたら:

1. version/helpを記録する。
2. toolなし最小runとread-only command 1回を実行する。
3. prompt、UUID、path、secretを匿名化して`tests/fixtures/probes/`へ追加する。
4. event type、timestamp、usage、ID、sub-agent fieldを本表と比較する。
5. unknown event testを残したままadapter fixture testを追加する。
6. replay、mypy、ruff、全testを実行する。

非公開のminified implementationやlocal transcript pathへruntime依存を追加しない。

