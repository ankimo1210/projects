# 動的モデル横断ヘッジ — 研究v1

2026-10-09。**設計・実現性調査・独立数学レビュー、Tasks1–4のprivate source実装・独立レビュー完了（開発branch）。正式pilot/主実験/研究受入・main統合は未実施。** 次はTask5のrunnerと正式pilot。

- [ソース実装チェックポイント](implementation/README.md)：5件の重要指摘を修正・再レビュー承認、変更範囲＋索引/docstring1193 testsと11Python ruff/format。
- [実装設計](DESIGN.md)：Heston/local、月次12fixing Asian、主月次12rebalance、stock/call、再較正市場クオートGreeks、Greek/band/NN全44cell/12fits。
- [実施計画](../../../docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md)：7tasks、exact private interfaces、テスト例、pilot/freeze/main/check/受入。
- [条件付き教師の実現性](CONDITIONAL_FEASIBILITY.md)：追加local spot/ℓ依存、auxiliary GBM control、calendar call PDE、shared drivers、保存/費用。
- [独立設計レビュー](DESIGN_REVIEW.md)：重要2件の修正と、原典/決定的数式probeの確認。
- [設計probe](design/design_probes.json)・[fixed-grid指数moment](design/implicit_cir_moment_bound.json)・[24条件の独立再計算](design/moment_recheck.json)。
- [最初の調査](RESEARCH.md)：当時の候補・小例。現行契約はDESIGN/実施計画を優先。

## 主な設計修正

1. CM2 lognormal variance + old-v stock log-Eulerは株価二次momentが無限となるため撤回。sqrt-CIR drift-implicitに変更し、固定格子/今回パラメータで四次momentの十分条件を数学確認した。新方式の数値精度/実行費用は正式pilotで別に測る。旧LN試作数値は無効範囲を明記して保持。
2. 5%risk改善は、同じpathのd=LNN²−LB²とr=LNN²−.95LB²から両方のCIを計算。random baselineをdelta-only CI外の閾値に置かない。
3. 24/48rebalanceは別の売買頻度・費用条件。内部SDE/教師/gridの精度誤差と混ぜず、主12回の全比較を先に完成する。

主成果は合成Qの動的P&L比較。NN優越や市場運用採用を完了条件にしない。raw failure/支持外/全原始分母、全init、全費用を残す。実市場data、rough、execution、funding/IM/capitalは本v1の範囲外。
