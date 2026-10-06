# P5 ロジック先行の実装状態

更新2026-10-06。目的：Ch22–25（台帳36項目）の計算ロジックを実装する。計算対象32項目（§25.5/6の既存価格計算の検証を含む）と、説明中心4項目（§22.7/23.4/24.1/24.3）を区別する。

- 完了条件：本文の式・数値例を節メモで確認し、private計算部品と本文再現・独立検証をそろえ、変更モジュールのtests/ruffを通す。原典入力が足りない箇所は不足を記録し、計算できる範囲を検証する。
- 本人承認のロジック先行方針を継続。計画は既存節メモに数行、1節1コミット/P5 §xx.y、節ごとpush。新公開API・依存追加なし。
- 実装ブランチ：`codex/p5-logic`。P4の計算を引き継ぐ。mainは進捗文書のみ反映する。
- 正式受入：P5 0/36、全体33/306。説明・教材・章受入・全suite・D1・保管庫復元は保留。
- 現在：計算9/32。次は§23.2（EWMA）。Ch22→23→24→25まで継続する。

## 節別の実装

検証件数はその節の変更モジュールの累計で、合算しない。表の完了は記載した計算範囲と対象検証を表す。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 | 対象検証 |
|---|---|---|---|---|
| §22.1 | `_market_risk.py` | 固有の印刷価格なし。正常/tの同じVaR・異なるES、sqrt(N)とAR(1)集計分散。独立裾積分・共分散和、固定seed MCの分位点6SE | 計算部分完了。loss_meanは正が損失。AR(1)はstationary日次SD。規制・説明/教材/正式受入は保留 | 8 passed・ruff check/format PASS |
| §22.2 | `_market_risk.py` | Table22.3の4行（印刷丸め許容.06千ドル）、Table22.4 VaR422.291/ES669.391、BRW VaR653.541/ES約833.2。独立Decimal cash、整数重複分布・分位関数の裾積分 | 計算部分完了。501日原系列は未保有、既知15最悪損失の下側はテスト用合成補完。p521累積.004833は誤植。Hull/Excel/stressedのVaR規約を分離し、250点ESはfractional tail mass。説明・受入保留 | 17 passed・ruff check/format PASS |
| §22.3 | `_market_risk.py` | MSFT/AT&T/相関.3のVaR1,471,300/367,800/1,620,100、ESの厳密値。印刷MSFT ES1,687,000はz2.326で再現。独立正規/対数正規裾積分・固定seed相関MC6SE | 計算部分完了。MSFT印刷ESと厳密ES1,685,629.5の丸め規約差を分離。正規はloss_mean/利益平均の符号を明示、lognormalにsqrt(N)を仮定しない。説明・受入保留 | 27 passed・ruff check/format PASS |
| §22.4 | `_market_risk.py` | Tables22.7/8 分散14404（印刷14406.193との丸め差）、VaR279.222/ES319.894、Ex22.1 sigma7.099、本文3CF30000/30000/1030000。独立多変量求積・債券再評価・mapping求根・FX/OIS cashflow | 計算部分完了。mappingは各cashflowのPV/分散を保存、bookの全cross covariance保存は保証しない。TN25配布先はエラーページ、公式検索に残る設定は確認したが全中間印刷pinは保留。説明・受入保留 | 35 passed・ruff check/format PASS |
| §22.5 | `_market_risk.py` | 脚注10の3 raw moments、TN10 mean−.2/SD2.2/skew−.4→normal−5.326/CF−5.976。独立多変量Gauss求積・二次式の正規区間CDF求根・full Hessian再評価 | 計算完了。CFは第三モーメントの近似で強い歪度で精度・単調性の保証なし。TN10の公式索引の式・例は確認、配布PDF取得不可。説明・受入保留 | 44 passed・ruff check/format PASS |
| §22.6 | `_market_risk.py` | 5000標本99%50位/95%250位。独立線形正規と単調BSM分位点を固定seed MC6SEで照合、full/partial同一shock・実際の10日maturity再評価 | 計算完了。Gaussian arithmetic return、future_bookがtheta/carryの扱いを決める。sqrt(N)はoptionに厳密でない。説明・受入保留 | 50 passed・ruff check/format PASS |
| §22.8 | `_market_risk.py` | 本文1%/7%（100日を明示した合成例）。独立二項和・尤度式・遷移表、将来値を変えても事前予測が変わらないこと | 計算完了。超過頻度だけでESやモデル全体の妥当性は判定しない。本文の標本数は未指定。説明・受入保留 | 55 passed・ruff check/format PASS |
| §22.9 | `_market_risk.py` | 全64loading/8SD、総分散152.5185、87.3%/95.6%/.96bp/2.42bp。Table22.11露出−1.998/−3.067→sigma25.49837/VaR59.31808。独立SVD/固有分解・trace・符号不変 | 計算完了。2631観測は未保有。印刷sigma25.45/VaR59.2は丸め表から一致しないため補正せず記録。市場説明率とbook残余riskを区別。説明・受入保留 | 60 passed・ruff check/format PASS |
| §23.1 | `_volatility_estimation.py` | 固有印刷価格なし。式23.1–6のlog/sample mean/m−1とsimple/zero mean/m、ARCH重みを独立小標本算術と解析MLEで照合 | 計算完了。日次分散を返し年率換算は別。ARCH historyは予測日前までのchronological履歴。説明・受入保留 | 4 passed・ruff check/format PASS |

## 残りと検証

- Ch22：8計算項目、§22.7の説明は保留。HSの501日原系列、PCAの2631観測、TN10の原典数値入力は未保有。
- Ch23：6計算項目、§23.4の説明は保留。原系列からの最尤推定と印刷係数からの再帰を区別する。
- Ch24：7計算項目、§24.1/24.3の説明は保留。P/QのPD、年率hazardと累積PD、回収率と損失率の単位を明示する。
- Ch25：11計算項目（本文の定性節§25.5/6も既存の計算部品を検証）。契約支払と経過分、CDOの全体元本/トランシェ元本を区別する。概観にとどまる動的モデルの実装は研究設計が別途必要。
