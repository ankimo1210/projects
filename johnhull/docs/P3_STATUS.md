# P3 完了に向けた実装状態

更新2026-10-04。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- main：§28.1–28.3受入、P3 3/37。M28全suite4046/6・台帳成果物/release/両保管庫を確認、main統合push済み。
- 現在：M29 §28.4をcodex/m29-numeraire-choicesで着手。原典12要求/独立Gaussian教師/仕様・計画を準備し、Task1のQ状態/条件付きbond/towerで4件RED→新旧11件GREEN。Jamshidian/較正は数学的に不変、vol26の丸め差3点とnotebookを再生成。全suite初回4049 passed/1 failed（28既受入節の旧HW source hash）；28D1更新をTask4で実施するまで全体受入はpending。Task2はprivate Gaussian/条件付き支払・annuity、独立63fixture/10 direct MC/8変異がPASS、対象40 tests PASS。Task3は6C教材11セル/4共有図・旧246セル保持・257全文freshとBook/portal16表示状態がPASS。図は合計194、Book144 warnings（旧140+新Plotly4）。次は28D1・5軸台帳・最終レビュー。M28はmain受入・独立レビュー修正・push完了。
- 未完了：§28.4–28.8、Ch29–34（計34節）。確率金利/複数測度、市場式、convexity/timing/quanto、短期金利、HW/BK木/曲線fit/時間依存σ/Bermudan/較正、HJM/LMM、非標準swapの本文要件。
- 並行準備：全35未受入節の要求照合、M28独立math参照、HW/BK/LMM実装仕様を読み取り専用agentで確認。
- 受入ゲートは節ごとに既存D1/両保管庫を維持。D3規約の軽量化は未承認で今回変更しない。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。Technical Note14/19の完全PDFは未取得、31.4/33.2/34.4の不足原典入力は未完了扱い。HWのQ OUとbond式の測度整合候補を後続の独立検証で調査。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）は記録し、現在段階表の未受入34を優先。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDF未取得、flexicapのstrike/対象期間、Table31.1の完全較正入力はpending。合成例で代替受入しない。
