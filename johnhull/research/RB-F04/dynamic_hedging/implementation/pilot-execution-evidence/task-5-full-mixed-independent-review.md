# 全 progressive / mixed graph の独立 metadata レビュー

2026-10-10。compiler/source読取のみ、Git・source編集なし。

## 判断

**v3 compiler の graph metadata 構造と semantic control cap coverage を限定承認する。**
元121cases /51attempts、4N/grid/seedsと原仕事の依存、選択後の teacher_N/grid向き、原cacheの出所を独立に照合した。
3138jobsという件数やrootのsignatureだけを根拠にしていない。金融数値・正式lock・pilot/main・budget・phase完了は承認しない。

## 固定対象

- task-5-progressive-pilot-plan-producer-v2.py: 70dd3c8c07c2a1a6688a1e0b38a5b32993e94f11eb59f2d8c76355eac5cacfa0
- task-5-progressive-pilot-plan-producer-v3.py: 0a8124af7dc233a5e41d6278bf612fef3d8afe081c83ed761d0276fb7718f59d

- v2原graph: task-5-full-progressive-pilot-plan-draft-source-unit-v1/
- v3修正版graph: task-5-full-progressive-pilot-plan-draft-source-unit-v2/
- dry-runのv1/v2原script/json/log
- v53 fixed sourceからのmetadata parser、v54 fixed sourceでのsupplement、v55 fixed sourceでの後続37限定testsと元Q反例再検査
- source契約の最終限定判断: task-5-pilot-v55-independent-decision.json

v3はcap_scopeだけを修正している。独立検査で全jobsのoperation/arguments/N/prediction等をcap_scope以外で比較し、原仕事が増減していないことを確認した。

## 確認した依存と原仕事

| 項目 | 独立確認 |
|---|---|
| 元roster | 全121caseと51attemptのID・設定・binding、元4N1024/4096/16384/65536、coarse/high、全seeds、SDE768/1536、frequency12/24/48 |
| progressive stages | 両モデル各8stage、原18state/12date、teacher・nextN・opposite grid・driverとactual stagePlanの一致 |
| physical teacher purpose | 48件。raw teacher/model/grid/N、元driverN/seed、MAX65536で独立reserved oracle streamを確認 |
| stageの数値source参照 | 当該モデルだけをrefine、相手モデルは元N1024/coarse、共通call cache不変 |
| 8 selected adapters | principal/teacher_N/teacher_grid/extra_dates×2model、原selector/actual teacher+driver mapを保持 |
| conditional work | 36state /24date /限定7dynamic attempts、actual controlsから元Nとproducerを決める |
| final work | 44primarycellsを最終mixed cachesでrerollout、全16Greek/band比較、teacher_N/grid各16、position16×3width、pnl16 |
| fitとvalidation | tiny fits4件・元N1024のtrain/validation streams、元band選択候補14、未訓練init29/47 slotsを成功へ置換しない |
| position reference | 原first independent referenceN4096 oracleを両モデル18state×2の36件再使用、元oracle namespace |
| exact frequency | frequency24/48×2modelの追加教師4件、extra_datesのactual driver、原4N prediction branch、各16比較、exact call/calendar source |
| Q / empty claim | 各36件、元N1024・18state・3refinement streams・5exact pricing dates、emptyは同モデル実Q source |
| precision | 原3N、両モデル×3refinement seeds、actual market/risk inputs |
| financial inputs | 元Dupire257×321/order1024/frequency_scale512/floor1e-10、call49dates/65spots、premium sourceとhalf_spreads保持 |
| cap coverage | 全3138jobのactual producer descendantsと、case/date/teacher_N/gridの数値・control参照を独立に再構成して照合 |

最初のJSONの numeric_dependency_edges=15281 という名前は、job_record / job_arguments を含む**全typed producer edges**を数えている。
純粋な数値仕事量の指標ではなく、費用見積へ変換しない。

## 自己整合 counterexamples

原preflightの14件は全拒否。refinement cache方向の交換、selectedcase model/date、固定市場N削減、field設定、Q pricing date、empty親Q、frequency、precision seed、fit欠落、position幅、stage binding、無関係cap parent等。

補足の11件も全拒否。
nextNをprincipalに代入しstagePlan/cache bindingもそろえる、MAX独立referenceをprincipalへ代入、反対gridをprincipalへ代入、driver変更、rawNの貼替、
相手モデルcacheを勝手にrefine、teacher_N/grid adapterのcap attempt coverage削除、selector state/date coverage削除、無関係case cap宣言を拒否した。

原14件のstage_other_model_refinedというprobe名は、実際にはstage IDを差し替えたprobeだった。
本当の相手モデルcache refinement反例は、補足のstage_other_model_cache_refinedで検査して拒否した。元script/json/logは変更していない。

## selector own-cap の元失敗と修復

v2 graphではselector自身のcap_scopeに原18selected states /12datesがなかった。
v53 sourceでは、完成selector raw N65536を保存した実時計capにもかかわらずadapterがsource defectへ落ち、独立ジョブが続行しない原反例を保存した。

v3はselectorsとactual adapter controlsを事前possible IDsへ加え、全semantic cap coverageを満たした。
v54固定sourceでは、完成selectorのraw/元job_argumentsを認証し、依存adapter/diagnosticを実数値未実行として原N65536・同じ実parentで保存する。
独立control-cap-v4 probeは両モデルで、選択元stateが既実行でもselectedcase/dateのrequired workにselectorを含め、
同じ実cap parentからunknownへ投影し、A concrete specに同じcontrol IDsが入ることを確認した。
独立ジョブ続行・saved resume一致・新RNGなし。state/date/gate数値checkerは明示metadata stubで、金融性能は証明しない。

## source修復の後続検査

v54 native Qの入力欠落/元worker入力不一致は別途独立に発見し、v55で修正された。
v55は旧保存4件を新RNGなしで再使用し、37限定testsと105元反例/入力mutationを拒否した。
このsource限定承認を金融資格へ広げない。詳細はv54/v55の独立report/decision/manifest。

## 正式lockに残るもの

graphはformal_plan_locked=false、financial_qualification=unknown、test_opened=false。
execution_projectionのcap_optionsは空、parent_expense_idはNone。未レビューrate・仕事/expanded bytes/事前budgetのunknownも残る。
原historyと10件のexternal inclusive expense receipts/aliasesを閉じていない。
現時点では正式A metadata/budget lock、全金融saved arrays/gates、main execution、phase acceptanceの承認条件を満たさない。

## 証跡・測定

- task-5-full-mixed-independent-preflight.{py,log,json}: 原14反例、内側12.945127303秒（親時計は未測定=unknown）
- task-5-full-mixed-independent-physical-cap.{py,log}、-results.json、-parent.json: 補足11反例・physical teacher/全semantic cap検査
- task-5-full-mixed-independent-selector-cap-v2.{py,log,json} /source-unit-v2/: 元v53実cap失敗
- task-5-pilot-v54-independent-control-cap-v4.{py,log} /-results.json/-parent.json: source修復の独立projection検査
- v54/v55固定source独立記録と元失敗を保持

補足の内側11.125576689秒、親subprocess12.951818457秒。RNG・正式金融計算・全suiteなし。未知費用と失敗を成功へ置換しない。
