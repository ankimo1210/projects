# データ変更・アクセシビリティ規則

R0以降の機能で、コンテンツ、SwiftData、バックアップ、UIテストの契約を分散させないための共通規則です。

## Accessibility Identifier

- 形式は`<feature>.<screen>.<element>[.<state>]`とする（例: `theoryExam.session.submit`）。
- 小文字英数字のcamelCaseとピリオドだけを使い、表示文言・翻訳文字列・動的リストの配列番号をIDに含めない。四択のように件数と順序が仕様で固定された操作対象だけは、安定した選択肢位置（例: `.choice.0`〜`.choice.3`）を末尾に使ってよい。
- タップ、入力、状態確認の対象へ付与し、単なる装飾には付与しない。
- 既存IDはUIテストとの公開契約として扱い、変更時は同じ差分でUIテストも更新する。
- 文字サイズはDynamic Typeを尊重し、主要基準画面を標準、Accessibility Extra Extra Extra Largeで確認する。色だけで状態を伝えず、ラベルまたはSF Symbolsを併用する。

基準画面はホーム、学習設定、記述式自己採点、理論模試、今日の学習、弱点分析、産地マップ、用語復習、テイスティング試験、ペイウォール、設定とする。各画面をライト／ダーク、VoiceOver、日本語固定、機内モードでリリース前に確認する。

## コンテンツパック

| パック | 現行schemaVersion | 正本 | 依存契約 |
|---|---:|---|---|
| 四択問題 | 4 | XLSX | `sourceHash` |
| 記述問題 | 1 | JSON | `sourceHash`、公開状態、レビュー情報、用語ID |
| 用語・格付け | 1 | XLSX＋用語IDレビューJSON | `sourceHash`、`questionPackSourceHash`、`termIDMigrations` |
| 産地マップ | 2 | JSON＋SVG | `sourceHash`、問題・用語・比較軸の出典参照 |
| AI評価fixture | 1 | JSON | リクエスト／応答schemaVersion |

- 正本だけを編集し、配布JSONと画像は生成スクリプトで作る。生成物の直接編集は禁止する。
- 必須項目の削除、型・意味・列挙値の非互換変更では`schemaVersion`を上げる。任意項目の追加は同一versionで許可するが、旧生成物を読める既定値を実装する。
- 生成物には正本ハッシュを保存する。別パックに依存する場合は依存パックのハッシュまたは参照IDを検証する。
- アプリは未知のmajor schemaを拒否し、参照切れ、重複ID、不正配点、非公開コンテンツを取り込まない。
- 変更時は`make verify`を実行し、件数、公開数、タグ／LO分布、参照切れと生成物差分をレビューする。
- 用語IDは表示名と独立した永続契約とする。統合候補を文字列一致だけで自動統合せず、[`用語ID統合レビューと履歴移行契約`](glossary-term-id-migration.md)に従い、担当者・日付・理由が揃った決定だけを`termIDMigrations`へ生成する。

## SwiftDataとバックアップ

1. 既存モデルへの追加は、まず任意値または安全な既定値を持つフィールドにする。
2. `WSETApp`、Preview、unit testのすべての`ModelContainer`へ新規モデルを同時追加する。
3. 永続データを意味単位で移す必要がある変更は、明示的な`SchemaMigrationPlan`を用意してからschemaを切り替える。
4. バックアップはSwiftDataモデルを直接`Codable`化せず、version付きDTOを維持する。購入権利と秘密情報は含めない。
5. 新規DTO項目は旧バックアップで欠落しても復元できる任意値から開始する。非互換変更ではバックアップschemaVersionを上げ、旧version用decoderまたは移行処理を残す。
6. 最低限、空データ、現行往復、旧fixture復元、不明version拒否、購入権利を復元しないことを単体テストする。

## リリース判定

- 自動判定: `make verify`、`make test-unit`、`make test-ui`、`git diff --check`。
- 手動判定: ライト／ダーク、最大Dynamic Type、VoiceOver、機内モード、バックグラウンド復帰、端末時刻変更、旧バックアップ復元。
- App Store、iCloud entitlement、実AIバックエンドなど外部設定がない機能は「非live」と表示し、設定完了と実機検証まではリリース済みと扱わない。
