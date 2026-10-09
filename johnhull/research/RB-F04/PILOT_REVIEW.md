# RB-F04 数値 pilot 独立レビュー

2026-10-09。判定: **approved — 下記の固定合成実験を主比較前に凍結し、実行してよい。**
主比較・研究採否・教材の最終受入は未確認。Asian 差の識別を承認した記録ではない。

担当は実装作者と別の independent f04_pilot_review。機械可読の正本は [pilot_review.json](pilot_review.json)。
元 pilot JSON の SHA-256 は a08d24eba6ff896dd2a00dedcba2909a576aa1c57e64e0a77072a4674fa0e2c6。
基準 HEAD は e803e00b、対象実装は未コミットのため、各現行ソースの digest を JSON に記録した。

## 検証と判断根拠

- 修正後の full fresh check は **PASS**（35.354秒）。保存された全配列と再計算要約が rtol=1e-8 / atol=1e-10 内で一致し、数値ソース5本の検査開始・終了 digest も一致した。
- pilot と面・経路・参照・統計量の **157 tests PASS**（6.34秒）。review/予算/主設定の結合を確認する **16 tests PASS**。共有 venv の元 checkout 参照を避け、PYTHONPATH にこの worktree の hullkit/src を指定した。
- C/F 各保管庫の blob を独立に読み、28,967,239 bytes、SHA、1,264配列、原始配列からの数値再計算を両方確認した。blob digest は 5d1f0084df7689527d0e0728312d42069a664bebe3cb7eabba679c8aca4bc1bc。
- CF の log-return / stock-measure 正規化・割引、Riccati 時間微分から terminal variance-weighted CF を得る式、Dupire numerator は整合。別実装 CF 積分との固定28 vanilla点の Fourier 最大価格残差は1.28e-13。
- 解析・時間依存分散 PDE、calendar time、境界、共通 Brownian、月次12観測の初期 spot 除外、失敗経路の保持を確認した。conditional は各モデル自身の分母と paired influence function、joint は tail を含む全8,192経路を使う。

## 選択面と凍結条件

joint_refined: 129時点 × 161 z点、z±5、最小時刻1/4096年、order1024、
cutoff512/sqrt(t)、density floor1e-10、明示した行の端の定数延長。
20,769セルすべて支持、支持密度最小約1.26e-9、両モデルの失敗経路0。
768steps で Heston の負 Euler 分散状態80、local の left-wing 延長38経路 / 3,108回を保持する。
wing6 の133未支持セルは NaN のままであり、支持端を延長する感度候補として使用する。

全選択格子を追加検査した。order1024→2048（cutoff固定）の local variance 最大変化1.11e-6、相対4.64e-5。
order2048固定で cutoff を倍増した最大変化1.50e-6、相対6.25e-5。支持変更0。
価格残差の極小性から局所分散まで同精度とは推論しない。

選択面の独立 PDE（1201空間点 / 768時間step）で28点最大残差3.44e-4。
選択面そのものの2401空間点 / 1536時間stepでも最大3.67e-4、
領域幅1.5→3を同じ空間刻みで変えた差は2.31e-14。
空間精細化で最大残差はわずかに増えたため、単調収束や厳密な bias 上限とは呼ばない。

主実験は65,536経路 × seeds9017/9029/9047、steps192/384/768、block2048。
面を含む実値は JSON の main に固定する。

| 数値目標（S0=100、価格は通貨） | 上限 |
|---|---:|
| Asian sampling 95% half width | .01 |
| Heston step empirical refinement | .006 |
| local step empirical refinement | .003 |
| pilot surface empirical refinement | .0005 |
| PDE vanilla residual | .001 |
| Fourier vanilla residual | 1e-9 |
| vanilla MC pointwise sampling multiplier | 6 |
| vanilla MC empirical step allowance | .015 |

選択面と全候補の Asian paired change は max(|mean|+1.96SE)=.000351205。
pilot の最終 vanilla step変化は Heston .0111612 / local .00442603（同じ経験的計算）。
主経路数の sampling half width は pilot から約.00865と予想するが、主比較の実測で判定する。
予算は経験的目標であり、厳密な Asian bias bound ではない。主結果を見て予算を緩めない。
main entry point は review の main / numerical_precision と厳密比較し、review blob の SHA を固定する。

## 読み方と限界

選択面の pilot Asian は Heston5.615052 / local5.609870、local−Heston=-.005182、paired SE=.021629。
この pilot では差を識別できない。主比較でも「未識別」「精度不足」を有効な結果として残す。
SE は sampling のみ。有限28点の再価格は全面の等価性の証明ではなく、PDE は Asian 誤差上限でもない。

conditional の第1 bin は分母 Heston545 / local562でも成功件数は2 / 4。
最低分母件数の支持判定は normal interval の信頼性を保証しない。
local の joint 空セル2個や SE0 を、真の確率0・効果なし・全bin同時信頼区間と読まない。
wing・最小時刻は明示した数値拡張であり、域外の真値を認定しない。

定数 r,q と平方可積分な stock martingale の仮定下では
$E[S_s S_t]=e^{(r-q)(t-s)}E[S_s^2]$。
真の単一時点 marginals が同じなら、固定月次平均の mean / variance も同じになる。
Asian call差は高次 joint-law / 平均分布の形に依存するため、小さい差や未識別は自然である。
この理論上の性質と、有限格子・wing・Euler の数値検査は区別する。市場での優劣は主張しない。

## 発見した欠陥と修正確認

1. **P2: 狭い PDE 領域の支持誤判定。** S100/K150/T1/v.04/r.03/q0/width.2で負call価格約−8.36966を支持扱いにした。境界のITM / OTM条件が成立しない領域を、計算前に unsupported_domain / NaN / 理由として返す修正を実装担当が行った。固定 pilot 条件は支持される。
2. **P2: 修正途中の NPZ 互換性回帰。** 成功結果の追加None metadataがobject配列となり、11pilotテストとfull freshの配列key照合が失敗した。成功時の元grid keysを維持し、未評価時刻をfloatNaNにする修正後、157 tests と全fresh再生成が通った。
3. **P2: review と主実験予算の結合不足。** review済みの面だけでなく、予算と全main設定を厳密照合する修正を実装担当が行った。1ULPの上限変更を含む16 focused testsで確認した。

未解決のblocking defectはない。承認対象の入力・予算・設定を変更する場合は再レビューする。
