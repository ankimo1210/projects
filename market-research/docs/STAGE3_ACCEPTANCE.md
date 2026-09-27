# 工程3 初版の受入記録

更新日: 2026-09-28

[統合仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md) の
F01–F19 と Q09–Q13 を、初版の採用範囲で照合した記録。
合成データでの計算・画面・ファイル連携を検証した。
認証が要る provider の実通信、古い一括取得ファイルからの過去PIT成績再現、
保存データ研究runの永続化は受入範囲に含めない。

## 機能ごとの行き先

| ID | 初版での扱い | 実装・残る境界 |
|---|---|---|
| F01 | 採用 | 日米株・ETF・FXの日足取得と保存。providerと調整方式を区別。[DATA](DATA.md) |
| F02 | 範囲限定 | 暗号資産の日足。旧market-vizのイントラデイは[退避先](../../_archive/market/market-viz/README.md)に保持 |
| F03 | 採用 | SEC財務・条件付きスクリーナーとテクニカル。[保存データ画面](../src/market_research/app_real.py) |
| F04 | 採用 | 構成基準日とPAF仮定を示すretrospectiveバスケット。過去PIT指数と混同しない |
| F05 | 採用 | 価格の品質・来歴・snapshot、明示FX換算。[入力契約](../src/market_research/contracts.py) |
| F06 | 採用 | ALFRED・ESRI・MoFの保存済み版と公表時刻。推定時刻を区別 |
| F07 | 範囲限定 | e-StatとSECを初版採用。BLS・BEA・Census・BoJ・EDINETの取得は後続 |
| F08 | 採用 | close-to-close、lag1、建玉変化への費用という単一契約。[backtest](../src/market_research/backtest.py) |
| F09 | 採用 | PIT信号・前向き分割・zero/mean/ridge/treeの同条件比較 |
| F10 | 後続 | CPCV・高度モデル・Chronosは現役の[quantkit](../../quantkit/README.md)に保持 |
| F11 | 範囲限定 | 手動ウェイトの仮想リスクのみ。実口座・税計算は接続しない |
| F12 | 後続 | 税/NISAの研究近似はquantkitに保持 |
| F13 | 採用 | 市場概要、相関、品質・欠損、画面内アラート。外部通知は対象外 |
| F14 | 範囲限定 | [合成デモの5ノート](../notebooks/README.md)と自己完結HTML。高度モデルの旧ノートはquantkitに保持 |
| F15 | 範囲限定 | Mag7の固定PIT研究例。自律編集ループは[退避先](../../_archive/market/autostock/README.md)に保持 |
| F16 | 非採用 | AIチャット・コード実行は[旧stock](../../_archive/market/stock/README.md)に保持 |
| F17 | 非採用 | FastAPI・Next.js scaffoldは旧market-vizに保持 |
| F18 | 採用 | 価格・FXの一方向exportと口座側任意adapter。定時レポートの従来経路は維持 |
| F19 | 独立 | JHRMBS・timesfm_lab・labor_ai_quadrant・rates-ui-labは移動しない |

## Q09–Q13 の確認

| 条件 | 実行した検証 | 結果と限界 |
|---|---|---|
| Q09 lag・費用・反転 | [手計算4足](../tests/test_backtest.py)で建玉0/1/0/-1、反転時のturnover 2、最終equity 1.074845079を確認 | 合成の終値近似。実約定の再現ではない |
| Q10 欠損・列・調整方式 | [backtestの拒否テスト](../tests/test_backtest.py)、[datasetの混在拒否](../tests/test_research_dataset.py) | 保有中の欠損、列ずれ、調整方式とproviderの混在を拒否 |
| Q11 将来情報の隔離 | [価格攪乱](../tests/test_research_signals.py)、[purge/embargoとlockbox](../tests/test_research_splits.py)、[Mag7例](../tests/test_autostock_example.py) | 観測済みsnapshotからの判断だけを比較。古い一括取得履歴のPIT成績は不明 |
| Q12 口座境界 | [export](../tests/test_portfolio_export.py)と[adapter](../../portfolio-analyzer/tests/test_market_export.py)のハッシュ・版・鮮度・FX ID検査 | 合成入力。日次レポートは従来経路のメールなし確認を最終同期後に再実行する |
| Q13 画面・再現 | [7画面AppTest](../tests/test_workflow.py)、[保存run](../tests/test_research_run_store.py)、5ノートをnbclientで先頭から実行 | デモはオフライン。手元の保存実データを用いた全画面の目視確認は未実施 |

## 旧バックテストとの差分

同じ4足の合成入力を旧stock・旧market-viz・新engineへ与えた。
日付は2026-09-21〜24 UTC、終値は (100, 110, 100, 105)、
始値は (100, 101, 109, 101)、終値で決める目標は (1, 1, 0, 0)。
元本1、手数料10 bpsとスリッページ5 bps、欠損なし・USDで揃えた。
旧コードは退避前commit 6fbd93ca の stockkit.analysis.backtest.run と
market_viz.analytics.backtest.run_backtest、新コードは
market_research.backtest.run_backtest を実行した。

| engine | 最終equity | 新engineとの差 |
|---|---:|---:|
| stockkit | 0.997138409 | 0 |
| market_viz | 1.086748616 | +0.089610207 |
| market_research | 0.997138409 | 基準 |

3者の建玉は (0, 1, 1, 0)。stockkitの損益は終値間の変化率を使うため
新engineと一致するが、取引ログの価格は次の始値を使う。
market_vizは始値間の変化率を使うため同じ入力でも成績が異なる。
この差を旧成績の移行誤差として隠さず、新契約では終値近似を明示する。
旧実データの成績を自動移管せず、必要なら保存済みsnapshotから再評価する。

## 結論

採用した初版機能は合成データ・画面・オフライン連携で検証した。
移さない固有機能は現役quantkit・macrokitと旧市場索引に残す。
本記録は認証付きライブ疎通や過去のPIT成績を保証しない。
