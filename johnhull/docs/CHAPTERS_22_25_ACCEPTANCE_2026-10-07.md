# Ch22–25 軽量受入 — 2026-10-07

目的：P5（Ch22–25）の36節をまとめて受け入れ、全体261/306節へ進める。
対象36節・125要件、計算32節・説明中心4節。基点`0c72b31d`、
ローカル`codex/johnhull-acceptance`で実施する。
方針は[fast-v1](FAST_ACCEPTANCE_GUIDE.md)、判定の正本は台帳と
[統合記録](validation/fast-ch22-25/acceptance-check.json)。

## 対象と検証

Hull 11e Global Editionの下調べにある要求ID・本文・読みを保持し、
日本語補足を`report/site/chapters/ch22.html`〜`ch25.html`へ配布する。

- private6モジュール・32節のtestと既存CDS/credit portfolioの2 suiteを対象とする。
  既存計算218 testsの独立実行PASS。受入検査27を含む対象245 tests、台帳41 tests、計286ケースを確認した。
  新guardはwrapperの未実装import失敗から26 passedへのRED→GREENを確認した。
- 要求は数値105・説明20。§22.7/23.4/24.1/24.3の4節は説明中心。
  数値verifiedは各要件の定義した計算部分を指し、原典未掲載price、歴史系列・市場fit、動的研究を含めない。
- 全36節・125要件、数式145個・表2つを1280pxでブラウザ確認した。本文の意味、節リンク、横overflowとruntimeも検査。
  要求欠落・本文改変を拒否するnegative controlも確認し、各章の代表1画像、計4画像を目視した。
- 旧225 accepted行・対象外270行の完全一致、全261 accepted行のnative artifact検査、summary、releaseを確認する。
  旧Ch16–21のsource/evidenceは変更しない。数値sourceに変動する台帳件数testを含めず、台帳証跡で別に固定する。
- 独立レビュー：新adapter、guard、36節のsource要求と教材、各範囲のN/A理由、4画像を確認する。
  最終判定と指摘の扱いは[レビュー記録](validation/fast-ch22-25/review-check.json)に保存する。

## 原典データとモデルの制限

- Ch22：501日HS系列と2631点PCA系列がない。最悪15損失の下側は合成補完。
  原典25.45/59.2対印刷loading再計算25.49837/59.31808の差を残す。
  MSFT ESの1687000対1685629.5、線形分散14406.193対14404は中間丸めの違いを明示。
  TN10 PDF・TN25全表は取得できず、CFの強い歪度や全book cross covariance保存を保証しない。
- Ch23：1259価格からの歴史fitと全尤度10837.4227は未再現。
  8.6333対8.633362、Q2170/13.2対2139.60985/12.94915を保持。
  P variance予測とQ IV、実効volと平均SDを区別する。数値探索は一意最適の証明ではない。
- Ch24：P/Q、年hazard/累積PD、区間無条件/条件付きPDを分ける。
  EDFの非公開較正とTN26詳細は未検証。CVAのLGD/割引は各1回、Ex24.6は1oz単位。
  wrong-wayは指定Gaussian factor例で一般first-to-defaultではない。
  既存TransitionMatrix docstringの残差記述と実装の不整合は既知のまま、共有計算は変更しない。
- Ch25：§25.3/5/6/7/11の不足入力は明示合成検証。原典印刷priceを再現したとはしない。
  原典waterfallの5/20%と既存vol12の5/15%、全体元本とtranche元本を分ける。
  Table25.6は歴史quote。§25.10は源60点とmidpoint default、loss/annuityの全curveを用いる。
  §25.11は静的ASB/double-t/因子依存/hazard mixtureのみで、全copulaやCR-11動的研究は別範囲。

## 独立レビューでの修正

重要な教材指摘3件を修正：§23.5の初期予測varianceはv3=u2²、
§24.7の担保基準値は20日後ではなく20日前、§24.2のBBB .29%は第2年の無条件PD（2年累積.45%）。
元要求や計算部品は変更せず、本文の添字・時点・確率種別を修正した。
旧generatorが「未再計算」を削って文を切っていた箇所は「未検証」を保持し、
research ticketや旧未固定表示を教材から除いた。元データ欠落と数値差は残す。
教材の最終未解決はCritical 0 / Important 0 / Minor 0、更新後4画像を独立再確認済み。
登録前検査がadapterとtest runnerのsourceリストの違いを拒否したため、同じリストを使う最小修正を加えた。
追加回帰はsource4件の欠落でRED、修正後GREEN。旧engineは未変更で、新guardは27ケース。

## 省略と現在地

ユーザー承認のfast-v1により全suite、全Book rebuild、2幅、全節画像、両保管庫への復元確認は省略。
補足教材の受入であり、既存Book本文の改訂・main統合・push/公開は未実施。
既存ロジックと以前の225受入行を変更しない。

P0/P1/P2/P4/P5/P6の受入完了。P3は29節、P7は16節、計45節が未評価。
P3 §33.2/P7 §36.4は原典入力不足の判断が残る。P7実装とP8完了は開発側mainからの報告で、このbranchへの取り込みは未実施。

## 再検証

WSLのrepo rootから共通venv、hullkit/srcとreportとrootのPYTHONPATHを設定する。
新しい証跡を作る場合のみbuild→test→browser→check→registerを実行する。

```bash
python johnhull/scripts/fast_acceptance_risk_credit.py build
python johnhull/scripts/fast_acceptance_risk_credit.py test
node johnhull/scripts/verify_fast_acceptance_options_browser.cjs docs/acceptance/fast-ch22-25.json
python johnhull/scripts/fast_acceptance_risk_credit.py check
python johnhull/scripts/fast_acceptance_risk_credit.py register
```

登録後のread-only再確認は`python johnhull/scripts/fast_acceptance_risk_credit.py verify`。
数式表示にオンラインMathJax接続が必要。native台帳とreleaseの結果は証跡を参照する。
