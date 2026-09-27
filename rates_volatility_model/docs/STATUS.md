# rates_volatility_model — status

更新日: 2026-09-27

状態: main に統合済み（マージ `b7480742`）。共有 `.venv` への editable 導入と統合後の検証も完了。

## ゴール

ノートブックの数式・数値・文章が正しく、現在の環境で最後まで実行でき、その正しさがノートブックの実コードに対するテストで裏付けられている状態にする。

## 完成条件

1. main で `uv sync --all-packages --inexact` 後、`uv run --no-sync pytest rates_volatility_model/tests -q` が緑（単体 62 + ノートブック実行 1 = 63）
2. ノートブックのモデル関数はすべて `ratesvol` から import しており、同名関数の再定義が無い
3. 2026-09-27 レビューの指摘 17 件（下表）がすべて解消している
4. README と本ファイルが実態と一致し、旧生成スクリプト・分割ノートブック・旧検証スクリプトが無い

## 2026-09-27 レビュー指摘と対応

| # | 指摘 | 対応 |
|---|---|---|
| 1 | HJM ドリフトが ∫_T^{T_max} を積分していた（「CORRECTED」のコメント付き） | `hjm_drift` を ∫_t^T に。σ 一定で α = σ²(T−t) をテスト |
| 2 | HJM が `np.trapz` を使い NumPy 2.4 で落ちる。ipywidgets が例外を握りつぶし、ヘッドレス実行ではエラー 0 件に見えた | `np.trapezoid`。例外を表に出すノートブック実行テスト |
| 3 | LMM が 2 通り定義され（片方は Ch9 の下）、どちらも測度が不整合、fixing 後もフォワードが動く。旧検証の「E[L]=L」は spot 測度では誤り | spot 測度 LMM を 1 本に。割引債と caplet を Black-76 と照合 |
| 4 | 旧 `test_suite_validation.py` はノートブックでなく自前の再実装を検証。その SABR は補正項が誤り | ノートブックが import する `ratesvol` を pytest で検証 |
| 5 | Bachelier vega を「per 1bp」と表示（実際は per unit、1e4 倍違う）、Black-76 gamma を「per 1%」と表示 | 関数名と表示に単位を明記 |
| 6 | Ch0 の瞬間フォワードが z + dz/dT（×T が抜けていた） | `instantaneous_forward` |
| 7 | Vasicek・G2++ のヒストグラムに重ねた密度が 100 倍ずれていた（% 軸に小数の pdf） | pdf を 1/100 |
| 8 | Vasicek キャリブで r0 を 6M ゼロ金利に固定し短期で 21bp 外れていた。カーブだけでは b と σ が識別できない旨の説明が無かった | r0 も推定、識別性の注記 |
| 9 | G2++ の φ(t) が定数 2% で、カーブにフィットしていなかった | Brigo-Mercurio の φ(t)。MC で初期カーブ再現をテスト |
| 10 | SABR の α を vol-of-vol と説明、弱点を「短い満期」と記載、スライダーで β を動かすと ATM 水準が跳ぶ | 文言修正、ATM vol から最小の正の α を逆算し、解が無い設定は案内を表示 |
| 11 | Ch10 に複利計算が無い。SONIA・€STR を政策金利と記載、「RFR は単一カーブ」 | `compounded_in_arrears` のデモ、事実関係を修正 |
| 12 | SVI の無裁定条件が必要条件だけ（文は 4/T、コードは 4）で g(k) 検査が無い | g(k) ≥ 0 をペナルティと検査に |
| 13 | 25Δ ストライクを ATM vol で求めていた | スマイル整合デルタ |
| 14 | SABR 式が 3 か所に重複、セルの章ずれ（LMM が Ch9、SABR 表が Ch10） | `ratesvol.smile` に一本化、迷子セル削除 |
| 15 | 再生成パイプラインが壊れていた（part1 生成器が無い、付録は統合版にしか無い＝再統合で 7 セル消える） | 生成器と分割版を廃止し、統合ノートブックを正本に |
| 16 | `VALIDATION_SUMMARY.md`（46 セル・6 テスト・完了）と `SABR_CORRECTION.md` が実態と不一致、`venv/` は空 | 本ファイルと README に置き換え |
| 17 | CIR の Feller 条件を「非負の条件」と説明（実際は 0 に到達しない条件） | 見出しと本文を修正 |

## 検証

- 2026-09-27: worktree で `PYTHONPATH=/home/kazumasa/rates-vol-completion-20260927/rates_volatility_model/src /home/kazumasa/projects/.venv/bin/python -m pytest rates_volatility_model/tests -q` → `63 passed in 10.10s`。main で `uv sync --all-packages --inexact` → `rates-volatility-model==0.2.0` を editable 導入し、`uv run --no-sync pytest rates_volatility_model/tests -q` → `63 passed in 11.14s`。
- `ruff check rates_volatility_model/src rates_volatility_model/tests` → `All checks passed!`。`ruff format --check` → `14 files already formatted`。
- ノートブック 71 セルを検証。保存出力は PNG 11 件、error 出力 0 件、kernelspec は `python3`。実行テストはウィジェットのコールバックも強制実行する。
- 保存出力は通常のヘッドレス `nbconvert` で再生成した（128.9 秒、35/35 コードセル実行、error 0、PNG 11 件）。worktree では以下をリポジトリルートから実行する。

```bash
PYTHONPATH="$(pwd)/rates_volatility_model/src" /home/kazumasa/projects/.venv/bin/python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=120 rates_volatility_model/rates_volatility_models.ipynb
```

main の共有 `.venv` から再生成する場合は、リポジトリルートで `uv run --no-sync python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=120 rates_volatility_model/rates_volatility_models.ipynb` を実行する。

- G2++ 対話セル `7aaa0880` の終了から次のコードセルまで 119.7 秒の待ちがあった。原因は未特定。短い全体タイムアウトではここで停止する。

## 既知の残件

- 通常のヘッドレス実行では G2++ 対話セル後に約 120 秒待つ。原因は未特定。
