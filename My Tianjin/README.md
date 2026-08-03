# My Tianjin

中国語 (HSK) 学習のための個人利用 iOS アプリ。公式 HSK 3.0 の 11,000 語を
レベル別パックに収録し、単語・語順整列・読解・産出（作文）までを一つのアプリで
学べます。学習履歴は端末内に保存され、オフラインで完結します。

App Store 版 1.0 を 2026-07-20 に提出済み（無料・日本のみ配信）。
リリース手順は [`AppStoreAssets/RELEASE.md`](AppStoreAssets/RELEASE.md)。

## 主な機能

- **語彙** — 公式 HSK 3.0 の 11,000 語（HSK 1〜9 を 7 パックに分割）。
  見出し・ピンイン・品詞・公式通番・レベルつき
- **学習セッション** — 順番 / シャッフル / 今日の復習 / 苦手 の 4 モード。
  seed 固定の決定的シャッフルで問題順と選択肢順をセッション開始時に凍結し、
  中断しても `Codable` で完全復元できる
- **練習** — 単語穴埋め、聞き取り選択、語順整列、短文・長文読解、
  HSK 5〜9 の産出課題（ルーブリック採点）
- **上級トラック** — HSK 7〜9 専用トラックと技能別ダッシュボード
- **復習** — 正誤に応じて次回復習日を更新する差し替え可能な `ReviewScheduler`
- **発音** — `SpeechService` による読み上げ

## 構成

```
My Tianjin/
├── My Tianjin/            # アプリ本体 (SwiftUI)
│   ├── Content/           # コンテンツのモデル・リポジトリ・検証
│   ├── Core/              # Practice / StudySession / Conversation のドメイン
│   ├── Data/              # 永続化 (学習履歴・進捗マッピング)
│   ├── Features/          # 画面: Home / Vocabulary / Practice / Reading /
│   │                      #       Advanced / Conversation / Settings
│   ├── Services/          # SpeechService ほか
│   └── Resources/         # 同梱 JSON パック
├── My TianjinTests/       # XCTest (8 スイート)
├── Tools/                 # コンテンツ生成・検証スクリプト
├── Docs/                  # 実装プラン・コンテンツ出典
└── AppStoreAssets/        # スクリーンショット・メタデータ・配布サイト
```

## ビルド / テスト

Xcode で `My Tianjin.xcodeproj` を開いてビルド・実行します（macOS + Xcode が必要。
このワークスペースの他の Swift プロジェクト `EitanQuest` / `NeonThread` / `WSET`
と同じ扱いで、uv workspace のメンバーではありません）。

テストは Xcode の Test（⌘U）、または:

```bash
xcodebuild test -project "My Tianjin.xcodeproj" -scheme "My Tianjin" \
  -destination 'platform=iOS Simulator,name=iPhone 16'
```

## コンテンツの再生成

出典・ライセンス・レビュー状況は [`Docs/ContentProvenance.md`](Docs/ContentProvenance.md)
に記録しています（要点: 語彙は公式大綱 PDF 由来、英語語義の補助に CC-CEDICT
(CC BY-SA 4.0)、日本語語義は `curated` 93 / `human-reviewed` 555 /
`machine-translated-cc-cedict` 10,352 のタグで確定度を区別）。

```bash
Tools/extract_hsk_vocabulary.swift    # 公式PDF → 11,000語 JSON
node Tools/generate_content_packs.mjs # 日本語語義とレベル別パック生成
node Tools/enrich_hsk1_examples.mjs   # HSK 1 の例文補完
node Tools/validate_content_packs.mjs # 収録前の全件検証
```

再生成しても、確定済み（`human-reviewed` / `curated`）の項目は ID を変えずに
維持されます。語順問題・短文読解・産出課題はこのアプリ用のオリジナル教材で、
公式過去問の転載ではありません。

## メモ

- 進捗は [`Docs/ImplementationPlan.md`](Docs/ImplementationPlan.md) の PR1〜PR10 で
  管理しており、全 PR が完了しています
- App Review 用の連絡先・電話番号はリポジトリに記録しません（App Store Connect 内で管理）
