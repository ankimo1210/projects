# 再生成手順

前提: WSL Ubuntu、Windows 側の Blender 5.2.1 LTS（`/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`）、
NVIDIA GPU（OptiX）、Python 3 と Pillow（平面ラベルのみ）。別の Blender を使う場合は環境変数 `BLENDER`、
出力先を変える場合は `SAUNA_DATA_ROOT` を指定する。

## 一括

```bash
cd /home/kazumasa/projects/sauna-design
scripts/make_all.sh
```

## 個別

```bash
python3 scripts/fetch_assets.py                 # CC0素材を取得（md5検証・取得済みは再利用）
scripts/blender.sh build                        # plan_a.json から全区画を生成 → model/sauna_a_v3.blend（約2秒）
scripts/blender.sh render main  --res 2400 --samples 1500 --threshold 0.01 --name sauna_main_v3
scripts/blender.sh render water --res 2400 --samples 1500 --threshold 0.01 --name sauna_water_v3
scripts/blender.sh render rest  --res 2400 --samples 1500 --threshold 0.01 --name sauna_rest_v3
scripts/blender.sh render overview --res 2400 --samples 400 --hide Ceilings --world 0.35 --name sauna_overview_v3
scripts/blender.sh render plan     --res 2400 --samples 400 --hide Ceilings --world 0.35 --name sauna_plan_v3
python3 scripts/label_plan.py                   # 平面描画に室名を重ねる
scripts/blender.sh glb --draco                  # model/sauna_a_v3.glb
python3 scripts/write_manifest.py               # delivery_manifest.json（サイズ・sha256・設定）
```

試写は `--res 1100 --samples 200` で数秒。`--exposure` `--wb` `--look` で露出・ホワイトバランス・ルックを一時変更できる。

軽量ビュー（ブラウザ。three.js を CDN から読むためネット接続が必要）:

```bash
python3 -m http.server 8765 --directory ../_data/sauna-design/fable-v3
# http://localhost:8765/viewer/   （#main #water #rest で視点指定）
```

## 設定と再現性

| 項目 | 値 |
|---|---|
| レンダラ | Cycles、OptiX GPU、Light Tree 有効 |
| シード | 描画 20261114、形状の乱数（板ごとの色差・石の配置） 20261114 |
| 室内3視点 | 2400×1600、最大1500サンプル、適応サンプリング閾値 0.01（最小64） |
| 俯瞰・平面 | 2400×1600、最大400サンプル、`Ceilings` コレクション非表示、環境光 0.35 |
| ノイズ処理 | OpenImageDenoise（albedo＋normal、accurate prefilter）、間接光クランプ 8、Filter Glossy 0.5 |
| バウンス | 全体12 / 拡散6 / 光沢6 / 透過12 / 透明12 |
| 水 | Glass IOR 1.333＋体積吸収。屈折コースティクス有効、浴槽上スポットは MNEE（Shadow Caustics） |
| 色 | AgX / "AgX - Medium High Contrast"、ホワイトバランス 4300 K（tint 10）、LED は黒体 2700 K |
| 露出（stop） | main 2.45、water 3.0、rest 3.2、overview / plan 1.6（各カメラのカスタムプロパティ `exposure`） |
| カメラ | 24 mm（センサー36 mm）、目線1.5 m、水平（垂直はレンズシフトで補正） |
| 実測描画時間 | main 80秒、water 55秒、rest 51秒、overview 10秒、plan 16秒（RTX 5080） |

同じシード・設定でも GPU ドライバや Blender の版が変わるとノイズの出方が僅かに変わり得る。

## 素材の出典

すべて Poly Haven（https://polyhaven.com、公式API経由）、ライセンス CC0 1.0。URL・サイズ・md5 は `assets/polyhaven/manifest.json`。

| 素材 | 用途 | ページ |
|---|---|---|
| cherry_veneer（2K: diffuse / roughness / normal） | すべての木部（色味と明度はシェーダで調整、板ごとに乱数で差） | https://polyhaven.com/a/cherry_veneer |
| moon_rock_02 / 03 / 04 / 06（1K glTF） | サウナストーン（回転・拡縮して配置、色を暗く調整） | https://polyhaven.com/a/moon_rock_02 ほか |

石タイル・濡れ床・水・布マット・金属・ガラス・光源は Blender のノードによる手続き生成で、外部画像を使わない。
参考の生成画像（`reference-v2/*.png`）はテクスチャ・背景・合成のいずれにも使っていない。
