# Architecture

## Scope

Phase 1はCodex CLIとClaude Codeの非対話実行を子processとして起動し、公式の構造化stdoutを
観測する。provider本体、非公開API、local transcriptを実行経路として改変しない。

```text
codex exec --json ──┐
                    ├─ async process reader ─ Provider Adapter
claude stream-json ─┘                            │
                                                ▼
                                      NormalizedEvent v1
                                                │
                       ┌────────────────────────┼──────────────────────┐
                       ▼                        ▼                      ▼
                 MetricsEngine           SessionRecorder        Textual TUI
                       │                        │
                       ▼                        ▼
                 summary/report       raw + normalized JSONL
```

## Components

| Module | Responsibility |
|---|---|
| `adapters/codex.py` | `thread/turn/item/error`を共通eventへ変換 |
| `adapters/claude.py` | SDK message/content envelopeとtask eventを変換 |
| `runner.py` | child起動、stdout/stderr同時読込み、signal伝播、上限付きline処理 |
| `metrics.py` | ID pairing、span、token、output attribution、並列時間 |
| `storage.py` | session directory、0600 file、retention |
| `privacy.py` | key/valueのbest-effort secret redaction |
| `replay.py` | raw JSONLを同じadapterへ時間差付きで再投入 |
| `tui.py` | event ingestとは独立したrefresh timerで表示 |
| `ccusage.py` | optional JSON-only usage reconciliation |
| `shell_integration.py` | bash/zshで標準形の`codex exec`を自動wrap |

TUIと集計はraw provider fieldを読まない。schema差の影響をadapterで止める。

## Process lifecycle

1. `agenttop`がprovider executableとworking directoryを検証する。
2. promptをmetadataへ保存せず、子process argvだけに渡す。
3. profiler process-start境界を記録し、stdoutとstderrを`asyncio.gather`で同時にdrainする。
4. raw eventを必要ならredactしてdiskへstream writeする。
5. adapterが0個以上の`NormalizedEvent`へ変換する。
6. normalized eventを保存し、metricsとTUI callbackへ渡す。
7. child終了境界を記録し、未完spanを`incomplete=true`で閉じる。
8. summary/report/metadataをatomic replaceで確定する。
9. `ccusage` executableがinstalled済みならoffline JSONで任意照合する。

`Ctrl+C`/TUIの`q`は新しいprocess groupのchildへSIGINTを送り、3秒後にterminate、さらに
2秒後にkillする。既存CLIの通常exit codeはそのまま返し、signal exitはshell conventionの
`128 + signal`へ変換する。

## Shell integration

`agenttop install-shell-hook`はbash/zshのrc fileへ、マーカー付きの小さなshell関数を追加する。
標準形の`codex exec ...`だけを`agenttop wrap codex -- ...`へ転送するため、利用者は毎回
wrapper commandを入力しなくてよい。`wrap`は引数を再解釈せず保持し、Codexの正式な
`--json` optionだけを追加して既存のprocess runnerへ渡す。

対話型`codex`、help/version、明示的なJSONL、pipe入力は直通させる。Pythonが起動する
子processには親shellの関数が継承されないためrecursive wrapは起きない。非公開session
fileのtailやprocess injectionには依存しない。

## Backpressure and memory

- stdout/stderrは別taskで継続的にdrainする。
- TUI refreshはdefault 250 msだが、event ingestはrefreshを待たない。
- metricsのrecent eventは2,000件、output rankingは100件に制限する。
- 1 JSONL eventのdefault上限は2 MiB。超過した1行はchunk単位で捨て、byte数と
  `oversized_event`だけを保存する。
- raw/normalized JSONLはsession全体をmemoryに保持せず逐次writeする。

JSON objectをparseするには完全な1行が必要なので、上限超過eventの内容は解析もredactionも
せず破棄する。redaction前の巨大secretをlogへ流さないための意図的なtrade-offである。

## Time model

start/endはevent IDまたはtool use IDを第一にpairingする。IDがないeventへ広いheuristicは
適用しない。

- `inclusive_ms`: 全spanの単純合計。並列toolはwall timeを二重計上する。
- `exclusive_ms`: すべてのstart/end境界で区間を分割し、同時にactiveなcategoryへ等分する。
  category合計は観測されたactive wall timeを超えない。
- `idle_or_unclassified_ms`: elapsedからexclusive active timeを引く。

これはCPU profilerのcall-stack exclusive timeではなく、parallel observability向けの
重複調整値である。reportへ定義を常に保存する。

## Extensibility

将来のPTY/sidecar adapterも`ProviderAdapter.normalize(raw, received_at)`から
`NormalizedEvent`を出せば、metrics/storage/TUIを再利用できる。schema versionを変更する場合は
normalized readerのmigrationを追加し、既存v1 eventを破壊しない。

## Reference performance

2026-07-23の開発machineで100,000 fixture eventを測定した結果:

```json
{
  "baseline_json_parse_seconds": 0.086752,
  "profiled_parse_normalize_metrics_seconds": 0.820615,
  "incremental_microseconds_per_event": 7.339
}
```

`benchmarks/overhead.py`は同じprocess内のJSON parse baselineと
parse+normalize+metricsを比較する。model/network、disk、TUI renderを含まないため、
end-to-end latencyの保証値ではない。
