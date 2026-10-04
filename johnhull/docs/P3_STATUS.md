# P3 完了に向けた実装状態

更新2026-10-04。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- main：§28.1–28.5受入、P3 5/37、全30/276。M30 `5c8bcbde` をFF統合/push、main fresh4223/6・台帳成果物/release/両保管庫PASS。Important1を固定seed消費時replayで4回帰RED→GREEN修正、Minor2保留。
- 現在：本人指示（2026-10-04）でロジック先行へ変更。`codex/p3-logic` に節ごとに実装・本文数値再現・独立検証をcommit/pushし、受入は章末にまとめる。§28.6–28.7のロジック完了、現在§28.8。
- 未完了：§28.6–28.8、Ch29–34（計32節）。多因子測度、市場式、convexity/timing/quanto、短期金利、HW/BK木/curve fit/時間依存sigma/Bermudan/較正、HJM/LMM、非標準swapの本文要件。
- 並行準備：M30多因子の原典/独立132条件付きfixture、TN14/TN19完全PDF/元XLSの回収、31.4回帰と全9点の独立再現。正式受入とは区別する。
- 章末：D3軽量受入（本人承認2026-10-03、PR #11は反映用のopen PR）。共通設定ツールで5軸受入、explanation/rendered必須、章内build/画面確認共有、依存変更節だけD1、全suite1回。節ごとは変更モジュールのtests/ruffのみ。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。TN14/19と31.4元worksheetの取得不足は回収記録で解消。正式数理/実装受入は未完、flexicapのstrike/date不足は保持。HW Q OU/bond式整合はM29で独立RED→GREEN。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）はM29の通常状態更新で未受入33へ整合。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDFとTable31.1完全較正入力の取得不足は[回収記録](prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)で解消。正式受入とflexicapのstrike/対象期間はpending。合成例で代替受入しない。

- M29独立レビュー：96tests/4checksと追加probe PASS。Minor3はportal練習文/極小accrual/極大aの境界として記録し、正式修正は後続。

- 後続準備：Black再訪/交換契約の原典名・独立求積・zero-hit MCのimportance sampling、TN14のequilibrium/curve fit/全Appendix・a=b/rho端/u0/微分方向をscratch照合。正式受入とは区別。

- 後続Ch29–30/Ch32/Ch34の原典全要求と独立scratchをdocs/prep/designへ保存。Ch32は著者DG201の終端1日規約でTable32.3とFig32.9を再現しsigma_R補正案を撤回。正式製品tree/較正/Bermudanは未完、Ch33 flexicap入力不足は保持。

## ロジック先行の進捗（正式受入とは別）

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 |
|---|---|---|---|
| §28.5 互換修正 | `_multi_factor_lesson.py` | teacher/固定seed MCの1e-15差を許容、既存の数値改変拒否も保持 | 章末に配布画面・依存節を再確認 |
| §28.6 | `_forward_black.py` | 印刷例なし。式28.26–29、7市場42価格のQ/T求積・raw MC、rare call 7.1683521394e-8 | ロジック完了。教材・正式受入は章末 |
| §28.7 | `_exchange_measure.py` | 印刷例なし。式28.30–32、33ケース独立求積、配当再投資密度と確率金利4条件MC | ロジック完了。教材・正式受入は章末 |
