# analytics 完成度監査と完成プラン — 2026-08-16

`analytics/` 配下の教材9冊 + SDE Web アプリ + 統合ポータルについて、
「未完成の部分」を機械的に洗い出した結果と、それを閉じるためのプラン。

対象コミット: `fff2cd6f`

> **2026-08-17 追記 — 実行結果**
> Phase 0〜5 をすべて実施した。S1–S10 のうち **S1〜S9 は完了**、S10 は完了だが
> その過程で sde-book のレビュー指摘 3 件(C-5 / C-6 / C-7)が未着手のまま残っていることが
> 確定した(見送りではない。`sde-book/docs/2026-08-02-review.md` の対応状況表に記録)。
> 実行後の状態は §6 にまとめてある。

---

## 1. 監査方法

主張ベースではなく、実行と走査で確認した。

| 検査 | 手段 | 結果 |
|---|---|---|
| テスト | `uv run pytest analytics -q` | 968 passed (28.9s) |
| ビルド | `make books` | EXIT=0、全10冊 |
| ポータル | `make report` | EXIT=0 |
| SDE アプリ | `make sde-check` | EXIT=0、typecheck/lint 警告0、6/6 pass |
| TOC 整合 | `_toc.yml` の全エントリに実体ファイルがあるか | 欠落0 |
| 出力欠落 | 全 `.ipynb` の code セルに outputs があるか | 欠落0 |
| 空セル | 全 `.ipynb` | 0 |
| 欠陥B（CJK 約物×太字） | `{admonition}` 展開 → markdown-it 描画 → 残存 `**` 計数。既知の壊れた文字列と修正後文字列で検算済み | 全10冊 0件 |
| 欠陥C（`$$` の前後空行） | markdown セル走査 | 全10冊 0件 |
| 完成度マーカー | `TODO` / `未実装` / `予定` / `placeholder` を README と notebook 双方に | 下記 S1–S3 を検出 |
| ポータル被覆 | `report/report_builder/` `report/templates/` を教材名で grep | 5冊のみ |

`make books` のビルド警告20件は myst-nb の
`skipping unknown output mime type: application/vnd.plotly.v1+json` のみ。
生成 HTML に `Plotly.newPlot` が入っていることを確認済みで、図は描画されている。
本ごとに件数が違うのはインクリメンタルビルドで再読込された本が違うためであり、
教材間の品質差ではない。

---

## 2. 現況

| 教材 | NB | tests | 演習解答章 | キャップストーン章 | 状態 |
|---|---:|---:|:-:|:-:|---|
| `linear_algebra` | 13 | 56 | ✅ | ✅ | 完成 |
| `neural_net` | 14 | 64 | ✅ | ✅ | 完成 |
| `bayesian` | 14 | 55 | ✅ | ✅ | 完成 |
| `fourier` | 10 | 47 | ❌ | ❌ | **最も薄い** (S2) |
| `laplace` | 12 | 46 | ✅ | ✅ | 4章に TODO (S3) |
| `ode-book` | 10 | 35 | ✅ | ❌ | キャップストーン欠 (S4) |
| `pde-book` | 11 | 38 | ✅ | ✅ | 完成 |
| `machine_learning` | 14 | 59 | ✅ | ✅ | 完成 |
| `statistics` | 11 | 142 | ❌ | ❌ | **3章欠落** (S1) |
| `quant_research` | 66 | 421 | — | — | B1–B11 44週 100%（Stage 3 / Capstone は意図的に対象外） |
| `sde-book` | 47章 | 6 (node) | ✅ | — | レビュー指摘の一部が未対応 (S5/S6) |
| `report`（ポータル） | — | 5 | — | — | 5冊しか被覆せず (S7) |

---

## 3. 未完成項目

### コンテンツ

**S1. `statistics` に3章欠落** — 本監査で最大の穴

`statistics/README.md` が「予定」と明記している3章が未着手。

| 章 | 内容 |
|---|---|
| `11_frequentist_vs_bayes` | 同じデータを頻度論／ベイズ両流儀で解いて比べる橋渡し章 |
| `12_capstone_three_lenses` | 頻度論／ベイズ／機械学習の3視点キャップストーン |
| `13_exercise_solutions` | 01–11章 演習の解答 |

**全11章に演習があるのに解答章が無い**ため、現状は読者が答え合わせできない。
実行時間予算も設計済み（全14章300秒に対し残り3章に247秒）。
計画書は `docs/superpowers/plans/2026-08-01-analytics-statistics-plan3-bridge.md`（1,678行）にある。

**S2. `fourier` が9冊中もっとも薄い**

- 4章に「TODO(発展として追記予定)」を本文中に明記
  - `04` — Plancherel の数値検証 / 変換性質の表 / デルタ関数と定数関数 / SymPy による解析的導出
  - `05` — デルタ関数と超関数 / Green 関数 / 理想フィルタのリンギングと実用フィルタ / バンドパス特徴抽出
  - `07` — wavelet 変換 / CWT スカログラム / 窓関数と COLA 条件 / 定Q変換
  - `09` — 実画像 2D FFT / 音声 WAV とメルスペクトログラム / Fourier features 回帰 / ウェルチ法+サロゲート検定
- 演習セクションが 6/10 章にしかない（04・05・07・09 に無い）
- **演習解答章もキャップストーン章も無い**（両方欠けるのは9冊中 fourier だけ）
- README の環境構築が古い — 「fourier をルート `pyproject.toml` の members に追加したうえで」
  「まだ members に未登録でも」と書いてあるが、**既にメンバー**

**S3. `laplace` の4章に TODO**

README は「03・07・08」と書いているが、実際は **11 章にもある**（README の記載漏れ）。

| 章 | 未追加項目 |
|---|---|
| `03` | ヘヴィサイド展開定理の手計算 / `scipy.signal.residue` / むだ時間 $e^{-as}$ |
| `07` | フィルタ付き微分の実装可能 PID / 状態空間表現 / 離散化 |
| `08` | ラプラス–スティルチェス変換と M/M/1 / 期間構造 / 特性関数との対応 / SDE 生成作用素 |
| `11` | サンプリング定理・エイリアシング / DTFT・DFT / 双一次変換フィルタ設計 / 連続コントローラ離散化 |

**S4. `ode-book` にキャップストーン章が無い**

`pde-book` には `10_capstone_three_lenses.ipynb` があるのに ODE 側に無い。
2分冊で構成を揃える方針に対して非対称。

**S5. `sde-book` レビュー指摘 D-2（未使用足場）が未対応**

`sde-book/docs/2026-08-02-review.md` の21指摘のうち、D-2 が現存を確認できた。

| 対象 | 状態 |
|---|---|
| `app/chatgpt-auth.ts`（90行） | 残存・import ゼロ |
| `db/index.ts`, `db/schema.ts`, `drizzle.config.ts` | 残存・参照ゼロ |
| `examples/d1/` | 残存 |
| `worker/index.ts:7` の `DB: D1Database` | 残存・未使用 |
| `package.json` の `drizzle-orm` | **`dependencies` に残存** |

「外部 API もランタイムダウンロードも要らない自己完結教材」という README の主張と矛盾する。

一方、A-1（ch2 の共有ドメイン）は per-panel ドメイン + `sd(Xₜ)` 数値表示に修正済み、
A-2（二項の正規近似）・C-1（履歴）・C-2（修飾キー）も修正済みであることを実測で確認した。

**S6. `sde-book` の数値回帰テストが薄い**

レビュー D-3 が挙げた7関数のうち、実装されたのは2つだけ。

- ✅ `normalCdf` / `normalQuantile`（互いに逆関数か）、`binomial`（希少事象）
- ❌ `feynmanKacExact`、`backwardValue`、`callValueDelta`（プットコールパリティ）、
  `symmetricStable`（α=2 で正規と一致するか）、`fractionalGaussianPath`（H=0.5 で独立増分か）、
  Vasicek 債券価格（σ→0 で $e^{-\int r}$ に一致するか）

数値計算コードは約4,600行あり、現状の4テストでは劣化を検出できない。

### 統合・運用

**S7. ポータルが5冊しか被覆していない**

`report/report_builder/figures.py` の `BookMeta` は linear_algebra / neural_net / bayesian /
laplace / machine_learning の5冊のみ。fourier・ODE・PDE はリンクカードだけ。
**statistics・quant_research・sde-book はポータルのソースに一度も現れない**（grep 0件）。
README は statistics の未統合には触れているが、残り2つには触れていない。

**S8. `fourier/tests` の47件が `make test` の対象外**

root `pyproject.toml` の `testpaths` に無い。fourier は import 名が `fourier_book` で
ディレクトリ名と異なるため、**testpaths に1行足すだけ**で済む
（`deep_hedge_price` と違い root `conftest.py` の変更は不要）。

**S9. `make sde-check` が `make test` / `make lint` から呼ばれない**

独立ターゲットとしては存在するが、横断チェックの経路に入っていない。
レビュー D-1 の趣旨（誰も回さないと壊れても気づかない）は未達。

**S10. sde-book レビューの対応状況が記録されていない**

21指摘のうちどれが閉じてどれが残っているかが、レビュー文書にも README にも git log にも無い。
今回それを実測し直す必要があった。

---

## 4. プラン

依存関係が薄いので Phase 0 以外は順不同でよい。工数は目安。

### Phase 0 — 見えない破損を止める（〜30分）

先にやる理由: いずれも「壊れても気づかない」状態を解消するもので、
以降の作業の退行検出に効く。

1. **S8**: root `pyproject.toml` の `testpaths` に `"analytics/fourier/tests"` を追加。
   `make test` で47件が回ることを確認
2. **S9**: `make test` から `sde-check` を呼ぶ（または CI 相当の集約ターゲットを作る）。
   Node 未導入環境で落ちないようガードを検討
3. **S2 の README 修正**: fourier README の workspace 登録手順を現状（既にメンバー）に合わせる
4. **S3 の README 修正**: laplace README の TODO 章を「03・07・08」→「03・07・08・11」に

### Phase 1 — statistics を完成させる（最優先・S1）

計画書が既にあるので設計から始める必要がない。

1. `11_frequentist_vs_bayes` — 橋渡し章
2. `13_exercise_solutions` — 01–11章の演習解答（**11 より先に着手してもよい**。
   既存11章の演習が対象なので独立して書ける）
3. `12_capstone_three_lenses` — 3視点キャップストーン
4. `_toc.yml` 追加、`make books` で再ビルド、実行時間が予算内（3章で247秒）か確認
5. README の「予定」を実測値に置き換え

**完成の定義**: 3章が outputs 込みでコミットされ、`make books` が通り、
`analytics/statistics/README.md` の章表に「予定」が残っていないこと。

### Phase 2 — fourier を他書と同水準に上げる（S2）

`statistics` の次に穴が大きい。作業量は Phase 1 と同等かやや大きい。

1. 04・05・07・09 に演習セクションを追加（他6章と同じ形式）
2. `10_exercise_solutions` を新規作成（laplace / ode-book / pde-book の解答章が雛形）
3. `11_capstone_three_lenses` を新規作成（pde-book の `10_capstone_three_lenses` が雛形）
4. 本文中の「TODO(発展として追記予定)」4件を、実装するか、
   「本書の範囲外」と言い切るかのどちらかに決着させる
   — **どちらでもよいが、TODO のまま残さない**
5. `src/fourier_book/` に必要なヘルパを追加した場合は `tests/` も追加

**完成の定義**: fourier の章構成が他書と同型（演習は全章、解答章あり、キャップストーンあり）で、
notebook 内に `TODO` 文字列が残っていないこと。

### Phase 3 — 残りの非対称を潰す（S3 / S4）

1. **S4**: `ode-book` に `10_capstone_three_lenses` を追加（pde-book と対にする）
2. **S3**: laplace 03・07・08・11 の TODO を、Phase 2 の 4 と同じ方針で決着させる
   （実装するか範囲外と明記するか）

### Phase 4 — sde-book のレビュー残（S5 / S6 / S10）

Python 側と独立に進められる（別ツールチェーン）。

1. **S6**: 数値回帰テストを5本追加
   （`feynmanKacExact` / `backwardValue` / `callValueDelta` / `symmetricStable` /
   `fractionalGaussianPath` / Vasicek）。いずれも決定的 seed で数行のアサーション
2. **S5**: 未使用足場を削除（`chatgpt-auth.ts`, `db/`, `drizzle*`, `examples/d1/`,
   `worker` の `DB`）し、`package.json` から `drizzle-orm` を外す。
   `make sde-check` が通ることを確認
3. **S10**: `2026-08-02-review.md` に指摘ごとの状態列（対応済 / 未対応 / 見送り）を追記。
   見送るものは理由を1行書く

### Phase 5 — ポータルを教材全体に追いつかせる（S7）

最後に置く理由: Phase 1–3 で章が増えるため、先にやると作り直しになる。

1. `statistics` を `BookMeta` に登録し、代表可視化をギャラリーに追加
2. `quant_research` と `sde-book` への導線を追加
   （`sde-book` は別ビルドなので、ポータルからは外部リンク扱いになる可能性がある。
   オフライン自己完結の要件と衝突しないか先に判断すること）
3. `analytics/README.md` のポータル説明を実態に合わせる
4. `report/tests` に「全教材がポータルに現れる」ことを検査するテストを追加
   — これがあれば S7 は二度と再発しない

---

## 5. 検査して問題が無かったもの（再調査を避けるための記録）

- 全10冊がビルドできる。`_toc.yml` の参照切れゼロ
- 出力欠落ノートブック・空セルともにゼロ
- 欠陥B（CJK 約物に隣接した `**`）は全10冊で0件。
  2026-08-01 の横断修正（`4dd108db`）以降に追加された `statistics` と `quant_research` にも無い
- 欠陥C（`$$` の前後空行）も0件
- 欠陥A（Plotly フレームの不変トレース再送信）は `go.Frame` の直接使用が全書で0件になっており、
  当時の修正が維持されている
- `quant_research` の Stage 3 / Capstone は**意図的な対象外**（2026-08-11 決定、
  成果物・データ要件が異なるため完成率の分母に含めない）。未完成として数えないこと
- `sde-book` レビュー指摘のうち A-1 / A-2 / C-1 / C-2 / D-1（ターゲット追加分）/ D-3（一部）は対応済み

---

## 6. 実行結果（2026-08-17）

| 項目 | 状態 | 実際にやったこと |
|---|---|---|
| S1 statistics 3章欠落 | ✅ | NB11 橋渡し / NB12 キャップストーン / NB13 解答54問。計画書の数値予測 3 件が実測と食い違ったので、実測に合わせて本文を書き直した(下記) |
| S2 fourier が最も薄い | ✅ | 04・05・07・09 の TODO を実装、全章に演習(計40問)、NB10 解答章、NB11 キャップストーン。実写真/実音声と 2D フーリエ理論は**範囲外と明記** |
| S3 laplace の TODO | ✅ | 03・07・08・11 を実装。SDE 生成作用素のみ範囲外として sde-book に委譲 |
| S4 ode-book キャップストーン欠 | ✅ | NB10「1つの振動を3つのレンズで」。pde-book の対になった |
| S5 sde-book 未使用足場 | ✅ | chatgpt-auth / db / drizzle* / examples/d1 / worker の DB / drizzle-orm 依存を削除 |
| S6 sde-book 数値テスト | ✅ | 6 本追加。5 本は変異注入で非空虚性を確認、Vasicek は σ>0 の凸性項を固定して初めて検出できた |
| S7 ポータル被覆 | ✅ | statistics を BookMeta に登録、quant_research を導線に追加、sde-book は静的 index.html を持たないため除外を**テストで固定** |
| S8 fourier が make test 対象外 | ✅ | root `testpaths` に追加 |
| S9 sde-check が呼ばれない | ✅ | `make test` から呼ぶ(npm 不在ならスキップ) |
| S10 レビュー対応状況が未記録 | ✅ | 22 指摘すべてにソース走査ベースの状態列を追記 |

### 計画時の想定が実測と食い違った点

プラン(`docs/superpowers/plans/2026-08-01-analytics-statistics-plan3-bridge.md`)の数値予測のうち
3 件が誤りだった。**実測を採用し、本文をそちらに合わせた**:

1. キャップストーンデータの端点は -2.9838 / 2.9827 ではなく
   **-2.98356900 / 2.98325961**(4 姉妹本とバイト一致を確認のうえ固定)
2. CV リッジは degree=5 では最小の $\lambda=10^{-4}$ を選び、機械学習レンズは
   最小二乗と一致する(どちらもノルム 7.40)。**滑らかに縮む想定は成り立たない**。
   縮小が見えるのは degree=9(53.7 → 4.2)で、両方をテストで固定した
3. 「事前分布が真の関数の MSE で勝つ」は degree=5 では偽(0.1558 対 0.0488)。
   実際の逆転位置を degree 5→11 の掃引で示す構成に書き直した

### 残っているもの

- sde-book の C-5(凡例が canvas 焼き込み・系列名が aria-label に無い)、
  C-6(軸目盛が両端のみ)、C-7(`s0 = 100` 等のハードコード)。
  いずれも canvas 描画の作り直しを伴うため未着手
- fourier: 実写真・実音声の読み込みと 2D フーリエ理論(**範囲外と決定済み**)
- laplace: SDE 生成作用素とレゾルベント(**範囲外と決定済み**)
- `quant_research` の Stage 3 / Capstone(**2026-08-11 に対象外と決定済み**)
