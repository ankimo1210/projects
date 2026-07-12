# NeonThread

暗い宇宙空間を舞台に、発光するコメット（トレイルを引く一本のライン）を操作して、迫りくる障害物の隙間をくぐり抜ける iOS 向け無限ランゲーム。片手・縦持ちで遊べるカジュアルなハイスコア更新型ゲームで、SwiftUI アプリシェルに SpriteKit のゲームシーンを埋め込んで構成する。仕様の詳細は `CLAUDE.md` を参照。

## ゲームプレイ

以下はすべて実装済み（`NeonThread/Game/GameScene.swift` で確認）。

- **操作**: タップ中だけ上昇、指を離すと降下。片手・縦持ち（Portrait 固定）。
- **進行**: 自機は画面左寄り固定、障害物が右→左へ流れる横スクロール。進行距離でスコア加算。
- **ライフ制**: ライフ 3。被弾で 1 減、直後 1.2 秒の無敵時間（点滅表示）。ライフ 0 でゲームオーバー。
- **コイン**: 隙間付近のリスクある位置に出現（出現率 75%）。取得で +5 点ボーナス。
- **難易度ランプ**: スクロール速度 180→320 pt/s、隙間 190→140 pt、出現間隔 1.7→1.05 s を距離に応じて変化（すべて上限/下限つき）。
- **障害物フェーズ**（距離 400 / 1000 / 1800 で解禁）: 静的な壁の隙間 → 上下に動く壁 → 回転バー → 複合（動く壁＋回転バー同時）。
- **演出**: トレイル emitter、パーティクルバースト、カメラシェイク、画面フラッシュ、効果音（AVAudioPlayer プール）、BGM ループ（フェード付き）、ハプティクス。
- **保存**: ハイスコアと累計コインを `UserDefaults` に永続化（`highScore` / `totalCoins`）。

## 技術スタック

- Swift / SwiftUI（アプリシェル・HUD・画面遷移）+ SpriteKit（ゲーム本体、`SpriteView` で埋め込み）
- 衝突判定はカテゴリビットマスク + `SKPhysicsContactDelegate`
- AVFoundation（サウンド）/ UIKit フィードバックジェネレータ（ハプティクス）
- Deployment Target: iOS 17.0、Portrait 固定、外部ライブラリなし
- Bundle ID: `com.ankimo.NeonThread`

## 開発状況

`CLAUDE.md`（2026-07-08）は「実装未着手」と記すが、その後実装が進んでおり **MVP スコープの 4 項目（ハイスコア保存・難易度ランプ・コイン収集・サウンド/振動）はすべてコード上に存在する**。障害物も仕様の Phase 1〜4 まで実装済み。

残り:

- 数値バランスの実機チューニング（コード内の定数は初期値と明記）
- サウンド/振動 ON/OFF の設定 UI（`isSoundEnabled` / `isHapticsEnabled` キーは参照されるが切替画面は未実装）
- 効果音・BGM は `Tools/generate_audio.py` によるプレースホルダ合成音（差し替え候補）
- Apple Developer Program 登録・配信作業（MVP 外: ランキング、課金、スキン等も未着手）

WSL2 上ではビルド・実行未検証（下記参照）。

## ビルド方法

macOS + Xcode が必要。このモノレポは主に WSL2 上で開発しているため、**本プロジェクトのビルド・実行は Mac 上でのみ可能**。

```
open NeonThread.xcodeproj
```

Xcode で `NeonThread` スキームを選び、iOS 17.0 以降のシミュレータまたは実機で実行する。

アセット再生成（任意、Python）:

```bash
python3 Tools/generate_icon.py    # アプリアイコン（light/dark/tinted）を PIL で生成
python3 Tools/generate_audio.py   # SFX/BGM の WAV を生成（afconvert で .caf 化）
```

## プロジェクト構成

```
NeonThread/
├── CLAUDE.md                     # ゲーム仕様（スペック確定版）
├── NeonThread.xcodeproj/         # Xcode プロジェクト
├── NeonThread/
│   ├── NeonThreadApp.swift       # @main エントリ
│   ├── ContentView.swift         # title / playing / gameOver の状態遷移
│   ├── Game/
│   │   ├── GameScene.swift       # SKScene: 自機・障害物・コイン・難易度・衝突・演出
│   │   └── GameViewModel.swift   # ObservableObject: スコア/ライフ/コイン、ハイスコア保存
│   ├── Views/                    # TitleView / GameView(HUD) / GameOverView
│   ├── Services/                 # AudioService / HapticsService
│   ├── Resources/Audio/          # bgm_loop.caf, sfx_*.caf
│   └── Assets.xcassets/          # アプリアイコン（light/dark/tinted）
└── Tools/                        # アイコン・音声のジェネレータスクリプト
```
