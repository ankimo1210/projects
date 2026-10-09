# RB-F05 pilotコード事前レビュー

## 判定・scope

**IID教師・選択・独立数値再生の数学を支持。費用schemaのImportantは修正後の狭い再検査で解消。残Important 0。正式pilot・N採用・main・性能は未承認。**

2026-10-09。read-only。対象pilot.py/test_short_maturity_pilot.py、固定spec/planのpilot契約。未完runnerは対象外。repository source/tests/docs/Gitを変更していない。/tmpにsmokeと検算だけ保存した。

- pilot source SHA256: 0a739e9a783b5cfa797c39dfedc9e01dc87fe421afc65a0becd6ad983e83b965
- test SHA256: 65624a4d1b6f098ae506d56c6956240d5543b6356379e8f19e2349707ec8af8f
- 独立欠陥probeと数式検算source: fdedc54d8161812cf2e07266d16ccd129142dff51f0aca8d00dd5539e7068542
- 修正前target suite21PASS（独立実行1.76秒）、修正後はowner報告29PASS。smokeは2cases×1stream、prefix128/512、raw512。full pilotを生成していない。
- 証拠: /tmp/rbf05-pilot-code-review-probe.json、/tmp/rbf05-pilot-code-review-numerics.json。

## 確認した条件・数式

- full executionは6times×7distances×2event=84cases、3streams、4prefix [2^14,2^16,2^18,2^20]、独立raw N=65536。selectionはmaxNを1回生成しoriginal sorted indicesでnested prefixを復元。各Nを独立replicateと数えない。
- Λ>0:全N Poisson counts、nonzero countのnormal marksのみ。sample mean/covariance/SEの分母は全N。Λ0 selectionはanalytic_deterministic、observed MC count0、actual random draws0。予約Nを観測件数にしない。rawは別count/mark/Brownian full-N streamで、その費用は別。
- 独立smoke再生でcounts/marks/Brownianを予約seedから直接再生成して全配列一致。selection zeroblock+activeを全512行へ復元しprefix128/512のmeanとddof1 SEが一致。raw 6method mean/cov/SEをcore helperを使わず式から再計算し、mean差最大4.33e-15。noevent selection0 draws、event active9で521 drawsを確認した。
- PWDelta、LRDelta、LRPWGamma、LR2Gammaはphysical Sの微分に対する既知のscore式と一致。naive Gamma0はnegative control。LR分母はsqrt(W)/Wで、carry tauとは分離されている。
- 選択は全84×3でrare active>=100、price SE<=.002、Delta SE<=.0005、SE(KGamma)<=.01 max(1,|KGamma|)、mean-reference<=6SE+tolを要求。min ready Nのみ返す。reference precision failure/不完全roster/smokeは採用しない。人工fixtureでactive99、SE上限超過、reference不一致はいずれもreadyFalse。
- CDF普通Poisson/core/density/Mertonの比較、n>nmaxのtilted tail bound、quadrature error estimate、eps/4再計算差は別々のbudget。Gamma primaryはboundary density、LR2Gammaの相殺誤差は別witness。LRwitness支持やrawの6SE agreementをprecision達成・coverage証明として扱わない。
- rawとCRNには原始N/normal arraysを保存し、CRNは同じpathsで3幅有限差分を作る。finite-h target/biasはtrue Gammaと区別。no crossingかつnonzero targetはdiagnostic_inconclusive。raw unsupportedは捨てずselectionを直接誘導しない。
- checkerは保存primitiveから再計算し、reserved seeds/source/protocol/case/stream/prefix roster、原draw費用、各moments、finite-h targets、failure状態を照合。default_rngを禁止してnumerical replay PASS、smoke freeze拒否を独立確認。保存値が整合するだけではseed生成provenanceの再確認にならないため、実full pilotレビューでfresh seed再生も行う。

## Important（解消済み）: 費用を丸ごと削除してもcheckerが受理した

[_check_expenses](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/pilot.py:149)は**存在する**timersからexpected費用を作り、[check_record](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/pilot.py:706)はpresent秒がfinite/nonnegativeかだけを検査する。

smoke recordを次のように同時変更した:
- record.timings={}
- 各case.reference_timings={}
- 各stream.timings={}
- record.expenses=[]

結果: numerical_replay_passed=True、元の数値判定と同じ。cost_scopeを「全てfree」に変えても受理。個別費用1列だけのtamper testは落ちるが、双方のreceiptを削除する改竄は検出できない。コスト無しの全pipeline証拠を正当扱いする欠陥。

**修正方向:** status別に必須keyset（正常case reference6timer、reference failure1timer、clock failure秒、実行stream4timer、root setup/serialization/run/scope）と固定cost_scope/scopeを検査し、その後expense IDs/カテゴリ/methodsを一対一照合する。timer値そのものをfresh walltimeと比較する必要はない。正常/各failure/omit/extra-keyのRED→GREENが必要。

## Minor・解釈の限界

1. raw log varianceは1/N Σ(logreturn−samplemean)^2。期待値は(N−1)/N×population varianceで、不偏varianceではない。保存SEはsamplemeanを含む中心化値のplug-in近似で、exact IID mean SEとは異なる。Nraw65536では小さいが、exact/unbiased/coverageと呼ばない。finite-N target補正またはasymptotic診断の注記を推奨。
2. 1分/noevent/S=100exp(.05)で3幅FD Gamma=[1.88e-11,1.01e-9,6.33e-9]、真Gamma≈0、tol1e-9。最小hのnumeric有限幅targetに丸めが混じる。finite_h_biasには実有限幅効果と価格差分丸めが混在し得る。no-crossing unknownを残し、raw CRN unsupportedだけから手法欠陥を断定しない。primary N選択はこのdiagを使わない。
3. successful clock/packing等はindividual receiptに分離されずAPI run wallへ含まれる。run_sはNPZ＋最初JSON writeまで、最後のaccounting JSON writeは明示除外。setup/serialization/runとexpense合計を重複加算しない。CLI/import/process全coldや未計測startupは別記録が必要。
4. raw countのint dtypeやsource metadataの固定契約はproto/checker guardで確認する。JSONのready/passed flagでは金融検証を認定しない。reference/pilot共同研究費用の各methodへの1回課金はrunnerの固定cold scopeを後でレビューする。

## 次段

必須費用schemaはlatest sourceで解消を確認。正式full84×3の数値・全seed・稀イベント・全prefix・実費用・digestを独立レビューしてからfreezeする。full pilotのN採用/teacher acceptance、6fit、NN速度優位、Bates/PIDE/rough/市場精度は本レビューで承認していない。

## 修正確認追記

ownerのmandatory root/status別reference/stream timer keyset、fixed COST_SCOPE/RUN_SCOPE、全expense一対一照合を読み、既存smoke receiptを直接再利用した。正常receiptは通り、全費用削除は「complete root timing roster required」、scope改変は「measured cost scope changed」で拒否。新RNG/新pilotは生成していない。source 0a739e9a783b5cfa797c39dfedc9e01dc87fe421afc65a0becd6ad983e83b965。owner報告29tests PASSは作者検証として区別し、独立確認はこの2改竄fixtureとsource経路。証拠 /tmp/rbf05-pilot-cost-fix-verification.json。rawvariance近似・FD丸め・全cold費用・未実施fullpilotの限界は維持する。
