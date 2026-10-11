# 多曲線統合risk / 商品横断P&L

2026-10-11。**正式設計の独立レビュー承認済み（Critical 0 / Important 0 / Minor 1）。原12quote・全144H・四項P&L bridgeを維持し、M1の参照再較正件数を計画へ明記。実装/pilot/main/研究受入は未実施。** 動的モデル横断ヘッジの採否記録後に金融実装・測定へ進める。

- [正式設計](DESIGN.md)／[実装計画](IMPLEMENTATION_PLAN.md)
- [独立設計レビュー](design/multicurve-formal-design-independent-review-v1.md)／[限定decision](design/multicurve-formal-design-independent-decision-v1.json)
- [調査と候補工程](RESEARCH.md)
- [独立再レビュー](../../../docs/superpowers/reviews/2026-10-09-next-research-design-rereview.md)：重要2件修正・未解決0。正式設計・実装・研究受入とは区別。
- [レビュー対象v2草稿](design/reviewed-research-v2.md)：同一バイト保存。正本RESEARCHは保管先の表記だけ整理。
- [初回草稿](design/initial-research-draft.md)：レビュー前の記録を保持。

完了条件は、独立参照・原始成果・全失敗/分母/費用・保存値からの再算出・両保管庫復元・教材・独立レビュー・採否。本編306節の受入件数は変えない。公開API/新依存/実データ利用は本案に含めない。

[4quote小例の実測](design/closed_form_probe.txt)・[ソースと範囲](design/closed_form_probe.json)。12quote本実験のrank/費用/精度とは区別する。
