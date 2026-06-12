# GTO Poker Suite — マイルストーン & サポートマトリクス

最終更新: 2026-06-12

---

## 実装マイルストーン

| マイルストーン | 状態 | 内容 |
|---|---|---|
| **Phase 0–3** | ✅ 完了 | モノレポ基盤、評価器、DCFR CPU/GPU、pyo3バインディング |
| **Phase A/D** | ✅ 完了 | ソリューションライブラリ 19,305 spots（Parquet + cache JSON） |
| **Phase B** | ✅ 完了 | Neon UI 全 6 画面（/neon /library /report /solver /simulation /review） |
| **Phase C** | ✅ 完了 | GPU最適化 1.64×（util 67%、fast 0.080 s/spot） |
| **Phase HU** | ✅ 完了 | gto-hu river / turn+river / flop / preflop / blueprint の5 CLI |
| **M1a** | ✅ 完了（2026-06-11） | GameSpec `POST /api/solve` + capabilities、Rake一般和、PokerVariant seam、Custom Solve Web フォーム |
| **M1b** | ✅ 完了（2026-06-12） | `solve_hu_flop` + `flop_dense_table_gb` pyo3バインディング + メモリ会計付き非同期ジョブ基盤 + flop非同期ルーティング + Custom Solve Web 非同期UX |
| **M2** | ✅ 完了（2026-06-12） | 6max v1: チャート8枚+整合性バリデータ、`table=6max`（チャート由来レンジ）、`game=tournament`、/solver・/simulation gto-hu移行、gto-cuda preview降格、単一ストリートCFR退役。残: 14ペア=M3、CPU並列化実験 |
| **M3** | ⬜ 未着手 | プリフロップ true solve（MCCFR）、ブループリント品質ラン、CPU並列化・GPU go/no-go |
| **M4** | ⬜ 未着手 | PLO: `PokerVariant`実装 + HU PLO river prototype |
| **Phase E** | ⬜ 未着手（M1後に着手） | Supabase認証 / Stripe / Cloud Run デプロイ / ドメイン |

---

## サポートマトリクス（M1a 時点）

軸: Game × Variant × Table × Spot × Street

| | **Cash** | **Tournament** |
|---|---|---|
| **NLHE / HU** | ✅ Postflop（下表） | ✅ M2（ante は pot_bb 折込・rake なし・10–40bb presets） |
| **NLHE / 6max** | ✅ M2 v1（opener-vs-BB 5ペア × srp/3bet、チャート由来レンジ） | ✅ 同左（tournament 軸は HU と同条件） |
| **NLHE / 9max** | ⬜ M3（chart authoring） | ⬜ M3 |
| **PLO / HU** | ⬜ M4 experiment | — |
| **PLO / 6max+** | — Non-goal | — |

### Postflop Street 別サポート（Cash / NLHE / HU）

| Street | エンジン | Rake | `equilibrium_claim` | レイテンシ | 状態 |
|---|---|---|---|---|---|
| **River** | gto-hu（exact） | ✅ none/site/live | ✅ true（expl添付） | ~1 s / 2000 iters | ✅ M1a で `POST /api/solve` 対応 |
| **Turn+River** | gto-hu（exact） | ✅ | ✅ | ~37 s / 10k iters | ✅ M1a で対応（sync-capped） |
| **Flop** | gto-hu（K_r=128 bucketing） | ⬜（rake path 未実装） | ✅（expl に抽象化損失込み） | ~49 min / 3k iters | ✅ M1b で `POST /api/solve` 非同期化（202+ジョブ、Web UX） |
| **Preflop** | 簡易 equity モデル（非均衡） | — | ❌ false | ~25 s / 800 iters | ✅ CLI のみ（M3 で true solve） |
| **Full hand** | gto-hu Blueprint（M-flop抽象） | — | ❌（M-flop内 CFR profile） | ~40 min / 1500 iters×7.7× | ✅ CLI のみ（M3 で productization） |
| **Instant-preview（Library）** | gto-cuda（single-street） | ❌ | ❌ false（uniform ranges / flop call→SD） | 0.080 s/spot（precomputed） | ✅ ライブラリ経由 — M2 で "近似" ラベル付きに降格 |

### カスタマイズ可能な軸（M1a、`POST /api/solve`）

| 軸 | 対応状況 |
|---|---|
| Board（3/4/5 cards） | ✅ |
| Ranges（記法 / 重みベクトル / preset） | ✅ |
| Bet sizes（%指定） | ✅ |
| Pot type（srp / 3bet / 4bet / custom） | ✅（pot_bb 必須） |
| Stack（bb） | ✅ |
| Rake（none / site / live / {pct, cap_bb}） | ✅ |
| Abstraction（buckets_river / buckets_turn / max_table_gb） | ✅（flop、M1b で Web露出済み） |
| Iterations | ✅（サーバー側でストリートごとにclamp） |

---

## ソルバー別均衡クレーム

| ソルバー | `equilibrium_claim` | 条件 |
|---|---|---|
| **gto-hu**（river/turn+river/flop） | ✅ true | exploitability（NashConv）数値添付が必須 |
| **gto-hu Blueprint** | ❌ | M-flop 抽象ゲーム上の CFR profile（Full NLHE の expl ではない） |
| **gto-cuda**（ライブラリ） | ❌ false | flop は call→showdown（single-street 近似）、uniform ranges |
| **Preflop trainer** | ❌ | ハードコード近似表 |

---

## 非目標（明示）

- 3+ player 同時均衡 postflop
- PLO フロップ / フルハンド（バケッティング研究前）
- 9max preflop true solve
- PLO の N×N equity model / blueprint value path（二乗メモリ、恒久的 non-goal）

---

## 参照

- 開発計画（WP 分解・見積もり・ゲート）: [development-plan.md](./development-plan.md)
- 詳細ロードマップ: `docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md`
- 進捗詳細: `PROGRESS.md`
- アーキテクチャ: `ARCHITECTURE.md`
