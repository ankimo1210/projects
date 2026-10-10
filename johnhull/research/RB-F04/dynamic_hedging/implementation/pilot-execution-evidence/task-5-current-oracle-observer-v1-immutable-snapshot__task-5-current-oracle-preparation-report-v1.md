# M7：原state00・N4096独立oracle二クラスの実測準備
2026-10-10。D限定。金融worker/RNG・CF/PDE・source/tests/docs/Git/CAS変更・追加agentは実施していない。正式pilot/main/金融精度は未承認。

## 原jobと仕事
|class|原fullgraph job ID|namespace/seed|元query/level/N|payoff生成遷移上限|別driver生成遷移|保守declared total|候補wall / RSS|
|---|---|---|---|---:|---:|---:|---|
|Heston|oracle:state00:Heston:referenceN4096|oracle / 3631740690|13 / 768・1536 / 4096|122,683,392|6,291,456|163,577,856|600s / 4GiB|
|local|oracle:state00:local:referenceN4096|oracle / 3631740690|13 / 768・1536 / 4096|122,683,392|6,291,456|163,577,856|600s / 4GiB|

元state00はdate0、S99.95、Q9.686255823501824、memory_sum/count=0。S bump0.02、Q bump1e-4、幅1・0.5・2、half-width選択index1、base＋各S/Q三幅±の全13 queriesを保持。原path ID4096・全16blocksを残す。先のfullgraph3138jobs/121cases/51attemptsからactual original job/typed argsを選択した。

per-financial-child path_steps=6,291,456、26 level/query children。aggregate1e9 capへの転用・原N/query縮小はしない。ここでは最大遷移の構造算術を記しただけで、拒否fitやcap時の実仕事をこの値へ補完しない。計測時は全native expense/fit/statusで実行・拒否・unknownを区別する。

候補600秒/classは未実測のgenuine oracleに対する行政上限、RSS4GiBは親又は子各processのRSS。RLIMIT_ASではない。合計1200秒はruntime/ETAの予測ではない。新しい別global capは追加しない。oracle/main金融rate・physical compressed量はNoneのまま。

## actual typed dispatchと依存
原graph arguments → run_pilot._resolve → _job_identity → _dispatch("oracle") → reference_methods.quote_positions_oracle。oracle signatureにはwork_directoryがない。原argsの全金融入力/seedを残し、候補wall_cap_secondsだけを追加する。元planned args SHAとmeasurement typed SHAはdescription/priorに保存。外側parent開始からのabsolute deadline_wallは実行時に追加し、resolved SHAと実値をdispatch前に保存する。observer出力はD内fresh task-5-current-oracle-observation-root-m7-v1のみで、元fullplan/原artifactに書かない。

共通field-currentは257×321、order1024/frequency_scale512/density_floor1e-10の元v4 field。state00の独立表は原job independent-table:state00:Heston/local。その全state roster/7spot/date0/現在fieldの物理byte signatureを対応付けた。H表3×1×7×33、local表4×1×7×7。

**既存M4/M5 rawを再利用する候補には、明示的なroot承認が必要**。元graphのtable controls={}に対し、M4/M5は別事前予算で space2401/time1920/halfwidth1.8/upper250を指定した。Hはbase/cutoff/quadrature、localはbase/space/time/domain(width2.25)を保存済み。table内controlsを引き継ぐbaseline direct selected-call refinementもM7費用に含める。元controls={}がそのまま測定済み、または正式solver controlsがlock済みとは扱わない。

既存M4費用5.425978319秒/CPU5.209234303秒、M5費用35.527945750秒/CPU36.236620963秒は原parent receiptsと共にhistoryへ固定。M7の新費用に再加算せず、このCF/PDE表のrateをoracleのrateへ転用しない。新codec/source closureの承認・実際のsource count/SHAはpending。古いv56や推測81をformal currentへ固定しない。

## 原独立乱数の目的と保存検算の限界
各classは元独立oracle parent seed3631740690を保持。chunk256×16、fine1536、2factor。原mappingは SeedSequence[parent_seed,7426,chunk_index]、fineからadjacent pairをcoarsenする。teacher principal/referenceのdriver/bankへ置換しない。oracleの元argsはnormalsを含まず、その元reserved_local_rng経路を使う。H/localは同一元seedでもそれぞれ原sourceの生成費用を実記録し、同じseedを理由に未実行扱いや費用消去をしない。

fine chunk6,291,456B、native max live paired driver12,582,912B、全fine conceptual100,663,296B。原oracleはnormal配列を保存せず、16driver_mapにfine normal hashes/child seed/path range/shape/clockを返す。driver expenseはnative expensesにも含まれるためdriver_mapのclockを二重加算しない。別保存bankやSDE replayを実施したとは主張しない。

check_pilot.check_oracle_recordは全13 raw payoffからprice/S・Q Greeks、3 widths、両scheme768/1536、全16blocks/covarianceを許容誤差で再計算する**保存算術検査**。独立path生成とfull common-domain call fitは原checkerがunverifiedとして残す。checker時はRNG/financial generator/CF・PDE関数を禁止する候補。金融資格はunknownであり、このcomponent計測だけで正式oracle合格としない。

## 保管・停止・費用
- 最初の新solver/RNGより前に、全2×13×4096 NaN・原status・first_failure/date・path/cluster IDs・全query roster・source/dependency receiptを別immutable initial-original-obligationへ保存。
- 原返却rawの全payoff、raw/paired/width/statistics、fit/refinement/status/failure/unknown、全expense/driver mapsをactual-original-oracleへ**checker前**に保存。削除・有限subsetへの置換なし。
- 外側class capはsource検査/import、原graph/field/table read、初期write、13 re-fit/direct refinement/RNG全生成、返却write/read、saved checker/write/readとsource stableを含む。全stage実clockとparent inclusive wall/CPU/peakRSSを保存。
- actual parent wall/RSS stop、原source declared cap、source/solver fault、child evidence不足は別判定。exit0だけで完了にしない。initial保存・返却raw・全expense/map・saved checker・source stableのcheckpointも必要。
- hard killでworker内の未保存partial finite arraysは観測不能と記録する。原full NaN obligationと利用できるraw/log/actual costを保持し、未観測数値や費用をゼロ補完しない。外側cap超過とsource defectを相互に読み替えない。
- payoffだけ851,968B、status212,992B、first failure851,968Bは原両schemeの展開下限。native duplicate aliases・table/CF/PDE diagnostics・stats・headers・原raw/cap storageは別であり、actual physical expanded/圧縮量は未実測。一般serializer/CASの変更・再検査は行っていない。

## 準備成果・確認
task-5-current-oracle-measurement-v1.py、preparation-v1.py、initial-description-v1.json、budget-candidate-v1.json、preparation-verification-v1.py/jsonを保存。36 immutable input file bindings（原fullgraph/prepared/currentfield・両表raw/receipts/元prior等）とsource読取snapshotを記録。source読取snapshotは承認ではない。

元2job/依存argsのSHAはisolated actual canonical関数と一致。追加worker keyは行政wall capだけ、runtime deadlineの許可signature、原13queries・4096・768/1536とworkを確認。候補guardは金融module import/dispatch/output作成前に拒否。純行政decisionの8 probesとAST/ruffはPASS。金融コードのruntime dispatch・保存checkerは未実行。

## rootが実行前に固定するもの
1. 新codec/physical node receipt bindingの独立承認とactual source closure/SHA/count。
2. 元controls={}とM4/M5実controlsの差を認めたcomponent用dependency reuse承認。これが無い場合はこの候補を実行不可。正式solver controlsのlockは別工程。
3. 別immutable root prior（budgetfalse→true、source/dependency approvalを具体的証跡で固定）、実MemAvailable/RSS/空き。
4. source承認後のactual signature/binding整合確認。追加金融精度/driver-generation検証が必要なら、この保存算術checkerとは別にscope/予算を固定する。

未実行command：
    /home/kazumasa/projects/.venv/bin/python task-5-current-oracle-measurement-v1.py --budget task-5-current-oracle-budget-root-fixed-v1.json --output task-5-current-oracle-observation-root-m7-v1
