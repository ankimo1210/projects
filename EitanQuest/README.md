# えいたんクエスト（英単語帳アプリ）- コード一式

## 最終決定事項（2026/07/07時点）

| 項目 | 決定内容 |
|---|---|
| アプリ名（表示名） | えいたんクエスト |
| Xcode Product Name案 | `EitanQuest`（英数字のみでプロジェクト作成時に指定、表示名は後からInfoで日本語に変更） |
| デザインテーマ | オレンジ/イエロー系（元気・ゲーム感） |
| 推奨AccentColor | オレンジ `#FF7A00`（Assets.xcassetsの`AccentColor`に設定するとボタン等に自動反映） |
| クイズの出題方向 | 英→日固定（確定） |
| 通知時刻 | 20:00固定（確定） |
| 例文表示 | クイズ回答後（解答表示時）に例文を表示（確定） |
| 発音と消音モード | 消音モードを尊重（消音時は読み上げ音も鳴らさない）（確定） |
| ゲーミフィケーション | ストリーク/XP/レベルはv2送り。MVPには含めない（確定） |
| 誤答選択肢の生成 | 全100語プールから抽出（復習モードで対象語が少なくても4択を保証） |
| Apple Developer Program | 未登録。実機テスト・App Store提出の直前に登録でOK（年間$99） |

### 実装フェーズで対応する既知事項（今すぐの判断は不要）
- アプリアイコン（オレンジ/イエロー系のクエスト風）を用意する必要あり
- Bundle Identifier（例: `com.kazumasa.eitanquest`）をプロジェクト作成時に指定
- App Store提出時にプライバシーポリシー＋プライバシーラベルが必要（データ収集なしなので内容は最小）
- 単語データ更新時のマイグレーション: 現状のシーダーはDBが空のときのみ実行するため、
  将来単語を追加してアップデート配信しても既存ユーザーには反映されない（v2で対応）

以下、プロジェクトの技術的な詳細です。

---

## VocabQuiz（英単語帳アプリ）- コード一式（内部コードネーム）

ここにあるのは Xcode プロジェクト本体（.xcodeproj）そのものではなく、
Xcodeで新規プロジェクトを作った後にそのまま組み込める **Swiftソースコード一式** です。
（この環境にはXcodeが無いため、.xcodeprojファイル自体はここでは生成していません）

## フォルダ構成

```
VocabQuiz/
├── VocabQuizApp.swift          # アプリのエントリーポイント（@main）
├── Models/
│   ├── Word.swift               # SwiftDataモデル（単語＋学習進捗）
│   └── WordCategory.swift       # カテゴリ（daily / business / exam）のenum
├── Data/
│   ├── words.json                # 初期プリセット単語100語（同梱データ）
│   └── DataSeeder.swift          # 初回起動時にwords.jsonをSwiftDataへ投入
├── Services/
│   ├── SpeechService.swift       # AVSpeechSynthesizerによる発音読み上げ
│   └── NotificationService.swift # 毎日20:00のリマインダー通知（固定時刻）
└── Views/
    ├── ContentView.swift         # タブ（学習 / 統計）のルート
    ├── CategorySelectionView.swift # カテゴリ選択・苦手復習への入口
    ├── QuizView.swift             # 4択クイズ本体
    └── StatsView.swift            # 正答率・進捗の統計画面
```

## Xcodeでの組み込み手順

1. Xcode → **File > New > Project** → iOS → **App** を選択
2. 設定:
   - Product Name: `VocabQuiz`
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: **SwiftData** にチェック
3. プロジェクト作成後、Deployment Target を **iOS 17.0以上** に設定
4. Xcodeが自動生成した `ContentView.swift` や `VocabQuizApp.swift`（テンプレート版）を削除
5. このフォルダ内の `Models` / `Data` / `Services` / `Views` フォルダと `VocabQuizApp.swift` を、
   Finderからプロジェクトナビゲータへドラッグ&ドロップ
   - "Copy items if needed" にチェック
   - "Add to target: VocabQuiz" にチェック
6. `words.json` がターゲットの **Build Phases > Copy Bundle Resources** に含まれているか確認
7. ビルド&実機 or シミュレータで実行

## MVPでの設計判断（仮置き部分）

- クイズの出題方向は「英単語 → 日本語訳を4択」固定（日→英は未実装、拡張しやすい構造にしてあります）
- 苦手単語の再出題ロジックはシンプル方式（間違えたら `needsReview = true` にして次回優先出題。本格的なSRSは未実装）
- 通知は固定時刻（20:00）。時刻変更UIは未実装（v2で検討）
- 1回のクイズセッションは最大10問（`QuizView.sessionSize` で変更可能）

## 動作に必要な権限

- 通知（初回起動時に許可ダイアログが表示されます。Info.plistへの追加設定は不要）
- マイク/カメラ等は不要（完全オフライン・ローカル動作）
