# 次段階研究案 v2 再レビュー — 2026-10-09

多曲線risk/P&Lと増分XVA＋IM・資本の両v2草稿を、計画段階へ進める内容として承認する。原Important2件は解決。Critical0 / Important0 / Minor0。正式DESIGN・source実装・pilot/main・study acceptanceの承認ではない。

初回レビューをjohnhull-next-design-review.md/.jsonへ保存した後、original→v2差分の2件だけ再確認した。原2草稿のSHA256は初回レビューと一致し、不変。repo/source/Git/full-suiteに変更・実行はない。

I1 解決（rates v2 §8、144–154行）: exact roll/forecast Vr、実fixing Vf、新calibration表現Vg、市場quotes V1を分離した四項bridgeはV1−V0+Cfへ厳密にtelescopingする。market TaylorはVg/fixing-conditioned qgをcenterとし、q1=qgでも残り得るVg−Vfを表現移行欄へ置く。primary logDF kernelはabsolute旧knots＋t1 anchorによる再現を検査し、一般のnew-tenor表現差、missing horizon、rank不足を隠さない。原zero-move反例への最小修正として十分。

I2 解決（XVA v2 §5、90行）: main(c)は同一legal setの異満期hedgeとなった。同じhedgeを別non-nettable setへ置く対照はvalidation rosterへ移り、既存IM不変＋nonnegative new-set IMを明記する。IMのrisk offsetとfunding/capital aggregateを区別し、主32cellsは計画候補のまま。この修正は初回確認したMGN20.14とdraft自身のset別IM規約に整合する。

新たな具体的な数学/金融riskはこの修正差分から見つからなかった。実装前のformal planでは、reset/publication条件を含む12quote rank/coverage、actual Gaussian conditioning dimension、closeout/IM返還/資金・資本のstop timesとOIS超過費用ledgerを具体化する。これらは初回レビューと両草稿の予定gateから引き継ぐ。既存sourceの限定的な再利用、国際規制subsetとcommercial SIMMの境界、未実行study/性能への非承認も不変。今回のtext修正で実測精度・価格・IM低下・速度・規制適合を証明したと扱わない。

原/現行草稿と初回レビューのSHA256は同名JSONに保存した。新RB-IDは付与していない。出典と読取source provenanceは初回レビューを参照する。
