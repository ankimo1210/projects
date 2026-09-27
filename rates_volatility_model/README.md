# Rates Volatility Model

金利ボラティリティモデルを日本語で学ぶ Jupyter ノートブックと、その計算部分をまとめたテスト付きパッケージ `ratesvol`。データはすべて合成。

## 中身

| パス | 役割 |
|---|---|
| `rates_volatility_models.ipynb` | 本体。Ch0 カーブの基礎 → Ch1–2 Black-76 / Bachelier → Ch3–6 Vasicek / CIR / Hull-White 1F / G2++ → Ch7–8 HJM / LMM → Ch9 SABR → Ch10 RFR 複利 → モデル比較 → Ch11 スマイル（SABR サーフェス・SVI・RR/BF）→ 付録 A/B（SABR サーフェス・ボラキューブ） |
| `src/ratesvol/` | モデル実装。ノートブックはここから import する（`options` / `curves` / `short_rate` / `market_models` / `smile` / `rfr`） |
| `tests/` | 単体テスト（解析解・無裁定条件・独立実装との一致）と、ノートブック全体の実行テスト |
| `docs/STATUS.md` | 完成条件と検証状況 |

## 動かし方（リポジトリのルートで）

```bash
uv sync --all-packages --inexact     # 共有 .venv に ratesvol を editable で入れる
uv run --no-sync jupyter lab rates_volatility_model/rates_volatility_models.ipynb
uv run --no-sync pytest rates_volatility_model/tests
```

## 規約

- 金利・ボラは小数（0.03 = 3%）。bp 表示は ×1e4。
- 乱数は `numpy.random.Generator` を引数で渡す。ノートブックは Ch0 で作る `RNG` を全章で共有する。
- ノートブックを編集したら `tests/test_notebook_executes.py` を通す。このテストは ipywidgets が握りつぶす例外（`interact` と `Output`）を表に出す。普通のヘッドレス実行ではインタラクティブセルの失敗が見えない。

## 既知の限界

- データは合成。実市場のカーブ・スマイルではない。
- SABR は Hagan (2002) の lognormal 近似のみ。長い満期・低いストライクで崩れる（負の確率密度）。マイナス金利向けの shifted / normal SABR は無い。
- 短期金利・HJM・LMM のシミュレーションは Euler（Vasicek のみ厳密遷移）。価格は MC 標準誤差の範囲で検証している。
- SVI の $g(k)$ 検査は $k\in[-1.5,1.5]$ の数値グリッド上で行う。全ストライクに対する厳密な無裁定保証ではない。
- 保存済みの対話型セル出力は初回描画を省いている。Jupyter でセルを再実行すると操作できる。
- スワップションの解析価格（Jamshidian など）と Bermudan は扱わない。
