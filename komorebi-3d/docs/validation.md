# 検証記録 — 2026-09-04

## ボラティリティーサーフェスViewer

`/volatility` にPlotly / Three.js / Babylon.jsの3種類を追加。
[操作とデータ仕様](volatility-surface.md)を参照。

- `npm run lint`、`npm run typecheck`、本番ビルドが成功。
- `npm test`: Node 7件とPlaywright 16件がすべて成功。ブラウザテストは1.8分。
  うちViewer専用はデータ処理5件・ブラウザ6件。
- 模擬データの既知のATM値、CSVの単位・並び替え・重複・欠損・不正数値、
  書出しと再読込で数値を保持することを確認。
- 3種類で実際にWebGLを描画。各画面からの回転が全Canvasの表示を変え、
  ドラッグで選択点が変わらないこと、視点リセット、ワイヤー表示を確認。
- Plotlyで上限までズームした後、さらにズームしても実際のカメラ距離と共通状態が22で一致。
  ネイティブのホバーとクリック、キーボードの満期・K/F選択、2D断面の更新を3種類で確認。
- CSVの実際のPlotly z配列を入力値と照合。不正なアップロード後も直前の格子を保持し、
  ダウンロードしたCSVの内容が一致することを確認。
- 390×844で表示・操作・横はみ出しを確認。初めからWebGLが利用できないケースと、
  描画中のコンテキスト消失でも、数値・断面・スライダーが使えることを確認。
- `python3 -m unittest discover -s tests -v`: 既存5件成功。Python 4ファイルの構文チェック成功。
- `web/outputs/volatility-comparison.png`、`volatility-mobile.png`に実描画の画像を保存。

環境はLinux Chromium / SwiftShader。スマホは画面幅のエミュレーションで、iPhone/Safari実機は未検証。
金融データの妥当性・無裁定性や実機の描画速度を検証するものではない。
大きなJSチャンクのビルド警告は残る。各描画ツールは遅延読み込みする。
Webサイトは未公開。Gitへの反映状況はコミット履歴を参照。

## エンジン比較の追加

Three.js / Babylon.js比較画面とBabylon版サイトを実装しました。
最新の検証と計測は[エンジン比較の記録](engine-comparison-validation.md)を参照してください。

## ORBIT Web（初版）

- Blenderで金属彫刻を生成し、Cyclesの画像とブラウザの実際の3D描画を目視確認。
  `orbit-core.glb`は357,792 bytes、8メッシュ、4材質。
- 2つのGLBのWeb用コピーとBlender出力のSHA-256が一致。
- `npm run lint`、`npm run typecheck`、`npm run build`が成功。
  lintはアプリ・使用中のUI部品・スクリプト・設定・テストを対象とする。
  初期テンプレートの未使用shadcn部品はlint対象外、型チェックには含む。
- 本番ビルドをローカルで起動し、Playwrightの4テストが成功（35.4秒）。
  実際の描画の変化、回転操作、スライダー、ワイヤーフレーム、設定コピー、
  フォーカス復帰、コレクション切り替え、実測値、拡大表示を検証。
- 390×844のモバイル表示・タップ操作・横方向のはみ出しを確認。
  `prefers-reduced-motion`で自動回転が初期停止することを検証。
- GLB取得を意図的に失敗させ、プレビュー画像と説明の表示、別作品への切り替えで
  3D表示が回復することを検証。
- `web/outputs/`に実際のスクリーンショットを保存。

ブラウザ検証はLinux Chromium + SwiftShaderによるもの。iPhone実機の描画速度や
Safariでの動作は未検証。フレームレートの保証はしていない。
ビルドはThree.jsを含む大きなチャンクについて警告するが、エラーはない。
3Dコードは遅延読み込みし、喫茶店のGLBは選択時に読み込む。
Web版は未公開。3100番ポートは開発用、3101番ポートは本番ビルドのローカル確認用。

## 確認済み

| 対象 | 結果 |
|---|---|
| Blender | Windows版5.2.1 LTS、RTX 5080、Cyclesでバックグラウンド実行成功 |
| 画像 | 1400×1400、64 samples。実際に画像を開き、看板・屋根・家具の配置を確認 |
| シーン | 664オブジェクト、649メッシュオブジェクト。`.blend`を保存 |
| GLB | 655メッシュ、30材質。ヘッダー・チャンク境界・外部参照の有無を確認 |
| Windowsコピー | GLBのバイト列とSHA-256がソースと一致 |
| コピー保護 | 新規コピー、既存保存先保護、入力欠落、破損GLB、ソース内へのコピー拒否の5テスト成功 |
| 静的検査 | Python構文、Ruff lint・format、PowerShell構文を確認 |
| 起動前診断 | `Open.ps1 -CheckOnly`がUnreal 5.8未導入を検出して停止 |

Blender由来のAREAライトはglTFで運べないため、UE側にRectLightを追加する実装です。
GLBの検査はファイルの基本構造の確認で、正式なglTF適合性検証やUE実機確認ではありません。

## 未検証

- Unreal Engine 5.8でのプロジェクト起動
- InterchangeでのGLBインポート、部品配置、センチメートルへの変換
- UEの照明・ガラス・材質の見た目、フレームレート
- 生成マップの保存と再起動

UEの標準保存先、Epicのマニフェスト、Windowsレジストリにエンジンは見つかりませんでした。
`Saved/komorebi_import.json`や`.umap`は未作成です。UEの実行結果を模擬したファイルはありません。
Pythonスクリプトは公式APIを参照して作成しましたが、UE実機での検証を代替しません。

## 実機確認の手順

1. Epic Games LauncherからUE 5.8を導入する。
2. Windows作業コピーの`Open.cmd`を起動する。
3. `Saved/komorebi_import.json`に`status: imported_and_saved`があることを確認する。
4. `Komorebi_Dusk`マップを開き、看板、椅子、ガラス、照明を確認する。
5. マップを再度開き、配置が保存されていることを確認する。

Python初回処理の成功記録はインポートと保存のみを示し、目視確認は別に行います。

## 2026-09-04 追記 — macOSでの修正と再検証

レビューで見つけた点を修正しました（Web: 起動時の欠損アセット案内、ワイヤーフレーム
切替のシーン再クローン回避、読み込み失敗GLBのキャッシュ解除、draw callsの表記、
未使用UI部品と依存の削除。Blender: GPUバックエンドの自動判定。ドキュメント: 環境固有
パスの一般化）。エンジン比較・ボラティリティ版の追加と同時期の作業のため、
そちらへrebaseして統合しています（`scene.tsx`の型import、`components/ui/tabs.tsx`の
保持、lint対象の統一）。

検証環境: macOS (Apple Silicon)、Node 22.23.2、Playwrightは同梱Chromiumではなく
インストール済みGoogle Chromeを`PLAYWRIGHT_CHROMIUM_EXECUTABLE`で指定。

| 対象 | 結果 |
|---|---|
| `npm run typecheck` / `npm run lint` | 成功。lint対象を`components`全体へ拡大した状態で0件 |
| `npm run build` | 成功。依存8件（recharts等）削除、Babylon/plotly追加後の状態で通過 |
| `node --test tests/*.test.ts` | 7件成功 |
| Playwright | 16件中14件成功。失敗2件は下記のとおり資産の代替が原因 |
| 復帰の回帰テスト | `clearAsset`を外すと失敗、戻すと成功することを確認 |
| `python3 -m unittest discover -s tests` | 5件成功 |
| Python構文 | `blender/`・`scripts/`・`unreal/`の全スクリプトで通過 |

**このMacに`assets/`が無いため、ビルドとブラウザ検証には三角形1枚の使い捨てGLBと
単色PNGを一時的に置いて実行し、検証後に削除しました。** これは配線（読み込み・切替・
失敗時の復帰・計測・操作）の確認であり、実際の造形・見た目の確認ではありません。
失敗2件は実資産の実測値を直書きした判定（`15,344`三角形、メッシュ数100超）のためで、
実資産があるPCでの再実行が必要です。

`tests/comparison.spec.ts`のベンチマークは、Git管理外の`outputs/`が存在しない環境
（新規cloneを含む）で`writeFile`がENOENTになるため、書き込み前に作成するよう直しました。

Blenderが未導入のため`build_scene.py`・`build_orbit_core.py`は未実行です。GPU自動判定
（OptiX/CUDA/Metal/HIP/oneAPI）は構文確認のみで、実機での選択結果は未検証です。
Unreal Engineの状況はこの時点では未検証のままです（翌日の次節で検証しました）。
## Unreal Engine への取り込み — 2026-09-05

UE 5.8.2 を導入し、`unreal/Content/Python/bootstrap_scene.py` を実データで
初めて走らせた。**取り込みは通り、照明は合っていない。**

### 通ったこと

| | 実測値 |
|---|---|
| エンジン | 5.8.2-56702186+++UE5+Release-5.8 |
| メッシュアクタ | 655（GLB のメッシュ数と一致） |
| シーン寸法 | 700.0 cm（GLB から独立に測った 700.0 cm と一致） |
| 生成アセット | `.uasset` 686 個 + `Komorebi_Dusk.umap` |
| Interchange / Python のエラー | 0 件 |

形状は完全に移った。ティール色の波板屋根、煙突、看板、日よけ、格子窓、街灯、
フェストゥーン電球、鉢植え、ベンチ、自転車、タイル舗装まで
`assets/previews/komorebi.png` と一致する。

### 初回実行で出たバグ 2 件（いずれも修正済み）

**1. カメラのバウンディングボックスで寸法ガードが誤爆した。**

```
RuntimeError: Unexpected scene size: 2460.0 cm; inspect import units
```

`inspect_bounds` は「StaticMeshComponent を持つアクタ」で絞っていたが、glTF の
カメラは `CameraActor` として取り込まれ、UE の `CameraActor` は**ビューポート
表示用のエディタ専用メッシュを持つ**ため通過してしまう。その bounds は固定の
半径 1000 cm で、原点が `(840, 1150, 800)` にあった。

$$\text{span}_Y = (1150 + 1000) - (-310) = 2460\ \text{cm}$$

エラーメッセージは "inspect import units" と単位を疑わせるが、**単位の問題では
なかった**。GLB は 700 × 443 × 620 cm で、ガードの 200〜2000 cm に収まっている。
`isinstance(actor, unreal.StaticMeshActor)` に変えて解決。

**2. 太陽の向きが最初から意図どおりに設定されていなかった。**

```
入力:   unreal.Rotator(-25, -40, 0)       # 意図: pitch=-25, yaw=-40
実測:   {pitch: -40, yaw: 0, roll: -25}
```

`unreal.Rotator()` の引数順は **`(roll, pitch, yaw)`**。キーワード指定に変更した。

### 合っていないこと

**空が黒い。** `SkyAtmosphere` が夕暮れの空を一切描画しない。Blender 版は
青灰色のグラデーション背景を持つ。**原因は未特定。** 以下は実測で否定済み。

- 光量ではない — 太陽を 3.0 → 8.0 lux にしても変化なし
- 設定漏れではない — 保存されたマップを読み出して確認した値:
  `atmosphere_sun_light: true` / `atmosphere_sun_light_index: 0` /
  `affects_world: true` / `transform_mode: PLANET_TOP_AT_ABSOLUTE_WORLD_ORIGIN` /
  `location: (0,0,0)` / `visible: true`

**RectLight の絶対光量が Blender と対応しない。** Cycles の AREA ライトはワット、
UE の RectLight はカンデラで、両者を結ぶ固定の換算係数は無い。
`build_scene.py` の 3 灯（Large dusk softbox 750W / Low golden sun 950W /
Cool rim light 1100W）から**移せるのは比だけ**で、絶対値は目視で合わせる必要が
ある。現状の 2500 / 3170 / 3670 は根拠のない初期値。

Blender の World 背景 `(0.13, 0.21, 0.32)` × 0.30 と、400m の Studio ground
背景板も GLB には含まれない。UE 側で作り直す対象。

### 検証方法

WSL から Windows の UE を起動し、ウィンドウを `PrintWindow` で直接取得した。
画面キャプチャ（`CopyFromScreen`）は壁紙しか写らない — UE のウィンドウは
`IsWindowVisible` が true でも別の仮想デスクトップに置かれることがあるため。
