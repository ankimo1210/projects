# P8 監査是正の実装状態

更新2026-10-06。目的：旧監査のR1–R4/R6/R11・保存値依存5項目を現コードと照合し、欠陥修正/根拠保存/対象改竄検証と必要な成果物再生成を行う。origin/main基点のcodex/p8-auditで作業し、未受入P3–P7コードを混ぜない。

## 作業と完了条件

| 項目 | 作業/完了条件 | 状態 |
|---|---|---|
| R1 | rough varianceの左端点更新/離散補償、antithetic組のSE、独立BSM/マルチンゲール検証 | 対象21 tests PASS・成果物待ち |
| R2 | 訓練残差のみのDuan smearing、10モデル/3 horizonの既存集合を維持 | 未着手 |
| R3 | 予測volと経路vol・共通公正premiumを分離し、walk-forward予測を同一経路の経済指標へ接続 | 未着手 |
| R4 | 正規/Poisson streamを分離、周辺価格/CRN対応/paired SE | Brownian対応回帰PASS・成果物待ち |
| R6 | 補償分解は正しい。gross不変は構成上の恒等式と説明修正。fee-aware在庫モデルは研究拡張へ | 判断済み・文書反映待ち |
| R11 | Ch19ロジック側で無利息/無割引表規約を検証済み、教材/章受入はP4側で扱う | 既存対応の照合済み |
| S18-residual | 同一test教師/raw/residual予測の配列からMAEを再計算 | 未着手 |
| S18-hard | hard probe入力/予測と閾値/分母から違反を再計算 | 未着手 |
| S19-start | raw optimizer停止/残差/予算の根拠を保存し、集約JSON flagを信用しない | 未着手 |
| S21-timing | warmup/clock/5回の生計測と来歴を保存、medianを再計算して照合 | 未着手 |
| S22-calendar | holiday/weekday/session検査の入力と出力を保存、保存違反数を再計算 | 未着手 |

- 正式台帳33/306はこの監査是正では変更しない。Ch1受入worktreeと既存mainの未push履歴・market-research変更を保持する。
- 判断：既定seedはモデルごとに保持し、一括統一しない。公開API/production依存を追加しない。大物の教材配置は章受入に回し、FRTB新巻・研究モデル・実市場評価・旧ノート再編はこの是正から外す。研究の置き場は承認済みresearch/<RB-ID>/を継承する。
- Phase-1 policyは実checkpointの外部positionsがある場合のみ評価する。新しい深層policyを捏造しない。R3は既存4戦略と10モデル×3horizonの予測による合成評価を接続する。
- 検証：各修正は失敗する回帰を確認してから修正、対象tests/ruff、保存根拠改竄。影響巻のreference/notebook/portal/releaseと統合suiteを最終確認する。
