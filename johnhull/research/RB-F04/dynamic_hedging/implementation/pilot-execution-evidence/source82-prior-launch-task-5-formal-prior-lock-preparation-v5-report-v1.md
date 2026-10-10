# 正式prior materializer v5候補

- 結果：D2-only候補を固定。新82源の検査と限定metadata 16件PASS。新resource prior、root承認、materialization、financial launchは未承認・未実行。
- materializer：task-5-formal-prior-lock-preparation-v5.py（47581B、SHA b505500d6c8c3601fd8e04e22d15a2beac41c9e3bae48bfcc7aee5c39236a83a）
- false候補：task-5-formal-prior-lock-preparation-pending-example-v5.json（6426995B、SHA c6f6d4f3ffeae5558f886c327ccc88bd5b1fb04e6ff292da83cab1685326a950）

## 保持した契約

旧D1の3138全予算行はJSON値完全一致。正規行digestは02da310d0bed91d6883171eed44cb22ae872cc6a2888837a5979755d9c68aee5。121 cases・51 obligations・原4N・65 thresholds・16blocks・全seed・573122cap options・2332 activation・原history/unknown/fault/costは旧候補/原recipeを使用し、変更していない。旧validate_budget_rows、cap_recipe_payload、全cap展開loopのAST一致を確認。worker/solver/RNG/Popen/import financeと実cap展開は0。

源は旧81→現82のhelper1追加＋check/run/reference3変更をfiles/protocol_sourceのSHAと唯一のhelper import edgeへ正規化し、他の全identity欄一致・現W2全82実bytes一致を要求。codec/stageの限定判断は各実schema・正確SHA・false budget/phase/resume scopeを確認する。旧source/prior/rawを新生成物として再ラベルしない。旧D1は読取のみ、出力は新D2直下のfresh directoryだけ。

## 再結合interface

- current plain75ac0db805e437af50fc101d6f82d1c9df26ff433897726b8800d107e72af29e / nativeef14264e5127ca5edbab5b642505fc7505589e351a8d64cba0b9387574cfb9c7
- approved_bindingsは18keysを維持。source_limited_decision_sha256をsource_limited_decisions_sha256へ置換、codec/stage実decision SHA集合のcanonical digestを使用。
- approval.independent_reviews.sourceは{codec: reference, stage: reference}。旧prior decision ef4…は歴史的根拠であり、新82 resource authorityには使用不可。
- sourceだけ再結合したexact cap recipe digestは83d0099dd31974d01d6f3fad202d669a92aa778242b7b13f76efc1b6b4aa96e1。予算値・順序は不変で、source identityの変更がdigestに反映される。
- 完全field/schema/SHA一覧はtask-5-formal-prior-lock-preparation-v5-interface-v1.json。

## 検査・失敗履歴

元v4は新82の源を結べずRED1件。最初の作者preflightではroot deltaの実field名を誤認して拒否され、旧script/失敗を保全した後、実fieldへ修正。限定probe初回10PASS/6FAILは、recipeの既存key(source_identity)誤認と、改変を正しく拒否した際のerror文字列照合誤り。源の修正は不要で、原probe/result/costを保全し最終16PASS（1.167166451s、CPU1.1671402s）。現82production/旧D1主要証跡は前後byte一致。最終receipt/記録tail費用はunknown。

## rootが次に行うこと・制限

新独立resource decisionは全3138行・exact573122 recipe・現源・本scriptを承認し、rootが新decision SHAだけを全budget.review_sha256へ結ぶ。新operational prior、actualroot approvalとfresh output pathを固定してから、既存APIでmetadata materialization。financial launchは別承認。false候補には古いreview SHAが歴史的placeholderとして残るため、そのまま使えない。

新codecの全量capacity/RSS/rateを認定していない。source限定2判断からbudget/launchへ自動昇格しない。既存producer/helper、金融5引数・cap照合、production・tests・docs・Git・CAS・旧partialは変更していない。
