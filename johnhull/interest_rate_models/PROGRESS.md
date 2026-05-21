# ir_models.ipynb — Progress & Future Plan

Last updated: 2026-04-30

---

## Overview

John Hull テキストに対応した金利モデル学習用 Jupyter ノートブック。  
ビルドスクリプト `build_ir_models_notebook.py`（2365行）から `ir_models.ipynb`（49セル）を生成する。

---

## Notebook Structure

| Cell | Section | 内容 |
|------|---------|------|
| 00 | Intro | タイトル・説明 |
| 01 | — | `%matplotlib widget`（独立マジックセル） |
| 02 | — | imports, `_kde_xy`, `_t_to_idx`, `_redraw_dist`, `plt.ioff()` |
| 03–06 | 0 | モデル分類 Treemap（plotly）、イールドカーブ4パターン（matplotlib） |
| 07–15 | 1 | 均衡ショートレートモデル: Vasicek / CIR / RB＋比較チャート |
| 16–27 | 2 | 無裁定ショートレートモデル: Ho-Lee / HW / BDT / BK＋比較チャート |
| 28–34 | 3 | フォワードレートモデル: HJM / BGM＋比較チャート |
| 35 | 4 header | Section 4 マークダウン |
| 36 | 4 | キャリブレーション関数定義 |
| 37 | 4 | Pre-compute: 全モデル × 全パターンのキャリブレーション実行 |
| 38 | 4 | 全モデルフィット比較（2×2、4パターン常時表示） |
| 39 | 4.1 | 均衡モデル フィット残差バー（2×2、4パターン常時表示） |
| 40 | 4.2 | 6M フォワードカーブ比較（dense grid、区分定数θブートストラップ） |
| 41 | 4.3 | RMSE ヒートマップ（9モデル × 4パターン） |
| 42–45 | 5 | モデル間対比テーブル（5軸） |
| 46 | 6 | 9モデル × 9観点 サマリーテーブル |
| 47 | 7 | 選択フローチャート（Sankey、plotly） |
| 48 | — | まとめ |

---

## Implementation Status

### Architecture

- **バックエンド**: `%matplotlib widget` + ipympl（全インタラクティブチャート）
- **例外**: Treemap（Cell 04）・Sankey（Cell 47）のみ plotly
- **UI**: ipywidgets FloatSlider + Dropdown
- **更新方式**: `set_xdata/set_ydata` + `fig.canvas.draw_idle()`（再描画コスト最小化）
- **日本語**: `japanize_matplotlib`
- **自動表示防止**: `plt.ioff()`（Cell 02 末尾）→ `comm_id` エラー対策

### Models

| Model | パス+分布 | スライダー | Section 4 |
|-------|----------|----------|-----------|
| Vasicek | ✅ | κ, θ, σ, T | 解析式 |
| CIR | ✅ | κ, θ, σ, T | 解析式 |
| Rendleman-Bartter | ✅ | μ, σ, T | 平均パス + Jensen補正 |
| Ho-Lee | θ(t)チャート | σ, pattern | piecewise-θ bootstrap |
| Hull-White | θ(t)チャート + パス+分布 | a, σ, pattern, T | piecewise-θ bootstrap |
| BDT | ツリー図 | σ | MC bootstrap |
| Black-Karasinski | ✅ | a, σ, T | MC bootstrap |
| HJM | vol/drift チャート | a, σ | 市場完全フィット |
| BGM/LMM | キャップレット価格 | σ | 市場完全フィット |

### Section 4 キャリブレーション詳細

- **均衡モデル（Vasicek/CIR/RB）**: 最小二乗法。`fit_params` にパラメータ保存済み
- **Ho-Lee/HW**: 区分定数θブートストラップ（`calibrate_hl_theta`, `calibrate_hw_theta`）
  - `fit_results` に model 評価値を格納（コピーではなく実評価、RMSE ~1e-12）
  - `hl_theta_store`/`hw_theta_store` を Section 4.2 の dense-grid 評価に使用
- **BDT/BK**: MC bootstrap（simplified、コメント明記）
- **HJM/BGM**: 市場完全フィット（Section 4 からは省略）

### Section 4.2: 6M Forward Curve

- 全テナーを 0.25Y 刻み（t = 0.25〜9.5）で評価
- `f(T, T+0.5) = [log P(0,T) - log P(0,T+0.5)] / 0.5`
- Vasicek/CIR: 解析式 `_vas_logP`, `_cir_logP`
- RB: 補間（spline on 10点）
- Ho-Lee/HW: `hl_logP`, `hw_logP`（区分定数θ → ノード間キンクが可視化）
- BDT/BK: spline on 10 MC 点

---

## Fixes Applied (2026-04-30, Session 2)

実装整合性チェックで以下のバグを修正：

| 対象 | 修正内容 |
|------|---------|
| `_hl_theta_continuous` (旧 `calibrate_ho_lee`) | Section 2 の連続式 θ 計算関数をリネームし、Section 4 の `calibrate_ho_lee(market_zr, tenors, sigma)` との名前衝突を解消。ウィジェットコールバックが Section 4 実行後も正常動作するようになった |
| `_hw_int_B` | `exp(-a*(T-t_hi)) - exp(-a*(T-t_lo))` の指数項の順序を修正 → `exp(-a*(T-t_lo)) - exp(-a*(T-t_hi))`。HW θ 値と Section 4.2 フォワードカーブの形状が物理的に正確になった |
| `calibrate_hl_theta` / `hl_logP` | Ho-Lee の σ 分散項の符号を修正: `- sigma²T³/6` → `+ sigma²T³/6`（正確な公式 log P = -r₀T - ∫θ(T-s)ds + σ²T³/6 に一致）|
| Sankey `target` | `[..., 7, 8]` → `[..., 10, 11]`。フロー先をノード 10（BGM/LMM）・ノード 11（HJM）に修正し、両ノードが図に表示されるようになった |
| Vasicek スライダー群 | 同一セル内の重複定義（`kappa_slider`, `theta_slider`, `sigma_slider`, `t_vas_sl`, `t_grid`, `_N_PATHS`）を削除 |

---

## Fixes Applied (2026-04-30, Session 1)

フィードバック対応として以下を修正：

| 対象 | 修正内容 |
|------|---------|
| `simulate_cir` | Reflected Euler である旨コメント追加（厳密は非中心χ²サンプリング） |
| `black_caplet` | `delta * disc * [F·N(d1) - K·N(d2)]` に変更。割引因子・アクルアルを追加 |
| `rb_zero_curve` | Jensen 凸性補正 `−σ²·z₀²·T²/6` を追加し σ を正しく使用 |
| `calibrate_ho_lee` / `calibrate_hull_white` | `market_zr.copy()` を廃止し piecewise-θ で実評価 |

### 残存する既知の近似

| 箇所 | 近似内容 | 対処 |
|------|---------|------|
| `rb_zero_curve` | Jensen 補正は小σ・μ≈0 の1次近似 | コメント明記済み |
| `black_caplet` | disc = `exp(-F*(T+δ))` はフラットカーブ近似 | コメント明記済み |
| `simulate_cir` | Reflected Euler | コメント明記済み |
| `bdt_bootstrap` / `bk_bootstrap` | Simplified MC | コメント明記済み |
| Section 2 Ho-Lee `calibrate_ho_lee(pattern, σ)` | θ(t) を有限差分で近似 | 教育用として許容 |

**全体評価**: 学習用途として良好。厳密実装ではなく教育的近似実装。

---

## Future Plan

### High Priority

- [ ] **Section 4.2 のキンク解説テキスト追加**  
  Ho-Lee と HW のフォワードカーブにキンクが出る理由（区分定数θの補間による）を Markdown セルで解説する

- [ ] **BK の外れ値対策の根本修正**  
  現状は Y 軸クリップで対処。MC bootstrap のパスを増やす・σ の初期値を調整することで発散を抑制できる可能性がある

- [ ] **Section 4.1 に無裁定モデルの残差を追加**  
  BDT/BK は RMSE ≈ 0 ではなく MC ノイズ分の残差がある。残差バーに含める価値がある

### Medium Priority

- [ ] **CIR の厳密サンプリング実装**  
  `np.random.noncentral_chisquare` を使った Broadie-Kaya 正確サンプリングを別セルで対比展示

- [ ] **rb_zero_curve の凸性補正を一般 μ に拡張**  
  現状の近似は μ≈0 かつ小σ。一般 μ での Var[∫r dt] 解析式を実装

- [ ] **Section 3: HJM の複数ファクター展示**  
  現状は指数型（HW 等価）の単一ファクターのみ。2ファクター HJM との比較

### Low Priority / Ideas

- [ ] **市場実データへの接続**  
  JGB や US Treasury の実際のゼロカーブを読み込んで各モデルでキャリブレーションするデモセルを追加

- [ ] **モンテカルロ収束チェックセル**  
  BDT/BK のパス数 vs RMSE プロットを追加し、MC 誤差の大きさを可視化

- [ ] **Swaption 価格付け**  
  Vasicek/HW の解析式を用いた Swaption PV の計算セルを Section 5 に追加

- [ ] **ノートブック分割**  
  現状 49 セルを Section ごとに分割して読み込み速度を改善（大型ノートブックの UX 問題）

---

## File Structure

```
interest_rate_models/
├── build_ir_models_notebook.py   # ビルドスクリプト（2365行）
├── ir_models.ipynb               # 生成物（49セル、手動編集不可）
├── market_data.py                # 共通マーケットデータ（4カーブパターン）
└── PROGRESS.md                   # 本ファイル
```

## Build Command

```bash
/home/kazumasa/anaconda3/bin/python build_ir_models_notebook.py
```

> `ir_models.ipynb` は `build_ir_models_notebook.py` から自動生成される。  
> ノートブックを直接編集しても次回ビルドで上書きされる。
