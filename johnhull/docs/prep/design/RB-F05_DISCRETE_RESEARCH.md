# RB-F05 離散バリアの追加調査

2026-10-09。次研究の準備メモ。実装・数値領域・学習予算は未確定。

## 契約と参照値

固定K/H・rebate0のup-and-out callを候補とする。接触、時点0、満期の監視を明記し、監視集合を固定したまま数値解像度だけを変える。
後続の具体化では正時点m回に時点0を加え、監視集合を{0,T/m,...,T}とする（主比較m=12では13時点）。
既存`exotics.barrier_call(n_observations=...)`はBGK近似、`barrier_tree`は全ノード吸収であり、有限回の離散契約の厳密参照には使わない。
log-priceの正規Markov遷移を逐次積分する参照と、監視日にだけkillする独立FD/treeを検討する。FDの領域はHより上まで必要。bridgeの区間内hit判定を足すと連続契約になる。

## 微分教師

初回監視時刻を\(t_1>0\)とすると、spotのscore教師は

\[
Y\frac{Z_1}{S_0\sigma\sqrt{t_1}}.
\]

満期の標準正規乱数だけをscoreへ使わない。最終増分の条件付きpayoffと初回scoreを組み合わせる方式は、不偏な比較候補となる。
最終増分だけを積分してPW微分する方式には、それ以前の監視indicatorの境界寄与が残る。正しい教師と呼ばず、負の対照として検証する。
one-step survivalでは生存確率の重みと条件付き状態の双方を微分する。価格の不偏性だけでGreekの妥当性を判定しない。

S002 v2 §3.5は初回transitionだけがscoreへ寄与することを説明している。
監視頻度の比較では満期Tを固定し、初回時刻がt1=T/mへ短くなる場合を別に測る。
scoreの分母はsqrt(t1)なので、「項が1つだけ」という理由で頻度増加時の分散が一定とは判断しない。
論文の固定刻み1/3年の実験設定と、固定満期で監視回数を増やす実験を区別する。

時点0も監視する場合、S=Hで即KOする一方、有限回監視の生存側価値は一般に正となる。Hで連続的なゼロをNNへ強制せず、通常のDeltaが存在しない境界を学習領域から区別する。
既存digitalの`discount×sigmoid`出力をbarrier callへ流用しない。固定H>Kで満期も監視する契約なら、callの上限候補は\((H-K)e^{-rT}\)。

## 実装順の候補

契約fixture → 1回監視の解析/積分 → 多回逐次積分と独立FD/tree → LRM/conditioned LRM/PW対照 → one-step survival → pilot → DML・参照補間・費用 → 成果保存/3図/レビュー/採否。
Hermite等の補間では、価格と同じ補間器の微分を比較する。0DTEはこの段階へ混ぜない。

## 一次資料と確認範囲

| 資料 | 確認した範囲 |
|---|---|
| [Differential ML with a Difference, v2](https://arxiv.org/html/2512.05301v2) | §3.2–3.6と式27–29。著者コード/学習結果は未再現。監視集合が満期を除くため、現行Hull契約と同一再現とは呼ばない |
| [Glasserman–Staum, One-Step Survival](https://business.columbia.edu/sites/default/files-efs/pubfiles/4311/one-step_survival.pdf) | §2.2、§3、§4。価格の分散結果をGreekへ自動的に転用しない |
| [Gerstner–Harrach–Roth, v4](https://arxiv.org/pdf/1804.03975v4) | §2.1、Theorem2.4、Corollary2.5。実装時に数式を独立に検算する |
| [Universal option valuation using quadrature methods](https://www.sciencedirect.com/science/article/pii/S0304405X0200257X) | 出版社のabstract/introduction。全文/appendixは未取得 |
| [BGK continuity correction](https://business.columbia.edu/faculty/research/continuity-correction-discrete-barrier-options) | 著者所属機関の書誌/abstract。今回の本文誤差証明は未読 |

既存[RB-F05設計](RB-F05_DESIGN.md)を補完する調査であり、確定した新specや完成判定ではない。
