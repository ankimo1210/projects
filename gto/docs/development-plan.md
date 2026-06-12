# GTO Poker Suite — 開発計画（全体ロードマップ）

最終更新: 2026-06-12
現在地: **M1a 完了**（GameSpec `POST /api/solve` + rake 一般和 + PokerVariant seam + Custom Solve Web）

サポート状況の一覧は [milestone-matrix.md](./milestone-matrix.md)、
各マイルストーンの詳細設計は
[mode-matrix-roadmap-design](./superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md) を参照。

---

## 0. 計画サマリ

2 トラックで進める。**Track A（開発）** は直列、**Track B（計測・計算）** は
GPU/CPU を長時間使うだけなので Track A と並行で夜間に流す。

| 順 | WP | トラック | 内容 | 見積もり | ゲート |
|---|---|---|---|---|---|
| 1 | **WP1: M1b** ✅ | A | flop バインディング + 非同期ジョブ基盤 + Web（**完了 2026-06-12**） | 1–2 日 | — |
| 2 | **WP2: Blueprint 品質ラン** | B（並行） | 頻度重み + 15k iters 計測 | 計算 ~7h（夜間） | — |
| 3 | **WP3: E1 改訂 + 実装** | A | ゲーティング表改訂 → 公開デプロイ + 認証 | 0.5 + 2–3 日 | G1: M1b 完了 |
| 4 | **WP4: M2** | A | 6max v1 + Tournament-HU + 移行 | 4–6 日 | — |
| 5 | **WP5: M3** | A+B | preflop true solve / full hand 製品化 | 週単位（計測ゲート） | G2, G3 |
| 6 | **WP6: M4** | A+B | PLO 実験トラック | 3–4 日 + 計測 | G4 |

E2（履歴永続化）/ E3（運用ハードニング）は E1 完了後の任意挿入。
Billing/Stripe は Phase E 全体で対象外（現方針 = 無料公開 + アカウント）。

---

## 1. WP1 — M1b: flop カスタムソルブ + 非同期ジョブ基盤

ロードマップ上の次のクリティカルパス。spec §4.4 / 受け入れ基準 6–7。

### タスク
1. **`solve_hu_flop` pyo3 バインディング**（現状 CLI のみ・バインディング不在）
   - `Abstraction{buckets_river, buckets_turn}` をシグネチャに露出
   - `py.allow_threads` + 重複カード検証（river/turn_river と同型）
2. **In-process ジョブ基盤**（現状は 2-worker ThreadPoolExecutor のみ）
   - job id / status エンドポイント / TTL 付き結果保存 / cancel
   - メモリ会計付き並列度制御: flop は `floor(free_RAM / 12GB)` = この箱では 1。
     2 本目の flop ジョブは **queue され OOM しない**こと（受け入れ 6）
   - 外部ブローカーなし（YAGNI）
3. **`/api/solve` ルーティング拡張** — flop ボード（3枚）を async tier へ。
   `GET /api/solve/capabilities` に cost class（sync / sync-capped / async）反映
4. **Web Custom Solve** — street-aware UX（river/turn+river は同期表示のまま、
   flop は submit → ポーリング → 結果）。abstraction バッジ + expl ラベル必須（受け入れ 7）
5. **テスト** — バインディング（小 K・低 iters で高速化）、ジョブライフサイクル、
   メモリキャップ、Playwright 実描画

### リスク
- flop ソルブは品質点で 10.5 GB / ~49 分 — テストは縮小構成（K_r=2〜8、iters 数十）で回す
- ジョブ結果の保持メモリ（per-combo 出力が大きい）— TTL と結果サイズ上限を設ける

### 見積もり: 1–2 日（M1a と同規模、subagent-driven 想定）

---

## 2. WP2 — Blueprint 品質ラン（Track B、WP1 と並行）

PROGRESS.md TODO 先頭。開発を止めずに夜間で流す計測タスク。

- `sample_flops` の頻度重み + 15k iters（~7h）で expl がどこまで下がるか
- K_r / K_t 感度（K_r=32→64、K_t ダイヤル）も 1–2 ラン
- 結果は **G2（M3 のブループリント方針）** の入力:
  expl が実用域（目安 < 0.1 bb）に近づくなら M3 で Web 露出を優先、
  停滞するなら f32 テーブル / ボードバケッティング / ディスクバックの基盤投資を先行

---

## 3. WP3 — E1 改訂 + 実装（公開デプロイ + 認証）

E1 spec（2026-06-09）は infra/auth は有効のまま、**ゲーティング表だけ M1 で陳腐化**
（決定ログ: M1 → E1 改訂）。

### 3a. spec 改訂（~0.5 日）
- ゲート対象を `/api/hu/*`（deprecated）から **`/api/solve` + cost class** に変更:
  - sync（river ~1s）/ sync-capped（turn+river ~37s）→ 認証 + レート制限
  - async（flop, 10.5GB/49min）→ **公開デプロイでは 503（local-only）**が現実解。
    公開キュー提供は E3 以降の判断
- turn+river 37s とプロキシタイムアウトの整合（spec 既記載のリスク）を再確認
- gto-cuda preview tier（`/api/solver/solve`, `/api/simulation/run`）の 503 ゲートは既定通り

### 3b. 実装（2–3 日、spec §4 のコンポーネント分解どおり）
- `auth.py`（Supabase JWT 検証）/ `ratelimit.py`（in-memory 30/min, 500/day）/ `config.py`
- multi-stage Dockerfile（gto_py wheel、gto_cuda 除外、Next static export 同梱）
- Web: ログインモーダル（magic link + Google）、NeonShell ユーザーメニュー、
  401 → モーダル、LOCAL バッジ
- デプロイ先（Fly.io / Cloud Run / Railway）+ カスタムドメイン
- 受け入れ: E1 spec §10 の 6 項目

### 備考
re_invest_os で Fly + Supabase 認証の本番実績あり（2026-06-09 デプロイ済み）— 構成を流用できる。

---

## 4. WP4 — M2: 6max ポジションペア行列 v1 + Tournament-HU

ソルバー作業ではなく**レンジデータが律速**（チャート在庫 7/35）。

### タスク（順不同、独立性高い）
1. **チャートデータ**（1–2 日、クリティカルパス）
   - v1 スコープ = BB-as-sole-defender: {UTG,HJ,CO,BTN,SB}-vs-BB SRP + 同 5 つの 3bet pot
   - 不足 8 チャート（BB ディフェンド 3 + opener-vs-BB-3bet 5）。
     公開済み検証チャートのインポート優先（hand-typing は次善）。
     gto-hu preflop 価値モデル由来は禁止（spec 明記）
   - 整合性バリデータ: ディフェンド表の 3bet 頻度 ⇄ opener-vs-3bet 表の照合
2. **/solver・/simulation の gto-hu 移行**（1 日）
   - 両ページを `POST /api/solve` ベースに再構築
   - 移行後 `gto-core` cfr.rs single-street `solve_spot`（CPU フォールバック）を退役
3. **gto-cuda ライブラリの preview 降格**（0.5 日）
   - `equilibrium_claim=false` + UI に "approximation" ラベル
   - uniform-range の扱い: 実チャート重みで再生成（~53 分）するか、uniform ラベルを明示するか決める
   - 3bet pot への拡張は**しない**（low SPR で single-street が最悪）
4. **Tournament-HU**（0.5–1 日）— ante/BB-ante + 10–40bb シャロースタックグリッド
   （F2: HU では ICM ≡ chip EV なので新ソルバー不要）
5. **実験: intra-solve CPU 並列化**（1–2 日、失敗許容）
   - turn_river/flop の 44–48 独立リバー文脈を rayon で並列化
   - 走査が `&mut self` 共有状態を持つため**リストラクチャリング**（注釈では済まない）。
     20 コアで最大 ~10×。結果が **G3（M3 GPU go/no-go）** の入力

### 見積もり: 4–6 日

---

## 5. WP5 — M3: preflop true solve / full hand 製品化（+ ICM）

すべて**計測ゲート**。着手前に WP2 の結果（G2）と WP4-5 の結果（G3）を見る。

1. **HU ブループリント品質**（M 拡大、カードバケッティング）+ Web 露出
2. **6max preflop MCCFR 実験** — 着手前にツリーサイズ/メモリ見積もり
   （169-hand × seats × raise-tree infosets）必須。CPU 数時間〜数十時間、計測で go/no-go
3. **ICM プリセット**（bubble / FT）— multiway preflop が成立した場合のみ
4. **GPU go/no-go** — M3 品質目標が flop ソルブ高速化を要求する場合のみ。
   gto-cuda の NVRTC/FFI シェルを再利用、O(N²) showdown カーネルは不可
   （O(N) two-sweep → segmented scan が必要）。CPU 並列化実験の後に判断

### 見積もり: 週単位（実験結果依存のため上限は切らない）

---

## 6. WP6 — M4: PLO 実験トラック

1. **ランタイム長 range リファクタ** — `[f64; 1326]` → 長さ検証付き `Vec<f64>`
   （7 ソルバーファイル・~90 ホットパス配列）。**NLHE ビット同一**を before/after で検証
2. **k-card blocker 包除原理** — 現行の single-card accumulator は 2 枚ハンド専用
3. **HU PLO river プロトタイプ** — 予想 ~3.5 分 / 2000 iters（CPU、270,725 コンボ）。
   計測して go/no-go（G4）

スコープ外（恒久）: PLO flop/full hand（バケッティング研究前）、
N×N equity model / blueprint value path の PLO 化（二乗メモリ）。

### 見積もり: 3–4 日 + 計測

---

## 7. ゲート（判断ポイント）

| ゲート | タイミング | 判断内容 |
|---|---|---|
| **G1** | M1b 完了時 | E1 spec 改訂に着手（ゲーティング表を GameSpec cost class へ） |
| **G2** | WP2 計測後 | M3 ブループリント: Web 露出先行 or 基盤投資（f32/ボードバケット/ディスクバック）先行 |
| **G3** | WP4-5 実験後 | GPU port go/no-go（CPU 並列化で十分なら GPU 不要） |
| **G4** | WP6-3 計測後 | PLO 続行 or 凍結 |

---

## 8. 横断リスク・留意事項

- **`uv sync`（`--no-sync` なしの `uv run` 含む）が maturin 製 `gto_py`/`gto_cuda` を消す**
  → `maturin develop --uv` で再ビルド（頻発。PROGRESS.md 留意事項）
- **flop ソルブのメモリ** — 品質点で 10.5 GB。この箱では同時 1 本。E1 公開時は 503
- **turn+river 37s** — プロキシタイムアウトと衝突しうる（E1 改訂で扱う）
- **チャートのソーシング** — 公開チャートのライセンス/品質確認が必要。
  hand-typing は整合性バリデータとペアで
- **rayon 並列化は失敗しうる** — `&mut self` 走査の分解が成立しない場合、
  G3 は「GPU port のみが高速化手段」側に倒れる
- **`_data/gto/solutions/` の Parquet は明示依頼なしに消さない** — 再生成 ~53 分。
  再生成時は必ず先にバックアップ（`mv solutions solutions_backup_<date>`）

---

## 9. 参照

- [milestone-matrix.md](./milestone-matrix.md) — 現状サポートマトリクス
- [mode-matrix-roadmap-design](./superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md) — M1–M4 詳細設計（rev 2）
- [phase-e1-public-deploy-design](./superpowers/specs/2026-06-09-phase-e1-public-deploy-design.md) — E1 設計（ゲーティング表は要改訂）
- [PROGRESS.md](../PROGRESS.md) — 完了済み実績・TODO
