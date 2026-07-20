# johnhull — デリバティブの数理を動かして学ぶ

John Hull *Options, Futures, and Other Derivatives* (11e) を土台に、**価格付け・リスク管理を
インタラクティブ可視化で直感に変える**学習教材です。コア(既刊ボリューム)に加え、Hull の先にある
クオンツの深掘りに加え、ML pricing、SPX/VIX・0DTE、RFR、crypto、気候・エネルギーまでを
再現可能なsynthetic artifactで扱います。

## 2つの入り口

- **この教科書(Jupyter Book)** — 概念 → 数式 → コード → 可視化を順に追う本文。
- **可視化ポータル** — 代表的な図だけをブラウザ内で動かせるギャラリー(オフライン)。
  `make hull-report` で `johnhull/report/site/index.html` を生成。

## 全体マップ(リスク中立評価という1本の背骨)

| レンズ | 中身 | 主な章 |
|---|---|---|
| ① ペイオフ | オプションと戦略の満期ペイオフ | Ch.10–12 |
| ② 価格 = 割引期待値 | 二項木・BSM・数値手法 | Ch.13–15, 21, 27 |
| ③ ヘッジ | グリークスと動的ヘッジ | Ch.19 |
| ④ リスク・信用 | VaR/ES・信用・XVA | Ch.22, 24–25 |

## コンテンツ

- **コア — Hull 11e 既刊ボリューム**: 基礎(Ch.13–14)、オプション基礎(Ch.10–12,17–18)、グリークス(Ch.19)、
  先物・先渡・金利(Ch.2–6)、ボラのスマイルと推定(Ch.20,23)、数値手法(Ch.21,27)、スワップ(Ch.7,34)、
  リスク VaR(Ch.22)、信用・XVA(Ch.9,24,25)、エキゾ・マルチンゲール(Ch.26,28)、金利デリバ(Ch.29,30)、
  定性まとめ(Ch.1,8,16,35–37)、BSM(Ch.15)、短期金利モデル(Ch.31–33)。
- **深掘り(A1–A4・順次追加)**: 確率解析(伊藤・Girsanov・Feynman-Kac)、確率ボラ&Fourier(Heston/SABR/COS)、
  高度な数値(分散減少・QMC・LSM・有限差分・AAD)、XVA(エクスポージャ・CVA・コピュラ)。
- **Hull の先(A5–A8)**: ML surrogateとGreeks、逆問題・無裁定surface、surface dynamicsとhedging、
  joint SPX/VIX、0DTE variance clock、RFR複利とsmile、crypto perpetual/liquidation/AMM、
  carbon・weather・renewable PPA。各巻はcommitted JSON/NPZだけで表示でき、研究trackはcoreから隔離しています。

## A5–A8 の読み順

1. vol 18–20で、teacher → surrogate → calibration → forecast → hedgeの検証鎖を作る。
2. vol 21–23で、株式ボラ最前線、超短期満期、post-LIBOR金利へ適用する。
3. vol 24–25で、取引所・AMMのsolvencyと、非完備な気候・エネルギー市場へ拡張する。

各巻の`VALIDATION.md`にはartifact fingerprint、主要metric、限界を記録しています。synthetic結果を
市場予測力やproduction readinessの根拠にはしません。

> 図はすべて `hullkit` の価格付け・リスク関数を `hullkit.plotly_viz` がラップして生成するため、
> 本文・ポータル・テストが同じ数式を共有します。
