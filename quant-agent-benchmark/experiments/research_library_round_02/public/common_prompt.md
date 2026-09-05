# 金利カーブ改善実験 Round 02 — 共通プロンプト

## 割当（主催者が記入）

```text
MODEL_KEY = {{MODEL_KEY}}
ARM = {{ARM}}
REPEAT = {{REPEAT}}
RUN_ROOT = {{RUN_ROOT}}
PYTHON_BIN = {{PYTHON_BIN}}
TIME_LIMIT_MINUTES = 60
```

未展開の値があれば停止して質問する。実行モデル・推論設定は主催者が
初回と同じ設定にする。自分では変更せず、確認できない設定は unknown とする。

## 目的と境界

自分の改善ラウンド01提出物を出発点に、新しい規約・データに対する
ゼロカーブの推定精度、フォワードの安定性、欠損・外れ値への頑健性を改善する。
元の提出物や旧スコアは変更しない。新データで再評価するため旧スコアとの差を
改善率として使わない。内部整合性・テスト件数・レポート体裁と推定精度は別物。

読み取りは RUN_ROOT 内と承認Python環境の標準的なライブラリ利用のみ。
RUN_ROOT/input、RUN_ROOT/baseline、RUN_ROOT/materials は読み取り専用。
書き込みは RUN_ROOT/work と RUN_ROOT/audit のみ。
他モデル・他条件・他repeat・親ディレクトリ・Git履歴・旧評価器・真値・
主催者の基準実装・セッションログは検索も読取りも禁止。
外部検索、ネットワーク、パッケージ追加、別モデル相談、追加エージェントは禁止。
この指示だけでOS隔離が保証されるわけではない。不適切な露出は主催者へ報告する。

## 条件の意味

- A: 既存の汎用数値ライブラリのみ。追加論文・QuantLibなし。
- B: Aに加え、materials に配布された共通論文・研究ノート。
- C: Aに加え、QuantLibとmaterialsの公式資料。論文配布なし。
- D: 論文とQuantLibの両方。

条件は利用可能資源の差であり、手法の強制ではない。利用しなかった場合も
理由を記録する。A/Cでも自分が既に知っている手法や継承コードは使える。
配布されていない資料を、他条件の説明から探してはいけない。

## 手順

1. 開始UTC時刻を実測し、準備・読書・実装・テストを含め60分以内とする。
   最後の10分は検証と整理。中断・環境障害・人の介入は時刻付きで残す。
2. input/TASK.md と input/market_data/CONVENTIONS.md を読む。
   CONVENTIONSは新規約であり、継承コード内の規約より優先する。
3. baselineを変更せず、workのコピーで元のCLIを新しい公開データに実行する。
   出力・失敗を audit/before に残す。失敗を捏造した比較値で置き換えない。
4. 既知の割引関数を直接渡す価格付け診断を作る。カーブ推定を介さず、
   端数満期・元本償還・クーポン・単位・負金利を独立した計算と照合する。
5. 規約適合だけを修正した状態も audit/convention_only に保存する。
   規約修正の影響と、推定方法を変えた影響を分離する。
6. 最大3つの改善仮説、データ分割、採用条件を audit/protocol.md に先に書く。
   各実験は原則一要素変更。失敗・不採用・計画変更も履歴に残す。
7. baselineとadvancedを比較。商品の一定利回りを満期ゼロ金利と同一視しない。
   年限別・商品別の残差を見る。短期をバケットに潰す、真の局所形状を外れ値と
   みなす、ノイズへ完全適合する等の可能性を検証する。
8. 同一instrument_idと近似重複商品を同じfoldに入れる。短期・中期・長期の
   検証範囲を記録する。公開検証を繰り返し見て選ぶことの限界を明示する。
9. QuantLibを使う条件では、利用API、版、規約との接続、使わない市場既定値を
   明示する。論文条件では主張→仮説→変更→検証結果を対応付ける。
10. 未見データでも同一ソース・設定・CLIで動く最終版をworkに保存する。

## 成果物

input/TASK.md のCLI・数値出力・テスト・レポート契約を維持する。
新しい規約のみに適合する設計でよい。旧データへの適合は採用根拠にしない。

- work/: 独立した提出プロジェクト、requirements、実行手順、テスト、研究レポート。
- audit/protocol.md: 仮説・事前の検証方法・採用基準。
- audit/experiments.csv: experiment_id, change, hypothesis, validation_split,
  metric_name, metric_value, unit, adopted, reason。推測値は禁止。
- audit/round_summary.json: model_key, arm, repeat, actual_model,
  reasoning_effort, started_at_utc, finished_at_utc, wall_time_seconds,
  test_command, tests_passed, tests_failed, resources_used,
  unresolved_limitations, human_interventions。
- audit/feedback_response.md: 採用・不採用理由、規約だけの改善との差、残る弱点。

トークンとAPI換算費用は主催者が実ログから集計する。自己申告で推測しない。
真値や隠し結果を要求しない。最終提出後の追加修正は別runとして扱う。
