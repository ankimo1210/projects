# デザインデータと再生成の案内

## 最初に見る画像
- artifacts/fable-v8/diagrams/sauna_floor_map_v8.png：現行の番号/凡例入り全体図。
- artifacts/fable-v8/diagrams/v8_plan.png：主な寸法・人体/動線の検討図。
- artifacts/fable-v8/renders/：現内装の主に浴室/サブ2室/離れの本番9画像。
- 主室・休憩の維持部分は artifacts/fable-v6/renders/sauna_main_v6.png、sauna_rest_v6.png、製品比較は artifacts/fable-v7/renders/。
- artifacts/fable-v9/renders/v9_axo.png、v9_plan.png、v9_section_deep.png、v9_v8cam_water.png：建築スタディの同モデル描画。
- artifacts/reference-v2/：初期のイメージ画像3枚と旧ブラウザ案。見た目の参照で寸法の根拠ではない。

## モデル
| パス | 用途 |
|---|---|
| artifacts/fable-v8/model/sauna_a_v8.blend | 内装現行。Blender 5.2.1 LTS/Cyclesで制作 |
| artifacts/fable-v8/model/sauna_a_v8.glb | 携帯用。Cyclesと照明/水/素材が異なる |
| artifacts/fable-v9/model/sauna_a_v9.blend | V8を保持した仮建築条件重ね合わせ |
| artifacts/fable-v9/model/sauna_a_v9_light.glb | 建築スタディ携帯用。製品床の焼込みなし |
| artifacts/fable-v7/model/sauna_a_v7.blend | V8の旧版一致検証に必要な参照。現行へ上書きしない |
| artifacts/architecture-v1/model/ | 断面3案用の別の小型モデル。全内装モデルとは別 |

V8とV9、V7はartifacts/内の兄弟構造を維持する。モデルを単独移動すると外部テクスチャの相対パスが切れる場合がある。
V8/V7のassets/polyhaven、assets/product_floorとmanifestを収録。Poly HavenのCC0出典・URL/MD5は元manifest。LIXIL等の製品参照・第三者素材は出典を保持し、自作の公式製品CADや無条件再配布可能素材とは扱わない。

## 軽量ビュー
ZIPを展開したルートでHTTPサーバーを動かす例（Pythonがある環境）:
```bash
python3 -m http.server 8765 --bind 127.0.0.1
```
V8: http://127.0.0.1:8765/artifacts/fable-v8/viewer/  
V9: http://127.0.0.1:8765/artifacts/fable-v9/viewer/

ドラッグ回転、ホイール拡縮、右ドラッグ移動。視点ボタン・人体/天井/建築線の切替がある。HTML直開きはGLB取得制限を受ける場合がある。
three@0.170.0/DRACOをjsDelivr CDNから取得するため、Viewerは完全オフラインではない。ZIP内のGLB自体とは依存が異なる。
ChatGPTでこのViewerの起動/3D表示が利用できることは保証しない。標準JSON/CSV、既存PNG、GLBのJSONメタデータから分析できるようにしている。

## 再生成
project_source/にplan、Blenderソース、scripts、tests、docsを収録。旧source-v4〜v7.zipはartifacts/source-history/。
元スクリプトはWSL/Windows Blenderとcanonical出力先を前提とし、旧版上書きを拒否する。**ZIP展開先でそのまま実行可能に改造したものではない**。新環境でパス/出力先/依存/Blender版を確認し、元成果や同じFable会話へ上書きしない。
V8はgeometry_seed=20261114と乱数ジャンプで維持部分を合わせる。V9はV8 BLENDの固定SHAに依存する。原モデル/GLBのSHAはFILE_INDEXと元delivery_manifestに記録。
新規GPU描画・Blender再生成は今回の梱包検証に含めない。元の画像とモデルを同梱し、頂点のBIN・画像・DRACOを再計算せずJSONメタデータだけ抽出した。

## 図面・表・検証
- artifacts/architecture-v1/drawings/：PDF、SVG、DXF、PNG。DXFは制御線の検討図で、施工詳細CADではない。
- artifacts/cost-v1/、property-v1/、candidate-search-v1/：PDF・XLSX・JSON/CSVと当時の検証。
- artifacts/candidate-search-v2/、candidate-detail-v1/、candidate-search-v3/、one-ginza-detail-v1/：物件調査の段階別資料。
- 旧delivery_manifestは当時の成果全体を指す。今回の収録範囲はPACKAGE_MANIFEST/FILE_INDEXが正で、旧manifestの全ファイルが同梱されていると仮定しない。

## 会話と再開
同じFable/high会話IDは 68de4adc-db0a-4644-a3a5-9be5012127a3、実モデル記録はclaude-fable-5-2。
SESSION_PROVENANCE.jsonに同一ID・元バックアップのハッシュ等を記録。raw会話はZIPへ複製せず、元環境で保持する。ChatGPTにこのUUIDだけで会話へアクセス/再開できるとはしない。
元環境での再開手順はproject_source/docs/FABLE_SESSION.md。重複起動、新規別会話への勝手な移行、purge/cleanup/削除は禁止というユーザー希望を引き継ぐ。
