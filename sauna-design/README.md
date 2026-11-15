# Sauna Design

東京で検討中の男性専用サウナ（A案 20×14 m 仮）の内装・3D制作。
生成した内装イメージと旧ブラウザ3Dの品質差を埋めるため、Fable / high が方式をゼロベースで選び直し、
**Blender 5.2 Cycles のパストレーシング**で座標から実3Dを制作した（v3）。検討模型であり、構造・法規・設備・費用は未検証。

## 見るもの

生成物は Git 管理外の `../_data/sauna-design/fable-v3/`（実測 約61 MB）。

| 内容 | パス（`fable-v3/` 以下） |
|---|---|
| 編集可能なネイティブモデル | `model/sauna_a_v3.blend` |
| メイン・水風呂・休憩の描画（2400×1600） | `renders/sauna_main_v3.png` `sauna_water_v3.png` `sauna_rest_v3.png` |
| 全体俯瞰・平面（天井非表示） | `renders/sauna_overview_v3.png` `sauna_plan_v3.png` `sauna_plan_v3_labeled.png` |
| 交換用 GLB（形状確認用） | `model/sauna_a_v3.glb` |
| 確認用の軽量ビュー | `viewer/index.html` |
| 素材と出典（CC0） | `assets/polyhaven/manifest.json` |
| 設定・ハッシュ・描画時間 | `delivery_manifest.json` |

## 文書

- 条件・品質基準: [制作依頼](docs/BRIEF.md)
- 現在の状態・方式判断: [STATUS](docs/STATUS.md)
- 参照画像との比較・残る差・未確認: [検証](docs/VERIFICATION.md)
- 再生成手順・設定・素材出典: [再生成](docs/REGENERATE.md)
- セッションID・再開方法: [セッション](docs/FABLE_SESSION.md) / 親の受入確認: [PARENT_REVIEW](docs/PARENT_REVIEW.md)

## ソース構成

- `plan/plan_a.json` — A案の区画・壁・扉・浴槽の座標と、v3で加えた調整の記録。
- `blender/build.py` — 全区画を生成して `.blend` を保存。`blender/sauna/` が形状・素材・照明のモジュール。
- `blender/render.py` — 保存済み `.blend` から1視点を描画。`blender/export_glb.py` — GLB書き出し。
- `scripts/blender.sh` — WSL から Windows の Blender を呼ぶラッパー。`scripts/make_all.sh` — 一括再生成。
- `viewer/index.html` — GLB の軽量ビュー（three.js をCDNから読む。画質評価には使わない）。

一括再生成:

```bash
scripts/make_all.sh
```

Fable の会話は継続用に保持し、削除・purge しない。参考画像と旧版（`reference-v2/`）は読み取り専用。
