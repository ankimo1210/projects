# Komorebi 3D

夕暮れの喫茶店「KOMOREBI」を題材に、Blenderでの造形からブラウザ・Unreal Engineでの
リアルタイム表示まで試す、個人用の3D制作プロジェクト。

## 現在の状態

- `web/`に、3Dを操作できるWebサイト「ORBIT」を追加しました。
  金属の彫刻と喫茶店を切り替え、回転・ワイヤーフレーム・描画計測を試せます。
- 比較ページ `/compare` で同じ作品をThree.js / Babylon.jsで並べて比較できます。
  同期回転と、片方ずつのFPS計測に対応。Babylon版のサイトは `/babylon` です。
- `/volatility` にボラティリティーサーフェスViewerを追加しました。
  Plotly / Three.js / Babylon.jsで同じ模擬データやCSVを表示し、視点・選択点・断面を連動させます。
  [操作とデータ仕様](docs/volatility-surface.md)を参照してください。
- Blender 5.2.1で制作・画像確認した喫茶店シーンを引き継いでいます。
- `.blend`、自己完結した`.glb`、プレビュー画像、再生成用Pythonがあります。
- Unreal Engine 5.8向けのプロジェクト定義と初回インポート用スクリプトがあります。
- **Unreal Editorでのインポート・表示は未検証です。** 作成時の環境では
  標準インストール先、Epicのインストール情報、Windowsの登録情報に
  Unreal Engineが見つかりませんでした。
- この段階はシーン制作とエディタでの鑑賞用です。歩行・ドア操作などの
  ゲームロジックはまだ実装していません。

## 開く

### Webブラウザ — ORBIT

```bash
cd komorebi-3d/web        # リポジトリルートから
npm ci
npm run dev -- --host 0.0.0.0 --port 3100
```

[ローカルプレビュー](http://localhost:3100/)で操作します。
セットアップ・機能・検証方法は[web/README.md](web/README.md)を参照してください。
未公開のローカル版です。外出先からのアクセス用URLは、承認後に発行します。

`assets/`はGit管理外の生成物です。未生成のPCでは起動時に不足ファイルと
再生成コマンドを表示して停止します。下の「再生成・検証」を先に実行してください。

### Blender

`assets/blender/komorebi.blend`をBlenderで開きます（未生成なら下記で再生成）。
`assets/previews/komorebi.png`はBlender/Cyclesによるレンダリングです。

### Unreal Engine（Windows）

1. [Epic公式手順](https://dev.epicgames.com/documentation/unreal-engine/install-unreal-engine)
   に従い、Epic Games LauncherからUnreal Engine 5.8をインストールします。
2. Windows機には作業コピーを1つ用意済みです（作成時のパスは
   `C:\Users\<ユーザー名>\Documents\Unreal Projects\Komorebi3D`）。
   別のPCで作る場合は下の`prepare_unreal.py`で新規に用意します。
3. そのフォルダーの`Open.cmd`をダブルクリックします。初回はGLBをインポートし、
   照明と確認用カメラを追加して`Komorebi_Dusk`マップを保存する設計です。
   初回処理が成功した場合だけ、マップを開く通常のエディタを起動します。
4. エディタのビューポートで右マウスボタンを押しながらW/A/S/Dで移動できます。
   マテリアル・ガラス・照明はBlenderと完全には一致しないため、実機で調整します。

エンジンを標準外の場所へ入れた場合はWindowsのPowerShellで指定できます。

```powershell
.\Open.ps1 -EditorPath 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
```

`Open.cmd`はアプリのインストール、ダウンロード、外部送信を行いません。
Python Editor Script PluginとEditor Scripting UtilitiesはUE付属の機能です。

## ソースと作業コピー

```text
komorebi-3d/
├── assets/blender/komorebi.blend    # 編集用の元データ
├── assets/export/komorebi.glb       # エンジン間の交換用
├── assets/previews/komorebi.png    # Blender描画の参考画像
├── blender/build_scene.py         # 形状・材質・照明の再生成
├── blender/build_orbit_core.py    # Web用の金属彫刻を生成
├── web/                          # ORBIT — ブラウザで操作する3Dサイト
├── scripts/prepare_unreal.py       # 新しいWindows作業コピーを用意
├── unreal/Komorebi3D.uproject      # Unrealプロジェクトのひな形
├── unreal/Content/Python/          # UEエディタ内で実行するPython
├── unreal/Config/                 # UE設定
├── tests/                         # 作業コピーの保護を確認するテスト
└── docs/                          # 設計、実装手順、検証記録
```

ソースはこのワークスペースに置き、Unrealの実行用コピーはWindowsローカルに置きます。
コピー後の`.umap`や`.uasset`はWindows側に保存され、自動ではソースへ戻りません。
**作業コピーを消したり上書きしたりしないでください。** UEで編集した成果は、
その作業コピーの`Content`と`Config`を明示的にバックアップします。
生成バイナリはこのリポジトリではGit管理外です。ソースを別PCへ移す場合は
Blenderで再生成するか、これらのデータを別途コピーします。

別の作業コピーを作る場合（リポジトリルートで実行。保存先はUnrealを動かす
Windows機から見えるパス。WSLからなら`/mnt/c/...`）:

```bash
python3 komorebi-3d/scripts/prepare_unreal.py \
  --destination '/mnt/c/Users/<ユーザー名>/Documents/Unreal Projects/Komorebi3D-v2'
```

保存先が既に存在する場合は停止します。コピー後の自動同期は行いません。

## 再生成・検証

Blender付属のPythonを使います。追加のpip依存関係やuvワークスペース登録は不要です。
生成スクリプトは工場出荷設定のバックグラウンドプロセスで実行してください。
実行するとソース側の`assets/`内の生成物を更新するため、手編集した`.blend`は
別名で保存します。

`build_scene.py`が喫茶店、`build_orbit_core.py`がWeb用の金属彫刻を作ります。
GPUはOptiX/CUDA/Metalなど利用できるものを自動で選び、無ければCPUに落ちます
（`RENDER_DEVICE:`行に出力）。

```bash
# macOS
'/Applications/Blender.app/Contents/MacOS/Blender' \
  --background --factory-startup --python komorebi-3d/blender/build_scene.py

# WSL からWindows版Blenderを使う場合
'/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe' \
  --background --factory-startup --python \
  "$(wslpath -w "$PWD/komorebi-3d/blender/build_scene.py")"

python3 -m unittest discover -s komorebi-3d/tests -v
```

Unrealインポートは新しいマップと専用のアセットフォルダーだけを対象にします。
既存マップ、既存インポート、未保存の編集を検出した場合は停止します。
失敗時は`Saved/Logs`を確認し、既存データを消さず別名の作業コピーで再試行します。

## 公式資料

- [UEのPythonスクリプティング](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python)
- [Interchangeによるシーンインポート](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/InterchangeManager?application_version=5.7)
- [BlenderからglTFへのエクスポート](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html)

最終確認: 2026-09-04。詳細は`docs/validation.md`を参照してください。
