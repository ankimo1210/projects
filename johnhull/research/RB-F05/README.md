# RB-F05 v1 — digitalの微分教師とDML

更新2026-10-07。**v1 digitalの計算・独立検証・6本のCPU学習比較・研究3図を実装。最終レビュー待ち。**
RB-F05全体の完了ではない。離散バリアと0DTE/roughは後続。
設計は[既存メモ](../../docs/prep/design/RB-F05_DESIGN.md)、順序は[研究計画§6.1](../../docs/superpowers/plans/2026-09-27-research-backlog.md)。

## 問いと結果

不連続payoffの正しいGreek教師を使うと、price-onlyよりDMLが良くなるか。
その教師生成・学習費用を含めても、解析式・積分・補間より有利か。

**この固定実験では全3seedで価格・deltaが改善した。しかし標準器への速度採用はしない。**
解析式は約0.12µs/件、ネットは約1.26–1.31µs/件。学習前からネットのonline費用が高く、
費用回収式の分母が正にならない。Hermite補間もネットより速く、精度が良かった。
教育用の教師検証・DML比較は採用する。実市場での優位、論文の学習結果の再現とは呼ばない。

| seed | price-only価格RMSE | DML価格RMSE | price-only delta RMSE | DML delta RMSE |
|---|---:|---:|---:|---:|
| 11 | 0.0060969 | 0.0040863 | 0.0042540 | 0.0012424 |
| 29 | 0.0061232 | 0.0045216 | 0.0038646 | 0.0012768 |
| 47 | 0.0046465 | 0.0044157 | 0.0022824 | 0.0015398 |

delta RMSEの改善は約32–71%。補間は価格RMSE0.00010155、delta RMSE0.00002551。
価格は通貨/現金額1、deltaは通貨/spot単位。p99・最大誤差・満期×距離の全誤差は保存配列に残す。
丸めたこの表を数値オラクルにしない。

## 固定した契約・領域・予算

- 配当なしGBMのcash-or-nothing call、現金額1、K=100、r=3%、sigma=20%。
- S=80–120、T=0.05–2年。train512/validation128は別scenario stream、test200は25 spot×8満期の格子。scenario IDを分離。trainの各scenarioは独立な2048本のpathを使う。
- 初期化seed11/29/47をpaired比較。共通の教師をprice-onlyとLRM-DMLの各単独導入へ同額課金する。split間ではpathを共有しない。
- CPU float64、2 hidden層×32 tanh、discount×sigmoidでdigital価格範囲を守る。Adam lr=.003/full batch。priceの標準偏差・deltaのRMS・featureの平均/標準偏差はtrainだけで決める。
- 価格・物理単位deltaをtrainのscaleで正規化し、DMLには両損失を重み1で足す。validationは診断、testは最終評価で、設定・seed・checkpoint選択に使わない。
- 教師生成・共通optimizer初期化・学習を各8秒に制限。capを次のupdate前に検査するため、最後の1 update等の超過は約0.3–1.3msで、全seedの実測を保存。
- 検証・OOD判定・解析fallbackを追加したoffline/online総費用を保存。既存Python runtime内の観測で、process起動/import費用は全方式で除外。hardware/threadsをJSONに記録する。
- test外の4件（S=70/130、T=.01/.02/3を含む）は固定domain規約で解析fallback。同じ204件のbatchで価格＋deltaの推論を計時する。単一件latencyと混同しない。
- 1000件の総費用はoffline＋1000×秒/件。比較器のonline費用−ネットのonline費用が0以下なら回収不能。seed・領域を落として採用結果を変えない。

## 教師と独立検証

正しいGBMは指数ドリフトをr−sigma²/2とする。digitalの解析価格はdiscount×N(d2)、
deltaはdiscount×phi(d2)/(S sigma sqrt(T))。既存cash_or_nothing、密度積分、中央差分で確認。

| 教師 | 条件・読み方 |
|---|---|
| LRM | 割引payoff×Z/(S sigma sqrt(T))。不偏、短期では分散が増える。解析2次モーメントと独立積分で確認 |
| 素朴なpathwise | 恒等的0。SE=0でも正しいdeltaではない負の対照 |
| 厳密な条件付き期待値 | T/2時点までsimulate、残りGBM増分を厳密に積分消去。同じdigitalの不偏価格/delta。fraction=0では全乱数を消去し解析値になる |
| CRN中央差分 | 共通ZでS±0.1。有限差分の不偏推定であり、真のdeltaに対する打切りbiasとは区別 |
| ramp | K±8のcall spreadに等しい別payoff。独立call spread価格/deltaとは一致し、digitalのdeltaとは異なる |

固定pilotはseed6017・32768本。**主実験を見る前に6SE＋独立参照誤差2e-12を確定**。
主diagnosticは別seed1107・65536本、S=95/100/105とT=.05/1/3/2年。
LRM/条件付き期待値に価格・deltaの6SE検査を適用し、pathwise/rampは負の結果として残す。
MCのSEはIIDのpath axisから計算し、シナリオ平均・seed分散と混同しない。

## 成果物・再実行

| ファイル | 役割 |
|---|---|
| [hullkit非公開教師](../../hullkit/src/hullkit/_digital_teachers.py) | GBM/解析/教師/SE/分散。torchをimportしない |
| [CPU学習](../../../deep_hedge_price/src/deep_hedge_price/_digital_dml.py) | plain array入力、train-only正規化、予算、物理delta |
| [教師テスト](../../hullkit/tests/test_digital_teachers.py) | 独立密度積分・既存binary/call spread・MC6SE・極限 |
| [学習テスト](../../../deep_hedge_price/tests/test_digital_dml.py) | CPU学習・autograd対中央差分・入力単位・費用 |
| [証跡テスト](../../hullkit/tests/test_digital_research.py) | 指標/重み/誤差/費用再計算、prediction/metric/split/cost改竄 |
| [reference.json](reference.json)・[reference.npz](reference.npz) | 契約・費用・全seed、teacher/SE、入力/ID、予測/誤差、数値重み。計約242KB |
| [build_reference.py](build_reference.py) | 固定比較と独立NumPy推論、積分、指標・費用・採否の再計算 |
| [digital_dml.ipynb](digital_dml.ipynb) | artifact-onlyで3図を表示する実行済みnotebook |
| [build_notebook.py](build_notebook.py) | notebook生成・実行。価格付け/学習をbuild中に行わない |

WSLの対象checkout rootから共有venvを使う。重い学習はcheck時に繰り返さない。

```bash
export PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/deep_hedge_price/src:$PWD/johnhull/report:$PWD"
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F05/build_reference.py --check
/home/kazumasa/projects/.venv/bin/python -m pytest -q johnhull/hullkit/tests/test_digital_teachers.py johnhull/hullkit/tests/test_digital_research.py deep_hedge_price/tests/test_digital_dml.py
# 全比較を作り直す場合のみ（時間予算のため、update数・学習結果・計時は変わり得る）
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F05/build_reference.py
/home/kazumasa/projects/.venv/bin/python johnhull/research/RB-F05/build_notebook.py
```

checkは保存配列から独立NumPy forward/chain rule、指標・誤差・費用・採否を再計算し、
独立積分と固定seedのteacher/SE再生成に照合する。SHA・ビット完全一致を数値判定に使わない。
CPU計時や学習結果の環境共通一致は要求しない。全配列を読み直し、成功フラグだけを信用しない。

## 判断・後続

- Ruling: 最小版をdigitalに固定する — 既存設計の教師bias/学習誤差の分離を実行する — バリア/0DTEへは直接一般化できず、後続実験が必要。
- 教師検証・教育資料は採用。速度での標準器昇格は不採用。負の費用回収分母を0や任意の回収件数へ置換しない。
- 離散バリアv2はM15/§26.9の参照に合わせ、無rebateの1契約、監視日/初回/満期/接触と参照精度を確定してから実装する。0DTE/roughはさらに後続。
- 公開API・新依存・本編Book/portal・節台帳の追加なし。既存vol18のaccepted教材/学習配列は変更しない。

## 出典

- Glasserman/Karmarkar, [Differential ML with a Difference, arXiv 2512.05301v2](https://arxiv.org/html/2512.05301v2)、§3.1–3.4。2026-10-07に一次本文を再確認。[S002確認記録](../../docs/prep/sources/sources_S001-S031.md#s002)。
- v2の式(3)/(18)は標準GBM・密度と不整合で、標準密度から独立に導いた教師を使う。著者コード・論文学習値の再現は行っていないため、著者実験の誤りとは判断しない。
- Hull 11e GE §26.10のcash-or-nothingは既存binary pricerとの独立照合に使う。データは合成、論文の本文・図の転載はしない。
