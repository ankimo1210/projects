# 次のfullmixed priorの最小gap（契約照合 v2、2026-10-10）

**root configの欠落を埋める作業と、外側storage停止を金融case/A capへ写すsource拡張は別。後者は現DESIGNの必須条件ではない。正式lock、全容量、金融qualificationは今回承認しない。** 元3,138jobs／121cases／51obligations／20teacher／10driver／全N・threshold・seed・失敗を保持する。

| 次の変更 | 現状・最小更新 |
|---|---|
| 全jobのprior/config | budget3,138件欠落、expanded_bytes3,138件None、rate_source未設定。lock_job_graphへ全IDのreviewed_budgets（正wall、planned_before_attempt、review SHA）、正しいchunk byte/work粒度と実測又は独立推計、4追加date教師の全4N枝を渡す。controlsの原{}とM4/M5実測deltaを区別し、source81 canonical408f2bc2…・input/historyを固定する。 |
| genuine capとA投影 | 全121/51のcap_optionsが空。元case/attemptを変えない事前wall cap option、実親job/limit/budget decision digestとexpense aliasを記入。v3の実祖先cap_scopeは維持。source例外は欠陥、独立jobは独立、数値未実行は元N/unknownとして保持する。 |
| 10現行external費用 | cold_imports/source_registry/code_review/math_review/pilot_review/serialization/saved_check/CAS_primary/CAS_mirror/domain_selectionの実clockと親scopeを結合。inclusive親・共有10driver・旧M2–M7・旧3capsは二重加算せず、checkpoint後の保存/レビュー/CAS費用は別receipt。未測定Noneは0にしない。 |
| 全phaseの運用上限 | rootがwork/cost行政cap、volume別reserve/staging/履歴、実空き監視のperiod/停止猶予、wall/RSS上限と外側receiptを決める。最大N候補の進行中測定後に記入し、追加計測案は増やさない。物理推計の幅・適用範囲・unknownを明示する。 |

**原契約の要求**：DESIGN.md:384は「rootが正式planでphaseのwork/cost capを固定する」。:390は「各次段階の予定path-step/保存byte/実測費用を先に記録する」とchunk256MiB・job/child 1e9分割を要求する。DESIGN・元実装plan・validate_locked_plan:3845–3973に、全phase whole-storage cap又は圧縮後物理保証上界の必須規定はない。予定byteは真の対象chunk粒度で記録し、推計を実測と混同しない。implementation/PROGRESSIVE_TEACHER_PLAN.md:49とPILOT_BUDGET_MEASUREMENTS.md:83のwhole-storage残課題は旧encoderの容量問題の診断であり、元DESIGNに新条件を加えたものとして扱わない。

**sourceを保つ運用境界**：外側の実free-space/wall/RSS監視は行政試行の安全停止・費用/partial保存に使える。ただし現runnerは返却後の実wall capとworker soft deadline、check_job_envelope:775–782もwallだけを認証する。外側storage/RSS/phase停止をA cap PASSへ写す契約はない。途中killで未完row/checkpointが残ればreadiness未閉鎖として保存する。監視周期中の増加量・staging量が未知なら、ディスク枯渇を必ず防ぐ保証にもせず、OSError/sourcefaultと実監視capの因果・順序不明を分離する。受入可能な実wall cap optionsを使って全原義務を閉じる方法は現契約にある。whole-storage中断で同じ受入closureを得たい場合だけ、別の最小source契約変更・TDD・独立reviewが必要になる。

**容量の読み方**：353,606,441,728 Bは論理配列の部分下限、364,185,768,816 Bも限定配列小計。圧縮後corpus Tの下限/上界ではなく、C/F不足をこの値で確定しない。各volumeの実空き・T推計・metadata/他job/旧失敗・staging/restore・二つの独立copyを別計上し、C/Fの空きを合算しない。N1024/syntheticの圧縮率を最大Nへ保証しない。

**完成の意味**：DESIGN:13–20は全rosterの「実行又は理由付き失敗」とunknown/不支持/失敗を成果に認める。NN勝利や全case金融qualifiedはv1成果の条件ではない。ただし:230/:384は精度未達ならstrict sourcefreeze前revisionへ戻す。承認済み実装の根拠PREFREEZE_REVISION.md:15–18/:20は、別readinessでunknown/not-qualifiedとresearch N32768を保持できるが、required attempt未完/source defect/integrity未確認を拒否する。全main/fresh/CAS/3図/notebook/独立review/受入は依然必要（同:9、DESIGN:15–18/:349–353、元plan Task6/7:253–266）。資源停止だけのnegative feasibilityやtinyをプロジェクト完了にはしない。

前v1の詳細counts・M2–M7実費整理を再利用。今回は元契約のread-only照合とDメモのみ。金融計算・solver/RNG/SDE・source/docs/tests/Git/CAS変更なし。
