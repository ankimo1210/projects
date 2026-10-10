# Pilot v53 独立ソースレビュー

## 結論

固定 v53 の **保存済み教師を選択・転送する範囲を承認**します。Critical / Important の新規指摘はありません。
正式計画の lock、正式 pilot の実行、金融の精度・性能、phase 受入は承認していません。
live source は作者が v54 を進めているため、本レビューの承認対象は下記 snapshot 3 SHA のみです。

## 固定ソース

- johnhull/research/RB-F04/dynamic_hedging/run_pilot.py: a2b31766ab10f5f4a692b623273e217b5383302ce11c958c48a1af8a222707dc
- johnhull/research/RB-F04/dynamic_hedging/check_pilot.py: be7df959523742c8cf5863ebd6980ecb98e40d2e4c77dd3d6be015db32160b41
- deep_hedge_price/tests/test_dynamic_hedging_pilot.py: 6e6e489dfe3982992a73de8db0f5fbf0ab4499664973f6d5abca8c28bb172587
- run_reference.py の実ファイル SHA: cc7183df08f8d4b7942929ccc44cbcc5899be5df74128016c7c6521bac2909b9

snapshot/manifest.json と 3 ファイルの byte SHA を開始・終了時に再確認しました。
source は編集せず、独立証跡のみ D/task-5-pilot-v53-independent-* に追加しています。

## 独立実行

| 検証 | 実測結果 | 範囲 |
|---|---:|---|
| snapshot 専用テストの限定再実行 | 25 passed / 88 deselected、pytest 0.66秒、subprocess全体2.43秒 | RNG・金融生成入口を禁止。metadata、geometry、conditional-N、adapter実cap/resume |
| Heston/local × 4N × 2grid × 4purposes | 64 checks PASS | principal/next-N/opposite-grid/extra-date の実 producer、driver/cache 原N、unknown 保持 |
| 自己整合反例 | 21/21拒否 | 単なる保存 SHA の古さによる拒否を避け、selectorや source arguments を再構成して検証 |
| genuine local next-N cap | PASS | 原65536保持、cache/driver=None、実 parent ID 保持 |
| 手組み保存 transport の5 refinements | PASS | 宣言した cache 配列→risk producer→paired source の結合と unknown。数値・cash の資格ではない |

作者の dedicated 113 passed（57.44秒）はログ・実行前後 SHA の一致を確認しました。
これは独立再実行数に足していません。作者の v52 95 PASS も同様です。
検証時点の execution_candidate は原121ケース・51 required pilot attempts を保持しています。
4N、coarse/high、原 teacher seed と max-N reserved oracle reference を確かめました。

## 読み取り・反例で確かめたこと

- selector の stage descriptor 4 IDs は実 stage_plan と一致する必要があります。
- max-N の next purpose は reserved independent reference が必須。principal 代用は拒否します。
- next-prefix N、opposite-grid、原 seed、実 principal driver の同一性を保持します。
- teacher_selected_inputs は selector を保存 raw から再計算し、全 producer control maps と一致させます。
- principal/extra_dates、teacher_N、teacher_grid の各目的を別の producer に接続します。
- 使わない prefix や solver/source defect を required purpose の cap に代用できません。
- cache 不在、driver の欠落・重複、保存 financial flag の昇格を拒否します。
- conditional diagnostic は4N全部の prior predictionと componentwise 最大を必要とし、選択N branchのSHAを保存します。
- 新 selected adapter の実cap/resume はRNG禁止下で、実祖先cap、inspection、原Nを保存します。
- stage exact risk/cache binder は同形でも別配列の cache、risk、field、dataset、parameters、
  validation/fit、position width を拒否します。他モデルの固定1024/coarseと共通call cacheを変えられません。
- 構造・転送の検証値は金融 qualification を unknown のままにします。

## 失敗した独立試行の保存

1. independent-tests v1: 25 PASS / 1 FAIL。レビュー用 finance-entrypoint 禁止ガードが、
   旧 selector cap テストの teacher worker 呼び出し自体を禁止しました。
2. independent-tests v2: 25 PASS / 1 FAIL。worker入口だけを許可すると RNG 初期化を呼び、
   RNG禁止ガードで停止しました。実数値を再生成して通すことはせず、この旧1件を範囲外にしました。
3. independent-tests v3: RNG禁止の25件 PASS。新 selected adapter 実cap/resume はこの中に含まれます。
4. independent-probes v1: 全purpose/反例検証の後に、レビュー側の attempt key 名を間違えて
   KeyErrorで終了しました。v2で required_pilot_attempt_ids に直し、全検証を再実行しました。
   元スクリプト・ログを保持しています。

上記は本ソースの金融失敗やqualificationではなく、独立レビューの試行記録です。
v1/v2の禁止ガードによるFAILを、成功した25件に混ぜて扱っていません。

## 受入に残る範囲

- root が作る final mixed graph、A metadataの7 attempts接続、v54差分の固定レビュー。
- 原Nでの actual teacher/market/Greek/cash 数値実験、全121/51の正式pilotとsaved checker。
- 事前budget・全費用・fresh replay・両保管庫semantic restore・表示・phase最終ゲート。

今回の手組みrisk配列は source transport の独立境界テストです。
actual金融SDE、価格・Greeks・cash再計算を独立に証明したものではありません。
元の金融ゲートを免除しません。

## 照合対象の訂正

依頼の b62ad... は reference_methods.py の固定SHAでした。run_reference.py とは別ファイルです。
reference_methods.py の実SHA b62ad68a70236289ab05279286b1b72cf2622335a897751b524e0af32087f4fc を確認しました。run_reference.py の実SHAとの差を source変更と扱った通知はファイル名の取り違えであり撤回します。
全source closure／正式金融計画の未承認は、今回のレビュー範囲に基づくもので、そのSHA差異を根拠にはしていません。
