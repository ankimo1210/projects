# ORBIT — 3D Playground

Blenderで制作した金属の彫刻と喫茶店を、ブラウザで回して鑑賞する3D Webサイト。
React / TypeScriptで共通UIを作り、Three.js（React Three Fiber / Drei）とBabylon.jsの2つの描画エンジンで同じ作品を表示します。
アプリの土台はSitesのVinextテンプレート、操作パネルはshadcnのBase UI版です。
テンプレート同梱のUI部品のうち、実際に使うbutton / sheet / slider / switch / tabsだけを
残しています。追加が必要なら`npx shadcn add <部品>`で取得します。

## 起動

Node.js 22.13以降が必要です。このディレクトリで実行します。

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 3100
```

[ローカルプレビュー](http://localhost:3100/)を開きます。
外出先からのアクセス用URLはまだ発行していません。公開はプロジェクトの承認後です。

起動・ビルドの前に`scripts/sync-assets.mjs`が親プロジェクトの`assets/`から
4つの生成物を`public/assets/`へコピーし、比較用のHDR照明もローカル生成します。両方の生成物フォルダーはGit管理外です。
別のPCでは親READMEの喫茶店生成に加えて、Blenderで`blender/build_orbit_core.py`を
実行するか、生成済みのアセットをコピーしてください。Blenderの再生成は、手編集した
同名のファイルを更新するため、編集成果は別名で保存してください。

## できること

- ドラッグ・タッチで視点を回転。自動回転の再生・停止、視点リセット、拡大表示。
- CODE: 回転速度、ワイヤーフレーム、実際のシーン設定をJSONとしてコピー。
- DATA: 読み込んだメッシュ・三角形数、描画命令、約1秒ごとのFPSを表示。
- RESEARCH: Orbital core / Komorebi caféを切り替え。
- キーボードでパネルとスライダーを操作。Escapeで閉じ、操作元へフォーカスを戻す。
- 端末の「視差効果を減らす」設定では自動回転を初期停止。
- GLBの読み込みに失敗した場合は説明とBlenderのプレビュー画像を表示。

この版にAI API・ログイン・データ保存のバックエンドはありません。
3DとReactの状態を組み合わせた、ローカルで操作できる作品集です。


## エンジンを比較する

- [比較スタジオ](http://localhost:3100/compare): 同じGLBを左右に表示。ドラッグ・角度スライダー・ワイヤーフレームを同期。
- [Three.js版](http://localhost:3100/): 元のORBIT。
- [Babylon.js版](http://localhost:3100/babylon): 同じReact画面と操作パネルを別の描画エンジンで実装。

比較スタジオは同一のGLBとHDR、視野角43度、同じモデル正規化・角度、環境光のみ、
露出1.2、ACES、DPR 1で表示します。光の前処理、BRDF、ガラス、トーンマッピングの
実装は異なるため、同じパラメーターでもピクセルは一致しません。
今回比較するのはWebの描画エンジンで、元の形状を作るツールは両方ともBlenderです。

「この端末で計測する」は、片方のCanvasとエンジンを破棄して一方だけを描画します。
GLB/HDRの準備後、1秒のウォームアップを除き4秒以上のフレーム開始間隔を採取。
FPSはサンプル数÷計測秒数、p95は描画間隔の95パーセンタイル（nearest rank）です。
視点は固定。タブ非表示・画面サイズ変更・WebGL描画コンテキスト消失で計測を中止し、途中結果は破棄します。
再計測では順番を交互に変えます。比較中の2画面同時FPSは性能指標に使いません。

モデル容量は実際の応答から求めます。初回ダウンロード、エンジン起動、HDR前処理、
シェーダー初期化の時間はFPSに含めません。計測はVSyncや他のアプリの負荷の影響を受け、
ひとつのシーン・端末での数値をエンジン全体の優劣と解釈しないでください。

各サイト全体の版では元の演出を残し、ディレクショナルライトと操作ノードを追加しています。
元のThree.js版はDreiのLightformer、Babylon版はそれに対応するローカルHDRを利用するため、
厳密に照明条件をそろえて見るときは `/compare` を使います。
共通HDRは `scripts/studio.mjs` から再生成でき、外部配信アセットは使いません。

本番プレビューを起動してから、初期JavaScript量も再測定できます。

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome node scripts/compare-route-load.mjs
```

新しいブラウザコンテキストで各ルートを開き、初期3D表示までに取得したJSを合計します。
共通UI込み、GLB・HDR・PNG・フォントは除外。gzipは各応答を個別に圧縮した推定値で、
公開環境の実際の転送量ではありません。結果は `outputs/engine-route-load.json` に保存します。

## ボラティリティーサーフェス

[Volatility Viewer](http://localhost:3100/volatility) は、同じ数値データを
Plotly.js / Three.js（React Three Fiber）/ Babylon.jsの3パターンで表示します。
1画面の切り替えと3画面の比較ができ、回転・拡大・ワイヤー表示・選択点を共有します。
元のORBITのGLB表示とは独立して、数値から面を生成します。このViewerにBlenderアセットは使いません。

- 最初の表示は**模擬データ**。Equity smile / Symmetric smile / Short-end stressを選び、
  ATM水準、スキュー、曲率、期間の傾きを調整できます。
- 満期とK/Fのスライダー、3D上のホバー・クリックで数値を確認。
  選択点を通るsmileとterm structureを2Dの断面として表示します。
- CSVの読込・書出しはブラウザ内で完結します。完全な格子が必要で、欠損は補間しません。
  列は `tenor_years,moneyness,iv`。1年、K/F 100%、IV 20%なら `1,1,0.20` です。
- 3Dが利用できない場合も、数値、パラメーター、断面、CSV入出力を利用できます。

3画面は同じデータ、軸範囲、色、カメラ位置を使用します。文字・線・面の補間はツールごとに異なります。
このViewerは描画速度を計測していません。追加依存は3D用のPlotly partial bundleとその型定義です。
数式、単位、CSV制約は[仕様](../docs/volatility-surface.md)を参照してください。

## 検証

```bash
npm run typecheck
npm run lint
npm run build
npx playwright install chromium
npm test
```

インストール済みのChromiumを指定する場合:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome npm test
```

`lint`と型チェックはアプリ・UI部品・設定・テスト・スクリプトの全体を対象にします。

本番プレビューを起動したまま再ビルドすると、古いアセット一覧が残る場合があります。
再ビルド時は3101番ポートのプレビューを停止し、完了後に再起動してください。

Playwrightは本番ビルドをローカルの3101番ポートで起動し、
実際のWebGL描画、2エンジンの同期操作・順次計測、ドラッグ、ワイヤーフレーム、設定コピー、
作品切り替え、計測値、モバイル操作、読み込み失敗時のフォールバックを確認します。
描画はSwiftShader（ソフトウェアWebGL）です。macOSでは
`PLAYWRIGHT_CHROMIUM_EXECUTABLE`にGoogle Chromeを指定すれば追加DLなしで動きます。
スマホ幅はエミュレーションで、iPhone実機のFPSは未計測です。FPSは端末やバックグラウンド状態に左右されます。
描画品質・影・ガラスはBlender/Cyclesの静止画と完全には一致しません。

## ファイル

- `components/orbit/experience.tsx`: 画面、コレクション、操作パネル
- `components/orbit/scene.tsx`: Three.jsのGLB読み込み、照明、視点、描画計測
- `components/orbit/babylon-scene.tsx`: Babylon.jsでの同等の描画・操作
- `components/orbit/comparison.tsx`: 比較画面と順次計測
- `components/orbit/measurement.ts`: ウォームアップと統計
- `components/orbit/render-contract.ts`: 共通のカメラ・サイズ・入力
- `scripts/studio.mjs`: 共通HDR照明の生成
- `components/orbit/types.ts`: コレクション定義と型
- `components/volatility/model.ts`: 模擬データ、CSV検証、格子点の選択
- `components/volatility/contract.ts`: 3種類が共有する軸、色、座標、視点
- `components/volatility/*-surface.tsx`: 各ツールの描画と入力の変換
- `components/volatility/viewer.tsx`, `slices.tsx`: 共通の操作画面と2D断面
- `tests/volatility*.ts`: データ、描画、CSV、視点同期、フォールバックの検証
- `components/ui/`: 使用中のshadcn部品のみ（button / sheet / slider / switch / tabs）
- `app/globals.css`: デスクトップ・モバイルのレイアウト
- `tests/orbit.spec.ts`: ブラウザでの動作検証
- `outputs/`: 確認用スクリーンショット（Git管理外）

参考: [React Three Fiber公式](https://github.com/pmndrs/react-three-fiber)、
[Drei Environment実装](https://github.com/pmndrs/drei/blob/master/src/core/Environment.tsx)。

Babylonの参考: [公式ローダー](https://github.com/BabylonJS/Documentation/blob/master/content/features/featuresDeepDive/importers/loadingFileTypes.md)、[公式HDR環境光](https://github.com/BabylonJS/Documentation/blob/master/content/features/featuresDeepDive/materials/using/HDREnvironment.md)。
