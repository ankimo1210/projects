# 次回アップデート用スクリーンショット

2026-09-25にXcode 27.0 / iOS 26.5 Simulatorから撮影。**App Store Connectには未登録**。

- `iphone-6.9/`: iPhone 17 Pro Max、1320 × 2868 px、4枚。
- `ipad-13/`: iPad Pro 13-inch (M5)、2064 × 2752 px、4枚。
- 両サイズとも [Appleのスクリーンショット仕様](https://developer.apple.com/jp/help/app-store-connect/reference/app-information/screenshot-specifications)に記載された解像度。
- 順番は「探索地図 → ボルドー産地詳細 → 学習 → 30分テイスティング試験」。各ディレクトリの `manifest.json` にファイルのハッシュと寸法を記録。
- `AppStoreScreenshotUITests` の `testCaptureProductScreens` と `testCaptureAtlasDetail` を両端末で成功させて採用。画面を目視確認し、アルファチャンネルがないRGB PNGであることを検証した。
- ボルドーの写真は Slywire 作、CC BY-SA 4.0。アプリ内の「写真の出典」に作者・原典・ライセンスを表示する。元画像と全写真の権利記録は `ReferenceSources/AtlasMedia/SOURCES.md` を参照。

公開中の1.0.1用画像は `../Screenshots/` に残す。次版を提出する前に、App Store ConnectのContent Rights、説明文、表示価格と、これらの画像の一致を確認する。
