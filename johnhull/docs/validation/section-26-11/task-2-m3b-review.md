# Task 2 独立レビュー

## Spec compliance: ✅ 適合

- 対象は `2ff7bd0a9481c6e057bffb94aa2af236117017b8..1cade65789519771ac21e01aea02e010c2ee0208`。brief/report/diff を順に確認し、差分を一度通読した。9ファイルの Task 2 レビューであり、全ブランチのマージ承認ではない。
- `johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py:658`: 六つの節、4契約、履歴極値、浮動型の全係数、Example 26.2、固定型の星付き履歴、観測頻度、適用範囲を確認。原著抜粋 `hull-623-625.txt` pp.623–625 と call/put の符号・係数・配当/割引項・複製式・例題を照合し、相違なし。給付恒等式から現在価値への説明と条件付きバニラ比較も妥当。
- 同 builder の lookback ブロック: `lb` 維持、共有図の4つの独立 show セル、合成値・単位・連続観測 GBM の前提を確認。`abs(r-q)<1e-8` の API 例外を明記し、除去可能特異点の価格エンジンは未実装という承認済み NA 範囲を守る。
- `johnhull/report/report_builder/figures.py:502`、`johnhull/report/assets/style.css:132`、`johnhull/report/tests/test_report_build.py:39`: 4カードと共有図の接続、lookback 限定の全幅指定、exotics 10 / 全90件およびキー集合の契約を確認。manifest/readmes も一致。テストの package-relative import 修復は承認済み範囲内。
- `johnhull/scripts/verify_lookback_lesson_browser.cjs:65`: semantic metadata により図を一意に特定し、実メニュー操作と可視 trace 値を検証。各状態の1440/1000px レイアウト検査、Book の六見出し・契約ラベル付き例題・境界・数式、18枚の証跡生成を確認。
- ⚠️ 生成 notebook の lookback 外ソース同一性と全プロジェクト検証は controller の統合ゲート。差分に lookback 外の builder 変更はなく、生成物・保存値の同一性について提供された確認報告を参照した。独立に再実行したとは主張しない。

## Strengths

- `johnhull/scripts/verify_lookback_lesson_browser.cjs:45`: floating/stock/cash/reconstructed/fixed の各脚を参照値と別々に比較し、合計一致だけに依存しない。`:85` の負の対照は floating +1 / stock -1 で合計を維持し、検出後 finally で復元して正常値を再検査する。両面・call/put 全組合せの rejection/restoration 記録あり。
- 同 verifier `:26` と `:30`: 必須プローブ点の存在と数値、節点間の極値も検査する。教材は折れ線の8区間での極値捕捉と連続 GBM の価格収束を区別する。
- 具体的リスク「参照値の実装再利用による自己検証」のため、変更外の `johnhull/hullkit/tests/test_lookback_reference.py:65` から価格オラクル部分だけを追加確認。極値分布積分で各契約を直接評価し、固定型を複製式から作らない独立オラクル。ブラウザー参照値68個（履歴36、複製脚30、例題2）を限定プローブで照合し、最大絶対誤差0。

## Issues

- Critical: なし。
- Important: なし。
- Minor: 今回の範囲で報告すべき問題なし。

## Verification

- `johnhull/docs/validation/section-26-11/browser-m3b-check.json`: 実行記録 PASS、両面各11状態、各面48個の節点間極値プローブ、call/put 負の対照の拒否と復元、layout/page errors 0、portal 外部通信0。Book 外部通信は記録された既存 MathJax とフォントのみ。数式60要素、エラー0、例題8.037120 / 7.790219を確認。
- 同 JSON のソース12件・成果物22件の SHA-256 を現物と比較し、34件すべて一致。ブラウザースイートの重複実行なし。
- 1000px の保存画像を目視: Book の4図と数式/例題、portal の履歴/複製図の計7枚。数式・凡例・軸・注釈・表に欠落や衝突なし。他状態/幅は verifier 実装と保存 PASS 記録を確認した範囲。
- `regression-tests.log`: 407 passed、警告なしを確認。全スイートの重複実行なし。独自実行は34件のハッシュ照合と68個の数値ピン照合のみ。
- ソース、Git index、HEAD、ブランチは変更していない。この文書と表示用画像コピーのみ作成。

## Task quality: Approved

- 説明・共有図接続・独立数値比較・負の対照・実ブラウザー証跡が Task 2 要件に対応する。ブロックすべき正確性・仕様・品質上の問題は見つからなかった。最終ブランチレビューと統合/acceptance 記録は controller が担当する。
