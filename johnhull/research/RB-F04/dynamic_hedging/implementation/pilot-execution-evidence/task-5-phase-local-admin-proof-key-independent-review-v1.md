# v3 行政引数と検算proof keyの独立確認

判定：固定v3の再利用境界だけを承認。正式pilot・正式予算・金融資格は承認していない。

- checkerのprivate関数1個だけが変更され、他80 runtimeファイルはv2とbyte一致。raw/source/物理file/parameters/field、初回完全検算、外側envelope/typedargs/cap、fresh contextの12実境界ASTは不変。
- proof keyから除くのはトップレベルの wall_cap_seconds と work_directory のみ。full operational resolved_arguments_sha256 は保持し、別の proof_arguments_sha256 を記録する。producer ID・operationによる所有者の区別は保持。
- 元保存fixture N16・Heston coarse・108節点で独立9/9 PASS。cold、driver引数差、fresh、別producerは各108節点、合計432節点を全N・全11sample/16block/covariance/SDE/cache検算した。数値の比較は runner._same の許容誤差。
- 行政2項目だけの差／両項目欠落はSDE0のhitで、full operational SHAの差とproof SHAの一致を実確認。seed差と実parameters変更は拒否。driver resolved args差は非reuseで全108再検算。formalのdriver引数監査は外側の既存境界であり、このhelperだけの確認をformal入力承認にしない。
- source81と元fixtureの前後SHAは不変。別operation/domainの所有者分離、失敗/unknown/capのordinary経路、activation guardは不変ASTで確認し、元v2の18probe・decision・失敗・資源を保持。今回genuine formal domain選別の金融資格は実行していない。

## 固定と費用

canonical runner._digest(source)：1cc16cf7fe567f7a825fe26d504e5bcf35d87d46a09034a2492017f6b5b6f067
native runner.payload_digest(source)：be858ced6b6b9befa0148a28168a063da735396cb88a7585dea94ea69fa75532

成功実時計14.799966s、inclusive CPU153.559514s、peak RSS763,162,624B。初回review失敗4.816448s/CPU38.734158s/RSS737,046,528Bも保存。全108のsaved検算後、reviewerが統計配列を含むdescriptorを11個ちょうどと誤認してassertしたためで、source欠陥ではない。最終runでは必要11sampleの存在と全元N16を確認した。2回合計wall19.616414s/CPU192.293672s、実saved検算540節点。静的準備の関数名誤記2件とshell開始前のtransport構文誤記も原記録と訂正を保持し、未測定準備費用・receipt尾部はunknown。

教師生成・新RNG・CF/PDE/solver生成0。production/source/tests/docs/Git/CASを変更していない。この小N測定をwholephase速度・金融精度・ETAの保証へ投影しない。

主要証跡：同prefixの decision-v1.json、expense-v1.json、observation-v2/results.json、static-v3.json。
