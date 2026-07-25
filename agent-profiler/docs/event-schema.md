# Normalized event schema

`events.normalized.jsonl`の各行は`schema_version = 1`のJSON objectである。
provider固有fieldをconsumerへ漏らさず、未知eventも`event_type=unknown`,
`category=other`, `details.preserved=true`で残す。

## Fields

| Field | Type | Meaning |
|---|---|---|
| `timestamp` | RFC 3339 string | provider timestamp、なければ受信時刻 |
| `timestamp_source` | `provider` / `received` | 時刻の出所 |
| `provider` | string | `codex` / `claude` |
| `session_id` | string/null | provider session/thread ID |
| `event_type` | string | stableなsemantic type |
| `category` | enum | metrics category |
| `status` | string/null | `started`, `in_progress`, `completed`, `failed`など |
| `event_id` | string/null | source event/item ID |
| `correlation_id` | string/null | start/end pairing key |
| `tool_name` | string/null | provider tool name |
| `command` | string/null | shell command。redaction対象 |
| `file_path` | string/null | relevant file path |
| `duration_ms` | integer/null | providerが直接出したduration |
| `usage` | object/null | actual token fields |
| `output_bytes` | integer/null | UTF-8 serialized output size |
| `parent_agent_id` | string/null | 親tool/agent correlation |
| `agent_id` | string/null | sub-agent ID |
| `raw_event_type` | string | original type/subtype |
| `measurement` | enum | `actual`, `reconciled`, `estimated`, `unknown` |
| `details` | object | consumer非依存の補足。巨大本文は入れない |

## Categories

```text
model_wait
reasoning
search
read
edit
shell
test
web
subagent
user_wait
other
```

command分類は保守的に行う。たとえば`pytest`, `cargo test`, `npm test`は`test`、
`rg`, `grep`, `find`は`search`、`cat`, `sed`, `head`は`read`である。判定不能なshell
commandは`shell`のままにする。

## TokenUsage

```json
{
  "actual_input_tokens": 1200,
  "actual_cached_input_tokens": 800,
  "actual_cache_write_input_tokens": 0,
  "actual_output_tokens": 120,
  "actual_reasoning_tokens": 40,
  "actual_total_tokens": 2120,
  "source": "actual"
}
```

reasoning outputはoutputの内数として扱い、totalへ二重加算しない。欠損値は`0`ではなく
`null`を保つ。

## Pairing

| Provider | Start | End | Key |
|---|---|---|---|
| Codex | `item.started` | `item.completed` | `item.id` |
| Claude | assistant `tool_use` | user `tool_result` | `id` / `tool_use_id` |
| Claude sub-agent | `task_started` | `task_notification` | `task_id` |

processが異常終了した場合、open spanは最後の観測時刻で閉じ、
`incomplete=true`とする。IDがないstart/endを名前だけでpairingしない。

## Compatibility behavior

- JSONでない行は`parse_error`として保存する。
- 2 MiBを超える行は内容を破棄し`oversized_event`を保存する。
- type/field欠損はadapter errorまたはunknown eventへ縮退する。
- provider eventにtimestampがない場合は受信UTCを使い、`timestamp_source=received`とする。
- normalized eventのvalidation errorでchild processのdrainを止めない。

