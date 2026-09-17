# §26.14 Options to Exchange One Asset for Another：受入記録

**判定：accepted。M6aで整理したE01–E06の根拠が、教材・実装・独立検証・図・実画面の5軸すべてで揃った。**

日付：2026-09-17（JST）。原典：Hull 11e Global Edition §26.14、物理・印刷pp.627–628。
開始コミット：42a6cbc0（M6a）。要求整理と独立価格検証は[M6aの記録](SECTION_26_14_REVIEW_2026-09-16.md)。

## 受入条件と結果

M6aで定めた7条件に対する結果である。

| # | 条件 | 結果 |
|---|---|---|
| 1 | E01–E02の本文（給付・2資産の文脈・$\hat\sigma$・$\rho$の効果・$q_U,q_V$） | vol10 §4.4.1–4.4.2。図 `exchange_payoff`・`exchange_correlation` |
| 2 | E03の$r$非依存を理由と測定の両方で示す | §4.4.3と図 `exchange_rate`。$r\in[-5\%,12\%]$の7点で最大差 $1.6\times10^{-14}$。**動く比較線**（行使価格を今日の$U_0$に固定した誤読）を並べた |
| 3 | E04の$V/U$読み替えを本文と数値で示す | §4.4.3–4.4.4と同図の太い点線。残差は3市場で最大 $2.842\times10^{-14}$。notebookの表にも列として出す |
| 4 | E05のbetter-of／worse-ofとRubinsteinの米国型 | §4.4.5、図 `exchange_american`、`better_of_two_assets`／`worse_of_two_assets`／`exchange_option_american` |
| 5 | 図を独立根拠で検査し、vol10の保存出力を再生成して別実行と比較 | 図4件・`test_exchange_lesson.py` 34件。保存出力は別実行と一致（[notebook記録](validation/section-26-14/notebook-m6b-check.json)） |
| 6 | Book/portalの実画面確認と、§26.9–§26.13の再検証 | 両面PASS（[browser記録](validation/section-26-14/browser-m6b-check.json)）。§26.9–§26.13は`m6b-recheck.json`5件 |
| 7 | E01–E06が揃ってからacceptedへ | 本記録で変更。§26.14の条件に独立レビュー要件はない |

## 実装

公開APIに4関数を追加した（`hullkit.exotics`）。既存の `exchange_option` は入力検証を足し、
$\hat\sigma\le0$ では割引フォワードの差を返すようにした。

| 関数 | 役割 |
|---|---|
| `exchange_spread_volatility` | $\hat\sigma=\sqrt{\sigma_U^2+\sigma_V^2-2\rho\sigma_U\sigma_V}$。$\rho\notin[-1,1]$ と負のボラを拒否する |
| `exchange_option_american` | Rubinsteinの読み替えによる $V/U$ 上のCRR木（金利 $q_U$、配当 $q_V$、既定1024ステップ） |
| `better_of_two_assets` | $U_0e^{-q_UT}+$ 交換オプション |
| `worse_of_two_assets` | $V_0e^{-q_VT}-$ 交換オプション |

## 測定した量

| 検査 | 結果 |
|---|---|
| 2経路の求積（24行） | 最大絶対差 $1.776\times10^{-14}$ |
| $r$非依存（24行×3レート、図では7レート） | 最大差 $1.6\times10^{-14}$ |
| $V/U$読み替えの残差 | 最大 $2.842\times10^{-14}$ |
| better-of／worse-ofの分解（24行） | 最大残差 $8.527\times10^{-14}$ |
| 早期行使プレミアム $q_V=0$ | $1.208\times10^{-13}$（同じ格子の欧州型と比較） |
| 同じ市場の格子残差 | $2.745\times10^{-3}$ |
| 早期行使プレミアム $q_V=6\%$ / $3\%$ | 最大 7.951 / 3.142 |
| 木の収束（$q_V=0$、非対称ボラ） | 128/512/1024ステップで 0.0457 / 0.0114 / 0.0057（倍にするごとに半減） |

**早期行使プレミアムは同じ格子で行使判定を外した価格と比べて測った。**
閉形式と比べると早期行使と離散化が混ざり、$q_V=0$ でも $2.3\times10^{-3}$ の「プレミアム」が出てしまう。
これは格子の誤差であって早期行使の価値ではない。図は両者を別の線として描いている。

## 図（portal・Book共通、4件）

| 図 | 示すこと |
|---|---|
| `exchange_payoff` | $\max(V_T-U_T,0)$ と、better-of／worse-ofが同じ給付の足し引きであること |
| `exchange_correlation` | $\rho$ を $-0.95$ から $0.95$ まで動かしたときの価格と $\hat\sigma$、$\hat\sigma\to0$ の極限 |
| `exchange_rate` | $r$ を動かしても動かない価格、$V/U$ 読み替えの重なり、**動いてしまう誤読** |
| `exchange_american` | 欧州型・米国型・即時行使、早期行使プレミアムと格子残差を別々に |

図は保存済みJSONだけを読み、生成元のハッシュが古いと読み込みを拒否する。
`test_exchange_lesson.py` は式26.5をテスト側で書き直して全点を突き合わせ、
価格関数をmonkeypatchで塞いだ状態で図が構築できることまで確認する。

## 検証の限界

定数係数の相関GBM 2本という仮定の上にある。確率的ボラティリティ、ジャンプ、時間変動する相関、
現金配当は対象外である。米国型は有限のCRR木で、残差は格子効果であって誤差上界ではない。
モンテカルロは標準誤差を持つ。$\rho=\pm1$ ちょうどと $\hat\sigma=0$ は端点として扱う。

**§26.14には印刷された例題が無い。** 本冊の 7.965567 は原典の値ではなく、
独立参照（求積2経路とモンテカルロ）で確かめた本リポジトリ由来の固定値である。
市場は合成8種で、実データによる検証ではない。

## 共有ソース変更の影響

`hullkit/src/hullkit/exotics.py`・vol10のnotebookとbuilder・`report/report_builder/figures.py`・
`report/assets/style.css` は §26.9–§26.13 と共有している。5節すべてを再検証し、
`m6b-recheck.json` に記録した（テスト123/107/192/215/274件、ブラウザ両面PASS）。

§26.12・§26.13の `lesson-data.json` は `exotics.py` をハッシュでpinしているため再生成した。
**`source_hashes` 以外の値はコミット済みファイルとキー単位で一致する**ことを確認している。

再検証で82枚中5枚のスクリーンショットが変化した。4枚は文字のアンチエイリアスで、
最大 12/255 が高々0.9%の画素。残る1枚（`section-26-11/book-lookback_replication-1440.png`）は
最大 86/255 だが、差は $y\in[6,55]$・$x\in[577,784]$ に限られ、
Plotlyのmodebarツールチップ（Autoscale）が今回は完全に不透明な状態で写り、
ドロップダウンのラベルを隠していたためである。図の中身の変化ではない。
**コミット済みの画像は復元した**ので、過去の受入根拠はバイト単位で不変である。

## 次

§26.15 Basket Options（GE p.628）。§26.14の分解で使ったレインボーの枠組みが続く。
vol10 §4.5に式26.3・26.4の再掲だけがある状態で、独立検証も図も無い。
