# date_gate N修正後のresume契約（読取・D限定）

## 結論

**既存APIだけでは、新sourceへ直した後に旧69保存済job rawをそのまま継続できない。**
run_date_gate_jobの N→original_N が1行でもrun_pilot.pyの実source SHA、81file closure identity、plan source／planSHAが変わる。専用testの変更はそのtestがclosure外ならsource81へ加わらないが、runの1件だけで拒否は成立する。今回の読取ではnative実rawや金融を再実行していない。

## 拒否される具体的条件

|経路|既存条件／結果|
|---|---|
|旧lockedplan＋新code|run_pilot._locked_bindings 3563–3576: current transitive sourceとplan.sourceのpayload digest完全一致必須。`current transitive source differs from locked pilot source`|
|新sourceでrelockし既存nativeへresume|run4078–4092: native/plan、最新checkpoint.locked_planと新planの完全payload digest一致必須。`resume locked plan differs`／`resume previous phase plan differs`|
|69rowだけ新directoryへcopy|run4113–4123/check_job_envelope748–786: 各row.plan_sha256、source_sha256、input bindings、元budget/prediction、原clock/expenseが新planと一致必須。旧rowのままなら `stale resume job`／`job source/input mismatch`|
|旧code／旧planで普通にresume|70番の保存fault rowが `unclosed_source_or_solver_defect` ならrun4126でbreak。修正したdate_gateの再試行へ到達しない|
|monitor v2へ既存nativeを渡す|load_guard262–265はfresh native＋fresh receipts必須。run commandは --plan/--inputs/--outputのみで --resume無し。source guardは固定v3 inventory／limited8a／current1cc/beに限定|

source_rootだけ旧snapshotに指定して新codeを旧identity扱いする、旧row source/planSHAを新値へ書き換える、faultを削除／cap・completedへ改名する、旧checkpointや費用を上書きする方法は真正な由来を保持しない。

## 既存APIでできる最小手順

1. 旧native/plan、全69row、70番fault、checkpoint、source snapshot、monitor実receipt／unknown／phase・job・driver・history費用を不変保存する。
2. 1行修正＋意味ある実cache→date_gate→savedchecker回帰と独立source確認を固定する。
3. 新sourceの実closureへ、同じ元3138job／121case／51attempt／4N／typedinput／original financial controlsをrelockする。旧失敗の費用を新historyへ真正な原receipt参照で保持し、inclusive clockを重複加算しない。
4. 新source・新planに対応するreview/root prior／monitor rebindと別launch承認を固定し、**fresh run**へ進む。現monitor/materializer固定v2は新source未対応なので、そのまま通るとは扱わない。

これは既存実装に沿う手順だが、旧69計算結果の数値再利用はしない。原teacher driver／rawの履歴があっても、現在lock_job_graph（producer402–416）はsource/input/historyを固定するだけで、旧jobを別sourceからimportする契約を持たない。

**69rawを再利用して70番以降へ進むには、別途の最小private continuation/import機能が必要。** 元rowは旧source/旧plan/原物理receipt/時計のまま別generation由来として認証し、新phaseではoriginal ID/args/inputs/dependenciesの変化がdate_gateの修正だけであることを検査、70番faultを旧historyとして保持し原job再試行の新費用を別phaseへ記録する必要がある。現APIにこのmixed-source authorityはなく、resumeフラグだけで代用できない。このメモでは新schema・機能を実装／承認していない。

## 同一sourceでのordinary resume

元source81、元plan/input/tree、saved rowの予算・原expense・実clockが完全一致し、既存rowにsource/solver faultがない場合に限り、既存 CLI `--resume` は保存済statusを読み未保存jobを続行する。cacheはfresh invocationで検算し直し、既存phase履歴を保持する。今回のsource修正＋保存faultという2条件では、このordinary契約は成立しない。

読取対象: run_pilot.py run_date_gate_job2793–2834/_locked_bindings3563–3576/run4066–4458/main4461–4480、check_pilot.py check_job_envelope748–786/check_pilot5032–5058、D producer lock_job_graph402–416、固定monitor v2 load_guard199–269/run337–621。production/source/tests/Git/CASの変更、金融/Popen/RNGは0。
