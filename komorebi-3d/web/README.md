# ORBIT — 3D Playground

Blenderで制作した金属の彫刻と喫茶店を、ブラウザで回して鑑賞する3D Webサイト。
React / TypeScript / React Three Fiber / Drei / Three.jsを使っています。
アプリの土台はSitesのVinextテンプレート、操作パネルはshadcnのBase UI版です。

## 起動

Node.js 22.13以降が必要です。このディレクトリで実行します。

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 3100
```

[ローカルプレビュー](http://localhost:3100/)を開きます。
外出先からのアクセス用URLはまだ発行していません。公開はプロジェクトの承認後です。

起動・ビルドの前に`scripts/sync-assets.mjs`が親プロジェクトの`assets/`から
4つの生成物を`public/assets/`へコピーします。両方の生成物フォルダーはGit管理外です。
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

`lint`はアプリ・使用するUI部品・設定・テスト・スクリプトを対象にします。
未使用の生成済みshadcn部品には初期テンプレートのlint違反があるため対象に含めていません。
TypeScriptの型チェックはそれらも含みます。

本番プレビューを起動したまま再ビルドすると、古いアセット一覧が残る場合があります。
再ビルド時は3101番ポートのプレビューを停止し、完了後に再起動してください。

Playwrightは本番ビルドをローカルの3101番ポートで起動し、
実際のWebGL描画、ドラッグ、ワイヤーフレーム、設定コピー、
作品切り替え、計測値、モバイル操作、読み込み失敗時のフォールバックを確認します。
この環境での描画はLinux Chromium + SwiftShaderです。スマホ幅はエミュレーションで、
iPhone実機のFPSは未計測です。FPSは端末やバックグラウンド状態に左右されます。
描画品質・影・ガラスはBlender/Cyclesの静止画と完全には一致しません。

## ファイル

- `components/orbit/experience.tsx`: 画面、コレクション、操作パネル
- `components/orbit/scene.tsx`: GLB読み込み、照明、視点、描画計測
- `components/orbit/types.ts`: コレクション定義と型
- `app/globals.css`: デスクトップ・モバイルのレイアウト
- `tests/orbit.spec.ts`: ブラウザでの動作検証
- `outputs/`: 確認用スクリーンショット（Git管理外）

参考: [React Three Fiber公式](https://github.com/pmndrs/react-three-fiber)、
[Drei Environment実装](https://github.com/pmndrs/drei/blob/master/src/core/Environment.tsx)。
