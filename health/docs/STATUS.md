# health の同期・時刻修復

更新日: 2026-10-02

## 目的・完了条件

Google Fitbit の日内データで現地時計が重複しても異なる実時間の観測を保持し、保存済みの
原本から欠落した投影を復元する。バックアップと旧データを保持し、現用の書き出し・画面まで
同じ時刻契約で使えることを完了条件とする。

## 状態

- **完了:** UTC の観測識別子、現地時計・明示 offset の保持、旧3列 DB の transactional migration。
- **完了:** 通信なしの `rebuild-intraday`、完全な原本の最新版の選択、中断した最終応答の復元。
- **完了:** checkpoint の穴を飛ばさない更新、過去の失敗・原本・再開 cursor の保持。
- **完了:** UTC 横軸と現地時計 tooltip、旧 civil 形式の読取り、分精度の UTC ズーム入力。
- **完了:** ローカル main への統合、実 DB のバックアップ・復元、当日14種類の再取得、
  開発用・静的サイト用 export の更新と現用 frontend validator による確認。

## 検証

- 修正前: health Python 526 passed。修正後: 540 passed（ローカル main でも再実行）。
- Web: 102 passed、typecheck / lint / build が成功。変更ファイルの pre-commit が成功。
- private なコピー DB と実 DB で旧観測の保持を確認。コピーでは raw JSON・日次・睡眠の
  件数と行ハッシュが一致し、再実行の行ハッシュと provenance 件数も一致した。
- 不完全ページ・ページ欠落・破損・checkpoint の穴・新しい不完全 attempt・中断直後の
  完全応答は合成データで確認。fresh review の重要指摘3件を RED→GREEN で修正した。
- 両 export の件数が DB と一致し、世代・時刻配列の整列・実時間の順序・private 権限を確認。
  実データの値や原本の識別情報はこの公開文書に記載しない。

## 維持する制約・次の作業

今回の修復は完了。Google 上の全履歴の取得完了は未確認で、原本の coverage は partial のまま。
必要な場合は既存の `health sync` で履歴取得を続ける。通常の更新も既存の同期コマンドを使う。

typed データは既存の microseconds 精度を維持する。nanoseconds 以下の識別は今回拡張しない。
元の応答はその精度を含めて保持する。実 DB の移行・復元は実装担当の検証で確認し、
fresh reviewer は私有データを参照していない。

設計・手順: [spec](superpowers/specs/2026-10-02-intraday-time.md) /
[plan](superpowers/plans/2026-10-02-intraday-time.md)。実装ブランチは
`codex/health-intraday-time`、主要実装は `3cbef8a6`〜`335f87cc`。
