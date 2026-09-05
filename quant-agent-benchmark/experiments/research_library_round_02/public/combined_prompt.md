# 金利カーブ改善 Round 02 — 論文＋QuantLib 併用

## あなたへの割当

```text
CAMPAIGN = combined_all_models
MODEL_KEY = {{MODEL_KEY}}
ARM = {{ARM}}
REPEAT = {{REPEAT}}
RUN_ROOT = {{RUN_ROOT}}
PYTHON_BIN = {{PYTHON_BIN}}
TIME_LIMIT_MINUTES = 60
```

**今回の作業は1セッション・1提出のみ。4パターンを作る必要はない。**
全モデルに同じ論文・QuantLib・新規約・公開訓練データを与える。
ARM=Dは併用条件の管理用ラベル。別条件や別モデルを実行しない。
未展開の値があれば停止して質問する。実行モデル・推論設定は主催者が以前と
揃える。自分では切り替えず、確認できない設定はunknownと記録する。

## 目的

自分のfeedback_round_01最終提出物から出発し、未見条件でのゼロカーブ精度、
フォワードの安定性、欠損・外れ値への頑健性を改善する。単に論文の方法や
ライブラリを採用したこと、テスト件数、レポート体裁を改善と呼ばない。
論文・ライブラリは利用可能資源であり、劣る方式を強制採用する必要はない。
利用しなかった資料/APIも理由を残す。

主催者は同じ新データ上で変更前・規約修正のみ・最終版を比較する。
旧スコアとの差を改善率にしない。追加時間・規約修正・論文・ライブラリが
同時に与えられるため、観測された改善を特定の資源の因果効果と断定しない。

## 読み書きの境界

読むのはRUN_ROOT内と、指定Python環境での通常のライブラリ利用のみ。
input/、baseline/、materials/は読み取り専用。書き込みはwork/とaudit/のみ。
親ディレクトリ、他モデル、旧pilot、Git履歴、旧レポート・評価器、真値、
主催者基準実装、セッションログの探索・読取りは禁止。
外部検索・ネットワーク・追加インストール・別モデル相談・追加エージェントは禁止。
この指示自体はOS隔離を保証しない。不適切な露出は主催者へ報告する。

## 1セッション内で行うこと

1. 実作業開始直前のUTC時刻を記録する。準備・読書・実装・テスト・整理を含め
   60分以内。最後の10分は検証と保存に使う。中断・介入を時刻付きで記録する。
2. input/TASK.mdとinput/market_data/CONVENTIONS.mdを読む。
   新CONVENTIONSは継承コード内の古い規約より優先する。実数年限を暦日に丸めず、
   最終支払日・元本・端数クーポン・単位・負金利を確認する。
3. baselineを変更せず、workにあるコピーで元のCLIを新公開データに実行し、
   出力または失敗をaudit/before/へ保存する。旧データの出力で代用しない。
4. 既知のD(T)を直接渡せる価格付け診断を用意し、独立計算と比較する。
   推定方法は変えず規約適合だけを修正し、その実行可能なソース・設定・テスト・
   出力をaudit/convention_only/へ保存する。baselineからbefore、
   convention_onlyから規約修正後、workから最終版を再実行できるようにする。
5. materials/papers/の共通論文と研究ノート、materials/quantlib/の公式資料を読む。
   ライブラリの市場既定値より公開規約を優先。推定に関係する仮説を最大3つ選び、
   変更要素・検証分割・採用条件をaudit/protocol.mdに先に書く。
6. 1要素ずつ変更して比較し、不採用・悪化・失敗も残す。短期の情報圧縮、
   一定利回りとゼロ金利の混同、長期の過剰な振動/平滑化、真の局所形状を
   外れ値として除去する可能性を検証する。複雑さを採用理由にしない。
7. 同一商品ID・近似重複を同じfoldに入れ、短期/中期/長期・商品別を検証する。
   公開検証を繰り返し見て選ぶ限界も記録する。隠し評価結果を要求しない。
8. 論文の主張→仮説→実装変更→結果を対応付ける。QuantLibの利用API・版・
   規約との接続・使わなかった既定値を示す。負金利でD<=1や正フォワードを強制しない。
9. 最終版をwork/に保存し、同一ソース・設定・CLIで別データにも対応させる。
   新規約への適合と数値品質を検証し、採用理由・未解決の弱点を明記する。

変更前、規約修正のみ、最終版の保存は**同じセッション内のチェックポイント**であり、
別々の60分実行ではない。再現に失敗した段階は失敗として残し、架空の数値を作らない。

## 成果物

input/TASK.mdのCLI・数値出力・テスト・研究レポート契約を維持する。
既存の良い設計は残してよい。公開仕様と承認環境だけに依存する独立プロジェクトにする。

- work/: 最終提出物、実行手順、requirements、テスト、研究レポート。
- audit/before/: 変更前の新データ実行結果・ログ。
- audit/convention_only/: 規約修正のみの再実行可能なプロジェクトと出力・ログ。
- audit/protocol.md: 仮説・検証方法・採用基準。計画変更は時刻付き追記。
- audit/experiments.csv: experiment_id, change, hypothesis, validation_split,
  metric_name, metric_value, unit, adopted, reason。
- audit/round_summary.json: campaign, model_key, arm, repeat, actual_model,
  reasoning_effort, started_at_utc, finished_at_utc, wall_time_seconds,
  test_command, tests_passed, tests_failed, resources_used,
  unresolved_limitations, human_interventions。
- audit/feedback_response.md: 規約修正との差、採用/不採用、残る弱点。

トークンとAPI換算費用は主催者が実ログから集計する。自己申告で推測しない。
最終提出後の追加修正・再実行で都合のよい結果を選ばない。
