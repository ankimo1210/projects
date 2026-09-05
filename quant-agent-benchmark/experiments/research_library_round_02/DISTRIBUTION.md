# 各モデルへ渡すもの — 1モデル1ファイル

**全7モデル、各1セッション、論文＋QuantLib、各60分。**
旧A/B/C/Dの12ファイルではなく、下表の新しいファイルを使う。
ファイルを全文貼るか、ローカルファイルを読める環境へその絶対パスを渡す。
MODEL_KEY、作業先、Python環境は記入済み。資料・データを個別に添付する必要はない。

| モデル | 渡すファイル |
|---|---|
| Astra | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/astra_r1/PROMPT.md) |
| Sol | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/sol_r1/PROMPT.md) |
| Terra | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/terra_r1/PROMPT.md) |
| Luna | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/luna_r1/PROMPT.md) |
| Sonnet | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/sonnet_r1/PROMPT.md) |
| Opus | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/opus_r1/PROMPT.md) |
| Fable | [PROMPT.md](/Users/ankimo1210/Documents/quant-agent-benchmark-private/research_library_round_02/combined_all_models/fable_r1/PROMPT.md) |

モデル・推論設定を以前と揃え、新規セッションで開始する。
セッション名の例は `R02 / Astra / Combined / r1`。
セッションIDを控えておくと、時間・トークン・費用を正確に対応付けられる。
この会話、旧総合レポート、実験キット全体、他モデルの結果、suiteは渡さない。

**まだ起動しない：ホスト側のファイル/ネットワーク隔離は未設定。**
自分の入力・資料・元提出物のみ読取り可、work/auditのみ書込み可にし、
非公開suite・他モデル・旧pilot・元リポジトリへの実アクセス拒否を主催者が確認する。
プロンプトやフォルダ分離だけでこの隔離を実現したとみなさない。
