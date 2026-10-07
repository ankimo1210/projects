# P8 監査是正 — 完了

更新2026-10-07。対象は旧監査のR1–R4・R6・R11、保存値依存5項目、監査§7の判断事項。
計算修正・根拠保存・改変検出・影響教材の再生成・最終検証を完了。正式台帳は受入33／未評価273／全306を維持する。

[統合検証](validation/p8-2026-10-07/p8-check.json)・[最終D1](validation/p8-2026-10-07/d1-final-check.json)・[画面確認](validation/p8-2026-10-07/p8-browser-check.json)。
origin/main基点のcodex/p8-auditで実施。未受入P3–P7コード、別worktreeのCh1受入、mainの既存未push履歴・market-research変更を保持する。

## 是正結果

| 項目 | 結果 |
|---|---|
| R1 | rough varianceを左端点に更新し、実際の離散カーネル分散で補償。反対変量ペア単位のSE、BSM・平均分散・マルチンゲール参照で検証 |
| R2 | 7つのlogモデルに訓練残差だけのDuan補正。既存10モデル・3horizonを保持 |
| R3 | walk-forward予測を9 held-outケース×10モデル×4戦略へ接続。予測vol／経路vol／共通公正premiumを分離し、独立にポジション・P&L・turnover・リスク指標を再計算 |
| R4 | 正規／Poissonの乱数streamを分離。ジャンプ強度が変わってもBrownian対応を保持し、13起点のpaired payoffとSEを保存・検証 |
| R6 | 補償分解は維持。gross LVR不変は構成上の恒等式と説明を訂正。fee-aware在庫モデルは研究拡張へ |
| R11 | Ch19ロジック側の無利息／無割引表規約の既存検証を照合。教材・正式受入はP4の章受入へ |
| S18-residual | 同一test教師・raw・residual予測配列からMAEを再計算 |
| S18-hard | hard probeの入力・予測・閾値・分母から8種の違反を再計算 |
| S19-start | raw optimizer停止理由・残差・予算・境界を保存し、集約success flagへの依存を除去 |
| S21-timing | warmup・clock・5回の生ns・来歴を保存。中央値を再計算 |
| S22-calendar | holiday・weekday・session・probe入力からカレンダー違反を再計算 |

## 監査§7の判断

| 事項 | 採用した方針 |
|---|---|
| Bookの出力方式 | 既存の実行済み出力をコミットする方式を維持。core19冊・frontier11冊を検証。新レンダラ・依存を追加しない |
| 既定seed | モデルごとの既定値を保持。一括統一しない |
| 出力が変わる修正 | R1・R2・R4を採用し、影響巻18–22の参照・教材を再生成。公開関数のシグネチャは維持 |
| acceptance集合 | 11巻・118チェックの名称・件数・閾値を維持。保存値ではなく生の根拠から合否を判定 |
| vol21のSHA／timing | SHAは配布ファイルの完全性に使用。数値再現は許容差で判定。通常buildは生計測と来歴を保持し、refresh-timing時だけ測り直す |
| 大物の教材配置 | 計算はロジックブランチ、教材の配置と受入はD3の章末まとめ受入で決める |
| FRTB IMA新巻 | Hull外の研究バックログ。P8の完了条件から外す |
| 公開API拡張 | P8では追加しない。昇格・複数満期化などは別の承認対象 |
| research track | 承認済みresearch/<RB-ID>/とhullkit非公開計算を継承。未昇格モデルは研究候補として扱い、性能承認を付けない |
| vol20／21評価設計 | vol20は予測接続済みの合成共通経路評価。外部Phase-1 policyは実positionsがある場合だけ評価。再学習・市場評価・vol21共同較正は後続 |
| 旧ノート・実データ | 旧ノート分割・ライセンスデータ導入は後続。既存の合成オフライン契約を維持 |

## 最終検証

| 検証 | 結果 |
|---|---|
| hullkit＋report全suite | 4,466 passed・6 skipped・既存deprecation warning2件 |
| deep_hedge_price全suite | 209 passed |
| 変更Python25ファイル | ruff check／format check PASS |
| vol19–28独立再生成＋通常再生成 | 2回とも数値許容差付きで一致 |
| ノートブックfresh実行 | core19冊＋frontier11冊PASS |
| Portal／Book | build PASS、影響6巻の18画面状態・18画像・表示数値の改変拒否を確認 |
| 既受入33節D1 | browser／runtime probe／pytest／C:・F:両保管庫からの復元PASS |
| 台帳 | 通常・check-artifacts PASS。受入範囲と要件を維持し、現行証跡の参照だけ更新 |
| tracked release | PASS |
| 独立最終レビュー | Critical／Importantなし。外部policy有限値検証のMinor1件をRED→GREENで修正 |

- 生の根拠の改変／欠損22テストがPASS。数値の1 ULP差がSHAだけで失敗する問題もRED→GREENで是正した。
- 統合テストで見つかった依存宣言、旧timing fixture、教材の鮮度、台帳証跡、旧ファイル名固定テストを修正してから最終全suiteを実行した。
- §26.11のブラウザ起動クラッシュは単独再試行でPASS。失敗した記録も保持する。初回D1の記録は後の表示修正版の記録に置き換えた。
- 画像と検証ログ・検査プログラムは両保管庫に保存し、それぞれから復元を確認。[保存manifest](validation/p8-2026-10-07/p8-validation-manifest.json)。

## 適用範囲と次の作業

- rBergomiは有限格子近似。幅広いパラメータ域での連続モデルへの収束率は承認していない。
- R3はhorizon1／5／21日・各fold最初のheld-out origin、128共通経路。未来の実現分散は評価用経路とoracle premiumだけに使い、forecast学習には使わない。年率volはsqrt(252×variance_sum/horizon)、0.05–1へclipする。
- 評価指標の単位は合成USD。実市場での予測力・取引可能なoracle価格・収益性の承認ではない。
- 次はP3–P7の説明・教材とD3章末まとめ受入。§33.2 flexicapと§36.4 Schwartz–Moonは原典入力不足を維持する。別worktreeではCh1の受入記録を作成済みで、Ch2–9を進行中。P8の台帳・統合には含めていない。
