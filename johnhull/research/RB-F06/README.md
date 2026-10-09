# RB-F06：固定beta SABR較正の識別可能性

更新日：2026-10-09。状態：基礎実装完了、pilot・条件固定・主実験は未完了。

## 問いと範囲

小さいquote残差だけでparameterと未使用strikeのvanilla価格が安定して決まるかを調べる。
固定beta=.5のHagan近似IV写像の逆問題。exact SABR価格・動学・exoticの受入ではない。
[設計](../../docs/prep/design/RB-F06_DESIGN.md)／[実施計画](../../docs/superpowers/plans/2026-10-09-sabr-identifiability.md)。

## 現在の実装

- private較正はscaled a/rho/nu、bounded TRF、全start/失敗/境界/実評価回数を保存する。
- rectangular Jacobianでも第三零特異値・right nullspaceを保持する。
- nu=0は解析列。tiny positive nuは多step差分・小特異値と数値不確実性・projectorの変動を確認する。
- 支持判定はbest finite/best convergedを区別し、baseline不足はdataset全体をunsupportedとする。
- pointwise profile参考線、未探索gap、有限採取価格幅とunknownの元分母を明記する。

[独立基礎レビュー](FOUNDATION_REVIEW.md)の4重要項目をguardで具体化した。
基礎の対象61件＋索引/docstring902件で963 PASSを確認（その後、profile失敗成果の監査regression 1件もPASS）。
[独立基礎レビュー](BASIS_REVIEW.md)は修正後PASS・残Critical/Important0。[独立参照](REFERENCE_METHODS.md)の22件も含む。
pilot受入・主実験受入はまだ完了していない。

## 実施候補

2真値（通常nu=.4／弱nu=.02）×full/ATM/sparse、noiseless＋5volbpノイズ16反復、固定9startsの918主fit。
profile・truth固定点・細分化を含む最大4830solver callsを候補とする。
別pilotの収束/費用/差分を確認し、financial source・全rosterを固定後にmainを実施する。

## 一次資料

- [Hagan et al. 2002](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf)：SABRと近似IV写像。
- [Raue et al. 2009](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)：nuisance再最適化profile。
- [Self & Liang 1987](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf)：境界・非正則性。
- [SciPy 1.17 least_squares](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html)：cost、bounds、nfevと差分呼出の仕様。

教材の完了は独立参照・保存全結果・fresh検算・3図実行/目視・費用・最終レビュー・採否・main反映で判定する。
本編の台帳は変更しない。

原著ATM式(2.18)の抽出OCRにsigma²/rho²の混同があるため、元の式画像と照合しrho²を採用した。抽出/原著ファイルは変更していない。
