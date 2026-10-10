# Native saved-check readiness: read-only limits

現source82と既承認の新plan/input結合は保持されています。whole native checkerの容量・金融資格は未確認です。live session49482を停止・読取り・check起動していません。

1. **入力contextは原typed inputsをinputsキーへ包装する。** check_pilot.py:4699はinputsを必須とし、4677–4686でinputs.parametersを原入力と照合して設定する。789–823は原plan/actual依存rawからresolved argumentsを再構築する。CLI5081–5084はunpack_inputs(context)だけで包装を自動追加しない。単に原inputs容器を--contextへ渡すとこの契約を満たさない。
2. **現source rootとplanを照合する。** 4655–4662はsaved locked planとexpected_planのdigestを比較。4971–4978は原inputs/expected_plan/source_rootで_locked_bindingsを実行。current82 sourceの直接SHAと新receipt/独立ac8判断は再確認した。これらはwholecheckerの実行完了・容量・金融PASSを意味しない。
3. **全jobをhydrateして保持する。** 5039–5065は最新checkpointを読み、全job artifactを順次decodeし、payload digestを確認してhydratedリストへ蓄積する。5061でsnapshot.jobsをその全リストへ交換する。node単位逐次読取りだけのAPIではない。
4. **最終返却にも全rawが残る。** 5017はraw_checks、5028はraw_snapshotを返す。圧縮保存やunique-DAG物理容量はdecode後のlogical object/array copiesや最終result serializationのRSS保証にならない。全hydrate＋check＋返却＋writer/read/最終receiptまでの実費が将来のscope。
5. **teacher boundedとmemoはwholejob容量保証ではない。** 2854–2859はbounded teacher報告。1166–1185は完全検算後label descriptorsへ置換するが、非teacher job raw/全snapshotは省略しない。2756–2770と4668–4675でinvocationごとにfresh memoを作るため、以前の実検算proofをdeserializeしてfresh checker資格にはしない。
6. **saved-onlyは軽いmetadata checkではない。** 130–156ではsaved normalから全originalNのteacher_primitivesを再計算、158でlabel再計算。quotes637–691は保存quadrature/PDE grid等からpriceを再構築し、state1432とwrapped2035/2053も原演算を検算する。全SDE/labels/stat/cov/blockと金融再計算費用を含む。今のreadinessではどれも実行していない。
7. **既往M6/maxnode判断は限定部品。** M6保存再検算はN1024四class/source81 bounded観測。最大N65536はmother1344節点のうち1節点でwhole mother job未完、financial unknown。現source82の全native job hydrationやwholechecker/全返却RAMを認証しない。元3caps・失敗・費用・unknownは保持。
8. **observer候補の審査範囲。** live/terminal原receipt不足・source/plan/input/context不一致を重いdecode/worker起動より前に拒否するpure境界だけを点検する。実terminal後のroot actual saved-checkは別。元30days、16GiB maximum individual physicalRSS（ASではない）、3volume各10GiB、1sを維持し、外側wall/parent+childCPU/peak/receipt-tail未知を分離する。行政停止はpartial_unclosed、金融A capPASSへ投影しない。closedとqualifiedは4987–4996で別、earlier solver/RNG/独立実行/financial approval/main freezeは5030–5035でunverified。

参照:
- R2/check_pilot.py SHA2f5b3e1e8a9b318521e143bbd24f0a29138e4136f7942e063039686a834ea30e
- 実保存metadata独立判断 ac8a0176c68ea3b6610a665b22c953af94df2358eb260d5ccae8808d676d90b7
- 実manifest00b8101210d492111c0dec555b2a3653f2878c15a213db9bee6a948ef466a8bd / plan artifact942f29bae2314432ef78cf32e7bb6b13c8b67281015814574034ea22b6601f57
- D1/task-5-M6-saved-recheck-independent-v1-decision.json
- D1/task-5-maximum-original-node-saved-root-component-review-v1.json

finance/RNG/SDE/solver/Popen/巨大checkpoint decode/production/source/CAS/Git変更:0。source82/readiness hash照合direct wallとCPUは末尾。全レビュー・書込末尾費用unknown。

小metadata/source照合direct wall0.003618s / CPU0.003598s（書込み以前、全レビュー費用ではない）。
