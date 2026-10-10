# M6：原N1024四teacher classの実行準備
2026-10-10。D限定の準備。金融worker/RNG実行、source/tests/docs/Git編集、agent追加はしていない。

## 原job・仕事・候補行政上限
|class / 原job ID|seed|原node / threshold数|生成conditional遷移|保存driver SDE検算込み遷移下限|wall cap|
|---|---:|---:|---:|---:|---:|
|Heston-coarse / teacher:Heston:N1024:coarse:raw|138674072|108 / 33|46,006,272|92,012,544|300s|
|Heston-high / teacher:Heston:N1024:high:raw|138674072|156 / 65|66,453,504|132,907,008|300s|
|local-coarse / teacher:local:N1024:coarse:raw|1345225788|520 / 33|214,302,720|428,605,440|600s|
|local-high / teacher:local:N1024:high:raw|1345225788|1344 / 65|542,244,864|1,084,489,728|900s|

原Nは全て1024、dateは全12。Heston stateは9/13。localはt0 spot5×state5/7、後続11date×spot9/17×state5/7。thresholds/geometry/evaluation_domains=[None]×12を縮小しない。最大local-highの宣言保守aggregateは1,056,964,608 path-step、per-nodeは786,432、financial_child_count=1344。1e9をaggregate global capへ読み替えない。

個別RSS候補4GiB（親又は子各processのRSS、RLIMIT_ASではない）、直列実行。cap合計は2100秒＝35分で、runtime/ETAではない。別global capを追加しない。全4生成869,007,360遷移＋保存SDE869,007,360遷移にlabel/統計/write/read/cache/source検査費用が追加される。

## 依存と費用
- 原teacher-driver:Heston:N1024とteacher-driver:local:N1024を一回ずつ生成し、各modelのcoarse/high・全restartへ実保存bankを共用する。seed一致を理由にdriver=Noneへ置換しない。namespace=teacher、purpose=principal、teacher_reference=None、fine global calendar769点/768step/2factor、chunk256、原IID path IDs/16clustersを保持する。
- 各driver786,432 transitions、normals12,582,912B。独立phase parent receiptをbanks/modelへ保存し、owner class（各coarse）の外側cap/費用へinclusiveで含める。highは同receiptを参照し、all-costsでdriver実費を再加算しない。driver失敗はbank/partial/raw/receiptを保持し、後続をunknownで残す。
- actual typed経路は原graph arguments→_resolve→_job_identity→_dispatch。field-currentの原257×321 field/order1024/frequency_scale512/density_floor1e-10をmaterializeする。既存Heston/local raw call cachesはimmutable contextとして固定するがteacher argumentsの依存ではなく、CF/PDEを再実行しない。
- 実checker.check_teacher_grid_recordは各nodeで保存driverからteacher_primitivesを再計算してapprox照合し、labels/cacheも再構築する。このSDE費用は生成とは別に保持し、class capに含める。grid/checkで新RNGは禁止し、保存原driverだけを使う。
- 原全4nodeのprimitive/status・IDs・全16blocks/3covariance・2共有driverだけでも展開5,494,775,552B。その他raw/cache/重複/headers/receiptsは別。新codecの実compressed量、全worker rate、oracle/main費用は未知のまま。

## 準備ファイルと未承認位置
- task-5-current-full-teacher-measurement-v1.py：未承認では金融import前に拒否するparent/child。原四class/二driverを直列実行、全原obligationを保存、外側wall/RSSで実停止時にも部分raw/費用/unknownを保持。driver/write/read/grid/check各clock、resolved arguments SHAを実行時に記録する。
- task-5-current-full-teacher-initial-description-v1.json：原fullgraph3138jobs/121cases/51attempts、四jobの全node roster、元planned args SHAとmeasurement typed args SHA、変更key/rationale、原driver prefix/purpose・workを固定。
- task-5-current-full-teacher-budget-candidate-v1.json：**root_preapproved=false**。source_approval_status=pending_new_native_teacher_codec_actual_closure、source_bindings/source_identity_sha256/source_file_countは**None**。v56をformal currentとしない。source数81等を推測で固定しない。
- 出力はD/task-5-current-full-teacher-observation-root-m6-v1（未作成）だけ。work_directoryと候補wall_cap_secondsだけを追加し、元artifact/旧fullplan出力へ書かない。原4job+2driverの両typed SHAをpriorに明記し、resolved numeric dependency SHAは実保存driverの取得後・各金融dispatch前に実記録する。
- 26 immutable input files：original fullgraph/root+pack、prepared-v4/currentfield、producer-v3、既存M2/M3 raw cachesをbyte binding。原入力・既存CASを変更せず、追加CAS検査をしていない。

## 確認結果とrootの次工程
metadata-only verificationで原4job+2driverのplanned/measurement SHAがisolated actual canonical関数と一致し、変更は行政wall capとfresh D work_directoryのみ。node数/workを確認。candidate起動がfinance import/dispatch・出力作成前に拒否されることを確認。3準備PythonのruffとAST構文はPASS。金融worker/RNG/source module importは行っていない。

source codec・独立node physical receipt bindingの承認とactual closure固定後、rootが別immutable budgetでsource_bindings/source_identity/approvalを埋め、MemAvailable/actual freeを確認して実行する。元N65536/status付きI/O部品測定は先行別工程であり、このN1024四class計測の代用ではない。

予定command（未実行）：
    /home/kazumasa/projects/.venv/bin/python task-5-current-full-teacher-measurement-v1.py --budget task-5-current-full-teacher-budget-root-fixed-v1.json --output task-5-current-full-teacher-observation-root-m6-v1

実行source/current codecとのsignature・binding整合は当該承認時に再確認する。formal pilot/main/sourcefreeze/金融精度は未承認のまま。
