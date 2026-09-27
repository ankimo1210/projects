# market-research 開発状況

更新日: 2026-09-27
基準: [工程2の統合仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md)、
[工程3の初期計画](../../docs/superpowers/plans/2026-09-27-market-research-core.md)。

## 目標と完了条件

F01–F19 の採否を実装と検証結果に結び、Q01–Q13 を満たす新入口で
市場研究を行えるようにする。旧入口の切替は、その機能の比較・受入後に行う。

| 段階 | 状態 | 根拠・残り |
|---|---|---|
| 工程2 設計 | 完了 | 上記統合仕様、ADR 0004 |
| 工程3a オフライン中核 | 合成デモ範囲を検証済み | 価格/マクロ契約、時点別読取、lag1バックテスト、CLI、合成7画面 |
| 工程3b 実データと保存 | 未着手 | J-Quants/yfinance/Stooq/crypto、カレンダー、cache、DuckDB、SEC/e-Stat |
| 工程3c 分析機能 | 未着手 | 財務・basket・高度信号・比較・リスク・5ノート・HTML |
| 工程3d 連携・切替 | 未着手 | portfolio向け一方向export、旧結果との照合、代表画面の手動確認 |

## 検証

- オフラインテスト44件、CLIの `demo --json`、Streamlit AppTestの7画面、ruff check/formatを確認。
  pre-commit、相対リンクと49件の索引（13 / 7 / 13 / 6 / 10）も確認済み。
- 比較基準として quantkit のバックテストと macrokit のPITテストを実行し、24件成功。
- 旧プロジェクトの実データ・保存DB、個人口座、外部APIへの疎通は確認していない。
- 同じ `run_id` は合成runの入力時刻・価格と費用条件のハッシュに基づく。
  デモの判断は足終端1時間後で、価格の `available_at` と一致する。永続run保管は未実装。
- 独立レビュー後に、日付ラベルから足境界を推定せず明示入力を要求し、provider symbolを照合、
  異通貨リターンを拒否する契約を追加した。実provider側の時刻・FX変換の検証は後続。

## 次の作業

1. 実providerの生入力を時刻付き契約へ正規化し、取得元・調整方式・確定足のfixtureでQ01–Q05を拡張する。
2. macrokitの保存層・公表calendarを比較してPIT保存と取得中断の検証を加える。
3. 旧分析の採用機能と7画面を順に接続し、Q09–Q13、HTML、portfolio向けexportを完成させる。
4. 依存を変えてroot workspaceを同期した後、portfolio-analyzerの日次処理をメールなしで検証する。

阻害要因: 取引所カレンダーと各providerの生入力は、この初期版の契約には未接続。
