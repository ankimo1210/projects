# えいたんクエスト（EitanQuest）

iPhone向けの英単語学習アプリ。プリセット100語を使った4択クイズ（英→日）で、
オフライン完結・App Store配信を目指すMVP。

- 言語 / UI: Swift + SwiftUI
- 永続化: SwiftData（ローカル完結、クラウド同期なし）
- 対応OS: iOS 17.0以降
- 音声: AVSpeechSynthesizer（オフライン、消音モード尊重）
- 通知: UserNotifications（毎日20:00のローカル通知）
- ネットワーク: 不要（完全オフライン）

## ビルドと実行

```sh
# シミュレータでビルド
xcodebuild build -project EitanQuest.xcodeproj -scheme EitanQuest \
  -destination 'platform=iOS Simulator,name=iPhone 17'

# UIテスト
xcodebuild test -project EitanQuest.xcodeproj -scheme EitanQuest \
  -destination 'platform=iOS Simulator,name=iPhone 17'
```

実機テストは Xcode で `EitanQuest.xcodeproj` を開き、
Signing & Capabilities で Personal Team を選択して ⌘R。
初回はデバイスの「設定 > 一般 > VPNとデバイス管理」でデベロッパを信頼する必要がある。

## 進捗と設計判断

実装済み機能・設計判断・残タスクは [PROGRESS.md](PROGRESS.md) を参照。
プロジェクトの確定仕様・データモデル・スコープ外事項は [CLAUDE.md](CLAUDE.md) を参照。

## フォルダ構成

```
EitanQuest/
├── EitanQuestApp.swift            # @main。ModelContainer生成、初回シード、通知登録
├── Models/     Word.swift / WordCategory.swift
├── Data/       words.json / DataSeeder.swift
├── Services/   SpeechService / NotificationService / FeedbackService
├── Sounds/     correct.wav / incorrect.wav
├── Views/      ContentView / CategorySelectionView / QuizView /
│               StatsView / SettingsView / WordListView
└── Assets.xcassets/  AccentColor / AppIcon
EitanQuestUITests/    SmokeUITests.swift
```
