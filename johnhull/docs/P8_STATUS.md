# P8 監査是正の実装状態

更新2026-10-07。目的：旧監査のR1–R4/R6/R11・保存値依存5項目を現コードと照合し、欠陥修正/根拠保存/対象改竄検証と必要な成果物再生成を行う。origin/main基点のcodex/p8-auditで作業し、未受入P3–P7コードを混ぜない。

## 作業と完了条件

| 項目 | 作業/完了条件 | 状態 |
|---|---|---|
| R1 | rough varianceの左端点更新/離散補償、antithetic組のSE、独立BSM/マルチンゲール検証 | 実装/参照成果物再生成・対象21 tests PASS |
| R2 | 訓練残差のみのDuan smearing、10モデル/3 horizonの既存集合を維持 | 実装/参照成果物再生成・対象10 tests PASS |
| R3 | 予測volと経路vol・共通公正premiumを分離し、walk-forward予測を同一経路の経済指標へ接続 | 9 held-outケース×10モデル×4戦略生成、独立P&L/gate再計算PASS・18画面状態の検査PASS |
| R4 | 正規/Poisson streamを分離、周辺価格/CRN対応/paired SE | Brownian対応回帰・13起点のpaired payoff/SE再計算PASS |
| R6 | 補償分解は正しい。gross不変は構成上の恒等式と説明修正。fee-aware在庫モデルは研究拡張へ | negative result/教材の解釈を修正、API/数値は保持 |
| R11 | Ch19ロジック側で無利息/無割引表規約を検証済み、教材/章受入はP4側で扱う | 既存対応の照合済み |
| S18-residual | 同一test教師/raw/residual予測の配列からMAEを再計算 | 根拠配列・gate・改竄検証PASS |
| S18-hard | hard probe入力/予測と閾値/分母から違反を再計算 | 根拠配列・gate・改竄検証PASS |
| S19-start | raw optimizer停止/残差/予算の根拠を保存し、集約JSON flagを信用しない | 根拠配列・gate・改竄検証PASS |
| S21-timing | warmup/clock/5回の生計測と来歴を保存、medianを再計算して照合 | 根拠配列・gate・改竄検証PASS |
| S22-calendar | holiday/weekday/session検査の入力と出力を保存、保存違反数を再計算 | 根拠配列・gate・改竄検証PASS |

- 正式台帳33/306はこの監査是正では変更しない。Ch1受入worktreeと既存mainの未push履歴・market-research変更を保持する。
- 判断：既定seedはモデルごとに保持し、一括統一しない。公開API/production依存を追加しない。大物の教材配置は章受入に回し、FRTB新巻・研究モデル・実市場評価・旧ノート再編はこの是正から外す。研究の置き場は承認済みresearch/<RB-ID>/を継承する。
- Phase-1 policyは実checkpointの外部positionsがある場合のみ評価する。新しい深層policyを捏造しない。R3は既存4戦略と10モデル×3horizonの予測による合成評価を接続する。
- 検証：各修正は失敗する回帰を確認してから修正、対象tests/ruff、保存根拠改竄。影響巻のreference/notebook/portal/releaseと統合suiteを最終確認する。

- R3の評価規約：各horizon(1/5/21日)・foldの最初のheld-out originを共通比較。未来の実現分散は評価用GBM経路とoracle公正premiumにのみ使用し、forecast学習に入れない。年率volはsqrt(252×variance_sum/horizon)、.05–1へclip。市場予測力や取引可能なoracle価格の主張ではない。

## 検証の現在地

- raw根拠の改竄/欠損22 tests PASS。deep_hedge_price全suite 208 passed。hullkit/report初回は4455 passed・6 skipped、9 failures（強化した依存宣言6、旧timing fixture、旧教材、証跡の鮮度）。前8件は修正/対象PASS、D1更新後に最終suite。
- vol19–28の独立再生成と二度目の通常再生成が数値許容差付きで一致。SHAは配布ファイルの完全性だけに使い、数値の合否には使わない。
- vol18 residual MAEは古い評価JSONと約5.1e-8異なったため、保存した今回の教師/予測から再計算。改善関係は不変。
- 残り：notebook/portal/book再生成、画面/リリース検査、最終レビュー、main統合。

- 最終レビュー：Critical/Importantなし。外部policyの有限値検査が抜けた既存API互換性を回復（回帰RED→GREEN、対象7 tests PASS）。型拒否は広げていない。
- 最終D1の33節はbrowser/runtime/pytest/両コピー復元PASS。新予測図のタイトル切替/ラベル/単位も確認した。§26.11のブラウザ起動クラッシュは単独再試行でPASS、失敗した記録も保持。

- 最終deep_hedge_price全suite 209 passed。数値配列の1 ULP差をSHA違いで落とす再生成検査を、配列の許容誤差で判定するよう修正（RED→GREEN、2 tests）。台帳--check-artifacts PASS、受入33件・要件・範囲は保持し証跡参照だけ更新。

- 統合suite再実行は4,465 passed/6 skipped/1 failure。残る1件は旧acceptance-check.jsonというファイル名への固定で、再確認したD1 v2のsection_id・browser/runtime/pytest・保存復元PASSを確認するテストへ更新し、最終suiteを実行する。
