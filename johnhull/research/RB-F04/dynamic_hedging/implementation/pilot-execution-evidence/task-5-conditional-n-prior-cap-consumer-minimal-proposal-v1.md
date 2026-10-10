# Conditional N prior-cap consumer 最小修正案
2026-10-10。**提案のみ。source/金融実行なし、実装はrootの実測終了通知後。**

## 結論・現契約

check_pilot.py:4023のoption選択条件へ「cap以外のplanが具体化baseと一致」を加える。親IDだけで先頭optionを選ぶため、同親のN1024枝が先にあると、正しいN4096枝も現行4032–4034で拒否される。元N候補1024/4096/16384/65536、conditional template、teacher producer/目的/元全roster、全実親capとinclusive費用は維持する。

concrete_original_n_plan:3248–3307は元templateのhashと実selectorのhashを付ける。しかし正式caller:4240–4247は既に selector_raw_sha256 をpopし、row.conditional_selection_bindingへ移す。未来の実hashをprior decisionへ予告する設計は不要。事前immutable枝は deepcopy(template) に original_n=N と prior_template_sha256=input_identity(template) を付け、元original_n_sourceを維持したもの。実selector hash/producer IDはchecked jobsから得る結果証跡。元templateを実Nへ書き換えて固定しない。

## 変更の範囲

4023の next は、元cap_options列の順序を保ち、(a) parent_job_idが元cap_parent_job_ids集合に属す、(b) option.planとbase_planのcapを除く全欄が一致、の両方を満たす最初の枝を取る。4024以降の実親failed_at_declared_cap、metric/limit、planned_before_attempt、decision/planSHA検査はそのまま残す。不一致・欠落に0/固定N/future SHA補完はしない。

plural親は1098–1144で元planned_jobs順に集め、元scope unionと全parent_cap_bindingsを確認している。選択処理へglobal「唯一親/唯一option」を新設しない。複数の真の親が互換枝を持っていても、既存option列における親相対順・最初の互換枝を保持し、全親bindingを4063–4068の証跡へ残す。同じ親の他N枝を理由に早期失敗しない。新しく親の並替え・費用scopeの集約はしない。

alias:4071は選択された実親expenseへの参照、全raw expense/all-parent bindingは既存投影に残す。実driver/shared/inclusive原費用を減算・再加算しない。cap値・予算審査hashの不一致で別枝へ逃げず、既存検査で拒否する。

## execution側への波及

_dynamic_hedging_execution.py:_review:746–764は、selector hashを含まない静的具体化枝（template hash/元source/N/cap）のplanSHAをそのまま検算できる。decisionのbudget_review_sha256結合も不変。rowの実conditional_selection_bindingは元per-row decision recordSHA/最終pilot digestに結合される。ここやconcrete_original_n_plan/公開APIの変更は不要。正規化candidateの4N recipeは事前に同じ静的option/decision digestを構成できるが、pending reviewをapprovedにせず、immutable予算固定後にだけ使用する。

## 最小TDD・独立確認（後続タスク）

1. 同じ実親の4N枝を置き、各原Nが正しい枝を選ぶ。非該当N枝を先頭に置く/4N内の順を反転しても値・template・decisionSHA一致。
2. N枝なし、未知/縮小N、template/source/producer/expense ID改変を拒否。実selector改変は既存checked-source境界で拒否し、未来selector SHAをprior planへ混入した枝も不一致拒否。
3. 正しいN枝でも親status/metric/limit、cap計画時刻、decision digest/planSHA改変を従来どおり拒否。固定N・uncapped既存経路は不変。
4. 複数actual親＋同親4Nを許し、既存親相対順の選択と全parent bindings/原費用を保持。同親以外の無関係capでは閉じない。
5. 正式callerがstatic prior planと実selector row証跡を分け、既存execution._reviewで承認済静的planSHAが通る正例を確認。未来hashの事前補完を許すテストは作らない。

metadataだけのscoped tests、関連既存projection/cap tests、ruffで検証し、独立reviewへ固定。金融RNG/SDE/CF/PDE・全suite・dtype/refactor/公開API変更は不要。source closureはcheckerのbytesのみ更新、既存実81file closureを再固定する（countの推測やfinance承認への拡大なし）。

根拠: task-5-fullmixed-prior-budget-independent-contract-gap-v2-review.md、v53 authorの静的4N recipe案。現在はcap候補/decisionとも未承認で、formal lock/phase false。

読取前後source SHA不変:

- johnhull/research/RB-F04/dynamic_hedging/check_pilot.py: a37626ff56e6ae74e08d6841c66ca9ec5712596d491930e623620d35607bce5b
- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_execution.py: fad2c73a27b8314b9cdfa5db8505fb56c382b4eab79ce4224aa475b450223b3e
