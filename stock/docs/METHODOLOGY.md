# Methodology

インデックスバスケット計算とウェイト推定の方法論、および公式指数との既知の誤差。

---

## 1. バスケットリターン計算

### 価格加重 (Nikkei 225, DJIA)

公式：
```
Index = Σ(price_i × PAF_i) / Divisor
```

我々の実装：
```python
# t=0 で 1/price_i 株を購入する Buy & Hold
shares_i = 1.0 / price_i_at_start
basket_value_t = Σ (shares_i × price_i_t)
basket_return_t = basket_value_t / basket_value_0 - 1
```

- **PAF (株価換算係数)** は全銘柄 1.0 と仮定 — Nikkei 225 のみ実 PAF と差異
- **Divisor** は使わない（リターン計算では正規化されるため不要）

### 時価総額加重 (S&P 500, NASDAQ-100)

公式：
```
weight_i = float_adj_mcap_i / Σ float_adj_mcap_j
```

我々の実装：
```python
# 現在の発行済株式数を全期間で使用
shares_i = yf.Ticker(t).fast_info.shares  # 現在値
basket_value_t = Σ (shares_i × price_i_t)
basket_return_t = basket_value_t / basket_value_0 - 1
```

- **浮動株調整なし**（総株数を使用） — オーナー保有率の高い銘柄を過大評価
- **NASDAQ の capping rules 未実装** — 上位銘柄を過大評価

### 通貨換算 (JPY → USD)

```python
basket_value_usd_t = basket_value_jpy_t / usdjpy_rate_t
basket_return_usd_t = basket_value_usd_t / basket_value_usd_0 - 1
```

- FX レート: yfinance `JPY=X`（USD/JPY 日次）
- 日次レートで都度換算（為替変動の影響をリターンに反映）

---

## 2. ウェイト推定

### 価格加重
```python
weight_i_t = price_i_t / Σ price_j_t
```

### 時価加重
```python
weight_i_t = (shares_i × price_i_t) / Σ (shares_j × price_j_t)
```

### ウェイト推移
全期間の各日付について上記を計算し、`DataFrame[date × ticker]` として返す（`compute_historical_weights`）。

---

## 3. 公式指数との既知の誤差

### 2024-05-19 〜 2026-05-19（2年）の実測

| 指数 | バスケット | 公式指数 | ETF | バスケット-指数 | ETF-指数 |
|---|---|---|---|---|---|
| N225 | +56.51% | +55.66% | +56.11% | **+0.85%** | +0.45% |
| DJIA | +31.96% | +24.82% | +24.85% | **+7.14%** | +0.03% |
| SP500 | +45.28% | +39.47% | +39.35% | **+5.81%** | -0.12% |
| NDX100 | +69.64% | +55.26% | +55.17% | **+14.38%** | -0.09% |

ETF は全て指数を ±0.1% 以内で追随 → **指数データ自体は正確**。
バスケットが系統的に上振れする原因は以下：

### 原因 1: 構成銘柄入替 (Survivorship / Inclusion Bias)

我々のバスケットは**現在の構成銘柄を過去全期間に適用**する。指数は実際の入替を反映するため差が出る。

#### DJIA 入替例（2024-2026）
| 日付 | 追加 | 除外 |
|---|---|---|
| 2024-02-26 | Amazon (AMZN) | Walgreens (WBA) |
| 2024-11-08 | Nvidia (NVDA) | Intel (INTC) |
| 2024-11-08 | Sherwin-Williams (SHW) | Dow (DOW) |

各銘柄の 2024-05〜2026-05 リターン：
| 銘柄 | リターン | バスケット |
|---|---|---|
| **NVDA** (追加) | **+135%** | 全期間保有扱い → 大幅上振れ |
| AMZN (追加) | +44% | 同上 |
| SHW (追加) | -2% | 中立 |
| INTC (除外) | +237% | 含まれず → 機会損失 |
| DOW (除外) | -35% | 含まれず → リスク回避 |

NVDA の +135% (4.5% 加重) の含有が +7% 上振れの大半を説明する。

### 原因 2: PAF 未対応 (Nikkei 225 のみ)

公式の N225 は値嵩株（Fast Retailing, SoftBank Group 等）に PAF<1 を適用して過大集中を抑制。我々は PAF=1 で計算するため、これらを過大評価。N225 で +0.85% の差はほぼこの寄与。

### 原因 3: 浮動株調整なし (SP500)

SP500 公式は **float-adjusted market cap** を使用（経営陣保有株などは除外）。我々は yfinance の `sharesOutstanding`（総株数）を使うため、Meta（Zuckerberg 保有比率高）等を僅かに過大評価。

### 原因 4: Capping rules 未実装 (NDX100)

NDX100 は modified market cap weighting：
- 単一銘柄 24% 上限
- 上位5社合計 48% 上限
- 四半期 + 年次でリバランス

我々は cap なしで純粋な時価総額比で重み付け → mega-cap（AAPL/MSFT/NVDA 等）の貢献を過大評価。NDX100 の +14% 差の主因。

---

## 4. 不可避な近似

| 項目 | 我々の扱い | 公式 | 影響 |
|---|---|---|---|
| 構成銘柄入替 | 現在構成で固定 | 都度反映 | バスケット +1〜10% |
| Nikkei PAF | 全銘柄 1.0 | 銘柄別 | バスケット +1% 程度 |
| SP500 float調整 | 総株数 | 浮動株のみ | バスケット +0.5% 程度 |
| NDX capping | なし | 上限あり + 四半期リバランス | バスケット +5〜10% |
| 配当 | バスケット・指数とも無視 | 価格指数も無視 | 影響なし |
| 株式分割 | yfinance Close が遡及調整済み | Divisor 調整 | 影響なし |

---

## 5. ETF が指数を正確に追随する理由

ETF (DIA / SPY / QQQ / 1306.T 等) は専門運用会社が：
- **公式の構成銘柄リスト** を都度入替反映
- **公式の浮動株調整 mcap** で実際にリバランス
- 配当を再投資（ETFの場合）

我々のバスケットが「現在構成の Buy & Hold シミュレーション」なのに対し、ETF は「動的にリバランスする実際の運用ポートフォリオ」。

**正確な指数連動を求める場合は ETF をベンチマークに使うべき**。

---

## 6. 改善可能な項目（将来的に）

| 改善 | 効果 | コスト |
|---|---|---|
| Nikkei PAF を手動メンテ CSV | N225 精度 +0.8% 改善 | 月1で公式 PDF 確認 |
| Wikipedia 入替履歴の取得 | DJIA/SP500/NDX 精度大幅改善 | 履歴テーブルのパース実装 |
| NDX capping rules 実装 | NDX 精度 +5〜10% 改善 | 公式 methodology 文書化 |
| SP500 浮動株調整 | SP500 精度 +0.5% 改善 | 浮動株データソース必要（無料無し）|
| 配当再投資オプション | "Total Return" モード追加 | 実装は容易 |

---

## 7. 解釈ガイド

我々のバスケット計算は **「もし今の構成銘柄を◯年前から保有していたら」のシミュレーション**。以下の用途には適切：

- ✅ 現在の銘柄構成での寄与度分析
- ✅ 個別銘柄ウェイトの推移確認
- ✅ 短期間（〜3ヶ月）のリターン近似
- ✅ セクター集中度や上位集中度の可視化

以下の用途には不適切：
- ❌ 長期 (1年+) の正確な指数リターン再現 → ETF を使う
- ❌ 過去の構成銘柄を含めたファクター分析
- ❌ NDX 等 capping ルールある指数の構造分析
