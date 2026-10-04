# P3 完了に向けた実装状態

更新2026-10-04。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- main：§28.1–28.4受入、P3 4/37、全29/277。M29 f8d57ef4をFF統合/push、main fresh 4125/6・台帳成果物/release/両保管庫確認済み。
- 現在：M30 §28.5をcodex/m30-multifactor-martingalesで着手。M29のworktreeを再利用。原典pp679–680/脚注7を画像照合し、private多因子計算・独立11市場132条件付きfixture・8変異拒否を実装。Task1は523tests PASS（新50＋model index473）、MC262144標本/187集計の最大2.5454SE。Task2は6D教材11セル/全268のfresh検査、旧257本文/出力/Plotly保存、4共有図/16表示/16画像がPASS。価格図は同じf市場でgの正/負/ゼロloadingを比較する回帰RED→GREEN。次は29D1/全五軸受入/最終レビュー。M29はCritical0/Important0/Minor3記録・main統合済み。
- 未完了：§28.5–28.8、Ch29–34（計33節）。多因子測度、市場式、convexity/timing/quanto、短期金利、HW/BK木/curve fit/時間依存sigma/Bermudan/較正、HJM/LMM、非標準swapの本文要件。
- 並行準備：M30多因子の原典/独立132条件付きfixture、TN14/TN19完全PDF/元XLSの回収、31.4回帰と全9点の独立再現。正式受入とは区別する。
- 受入ゲートは節ごとに既存D1/両保管庫を維持。D3規約の軽量化は未承認で今回変更しない。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。TN14/19と31.4元worksheetの取得不足は回収記録で解消。正式数理/実装受入は未完、flexicapのstrike/date不足は保持。HW Q OU/bond式整合はM29で独立RED→GREEN。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）はM29の通常状態更新で未受入33へ整合。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDFとTable31.1完全較正入力の取得不足は[回収記録](prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)で解消。正式受入とflexicapのstrike/対象期間はpending。合成例で代替受入しない。

- M29独立レビュー：96tests/4checksと追加probe PASS。Minor3はportal練習文/極小accrual/極大aの境界として記録し、正式修正は後続。

- 後続準備：Black再訪/交換契約の原典名・独立求積・zero-hit MCのimportance sampling、TN14のequilibrium/curve fit/全Appendix・a=b/rho端/u0/微分方向をscratch照合。正式受入とは区別。
