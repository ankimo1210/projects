# rates_volatility_model — status

更新日: 2026-09-27

状態: `rates-vol-completion` ブランチで実装・worktree 検証済み。main への統合と共有 `.venv` への editable 導入は未実施。

## ゴール

ノートブックの数式・数値・文章が正しく、現在の環境で最後まで実行でき、その正しさがノートブックの実コードに対するテストで裏付けられている状態にする。

## 完成条件

1. worktree で `PYTHONPATH=rates_volatility_model/src .venv/bin/python -m pytest rates_volatility_model/tests -q` が緑（単体 60 + ノートブック実行 1 = 61）。統合後の editable 導入・再実行は別途確認する
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
| 10 | SABR の α を vol-of-vol と説明、弱点を「短い満期」と記載、スライダーで β を動かすと ATM 水準が跳ぶ | 文言修正、ATM vol から α を逆算 |
| 11 | Ch10 に複利計算が無い。SONIA・€STR を政策金利と記載、「RFR は単一カーブ」 | `compounded_in_arrears` のデモ、事実関係を修正 |
| 12 | SVI の無裁定条件が必要条件だけ（文は 4/T、コードは 4）で g(k) 検査が無い | g(k) ≥ 0 をペナルティと検査に |
| 13 | 25Δ ストライクを ATM vol で求めていた | スマイル整合デルタ |
| 14 | SABR 式が 3 か所に重複、セルの章ずれ（LMM が Ch9、SABR 表が Ch10） | `ratesvol.smile` に一本化、迷子セル削除 |
| 15 | 再生成パイプラインが壊れていた（part1 生成器が無い、付録は統合版にしか無い＝再統合で 7 セル消える） | 生成器と分割版を廃止し、統合ノートブックを正本に |
| 16 | `VALIDATION_SUMMARY.md`（46 セル・6 テスト・完了）と `SABR_CORRECTION.md` が実態と不一致、`venv/` は空 | 本ファイルと README に置き換え |
| 17 | CIR の Feller 条件を「非負の条件」と説明（実際は 0 に到達しない条件） | 文言修正 |

## 検証

- 2026-09-27: `PYTHONPATH=rates_volatility_model/src /home/kazumasa/projects/.venv/bin/python -m pytest rates_volatility_model/tests -q` → `61 passed in 10.26s`（worktree `rates-vol-completion`、NumPy 2.4.6）。
- `ruff check rates_volatility_model/src rates_volatility_model/tests` → `All checks passed!`。`ruff format --check` → `14 files already formatted`。
- ノートブック 71 セルを検証。保存出力は PNG 11 件、error 出力 0 件、kernelspec は `python3`。実行テストはウィジェットのコールバックも強制実行する。
- 通常のヘッドレス `nbconvert --execute` は対話型サーフェスの初回描画で時間切れになるため、保存出力だけは初回ウィジェット描画を抑えて生成した。ソースは元へ戻しており、対話型の初回表示は Jupyter でセルを再実行すれば描画される。
