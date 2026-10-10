# stage risk 引数binding修正 — 限定独立レビュー

**判定：source・metadata契約の最小修正として承認。金融合格、正式pilot/main起動、元priorの新source再認証、資源予算、phase受入は未承認。**

対象checkerは 2f5b3e1e…、専用testは 2d1f468f…。旧正式214件目のrawNone/unknownと費用・失敗履歴を受入へ昇格しない。

## 確認した境界

- 修正は check_teacher_stage_risk_sources の比較から wall_cap_seconds **1keyだけ**を分けるもの。金融5args（parameters/surface/dataset/caches/chunk_paths）と余分keysは比較に残る。
- 独立tiny probe **15項目PASS**。元5金融args＋actual capの正例、金融5key欠落、raw/stage側の余分key、原priorと違うcap（481・欠落・False・文字列）に合わせてresolvedSHAを書き直す反例、両側余分key＋自己整合SHA、envelope budget/planSHA改変を確認。
- 限定pytest **7 passed / 0.77 s**。金融5値の改変と、raw cap改変時の古い/自己整合resolvedSHAの両方を拒否。
- cap改変はstage比較単独では金融unknownのまま通る設計。正式 check_resolved_job_arguments が元jobのbudget capを含めて全actual argsを再束縛し拒否する。check_job_envelope は元budget/planを別途照合する。両関数はAST不変で、実check_pilot_records callerもraw check前に両方を実行する。
- 元N1024、65threshold、16blocks、NaN/unknownを保持。金融workerは構造fixtureのstub。SDE/RNG/solver、巨大NPZ/650MBcheckpoint、W1/native/CAS/Gitの操作なし。

## sourceと費用

実closure **82files/dynamic0**、全82actualbyte一致。変更はchecker **1path・1関数**のみ。canonical runner._digest=75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e、native payload_digest=ef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7。codec ac98536b… と前限定判断は不変。新sourceで旧正式runをresumeする承認ではない。

tiny probe 0.701573 s wall/0.700989 s CPU、限定pytest親1.040464 s wall/1.034788 s CPU。各tool外側wallは2.506112 s/2.305297 sであり内側費用へ加算しない。import・source読取・記録を含む全レビュー費用はunknown。全suiteと金融saved gate再計算は行っていない。

詳細は independent-stage-cap-binding-v1-results.json、independent-stage-cap-binding-scoped-pytest-v1-results.json。判定は independent-stage-cap-binding-v1-decision.json。
