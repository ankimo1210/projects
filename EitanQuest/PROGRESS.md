# えいたんクエスト（EitanQuest）実装進捗

最終更新: 2026-07-07

iOS向け英単語学習アプリ（SwiftUI + SwiftData、iOS 17+、完全オフライン）。
本ドキュメントはMVP実装の進捗と各機能の設計判断を記録する。

## 現在の状態

- Xcodeプロジェクト（`EitanQuest.xcodeproj`）に全ソースを組み込み済み。
- シミュレータ（iPhone 17 / iOS 26.5）でビルド・起動・全画面遷移を確認済み。
- 実機（iPhone 16 Pro / iOS 26.5.2）でも起動確認済み（Personal Team署名、7日間有効）。
- UIテスト（`EitanQuestUITests`）3本がグリーン。

## 実装済み機能

### 基本（MVP）
- カテゴリ選択（日常会話 / TOEIC・ビジネス英語 / 大学受験・英検）→ 4択クイズ（英→日）→ 統計。
- 100語のプリセット（`Data/words.json`）を初回起動時にSwiftDataへ投入。
- 苦手単語（`needsReview`）の優先出題、1セッション最大10問。
- 毎日20:00のローカル通知、AVSpeechSynthesizerによる発音（消音モード尊重）。

### 回答フィードバック
- 正誤バナー（「正解！」緑 /「おしい！」赤）＋アイコン。色覚多様性に配慮し、
  選択肢自体にも ◯/✕ アイコンと緑/赤の塗りを付与。
- ハプティクス（正解=success / 不正解=error）。
- 効果音（正解=上昇チャイム / 不正解=下降音）。`FeedbackService` は
  AVAudioSessionを設定せず、消音モードを尊重（振動は消音時も有効）。
- 正解時は約1.4秒後に自動遷移、不正解時は「次へ」を画面下部に固定表示。
- 回答後は**全4択（誤答ダミー含む）に対応する英単語**を表示し、ダミーからも学べる。

### 単語データの拡充
- 全100語に発音記号（IPA・第一アクセント付き）を追加し、出題時から常時表示。
- 全100例文に日本語訳を追加し、回答後の例文カードに英文＋和訳を併記。

### 学習効率（追加実装）
- **重み付き出題**: 復習フラグ優先は維持しつつ、残り枠は未学習・誤答の多い語ほど
  出やすいルーレット式抽選（`weightedSample` / `reviewPriorityWeight`）。本格SRSは非導入。
- **間違えた単語だけ再挑戦**: 結果画面から、そのセッションの誤答語のみで即再挑戦。
- **出題時の自動発音**: 新しい単語表示のたびに自動読み上げ。設定でオン/オフ可（既定オン）。
- **単語一覧（ブラウズ）画面**: カテゴリ行を左スワイプ →「単語一覧」で、発音記号・
  意味・例文（英/和）付きの下見用リストを表示。

### データマイグレーション
- `DataSeeder` を「DB空のときのみ投入」から `seedDataVersion` ベースのアップサートに変更。
  バージョンを上げると既存ユーザーのDBにも単語コンテンツのみ反映（学習進捗は保持）。
  → CLAUDE.md の既知課題「単語データ更新のマイグレーション設計」を解消。

### アセット
- AccentColorを `#FF7A00`（オレンジ）に設定。カテゴリ別アイコン/カラー（橙/ティール/藍）。
- アプリアイコン（1024×1024、開いた本＋クエスト風の星、オレンジ→イエロー）をコード生成。

## ファイル構成

```
EitanQuest/
├── EitanQuestApp.swift（VocabQuizApp.swift）  # @main
├── Models/            Word.swift / WordCategory.swift
├── Data/              words.json（100語 + phonetic + exampleSentenceJa） / DataSeeder.swift
├── Services/          SpeechService / NotificationService / FeedbackService
├── Sounds/            correct.wav / incorrect.wav
├── Views/             ContentView / CategorySelectionView / QuizView /
│                      StatsView / SettingsView / WordListView
└── Assets.xcassets/   AccentColor / AppIcon
EitanQuestUITests/     SmokeUITests.swift（クイズ通し・設定トグル・単語一覧）
```

## 確定仕様（変更時は要相談 / CLAUDE.md準拠）

- 出題方向: 英→日固定。復習: シンプル方式（本格SRSなし）。
- 誤答選択肢: 全100語プールから抽出。通知: 20:00固定。1セッション最大10問。
- MVPスコープ外: 自作単語登録、クラウド同期、通知時刻カスタム、iOS16以前、
  ストリーク/XP等のゲーミフィケーション。

## 残タスク（配信に向けて）

- [ ] 実機での触覚・効果音・消音モード連動・20:00通知の最終確認。
- [ ] Bundle Identifier確定（現状 `com.ankimo.EitanQuest`）と `DEVELOPMENT_TEAM` の整理。
- [ ] App Store提出用のプライバシーポリシー＋プライバシーラベル（データ収集なしなので最小）。
- [ ] Apple Developer Program登録（$99/年、配信直前でOK）。
- [ ] アイコンのダーク/ティントバリアント（任意）。
