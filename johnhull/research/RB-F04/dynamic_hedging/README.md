# 動的モデル横断ヘッジ — 研究v1

2026-10-10。**Tasks1–4、Task5統計/protocolとstudy/replay/runner/checkerのprivate source実装・独立レビュー完了（開発branch）。37quotes/18states、tiny全44cells、actual N1024教師を事前測定。Task5全体・正式pilot/freeze/主実験/研究受入・main統合は未完了。** 別execution契約・固定domain・保存再計算・入口の限定source承認を完了。12本の学習・検証sourceと、主実験結果の分割保存接続も限定承認済み。fresh実行器・保存checkerの限定source確認を完了。現在は正式pilotの入力/事前予算固定と、主実験のchunk/保存checkerを開発・確認中。

- [prefreeze revision候補](PREFREEZE_REVISION.md)：旧v1の精度契約は保持。state15.Hの元quote条件拒否とfull Cartesian cacheの未知tailを受け、別execution-readinessと日付固定domainを検討。[独立設計レビュー](prefreeze-review/README.md)でA/Bの限定設計を承認。[private source/TDD・最終独立レビュー](implementation/PREFREEZE_SOURCE.md)を完了、正式pilot/mainは未開封。候補文書はレビュー前snapshotを保持。
- [12本の学習・検証source確認](implementation/NN_CLOSURE_SOURCE.md)：元8,192経路・512更新、全12 NNの2,048検証経路、4×14baseline、保存算術と実費用を接続。38tests・独立6群・索引/docstring1,129件、合成経路での実12fitと分割保存/replayを確認。正式金融pilot/主実験は未完了。
- [独立再計算・保存checker](implementation/FRESH_SOURCE.md)：対象4 sourceを独立承認。82tests、実N1024/13queries/768+1536/16blocksのsaved-only検査、改変8件拒否。正式金融fresh/premium/mainは未実行。
- [上限に達した依存の入口](implementation/DEPENDENCY_CAP_SOURCE.md)：元N・全396枠を理由付きで保持する入口を限定承認。51runner tests・独立6件、金融mainは未実行。
- [正式pilotの予算測定](implementation/PILOT_BUDGET_MEASUREMENTS.md)：元18入力の実2,304再較正とAsian/16blockの6,912query・13再較正936queryを計測。部品raw・原入力の両保管庫復元/算術PASS。main N256の実chunkからexpanded約70–141 GBを参考推計。正式全phase費用・金融資格は未測定。
- [正式実験のsource照合](implementation/PHASE_SOURCE_IDENTITY.md)：全10入口と学習closureを必須登録、bare依存・別checkoutのloaded aliasを照合。48scoped tests、独立14件と実在80ファイルinventoryを確認。正式freezeは未実施。
- [主実験結果の分割保存接続](implementation/MAIN_SINK_SOURCE.md)：元396件の結果を36回に分けてsinkへ渡す。41scoped tests、独立writer例外probe、限定レビュー未解決0。正式金融mainは未実行。
- [追加の測定・証跡](preflight-diagnostics/README.md)：元全36教師slots、実2日付108groups、保存call/put比較と独立feasibility監査。45ファイルの原byte保持、rawは両保管庫からbyte復元済み。追加保管庫の金融semantic認証は未実施。

- [Task5接続・予備測定](implementation/TASK5_CONNECTORS.md)：最終runner27tests・独立レビュー未解決0。latest tiny/教師rawの両CAS復元・saved checker PASS。N1024のSE同時条件6/36、fitunknown1/underresolved5を保持。
- [Task5 helperチェックポイント](implementation/TASK5_HELPERS.md)：未解決0、変更範囲＋索引/docstring1200 tests・5Python ruff/format。候補12fits/44cellsを保存。helper時点の証跡を保持。正式pilotは未完了。
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
