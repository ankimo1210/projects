# §26.16 Volatility and Variance Swaps：受入記録

**判定：accepted。VS01–VS06 について、教材・公開実装・独立検証・図・実画面の 5 軸が揃い、独立レビューの指摘 F1–F19 に対応した。**

日付：2026-09-25（JST）。原典：Hull 11e Global Edition §26.16、物理・印刷 pp.629–632。
要求・独立参照・納品時の検証は [M8 レビュー](SECTION_26_16_REVIEW_2026-09-25.md)、
独立レビューの指摘と対応は [FEEDBACK](SECTION_26_16_FEEDBACK_2026-09-25.md)、
最終検証は [M8 統合記録](validation/section-26-16/m8-check.json) にまとめた。

## 受入条件と結果

| ID | 条件 | 結果 |
|---|---|---|
| VS01 | 実現ボラ（$n-2$／$n-1$）、2 つの給付、$\bar V=\bar\sigma^2$、$L_{\rm var}=L_{\rm vol}/(2\sigma_K)$、凸と線形 | vol10 §4.6.1。`realized_variance` / `realized_volatility` / `variance_notional`。GBM 日次推定量の厳密期待値と MC、給付図 |
| VS02 | 式 26.6 の静的複製、対数契約、$S^*$ 非依存、平坦スマイル以外での検証 | §4.6.2。平坦 BSM で最大差 8.3e-17、Heston 3 市場で閉形式との最大差 1.51e-12 |
| VS03 | 式 26.8 と Example 26.4、格子・打切り誤差 | §4.6.3。印刷 $Q$ 9 本・0.008139・0.0621・1.69 を再現。wide 範囲で $\Delta K=10\to1.25$ に 3.39e-3 → 5.31e-5 |
| VS04 | 式 26.9 と Example 26.5、厳密 $E(\sqrt V)$ と MC に対する誤差 | §4.6.4。0.2484・1.82 を再現。近似誤差は ξ=0.3 で −1.9e-5、ξ=1 で −4.6e-3、MC は最大 1.08 SE |
| VS05 | VIX：式 26.10 の打切りとその大きさ、30 日補間と年率化 | §4.6.5。打切り差 1.385e-5、補間誤差 −3.24e-4。`vix_index`。Book §4.6.5 の画像 |
| VS06 | 6 小節・4 共有図を Book/portal 両面に置き、領域と限界を明示 | 115 セルの保存 notebook、両面 × 2 幅 × 4 図 × 2 状態 = 32 状態、20 画像 |

## 実装

`hullkit.variance_swaps` に `realized_variance`、`realized_volatility`、`variance_notional`、`vix_index` を追加した。
既存関数の契約は変えていない。図は `hullkit._variance_swap_lesson` の 4 図で、source hash 付きの保存 JSON だけを読む。

## 独立レビュー

観点の違う 2 つのレビュー（原典・数値・本文／検証の仕組みと記録）を行った。価格式・原典の数値・独立参照の中核に誤りはなかった。
受入を止めた指摘は VS05 の可視化の根拠画像（F1）の 1 件で、残る 18 件は P3。すべて対応した。
修正範囲に絞った再レビューでは P1/P2 と退行は無く、F1–F19 のうち 17 件を確認済みとした。
残る 2 件（F3・F7）の不足と新しい P3 の 4 件を N1–N6 としてまとめ、すべて直した。詳細は FEEDBACK にある。

## 共有ファイルの変更と既受入節

vol10 の notebook・builder・`figures.py` を変えたため、既受入 §26.9–§26.15 のテスト（1,232 passed / 6 skipped）と
Book/portal の再検査を最終ビルドで回し、`m8-recheck.json` / `browser-m8-recheck.json` を台帳の現行証跡にした。過去の記録は残してある。

## 限界

- 複製は連続パス・連続観測の拡散を仮定する。Hull の契約は日次の離散観測で、離散観測の補正は GBM の 1 ケースでしか測っていない。
- ジャンプ、現金配当、CBOE VIX の完全な手順は対象外。
- Example 26.4/26.5 以外の市場は合成。誤差は選んだ市場と格子の実測で、全域の上界ではない。
- PASS は教材と実装の整合・数値恒等式・再現性を表し、実市場での性能を承認するものではない。
