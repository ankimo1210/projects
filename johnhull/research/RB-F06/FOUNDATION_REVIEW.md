# RB-F06 独立基礎レビュー

2026-10-09。対象：/tmp/rbf06-research-plan-draft.md（SHA256 5d2ba6f8b81fd8844899405982c5ad41d98cdcfcf77b88fdf590aa0598f238bd）、現行sabr.py（e4e86a37fc722c20159bd5241b493ea8f126aaa9cd97fce23374fb09a9f146d6）、関連test/正本設計。これは実装レビュー・main受入ではない。repository/Git変更なし。

**結論：研究基礎は条件付き適合。Critical 0、実装前に固定すべきImportant 4、補完2。** 918 main-fitの小規模roster、既知IV noise、固定β、nested quote、noiseless固定W、全失敗保存、未使用strikeのvanilla比較は妥当。以下の修正を狭い検証で確認してからprotocolをfreezeする。rootから修正採用予定の連絡を受けたが、実装・test結果は本レビューで未検証。

## Important：具体例と修正

1. **差分J全体の安定性ではrank/nullspaceを認定できない**（草案§3、sabr.py:40–44）。
   独立小実験：F100/T1/β.5/α2/ρ0/ν0、x=±.1、W=I/.0005、D=diag(2,.5,.5)。解析上∂IV/∂ρ=∂IV/∂ν=0でrank1だが、片側3点差分h={1e−4,3e−5,1e−5}は全てrank2。h=1e−5の第2SV=.0037507463、τ=5.6669e−6。step間の相対J差6.80e−6は草案gate1e−5を通る。ε_J=.003854606は偽の第2SVより大きい。対数の取消しが偽ν列を生む。一般反例diag(1,1,1e−9)→diag(1,1,1e−6)も相対差7.06e−7でrankを変える。
   **修正：** 各hのSV/rank、ε_J=max||J_h−J_ref||₂、零/弱方向projectorの変動と||Jv||を保存。小さいmodeがε_Jやτと重なる場合はnumerical_unresolved。ν0解析列とρ0 rank1のregressionを必須にする。tiny positive ν（例1e−10）も対象にする。public SABRは変更せず研究private診断で扱える。right nullspaceは3−rank本を保存し、弱方向price差はbounds内の可行stepのみ。rank不足は内点での局所写像の診断であり、境界では可行方向を保証しない（x+y=0、x,y≥0はrank1でも解が一意）。rootはν0解析列・方向安定性を採用予定。

2. **Q baseline不足は全datasetの支持域を無効にする**（草案§4、代表curveだけでなく全truth固定点）。
   反例：rep≠0でunprofiled best Q=10、truth固定点でQ=1ならΔQ=−9が包含として集計され得る。曲線単位のunsupportedでは、そのdatasetの他parameter判定も誤る。
   **修正：** 同一boundsのbest convergedをbaseline候補として明記し、全profile点・slice・best finiteにもQ比較を実施。より低いfeasible値を発見したdatasetは全LR/包含判定をunsupportedへ。再fitするなら再開始点・予算・全ΔQ更新を事前固定。失敗statusでも低いfinite feasible値があれば無視しない。noiselessの真値Q=0は監査対照に使えるが、真値をoptimizer startへ追加しない。rootはdataset全体の無効化を採用予定。

3. **unknownを非包含へ暗黙変換しない**（草案§2/§4の元16分母/Wilson）。
   8包含・8profile失敗なら、包含数は8〜16の未確定であり「被覆50%」とは確定できない。
   **修正：** contained/noncontained/unsupported/invalidを元16のslot別に保存。k/16は「計算成功かつ包含率」と呼び、unknown u=unsupported+invalidの包含率未確定範囲[k/16,(k+u)/16]を併記する。Wilsonは定義済みのend-to-end Bernoulli指標に限り、unknownを解消するCIとして使わない。成功例だけの率は選択された条件付き記述値。16/16でもWilson95%下端は.806392であり、95%較正は認定できない。rootはunknown分離を採用予定。

4. **数値profileの局所最小値・未探索gapを全支持域と扱わない**（草案§4）。
   4start全てがQ=10へ収束しても、対応sliceがQ=1なら既知のfeasible witnessによる上界1を超え、profile=minという表示と整合しない。非凸profileは複数支持成分を持ち、grid両端が同じ閾値側でも内側に成分が隠れ得る。
   **修正：** 算出値は「multi-start数値profile推定」と明記。数学的profile≤sliceをfeasible witnessで監査し、違反はunsupportedへ。全initial adjacent crossing bracketと観測された支持成分を保存し、unsupported点越しに曲線を接続しない。最大12追加点/curve・最大6/bracket、increasing-grid-orderで予算配分する。細分化未完bracketとcrossing無しgapも未探索interiorを残し、単一CI・全成分の確定とはしない。rootは全bracket保存とglobal12 capを採用予定。profileの定義とpointwise区間の根拠は[Raue et al. (2009), §2.2/§4 Eq.(10), 原著](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)。

## 補完：統計ラベル・全費用上限

- χ²₁(.95)=3.841458820694124は単一parameterのpointwise参考値。正則な線形3parameter例でも、3DのQ差に同値を使った真値同時包含率はχ²₃のCDF=.7208995。現行価格幅は「ΔQ≤3.84146の有限採取fit集合の価格幅」であり、3D95%域・price95%intervalではない。ν0でρも非識別なのでχ²₁や特定混合χ²を自動適用しない。[Raue原著](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)、[Self & Liang (1987), 原著](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf)。sparseのtruth固定profileは2nuisance/2quoteであり、局所完全補間によるΔQ≈0・包含100%も95%較正や識別の証拠ではない。

- **918はmain数だけ。全solver-call capは4830で算術一致。**

  | 固定最大roster | calls |
  |---|---:|
  | main：6×17×9 | 918 |
  | noisy代表grid：6×(a≤14＋ρ≤19＋ν≤17)×4 | 1200 |
  | noiseless ν grid：6×17×4 | 408 |
  | 全noisy truth固定点：6×16×3×4 | 1152 |
  | noisy refinement：18curves×12×4 | 864 |
  | noiseless refinement：6curves×12×4 | 288 |
  | 合計 | **4830** |

  各gridへのbest追加、ρ真値追加を含む。重複点・rep0のtruth点再利用は減少のみ。新しい追加start/refitを入れるなら、この上限から明示予算を割り当てる。400/250 nfevでの保守合計上限は1,345,200 nfevであり、数値Jacobian呼出しは別。local SciPy1.17.1のdocstringでも確認済み。[SciPy公式仕様](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)。pilotでwall/実residual call/各IV・Black callを測り、本前に実call・wall上限、budget到達時の未実行slot保存を固定する。大きなnoise/quote追加sweepは不要。

## 尺度・境界・独立参照の確認条件

- u=(a/.2,ρ/.5,ν/.5)、a=α/10なのでD=diag(2,.5,.5)とWJDは整合。solverがu上のnormalized residualを返すならres.jacは既にWJDであり二重scaleしない。rawJ=W⁻¹ res.jac D⁻¹。noiselessのs_ref=.0005は設計尺度として固定し、noise SD=0では割らない。
- α/rho/nuの有限boundsは探索制約。bound打切りを有限CI・識別成立と解釈しない。外挿holdoutも同じHagan teacherなので、用途の価格誤差診断を超えた市場/モデル性能受入ではない。
- β1/ν0：SDEからlognormal終端、全strike IV=α、ρ非識別。独立Blackと正規密度quadを突合する（価格atol1e−10、IV1e−12候補）。β.5/ν0のρ消失も確認し、exact CEV価格一致は主張しない。[Hagan et al. (2002), 著者が公開した原著、(2.15)/(2.17)/(2.18)](https://www.researchgate.net/publication/235622441_Managing_Smile_Risk)
- 一般ν>0のHagan→Hagan fit・profile/SVDは**Hagan-mapの逆問題検証**。exact SABR pricingの独立受入ではない。原著は漸近展開を用い、低strikeの裁定問題も報告されている。[Hagan et al. (2014), 原著要旨](https://onlinelibrary.wiley.com/doi/abs/10.1002/wilm.10290)

未確認：固定βでの大域単射性、全局所/大域解の捕捉、有限sample LR較正、当該条件のexact SABR近似誤差、市場noiseと用途別許容差。今回の検証は読取・境界差分小実験・線形代数/費用手計算のみ。918-fit/main noise/profile sweepは実施していない。
