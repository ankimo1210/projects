# RB-F07 v1 — 較正を通した市場クオート感応度

更新2026-10-07。**v1完了。計算・独立数値検証・研究notebook3図・独立レビュー・既存ゲート確認まで完成。**
承認済み研究計画のv1を実装した。正式な節受入とは別の研究で、受入件数は増やさない。
設計の正本は[既存メモ](../../docs/prep/design/RB-F07_DESIGN.md)、範囲は[研究計画§6.2](../../docs/superpowers/plans/2026-09-27-research-backlog.md)。

## 問いと設計

曲線の柱のリスクと、市場クオートを動かして曲線を再較正するリスクはどう違うか。

- 単一通貨・単一曲線、柱の連続複利zero。預金・FRA・par swapを正方の連立方程式で厳密に較正する。
- 解析Jacobianを使う減衰Newton。独立参照は解析微分を共有しない逐次brentq。
- zero線形補間・区間外フラット。比較用のlog DF線形も区間外はzeroをフラットにする。
- 随伴形 `J.T @ lambda = grad_z` でクオート感応度を求める。価格の直接クオート依存は0。
- 計算は非公開 `hullkit._quote_risk`。公開API・依存・Book/portal・正式台帳を変更しない。

較正残差 $F(z,q)=m(z)-q=0$ が局所可逆なら、

$$
\frac{dz}{dq}=J^{-1},\qquad
\frac{dV}{dq}=\nabla_z V^\top J^{-1},\qquad J=\frac{\partial m}{\partial z}.
$$

クオートは入力順、既定の柱は満期順。明示柱は情報不足の実験にも使える。
債券は支払時刻とcashflowを渡す。日付・day count・多曲線は扱わない。

## 固定した入力と結果

市場データではなく合成fixture。年率は単利、支払期間は時刻の差。

| 商品 | クオート | 柱 | 柱リスク / zero 1bp | クオートリスク / quote 1bp |
|---|---:|---:|---:|---:|
| 6か月預金 | 3.00% | 0.5年 | 0.00 | +106.30 |
| 6×12 FRA | 3.20% | 1年 | +183.54 | +106.19 |
| 年次par swap | 3.30% | 2年 | +154.60 | +220.69 |
| 年次par swap | 3.45% | 3年 | −1,882.89 | −1,822.17 |
| 年次par swap | 3.60% | 5年 | −1,796.20 | −1,844.05 |

ポートフォリオ：4年receiver swap（元本1,000万・固定3.2%）＋1.5年割引債の売り300万。
PVは **−2,980,843.0683**、クオート感応度の合計は **−3,233.038188/bp**。
既存 `swap_rate`・`irs_value_fras`、独立brentqと一致する。

- **柱0でもクオートは0ではない。** 預金の変更がFRAを通じて1年の柱にも効く。
- **座標・残差の書き換えに不変。** zero/log DF座標、quote/PV残差を正しく微分すれば市場リスクは変わらない。
- **補間はモデル変更。** log DF線形のPVは−2,986,256.89、5年swapリスクは約−2,294.84/bp。合計の近さを補間不変性と一般化しない。
- **情報が薄い柱は不安定。** 5年柱を固定して最後のswapを3.1/3.01年満期にすると、増幅は約20.81/208.38 zero bp / quote bp。大きな反対符号のリスクが打ち消し合う。

手計算例（1年預金3%・2年swap3.5%・1.5年割引債100万）は、zero線形補間の
$P(1.5)=P(1)^{3/4}P(2)^{3/8}$ によりPV953,101.4852、感応度−68.17998013 / −70.45357276 per bp。
Hull GE Table4.3の1.75年割引債100万の感応度は、**通貨 / 債券価格1.00**で
`[0, −218.967, −218.967, 5574.455, 4299.115]`。金利bpと単位を混ぜない。

## 成果物と再実行

| ファイル | 役割 |
|---|---|
| [計算モジュール](../../hullkit/src/hullkit/_quote_risk.py) | 商品式・解析微分・Newton・診断・随伴感応度 |
| [24テスト](../../hullkit/tests/test_quote_risk.py) | 手計算・Hull表・brentq・中央差分・不変性・複素ステップ・rank/単位/順序 |
| [reference.json](reference.json) | 入力・結果・独立比較・図の生データ |
| [build_reference.py](build_reference.py) | 研究データの計算と許容差付き照合 |
| [quote_risk.ipynb](quote_risk.ipynb) | 保存データのみから3図を表示する実行済みnotebook |
| [build_notebook.py](build_notebook.py) | notebook生成・artifact-only実行 |

WSLのrepo rootから、共有venvと対象checkoutのhullkitを使う。

```bash
export PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/johnhull/report:$PWD"
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F07/build_reference.py --check
/home/kazumasa/projects/.venv/bin/python -m pytest -q johnhull/hullkit/tests/test_quote_risk.py
# 作り直す場合
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F07/build_reference.py
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F07/build_notebook.py
```

## 検証と境界

- 最初の22テストは未実装でRED、実装後にPASS。順序・金利/価格混在の2検査を加えて計24 PASS。
- 既存rates/swaps・全docstring/索引を含む対象649 tests PASS。変更Pythonのruff check/format check PASS。
- 保存・新規計算の独立数値検査PASS。notebookはfresh実行・nbformat・3枚のPNG目視確認PASS。
- 独立最終レビュー：Critical/Important/Minorすべて0。数式・単位・停止・独立検証・notebook内容を確認、レビュー側でも保存/新規数値照合PASS。
- `verify_release.py --require-tracked` PASS、`verify_section_ledger.py --check-artifacts` PASS（受入33/306維持）。本編の受入・依存範囲を変更しないため、全suite・D1再撮影・Book全buildは繰り返していない。
- 停止条件はquote step正規化残差1e-10以下。非収束はRuntimeError、数値rank不足はValueError。部分較正結果を成功として返さない。
- rankはzero 1bp / quote 1bpまたは価格1.00へ単位を固定したJで判定。増幅10超は研究上の警告値で、生の条件数だけで拒否しない。
- 単位別許容差は既存設計メモ§12。SHA・ビット一致は数値オラクルに使わない。
- 中央差分は打切り領域の二次収束を検査。小さいbumpの丸め誤差は観測として保持し、再生成照合幅は `40*eps*abs(PV)*1e-4/h`。特定のV字右端をOS共通gateにしない。
- 近似勾配を渡す場合、呼出側が `gradient_method="finite_difference"` と明示する。数値だけから解析/近似の由来は判定できない。

v2（非正方・最小二乗）・v3（HW1F swaption較正）・公開API昇格は別承認。
残差が非ゼロの最小二乗では、最適性条件の残差Hessian項が必要で、v1の逆Jを流用しない。
本編への組込み・正式受入・市場性能評価はこの完了に含めない。

## 出典記録

確認は準備時2026-09-27。今回Java実行やStrataとの数値比較は行っていない。

| ID | 資料・確認範囲 | 実装との関係 |
|---|---|---|
| S003 | Marc Henrard, *Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem*, 2011-11-01改訂、§2–3。[確認記録](../../docs/prep/sources/sources_S001-S031.md#s003) | 微分可能・正方・局所可逆、直接依存項。v2最小二乗の保証として使わない |
| L01 | OpenGamma Strata `MarketQuoteSensitivityCalculator` / `JacobianCalibrationMatrix`。[確認記録](../../docs/prep/sources/sources_S032-S062_L01-L03.md#l01)、[公式行列定義](https://strata.opengamma.io/apidocs/com/opengamma/strata/market/curve/JacobianCalibrationMatrix.html) | 格納する向きは `dz/dq`、本実装の `J=dm/dz` と区別。Apache-2.0コードの移植・Java依存追加は行わない |
| Hull | 11e Global Edition Ch4 Table4.3、既存ratesテストと[§4.7準備記録](../../docs/prep/sections/ch04.md) | 債券価格の再較正は既存 `bootstrap_zero_curve` を独立オラクルにする |

## 最終レビューで確認した境界

既承認の範囲を維持した判断で、追加のscope変更はない。

- Final: Ruling: 型拒否の網羅はユーザーの最小入力検証方針に従い対象外。数学的に無効な入力は検査する。将来、型ごとの詳細な拒否契約が必要なら追加検査が要る。
- Final: Ruling: 最小二乗・多曲線・直接クオート依存・HW1F・公開APIとしての堅牢性はv1外。正方局所可逆・直接依存0の条件を明示する。拡張時は式と検証を追加する必要がある。
- Final: Ruling: 小bumpの固定V字・ビット一致は丸め誤差の観測として対象外。単位別許容差とPV規模の比較幅を用いる。最適bump幅のOS共通保証は与えない。
- Final: Ruling: 他branchの正式受入・市場性能・全workspace回帰はこの研究から判定しない。対象649 testsと既存リリース/台帳gateを実行。追加の保証には受入成果の統合、別の市場評価・回帰検査が必要。
- Deferred minors：なし。
