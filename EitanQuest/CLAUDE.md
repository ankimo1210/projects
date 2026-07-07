# CLAUDE.md — えいたんクエスト (EitanQuest)

このファイルはプロジェクトルートに置いてください。Claude Codeがセッション開始時に自動で読み込みます。

## プロジェクト概要

英単語学習アプリ（iPhone / iOS）。プリセット単語100語を使った4択クイズ形式で、
オフライン完結・App Store配信を将来的に目指すMVP。

- Xcode Product Name: `EitanQuest`
- 表示名（Display Name）: えいたんクエスト
- デザインテーマ: オレンジ/イエロー系。AccentColorは `#FF7A00` を推奨（Assets.xcassetsの`AccentColor`に設定）

## 技術スタック

| 項目 | 内容 |
|---|---|
| 言語 / UI | Swift + SwiftUI |
| データ永続化 | SwiftData（ローカル完結、クラウド同期なし） |
| 対応 OS | iOS 17.0 以降のみ |
| 音声合成 | AVSpeechSynthesizer（オフライン。意図的にAVAudioSessionのカテゴリ設定はせず、消音モードを尊重する仕様） |
| 通知 | UserNotifications（ローカル通知のみ） |
| ネットワーク | 不要（完全オフライン） |

開発環境（確認済み）: macOS 26.5.2 / Xcode 26.6 / iOS SDK 26.5 / Swift 6.3.3。
現時点でシミュレータのみ動作確認可能（実機は未接続、コード署名も未設定）。

## 確定済み仕様（変更する場合は要相談）

- クイズの出題方向: 英→日固定（4択、日→英は無し）
- 復習ロジック: シンプル方式。不正解になった単語は `needsReview = true` にして次回セッションで優先出題。本格的なSRS（間隔反復）は実装しない
- 誤答選択肢: 出題対象（カテゴリ or 復習リスト）ではなく、**全100語プールから**ランダムに3つ選ぶ（復習モードで対象語が少なくても4択を保証するため）
- 例文表示: クイズ回答後（解答表示時）にカードで表示
- 通知: 毎日20:00固定。時刻カスタマイズ機能は無し
- 1セッションの問題数: 最大10問（`QuizView.sessionSize`）
- ゲーミフィケーション（ストリーク/XP/レベル等）: MVPには含めない。v2で検討

## データモデル

- `Word`（SwiftData `@Model`）: id, headword, meaning, categoryRaw, exampleSentence, correctCount, incorrectCount, needsReview, lastAnsweredAt
- `WordCategory`（enum, String rawValue, Hashable必須）: `daily` / `business` / `exam`
- 単語データは `Data/words.json`（100語: daily 34語 / business 33語 / exam 33語）に同梱。`DataSeeder` がDB空のときのみ初回投入する

## ファイル構成（既存のドラフトコード）

```
VocabQuiz/
├── VocabQuizApp.swift          # @main。ModelContainer生成、初回シード、通知スケジューリング
├── Models/
│   ├── Word.swift
│   └── WordCategory.swift
├── Data/
│   ├── words.json
│   └── DataSeeder.swift
├── Services/
│   ├── SpeechService.swift
│   └── NotificationService.swift
└── Views/
    ├── ContentView.swift        # タブ（学習 / 統計）
    ├── CategorySelectionView.swift
    ├── QuizView.swift           # 4択クイズ本体（未検証・未ビルド）
    └── StatsView.swift
```

※ これらのSwiftファイルはXcodeが無い環境で書いたため、**一度もビルドされていません**。
文法的な整合性は手動でレビュー済みですが、実際のビルドで初めて出るエラー（import漏れ、SwiftDataのAPI差異など）がある前提で見てください。

## 既知の未対応事項（次にやること）

- [ ] Xcodeプロジェクト作成（SwiftUI + SwiftData, iOS 17+ Deployment Target）→ 上記ファイルを組み込みビルド確認
- [ ] `words.json` が Build Phases > Copy Bundle Resources に含まれているか確認
- [ ] アプリアイコン作成（オレンジ/イエロー系、クエスト風のコンセプト）
- [ ] Bundle Identifier決定（例: `com.kazumasa.eitanquest`）
- [ ] 実機テスト用にApple IDをXcodeに追加（Personal Teamで可、Apple Developer Program未登録でも実機テストは可能）
- [ ] Apple Developer Program登録（$99/年）は配信直前でOK
- [ ] App Store提出時にプライバシーポリシー＋プライバシーラベルが必要（データ収集なしなので内容は最小限）
- [ ] 単語データ更新のマイグレーション設計（現状シーダーはDB空時のみ実行。将来の単語追加アップデートが既存ユーザーに反映されない）

## スコープ外（v2以降で検討、MVPでは実装しない）

- ユーザーによる単語の自分登録・編集
- クラウド同期・複数端末対応
- 本格的なSRS（間隔反復）アルゴリズム
- 通知時刻のカスタマイズ設定
- iOS 16以前への対応
- ストリーク/XP/レベルなどのゲーミフィケーション
