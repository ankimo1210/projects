# Token accounting

token数は精度と出所が異なるため、三つの層を混ぜない。

## Actual

provider eventが直接報告した値。

| Normalized field | Codex 0.145.0 | Claude Code 2.1.218 |
|---|---|---|
| input | `input_tokens` | `input_tokens` |
| cached input | `cached_input_tokens` | `cache_read_input_tokens` |
| cache write | `cache_write_input_tokens` | `cache_creation_input_tokens` |
| output | `output_tokens` | `output_tokens` |
| reasoning | `reasoning_output_tokens` | unavailable |

Codexは`turn.completed.usage`をturn単位で合計する。Claudeはassistant messageにもusageがあるが、
最終`result.usage`をsession cumulative valueとして優先し、二重加算しない。

\[
T_{\mathrm{actual,total}}
=T_{\mathrm{input}}+T_{\mathrm{cached}}+T_{\mathrm{output}}
\]

reasoning outputはoutputの内数、cache writeはprompt cache作成量なので、このtotal式へ
追加しない。

Claude APIのtool useは`tool_use.id`と`tool_result.tool_use_id`で対応することが
[公式tool use資料](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
に明記されている。token usage fieldの意味は
[Claude streaming資料](https://platform.claude.com/docs/en/build-with-claude/streaming)も参照した。

## Reconciled

`ccusage` 20.0.18は次の機械可読commandを実測済み。

```bash
ccusage codex session --json --offline
ccusage claude session --json --offline
```

Agent ProfilerはPATHに`ccusage`がある場合だけ実行し、`sessionId`または`sessionFile`を
provider session IDと照合する。terminal tableはscrapeしない。照合結果は
`summary.json.reconciled_tokens`へ別objectとして保存し、actualを上書きしない。

`npx ccusage@latest`は調査時だけ使った。通常実行中にpackage downloadやpricing network
requestを発生させないため、自動fallbackには使わない。

## Estimated attribution

tool result、shell output、file readが次のpromptへ何token残ったかはprovider eventだけでは
厳密に求められない。MVPはUTF-8 byte数から次を計算する。

\[
\widehat{T}_{\mathrm{next}}
=\left\lceil\frac{B_{\mathrm{output}}}{4}\right\rceil
\]

仮定:

- 1 tokenあたり4 UTF-8 bytesという言語非依存ではない粗い近似。
- providerによるtruncation、deduplication、tool-specific compactionを反映しない。
- 次turnへ実際に再投入された割合を反映しない。

この値は常に`measurement=estimated`、UIでは`~`、reportでは`estimated`と表示する。
actual/reconciled tokenと加算しない。

将来、providerが正式なcontext attributionまたはmodel固有tokenizerを提供した場合は、
method名とversionを保存する新しいestimatorとして追加する。

## Context window

context usageゲージには分子と分母が必要である。現行probeではCLI eventに公式の
context capacityを確認できなかったため、model名からcapacityを推測しない。
取得できない場合は`unavailable`と表示する。

