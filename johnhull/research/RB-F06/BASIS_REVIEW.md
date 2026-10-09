# RB-F06 基礎ガード独立レビュー

**結論：今回の基礎ガードは PASS。残 Critical / Important / Minor は 0。** 独立レビューで発見した Important 2 件は修正後に同じ再現例を再検査した。pilot / main / exact SABR pricing の受入は含まない。

- 検査時点：2026-10-09T06:19:28.119312+00:00
- 対象：現在の作業 tree の `_sabr_identifiability.py`、`analytics.py`、`protocol.py/json` と対応 tests。Git は操作・参照していない。
- 前提：F=100、T=1、β=.5、θ=(a,ρ,ν)、α=aF^(1−β)、u=θ/(.2,.5,.5)、IV noise scale=.0005。Python 3.12.3 / NumPy 2.4.6 / SciPy 1.17.1、BLAS 環境変数 1。
- 検証：独立 inline numerical probe exit 0。probe 前後の対象 8 ファイル SHA 一致。作者の対象 18 tests PASS は報告として区別し、同じ suite の再実行は省いた。1 件の max_nfev=1 fit と限定された Jacobian 計算のみで、main noise は生成していない。

## 数値ガード

### ν=0 / tiny positive、scaled J と nullspace

実際の Hagan IV を K=100 exp(±.1)、h=(1e−4,3e−5,1e−5) で検査した。

| ν, ρ=0 | numerical ranks | stability | relative ΔJ | 最小非ゼロ singular / 推定誤差 |
|---|---|---|---:|---:|
| 0 | 1,1,1 | stable_estimate | 3.74e−12 | 2.67e11 |
| 1e−10 | 2,2,2 | numerical_unresolved | 9.47e−7 | .718 |
| 1e−8 | 2,2,2 | numerical_unresolved | 8.38e−6 | .0219 |

`_sabr_identifiability.py:68` の ν0 解析列は ρ列=0、ρ0 で ν列=0。独立 60 桁 Decimal による原著 Hagan 式の ν±1e−8 中心差分（β=.5/1、ρ=−.8/0/.8、3 strikes）との最大 scaled ν列差は 7.11e−15。ν>0 の不安定列を ν0 の解析列で置換せず、`analytics.py:140` が小 singular と step 誤差を比較して解釈を保留する。

raw J @ diag(2,.5,.5) / .0005 = scaled J を 1e−12 で確認した。独立矩形 2×3 行列は padded 第3 singular=0、Vh 3×3、直交・null residual=0。失敗 fit は success=False / status=0 / finite Q を保持し、nfev=1 でも residual_calls=7、diagnostic_calls=7、実測 scalar IV calls=保存値=98。nfev を実費用と誤認しない。

## 今回発見・修正した Important

1. **真値固定点が dataset baseline 監査を通らなかった**（`analytics.py:25`）。
   修正前 `dataset_support(10, [], [{q:1,success:True},{q:10,success:True}])` は supported / included。低 Q の failed truth、truth-only slice 違反も監査から漏れていた。
   修正後は profiles + truth records/scalars + 有限 slice witness を監査する。上記例、failed finite Q=1、failed Q=11/slice Q=1、成功 truth Q=5/slice Q=2 に対して全 dataset を unsupported、全 truth 軸を unknown とすることを独立確認した。最適化成功 flag に関係なく feasible な改善点は基準値の不足を示す。

2. **部分 source registry の自己整合 frozen record を読込側が受理した**（`protocol.py:68`）。
   修正前は `source_registry` を必須 sabr.py を除いた部分集合に in-memory 置換し、同じ registry / canonical digest を持つ frozen record を渡すと通過した。
   修正後は live と saved の両 keyset が全 SOURCES と一致する必要があり、freeze と require_frozen validate の両方で ValueError を確認した。検査時点では必須 6 sources が存在する。実 pilot の承認を意味する検査ではない。

## 支持・率・費用の解釈

- failed profile の低 Q と profile > feasible slice は全 dataset / 全 truth 軸を unknown にする。
- 8 included + 8 unknown は元分母16、known分母8、元率の可能範囲 [.5,1]。known-only Wilson [.67559,1] を元16回の率や95%被覆認定として使わない。
- 交互 Q=(0,5,0,5,0) の独立 fixture は 4 crossing brackets / 3 observed components、両端打切りを保持。unsupported 点を越えて接続せず、未探索 interior / 全支持域非保証の表記を保持する。
- 全40 physical seed は独立 SeedSequence 再生成と一致し、一意。main noise を先に観測していない。
- solver call cap は 918+1200+408+1152+864+288=4830 と roster 総和が一致。refinement は初期 crossing 全保存、全12点/curve・6点/bracket の上限、未解決 bracket の精度未主張が必要。実 runner の執行は別レビュー対象。

## 範囲と限界

この検査は [Hagan 原著 (2.15)/(2.17)/(2.18)](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf) の **近似 IV 写像の逆問題ガード**を検査する。Decimal の式比較も exact SABR の一般価格・動学の検証ではない。step 差は数値誤差の推定であり、構造的・大域的識別の証明ではない。

profile threshold は [Raue et al. 原著](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf) に基づく pointwise の記述的参考値。ν0でρが非識別となるため、[Self & Liang 原著](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf) の特定 χ² 混合分布や95%被覆を自動認定しない。有限訪問 fit の holdout 価格範囲は joint confidence envelope ではない。

reference_methods / build_reference は完全 registry のため digest だけ捕捉し、今回その金融実装をレビューしていない。pending runner、pilot 数値結果、typed review の pilot binding、実 freeze、main の受入は後続。保存 JSON の decision flag だけから金融検証を認定しない。

## Source fingerprint

詳細な probe 数値・再現手順・修正前後の証拠は [rbf06-basis-review.json](/tmp/rbf06-basis-review.json)。

| reviewed file | SHA256 |
|---|---|
| hullkit/src/hullkit/sabr.py | e4e86a37fc722c20159bd5241b493ea8f126aaa9cd97fce23374fb09a9f146d6 |
| hullkit/src/hullkit/_sabr_identifiability.py | 81d91d6fe8e3dbf5a0de1a7a18439a3f10898a897f72744fb3c32eb0c6667fa5 |
| research/RB-F06/analytics.py | 9d6076382a9dd1c308248c6dcf07e7218b3954bd80a62da8795c5e7aea97d135 |
| research/RB-F06/protocol.py | 5b6e47c39f6c7ac0b009027883e29186b8f385961e99e2f622ae6b035d8d632d |
| research/RB-F06/protocol.json | 1d4e7e72e2bed160b3314b907293b75777926ecd065427c7da4baee651f81752 |
| hullkit/tests/test_sabr_identifiability.py | aee5b4870efa037fba799b0b1af506c497f638cc6d3918ff88fb80029727f629 |
| hullkit/tests/test_sabr_identifiability_analytics.py | d59605051b97d78033b8575fcd2bc1a9cef177277bd3931f16a72f7ca8ce4385 |
| hullkit/tests/test_sabr_identifiability_protocol.py | 7dc1e3a8e6f54aefb021c01937395ea13a302dc9d991f4f5b7b816a4c5d591d0 |

## Schema 統合 addendum — 2026-10-09T06:19:28.119312+00:00

root が追加した `analytics.py:208` の全 profile fit witness 経路を独立に再検査した。既存 Important 2 件と数値ガードの評価を保持し、今回の追加統合修正も PASS。残 Critical / Important は 0。

baseline Q=10、成功集約 point Q=(11,12,13)、保存された失敗 profile attempt Q=1 の fixture を用いた。旧 witness 行を in-memory だけで再現すると supported / 3軸 included、現在版は全 dataset unsupported / 3軸 unknown。全 profile 試行を監査するため、point.q が best converged を表していても lower failed finite は隠れない。各軸の元分母1・unknown1・率範囲[0,1]を保持した。失敗 profile Q=None の対照は改善の証拠として扱わず、成功 point の支持を保持した。

独立 schema probe exit 0。変更は基礎対象内では analytics と対応 test のみ。作者の analytics 12 / protocol 6 tests PASS は報告として保存し、suite は再実行していない。core/J・dataset_support/freezeガードの金融計算は追加変更なし。pending runner は対象外。
