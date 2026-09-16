# Task 3 independent spec and quality review

Verdict: **Approved** (2026-09-16).

対象は `4fcb8f9b..4a83a5ba`（Task 3 と追加レイアウト修正）。Task 1 数学実装・Task 2 図の意味の独立承認を前提に、Task 3 brief/report、46KBの全差分、原要求表S01–S06、独立ブラウザー参照生成器、最新配布検証記録を照合した。ソース編集、コミット、再ビルド、既実施スイート／ブラウザーの再実行は行っていない。

## Findings

Critical / Important / Minor の修正要求なし。Task 3を妨げる数学的説明の誤り、要求欠落、公開インターフェース変更、他図へのCSS波及は見つからなかった。

## 要求との照合

行番号は `johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py` の現行ソース。

| 要求 | 根拠 | 判定 |
|---|---|---|
| S01 | 800–819: 一回または未行使、満期払い、50/60例、文字通りの給付と本源的価値の床、S<Kの支配関係 | 適合 |
| S02 | 830–838: 割引した符号付き現金とリセットATM callの区別 | 適合 |
| S03 | 842–857, 865–875: CRR確率・後退max・満期条件・N=3全節点、有限判断日の近似、振動・残差・境界の限界 | 適合 |
| S04 | 883–897: 同一GBM／市場／満期／行使価格／新規極値での比較理由、36行6市場・ATM14行・put拡張の限定 | 適合 |
| S05 | 893–895, 905–919: r=q対応とlookback欠測、単位・入力条件・対象外・確認問題と解答 | 適合 |
| S06 | 独立showセル4個、共有図、現行Book/portal証跡と画像 | 適合 |

S04は4.2.5、S05は4.2.6、S06は主に4.2.4と4.2.6に対応する。6見出しがSxxを機械的に誤対応させていない。M4a原要求表の「42件全て／7市場」の広いlookback主張は、現行教材で36行6市場に限定されている。

Portalの `report/report_builder/figures.py:546–580` でもcall主体、符号付き脚、有限N、独立境界非包含、r=q欠測、GBM／正入力／対象外／put拡張を提示する。CSS追加はshout IDを含むカードだけで、既存lookback等の規則は保存されている。registryとmanifestは94図／exotics14図／12テーマで一致する。

## 検証の独立性と実画面

`scripts/build_shout_browser_reference.py` を読み、新tree/figure helperを呼ばず、直接対数正規積分、凍結M4a価格、独立極値積分、独立N3後退計算、M4a B400境界を使うことを確認した。ブラウザー検査はメニューをクリックし、可視traceの実数列・全非終端節点の符号付き脚を参照値と照合する。N3はDOMの描画済みラベルも照合する。合計を保存したcash+1/call−1の破損を拒否し、復元後に数値とラベルを再確認する（verifier:126–149）。metadataだけの検査ではない。

最新 `browser-m4b-check.json` を限定的に解析した結果、source/artifact SHA256は全件現行ファイルと一致し、不一致0。Book/portal各26状態、合計52状態すべてでnumeric_checked=true。両面の破損検査拒否／復元済み、layout_errors=0、page_errors=[]。画像は16図画像＋2式・例画像。Bookは42 MathJax、errors=0、独立した6見出し。PortalはHTTP(S)遮断、実要求0。Bookは既存MathJax本体と7フォントを許可・記録しており、完全オフラインとは主張していない。

レビュー担当も実保存画像 `book-shout_decision-1000.png`、`book-shout-example-1000.png`、`portal-shout_boundary-1000.png` を閲覧した。節点の負の現金脚、式と50/60例、境界の軸・凡例・残差・脚注を読め、タイトルとmodebarの干渉や欠けを認めなかった。他の4図・更新比較画像の目視はcontroller報告を根拠とする。

## 明示的な限界と統合責任

- 本レビューはN128/256/512の残差を再価格付けしていない。ブラウザー側もN1024残差だけを独立価格と照合するという正しい限定を持つ。
- CRR境界上下点の格子所属検査は、独立な最適判断の再計算ではない。図・教材とも連続境界を必ず包む保証を否定している。
- 74セルの保存／fresh実行／ソース保存、共有4図一致、622passed/6skipped、既存3節ブラウザー回帰はcontrollerの実施報告を採用した。ここで再実行したとは主張しない。
- 全体スイート、受入・台帳・現在の状況資料、生成物の統合はcontrollerの残作業。Task 3承認だけで全体リリース完了や台帳acceptedを主張しない。

**Approved**
