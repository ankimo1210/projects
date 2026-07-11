# データモデル

`SourceConfig` は人が承認する取得設定、`SourceRecord` は取得結果、`QuestionRecord` は出典系譜を保持した質問候補、`QuestionPatternRecord` は独自に作成した抽象パターンです。

`QuestionRecord` の必須系譜は `source_id`, `source_url`, `source_position`, `extraction_method`, `parser_version` です。`raw_text` と `normalized_text` は分離し、正規化で原文を上書きしません。

アプリ用の自作問題300問はこのモデルを経由せず、ルートの `QuestionSources/wset_level3_original_questions_300_v2.xlsx` から専用スクリプトで生成します。
