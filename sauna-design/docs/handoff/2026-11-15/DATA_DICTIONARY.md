# データ辞書・単位・状態
ZIPルート基準。現実の測定/承諾と仮の計画値を区別する。

| データ | 意味 |
|---|---|
| project_source/plan/plan_a.json | 原型20×14m、15区画、壁/扉/槽、版別注記。m単位 |
| project_source/blender/sauna/*_layout.py | 実装した人体/ベンチ/水槽/休憩の座標と姿勢。bpy不要の計画データ。静止姿勢数と営業定員は別 |
| analysis/room_program.csv | plan_a.jsonのrectを区画ごとに展開。外形面積合計280㎡、内法有効面積ではない |
| analysis/pools.csv | 矩形/水深/控除前容積。水量を階段控除後に自動置換しない |
| analysis/glb_v8_metadata.json、glb_v9_metadata.json | 元GLBのJSONチャンクを読み出したメタデータ。頂点/画像のBINチャンクや衝突の判定ではない |
| analysis/glb_*_nodes.csv | ノード局所translation/rotation/scale/matrixと子/mesh/cameraの索引。ワールド座標に展開済みとはしない |
| artifacts/architecture-v1/calculations/design_balances.json | 原型の設備の仮条件別計算。日量は一般用追加分との区別が必要 |
| project_source/plan/basic_design/cost_items.csv | 84項目。low_man/base_man/high_manは**万円**単価。数量×単価へ10000を掛ける |
| artifacts/cost-v1/calculations.json | 金額は**円**。direct/経費/予備費/税/現金/運転の別。原型に対する条件付き試算 |
| artifacts/one-ginza-detail-v1/calculations.json | 347㎡分割の仮賃料/共益/追加枠9ケース。実募集額/工事見積ではない |
| analysis/revenue_model.json | 最新チャットの集約的な固定/変動・税抜参考換算を再現した仮モデル。元費用を上書きしない |
| analysis/revenue_scenarios.csv | 人数×税込平均単価の感度。実需要/価格予測ではない |
| analysis/source_catalog.csv | 元ファイル名＋source_idをキーに引用先を索引。IDだけで全体をJOINしない |
| analysis/requirements_and_decisions.json | ユーザー要件、作成側仮定、採用/未確定/旧条件を整理 |
| analysis/open_issues.csv | 成立ゲート、必要根拠、影響を記録。担当roleは必要な役割で依頼/担当者決定の事実ではない |

## 座標・版
plan/Blender: m、原点南西、x東・y北・z上。FL=0、原型スラブ上端−0.20mは仮。rect=[x,y,width,height]。
GLBはY-up出力、Viewer変換は(x,y,z)→(x,z,−y)。ノードのlocal変換とplanの絶対座標をそのまま比較しない。DXFはmmなのでmとの1000倍差に注意。
V8は内装現行、V9は仮建築スタディ。以前のv3〜v7/参考画像は履歴・参照用で現仕様の代替ではない。

## 金額・税・運転
- *_ex_yenは税抜円の入力。*_cash_yen/支払現金には給与・預託等も混ざる。全額を1.1で割ることは正式会計でない。
- 直接工事→工事支払の基準倍率は1.10×1.15×1.10=1.3915。元請経費/予備費/税をもう一度足さない。
- 保証金全額は一度現金に含め、償却を二重に加算しない。返還条件は物件ごと未確認。
- 運転3か月は売上を控除しない資金バッファ。月次売上/利益の予測ではない。
- 収益の給与374万円/月は現場324万＋管理50万。14時間営業に最適化した実シフトではなく元の18時間カバー仮定を維持。
- 収益350円/客は6000人/月の基準点総額を保つための仮分割。リネン180円税込/客等から水/ガス等の原価配賦を実証した値ではない。
- 月20万円の増床運営枠はONE GINZA月次に既に含む。収益の販促30万円はその後の追加仮定で、二重に増床20万円を足さない。
- 入館売上の税率10%と給与以外の税抜換算は収益感度の仮定。飲食/物販の税率ミックス、仕入控除・保険/積立/外注の税区分は未精査。

## 未知値と状態
- budget_cap_yen:null は**上限一旦解除**。価格未取得のnullとは意味が異なる。
- rent_ex_yen、bath_use_consent、actual_total_project_yen等のnull は未取得/未確認。0円/不可/適合に変換しない。
- unapproved_reuse_saving_applied_yen:0 は未確保の減額を使わない方針。再利用が確認済みで0円という意味でない。
- building_extra_direct_yen:0 は追加工事を**未算入**とした感度。不要と証明したケースでない。
- advertised_areaは広告表示、common_allocated_areaは共用按分、measured_usable_areaは実測有効面積、prototype_areaは仮原型を区別。
- 天井高/梁下/階高、口径/供給量、冷熱/電力/排熱、kW/kVA、料金用110kW/計画包絡約103kVAを混同しない。
- as_of/checked_atは読取日、updated_atは掲載更新日。実空室確認日と同一にしない。
- source_idは元ファイル内のIDで、ファイルを跨ぐ同名IDがある。作者仮定に公開価格URLを捏造しない。
- メッシュ検査failures=0は検査項目の範囲だけ。人の安全・衛生・消防・構造・費用・物件の成立を保証しない。
