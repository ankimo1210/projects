# エンジン比較 — 2026-09-04

## 同じ作品を別の描画エンジンへ

Three.js 0.185.1 / R3F 9.7.0 と Babylon.js 9.25.0。
`/compare` は同じGLB・HDR照明・カメラ・モデルサイズ・姿勢で比較する画面、
`/babylon` は既存ORBITと同じReact UIをBabylon.jsで動かす版です。
Blenderによる造形は共通。UEやSplineで制作した結果ではありません。

同じ設定でも、金属の反射はThree.js側がくっきり、Babylon.js側が柔らかく見えました。
喫茶店ではThree.js側の屋根と窓が明るく見えました。今回の共通プリセットでの観察で、
各エンジンの描画品質の優劣ではありません。HDRの前処理・PBR・ガラス・ACESの実装差が残ります。

## 描画の計測

計測日時: 2026-09-04T07:38:57.069Z（UTC）。Linux Chromium + SwiftShader。
画面は1440×1000 CSS px、各描画バッファは644×435、DPR 1。
Orbital coreを固定視点で連続描画。片方のエンジンを破棄して順番に測定。
1秒のウォームアップ後、4秒以上を採取します。

| 指標 | Three.js | Babylon.js |
|---|---:|---:|
| FPS | 60.0 | 60.0 |
| フレーム間隔 p95 | 16.9 ms | 16.8 ms |
| 採取フレーム | 241 | 241 |
| モデルの三角形 | 15,344 | 15,344 |

両方とも約60fpsで、この条件では速度の優劣を判断できません。
FPSはVSyncの上限・他のアプリ・熱や電力設定にも左右されます。
この数値はRTX 5080の実測やiPhone実機の性能ではありません。
GPU識別: `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)`。
生の表示記録は `web/outputs/engine-comparison-measurement.json`。

## 初期JavaScript量

計測日時: 2026-09-04T07:40:33.982Z（UTC）。各サイトを新しいブラウザコンテキストで開き、
最初のcore描画までに取得したJS応答を合計しました。共通UIを含み、
GLB・HDR・PNG・フォントは除外しています。エンジン単体のnpm配布サイズではありません。

| 指標 | Three.js版 `/` | Babylon.js版 `/babylon` |
|---|---:|---:|
| JSファイル数 | 20 | 110 |
| 展開されたJS | 1,632,192 bytes | 3,084,634 bytes |
| 各JSをgzipした合計（推定） | 471,280 bytes | 810,290 bytes |

今回の実装ではBabylon版のgzip推定合計が約1.72倍。
実際の転送量は配信側の圧縮・キャッシュ・プリフェッチ等で変わります。
再現スクリプトは `web/scripts/compare-route-load.mjs`、詳細は
`web/outputs/engine-route-load.json`。本番ビルドの大きなチャンク警告は残っています。

## 確認

- `npm run typecheck`、`npm run lint`、本番ビルドが成功。
- Nodeの計測テスト2件、Playwright 10件が成功（約1分24秒）。
- 実際のCanvasの画素変化で同期ドラッグを確認。両方でcoreは8メッシュ／15,344三角形、
  caféは655メッシュ／151,362三角形。
- 作品切り替え、ワイヤーフレーム、単独計測、同じバッファ寸法、リサイズ中断、
  モバイル390px幅、キーボードスライダー、元のORBIT操作、GLB失敗からの回復を確認。
- `WEBGL_lose_context`で両方の描画を意図的に中断し、途中計測を破棄することを確認。
  このテストは修正前にThree.js側で失敗し、修正後に両方成功。
- スクリーンショットをデスクトップ／スマホ幅で開き、文字の重なりとモデルの切れを修正。
- Pythonの既存コピー保護テスト5件も成功。UE Editorの実機検証は今回行っていません。

Webサイトは未公開のローカルプレビュー。Gitへの反映状況はコミット履歴を参照。
生成GLB・HDR・画像・測定JSONはGit管理外、生成／再測定コードをソースとして残します。
