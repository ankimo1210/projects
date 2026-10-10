# Phase内の不変検算結果再利用：独立のtamper / retention補足

## 判断と対象

**条件付きで最小変更は可能。未実装・未検証・正式承認なし。**
まず同一実行phaseで繰り返し呼ばれる **teacher_gridのsaved算術結果** に限定する。
既に全original NのSDE replay・11 sample fields・16 blocks・covariance・cache比較を
終えたbounded結果を、その同一不変入力について共有する。
SHAは不変証跡との同一性を結ぶ。価格・Greekの正しさをSHAだけで認定しない。

読取時source81 identityは `dc7631fe73a457cd995d109aa693be9401b266410b9f53aa4e2d51e59f56d39c`、全81実byteは候補identityと `True`。
検討は現在のprivate境界に限定し、ContextVar/新公開API/新必須gateを要求しない。

## 既存境界と最小配置候補

- `check_pilot.py:4403–4469` の毎job envelope、原inputs、dependency、
  `check_resolved_job_arguments:787–956` のtypedargs再結合は **memoの外側** に残す。
  別producer、driver除去、conditioned N、Q必須入力等を先に検知する。
- `calculate_teacher_candidate_gate:3860–3875` は毎stageでrisk producer/geometryを検査後、
  同じteacher_gridを `_raw_job_check` → `check_teacher_grid_record` で再検算する。
  ここでprivate contextにphase-local memoを渡すのが限定候補。
- teacher_gridの初回は `check_teacher_grid_record:1198–1283` の全roster/物理node読取・
  binding・全N SDE/labels・cache再構築まで実行。成功してreturned結果ができてから登録。
  cache=None、failed/capped/partial、例外中の未完成結果は初回の通常処理を維持し、
  今回の最小memo対象から除外する。unknownをready/qualifiedへ書き換えない。
- `run_pilot.py:3976` の各fresh実行、`check_pilot:4777` の各保存検算/独立review/
  CAS復元で **新しい空memo**。再開は新phaseとして空にする。
  module-global/persisted/CAS-export memoは不可。rootをまたぐ再利用はしない。
- 既存 `teacher_activation_decision:3794` の(key=gate ID, raw, args) cacheは
  外部node/driverの後続物理変更をkeyに含まない。新memoをここで早期returnさせるだけでは
  不十分。activation/selectionが候補gateを再計算する入り口でも、teacher検算結果を
  使用する前の物理/入力再結合を維持する必要がある。

## hit前に毎回必要な結合とinvalidate条件

| 境界 | 不変の条件・変更時の処理 |
|---|---|
| caller / producer | 原job ID、operation、stage/evidence producer IDs、plan binding、scope/目的を保持。別producerやpurposeを同じseedだけで同一扱いしない |
| typed inputs / resolved args | 既存のinput_identityでparameters・実LocalVarianceGrid（times/z_nodes/values/parameters/wing_boundaries/support_mask）・全args・原inputs/driverを現在値から再結合 |
| in-memory raw | 原grid raw、axes/roster/N/seed/thresholds/date/state、driver descriptor、restart/cache/status/failure/unknown等を現在値でcontent fingerprint。id(obj)、readonly flag、旧digestだけでは不可 |
| 外部node | 原pathを現artifact_contextでrebasing。全nodeのroot/全packの実物理byteとdeclared raw_binding/legacy raw_sha256、source-bound recipeを再照合。追加/欠落pack、改変receiptも拒否 |
| 外部driver | 全declared driver chunkの実物理byte/coverage、normal binding、seed/purpose/stream/global-prefix/date/slice/原Nを再照合。directory文字列/保存されたdigestだけでは不可 |
| current source | 旧prior文字列だけでなく現在の実transitive source bytes＋checker/recipe identityを結合。変更したsourceで古い算術結果を再利用しない |
| context | phase固有の所有context、original/restored rootの現在実解決先。別fresh/review/restoreでmemoを共有しない。portable reportにはruntime rootを保存しない |
| mutable memo result | callerが返却後にstatus/SE/cache/coverageを変えても次callerが信じない。memo内部は独立の小bounded copy、返却時も小copy等でaliasを切る |

原raw/argsの変更はkey missにして通常の全算術を実行し、既存の比較/入力検証が拒否する。
物理byte/declared binding/source不一致は既存のreader/binding検査で拒否し、
古いPASSを返さない。mtime/sizeだけの検査は同サイズ改変を見逃すため十分ではない。

in-process fingerprintで現在の派生sampleを識別する場合も用途はmutation検知のみ。
recipe nodeの跨環境金融照合へ再構成float SHAを導入しない。物理receipt bindingと
初回全N許容誤差比較の分担を維持する。hit前後に物理/入力が変化し得る経路なら、
検算中と同様にbefore/after不変を確認できないhitを承認しない。
元codeが検証するQ入力・cash・risk producerのチェックまでgeneric memoで飛ばす案は対象外。

## 最小tamperテスト観点（将来実装時のみ）

新金融生成や全suiteを加えず、既存小saved fixtureとscoped testsで以下を確認する。

1. 同context・同producer・同原inputsは初回全N処理を1回だけ行い、2回目も同bounded値/
   portable referenceを返す。fresh/default/独立review/restored rootはそれぞれ初回再検算。
2. 原raw/cache/axes/threshold/失敗mask/SEのin-memory mutation、parameters/field array/
   args mutationはmiss→既存検査。第一回から不正ならmemo未登録。
3. 最後node・最後driver chunk・同サイズ物理byte/receipt変更、extra/missing pack、
   別producer/同seed別purpose/driver除去はmemo hitで通過しない。
4. Qのparameters/surface/initial state/seed/call_cache/chunk入力欠落は、teacher memoが
   warmでも既存の必須拒否を維持。教師以外のチェックを丸ごとキャッシュしない。
5. 小bounded reportをcallerが改変しても次hitは汚染されず、全11 samplesやnormals/
   primitivesをmemoが保持しない。cap/NaN/unknown/未実行の原rosterが保持される。

## memory・実費

memoにはbounded node参照＋SE/status/count/coverageと既存小cache検算結果だけを保持。
全N×threshold label samples、SDE primitive/normal arrays、source raw rows/generator closures
を保持しない。full report mode/standalone defaultにこの再利用を暗黙適用しない。
grid raw自体とmemo resultをmutable aliasにせず、保持件数は元teacher producer数以内。
node失敗/unknownとcoverageは元通り小要約へ残し、report_modeを変えてgateを弱めない。

first calculationの実wall/CPUは元job/phaseの実inclusive intervalへ一度だけ含む。
hitの物理byte照合/hash/lookup/copyも実clockで費用を残す。first receiptへ参照して
同じ初回再計算費用をhitごとにduplicate expenseとして加算しない。
原history/失敗/capと全expense IDs/alias scopeを残し、zero expenseを発明しない。
hitでは将来の省略SDE時間を費用として計上せず、実際に使った検査時間を記録する。

**残る不確実性:** 毎hitの全node/driver物理読取・hash・小copyは未測定。
現physical_artifact_bindingはprotocol.read_artifactで各packを読取するため費用は0ではない。
SDE再計算削減は見込めるが、総606.881h外挿のどの部分まで削れるか・ETAはこの静的調査で
保証しない。stage全体/Q/全rawoperationのmemoへ一般化せず、source_completionの費用調査と
rootの次の限定source案で判断する。

## 読取scope

`- check_pilot.py: 952b8f89c930578db1f6531bd6e73ade947d7cfbef246cc8510d246a54ed6197
- run_pilot.py: 7c08929f4c17d70d4bff48911c10dec3e3949c690f003b24d74b98db5af4e0dc
- _teacher_storage.py: 6a1ea6e53ae46d048badf39974a25df250065c46e0ddb2f86f85661623c58cac`

金融/RNG/SDE/solver生成、tests、source/docs/Git/CAS変更なし。
D内本メモのみ。初回rgのPowerShell brace構文拒否、推測helper filename不在は
read-only検索の失敗であり、以後実import名 _teacher_storage.pyを確認した。
