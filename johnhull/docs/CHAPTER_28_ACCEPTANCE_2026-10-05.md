# Ch28 章末まとめ受入（§28.6–28.8）

日付：2026-10-05。D3（本人承認2026-10-03、PR #11）の共通build・画面巡回を適用。
既受入§28.1–28.5を保持し、以下の7要求を追加対象とする。

| 節 | 原典GE頁／式 | 教材位置／要求 | ロジック・独立検証 |
|---|---|---|---|
| 28.6 | 680–681／28.26–29 | vol10 §6E／D28.6-01,02 | `_forward_black.py`。7市場42価格、Q/T求積・parity・raw固定seed MC・rare-event importance sampling |
| 28.7 | 681–682／28.30–32 | vol10 §6F／D28.7-01,02 | `_exchange_measure.py`。33市場の比給付求積、配当再投資密度、確率金利Q MC、§26.14接続 |
| 28.8 | 682–684／28.33–35 | vol10 §6G／D28.8-01,02,03 | `_numeraire_change.py`。9相関条件、逆変換、P→Q、絶対係数、TN20、Gaussian tilt求積・raw MC |

3節とも本文の印刷価格はない。図の数値は入力を明示した合成例であり、本文値の再現と偽らない。
数値比較は許容誤差付き。MCは固定seed・標準誤差の倍数で判定し、数値digest照合は使わない。
低確率callの独立値は7.1683521394e-8。ゼロhitを価格ゼロとせず、raw importance重みで確認する。

## 共通の受入手順と証跡

- [章設定](acceptance/chapters/ch28.json)が節ID、要求、実装、検証、図、入力規約を保持する。
- `scripts/chapter_acceptance.py <設定> prepare/build/test/d1-plan/bind/check/register`を章ごとに使用。
  数式ごとの専用受入・台帳更新スクリプトを複製しない。
- Bookとportalは共通build、共通browser verifierの1巡回。6図×2幅（1440/1000）×2面を対象位置で確認。
  各節の説明anchor、数式、局所リンク、表示数値、図の配置、数値改変の拒否を対応付ける。
- 独立参照は`hullkit/tests/_chapter28_reference.py`。`build()`はhullkitを呼ばずmath/scipyで求め、
  実装・保存参照・配布図は数値として許容誤差で照合する。
- 依存が変わった既受入節だけD1を実行。変わらない節は完全な依存指紋と観測runtimeを比較し、
  直接のredrawn基点画像を共通記録へ結び直す。実行していないbrowser/pytestを再実行済みと記録しない。
- 新図・基点画像は一次／ミラー保管庫から独立に復元して照合。代表portal画像6枚を台帳image evidenceに残す。
- hullkit＋reportの全suiteは章の受入用ブランチで1回実行。細部修正の確認は対象tests/ruffで行う。

実行結果・テスト数・D1対象・両保管庫結果は
[共通受入記録](validation/chapter-28/acceptance-check.json)、
[数値検証](validation/chapter-28/numerical-check.json)、
[画面巡回](validation/chapter-28/browser-check.json)、
[全suite](validation/chapter-28/full-suite.json)を参照。
台帳登録は検証済み5観点の候補をローカルへ反映する段階。main反映には、
全suite（失敗があれば対象テストによる修正確認）と最終`check`が必須。
共通ツール`check`と`verify_section_ledger.py --check-artifacts`のPASSを正式受入条件とする。

## 範囲と制限

- Blackは同じ決済満期のforwardがT測度で対数正規という仮定。spot/futures代用や一般金利モデルの分布保証ではない。
- 交換は共通通貨、連続配当、再投資numeraire、定数loading。Q/Uの比の平均とlog driftを区別する。
- 測度変更は新/旧h/g。Brownianは逆符号、非取引状態のQ driftは固有のrisk-adjusted drift。
  相対／絶対loadingを混ぜず、局所係数の恒等式から一般の真のmartingaleを断定しない。
- 新計算・教材はprivate、`hullkit.__init__`と既存公開APIを維持する。
- mainにはこの章の実装と受入だけを統合する。後続Ch29–34のロジックは`codex/p3-logic`に保持する。
  §33.2はflexicapのstrike/reset・payment日、sticky K0不足で保留。合成値を使って印刷価格へ合わせない。