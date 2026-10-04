# P3 完了に向けた実装状態

更新2026-10-04。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- main：§28.1–28.4受入、P3 4/37、全29/277。M29 f8d57ef4をFF統合/push、main fresh 4125/6・台帳成果物/release/両保管庫確認済み。
- 現在：M30 §28.5が全五軸/統合gate/29D1/両保管庫を通過し、作業ブランチ30/276・P3 5/37。新268/旧257保持・16表示PASS。29既受入節をclean6d7cf486から再描画し、個別pytest計2,215件、browser/runtime/両保管庫復元PASS。全478画像のpayload合計20,387,859バイト。重複排除後の実増加容量は未測定。採用29パス/SHAはm30-checkで固定。最終hash更新後29D1を全再実行し29reuse／新規保存0B、2215 tests／478画像／両保管庫PASS。初回全suite4219/6 PASS、最終全suite4219/6 PASS（272.81s）／独立レビューImportant1を4回帰RED→lesson20GREENで修正、Minor2保留。修正後全suite4223/6 PASS（293.49s）。main統合は次工程。
- 未完了：§28.6–28.8、Ch29–34（計32節）。多因子測度、市場式、convexity/timing/quanto、短期金利、HW/BK木/curve fit/時間依存sigma/Bermudan/較正、HJM/LMM、非標準swapの本文要件。
- 並行準備：M30多因子の原典/独立132条件付きfixture、TN14/TN19完全PDF/元XLSの回収、31.4回帰と全9点の独立再現。正式受入とは区別する。
- 受入ゲートは節ごとに既存D1/両保管庫を維持。D3規約の軽量化は未承認で今回変更しない。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。TN14/19と31.4元worksheetの取得不足は回収記録で解消。正式数理/実装受入は未完、flexicapのstrike/date不足は保持。HW Q OU/bond式整合はM29で独立RED→GREEN。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）はM29の通常状態更新で未受入33へ整合。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDFとTable31.1完全較正入力の取得不足は[回収記録](prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)で解消。正式受入とflexicapのstrike/対象期間はpending。合成例で代替受入しない。

- M29独立レビュー：96tests/4checksと追加probe PASS。Minor3はportal練習文/極小accrual/極大aの境界として記録し、正式修正は後続。

- 後続準備：Black再訪/交換契約の原典名・独立求積・zero-hit MCのimportance sampling、TN14のequilibrium/curve fit/全Appendix・a=b/rho端/u0/微分方向をscratch照合。正式受入とは区別。

- 後続Ch29–30/Ch32/Ch34の原典全要求と独立scratchをdocs/prep/designへ保存。Ch32は著者DG201の終端1日規約でTable32.3とFig32.9を再現しsigma_R補正案を撤回。正式製品tree/較正/Bermudanは未完、Ch33 flexicap入力不足は保持。
