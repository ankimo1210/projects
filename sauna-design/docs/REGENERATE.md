# 再生成（v8）

Windows Blender5.2.1 LTSと既存のWSL環境を使う。追加の本番依存はない。

- ソース: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\.claude\worktrees\sauna-design-v3\sauna-design`
- 生成物: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\sauna-design\fable-v8`
- v3〜v7・reference-v2への出力を拒否（`scripts/blender.sh`・`make_all.sh`）。旧版の生成物・セッションを削除しない。
- v6以下の再現はsessions/source-v6.zip、v7はsessions/source-v7.zipのソースを参照し、現在のv8スクリプトから旧版フォルダへ書き込まない。

WSLで:

```bash
cd /home/kazumasa/projects/.claude/worktrees/sauna-design-v3/sauna-design
bash scripts/make_all.sh
```

個別の手順（WSL）:

```bash
D=/home/kazumasa/projects/_data/sauna-design/fable-v8
python3 -B scripts/fetch_assets.py
bash scripts/blender.sh build
bash scripts/blender.sh py "$PWD/blender/verify_v8.py" "$(wslpath -w $D)"
python3 -B scripts/v8_diagram.py $D
for v in self self_seat dry water annex annex_pool; do bash scripts/blender.sh render $v --res 2400 --samples 1500 --threshold 0.01 --name sauna_${v}_v8; done
bash scripts/blender.sh render dry_seats --res 2400 --samples 1500 --threshold 0.01 --show Check_people --hide-objects Body_DT --name sauna_dry_people_v8
bash scripts/blender.sh render bath_top --res 2400 --samples 400 --hide Ceilings --world 0.35 --name sauna_bath_top_v8
bash scripts/blender.sh glb --draco
python3 -B scripts/write_manifest.py $D
```

## ソースの構成（v8で変わった所）

- `blender/sauna/water_layout.py`：水風呂2槽・仕切り壁・休憩の離れ・人体・通路幅・動線・需要の例（bpy不要）。`room_water.py`の`cold_pools()`と`splash_wall_and_annex()`がこれを読む。
- `blender/sauna/sub_layout.py`：サブ2室の段・席・人体・TVの見え方・天井の比較（bpy不要）。`room_sub.py`が模型と確認用の人体を作る。`room_other.py`は裏方の室とTVの壁内部・桶だけになった。
- `plan/plan_a.json`：浴槽の矩形（`v7Rect`に旧値）、サブ2室の天井（`v7Ceiling`に旧値）、`v8`の注記。
- `scripts/v8_diagram.py`：検討図。`blender/verify_v8.py`：メッシュ確認とv7との照合。
- カメラは`blender/build.py`。v8で追加：`Cam_self`（扉から）`Cam_self_seat` `Cam_dry`（扉から）`Cam_dry_seats` `Cam_dry_tv` `Cam_annex` `Cam_annex_pool` `Cam_bath_top`。`Cam_self`と`Cam_dry`はv7から位置を変えた。他のカメラはv7のまま。

## 変えていない室を同じに保つ仕組み

板ごとの色むらとUVのずらしは1本の乱数列から取っている。浴室とサブ2室を作り直すと、その後に作る室の乱数がずれる。`blender/rng_probe.py`でv7ソースの各段階の終わりの位置を測り（構造190・メイン6700・浴室10361・休憩13493・サブ2室19963）、`build.py`が変えていない段階の前で`geo.jump()`によりその位置へ合わせる。`verify_v8.py`は凍結v7を読み取り専用で開き、Main・Rest・Doors・Product_study_v7・裏方のメッシュが形もUVも一致することを確かめる（一致しなければ終了コード1）。

`products.py`（ZL-300外形と浴室床）とGLB出力時の床の焼付け（`product_bake.py`）はv7のまま働く。浴室の床は新しい浴槽の穴に合わせて面が切り直される。

## 旧版用のスクリプト

`blender/verify_products.py`はv7専用（凍結v6との一致を前提にするのでv8のモデルでは失敗する。v8では使わない）。`verify_main.py`・`verify_sight.py`・`scripts/main_diagram.py`・`overflow_diagram.py`・`sightline_diagram.py`はv6の検討用で、v8の生成手順には入っていない。`bath_layout.py`の浴槽まわりの動線・距離はv6/v7の浴槽のもの（冒頭に注記）。`main_layout.py`の円筒ヒーターの寸法をZL-300の数値として使わない。

スクリプトはネイティブBlenderのPython失敗を`--python-exit-code 1`で伝え、`set -euo pipefail`でパイプの失敗も止める。試写は`--res 960 --samples 160 --threshold 0.05 --tests --name <name>`で生成データ側tests/へ。確認用の人体は`--show Check_people`で描画に出せる（`--hide-objects <名前の先頭>`で一部を隠す）。コミット/公開は行わない。
