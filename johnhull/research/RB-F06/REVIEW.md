# RB-F06 独立最終レビュー

2026-10-09。**教材scopeで approved / approved=true。残 Critical 0、Important 0。**

固定β=.5の **Hagan近似IV写像の逆問題**について、主成果・原価・保存教材を承認する。exact SABR価格／動学、大域識別、保証95%被覆、joint価格包絡、市場・exotic・NN性能は認定しない。raw JSONの teaching_acceptance=False は原記録として保持し、採否は本外部レビューで判断する。関連全suite／tracked release／main反映はrootの別gateで、本レビュー承認に含めない。

## 対象とbinding

- 既存research worktreeをread-onlyで確認。financial source 6件はpilot freezeから不変。金融source・Git・研究原始成果を変更していない。
- main：102 dataset、918 unrestricted＋3480 profile＝4398 solver calls。NPZは23,154,318 bytes／76,160 non-object arrays。
- canonical record: `1cc8f49bdd2d03a966b4c0e74b0f0f0df9e444d99503a4d9f4ee39dc703ba95b`
- typed arrays: `1ad91ea9f180aaf9e4d106651a013d5976f9942e10837a811290c635f53fd9f4`
- frozen protocol: `54fccc16e344f2a1221c477f637f75b556c759c8e28bedcea77ddc0d4c891e7e`
- financial source registry: `028eb8496f68df3b83ba3d33b3bc2cce7f456099e2ebbb20873582dcc1291845`
- NPZ file SHA256: `eebb2b12ac737da8e790df9d943fedf4c43173d2b317d566882a9e751e6c9e86`
- current notebook SHA256: `bd71dba3c7c1f840852836f0ad44582e06253d0689a4ef5a5d68b1ce6efb5e29`
- builder SHA256: `0142a4163af403b57e7cf1123683c07d5a5a2af7139a429a465d7918c7047554`

各financial source／JSON／cost receipt／CAS manifest／3PNGの全hash、102 slotの証拠、検証許容差は隣接JSONに記録した。

## 独立検証

全4398 fitのin-sample IV／raw・scaled residual／Q、全holdout IVと価格、全102 truth holdoutを独立Hagan転記と **math.erfcによる別Black式**で再計算した。最大IV差2.1131e-11、holdout Black差6.8587e-10。Q最大絶対差3.5831e-7はQ約301.67のrho=0 profile点で、全件の差/(1+Q)最大4.0741e-8。IV atol1e-9、Q atol/rtol1e-7の整合範囲内である。tiny-z近似枝の転記差を弱方向精度の認定には使わない。

全fitのraw→theta→scaled J、SVDの第三零値、right-vector直交性／Gram再構成、境界flagsとscaled距離、実呼出数を照合。全918 unrestrictedの保存3step Jを再計算し、870 stable／48 numerical_unresolvedを再現した。別5point差分で代表12最良解を確認し、weak ATM rep0は最小SVが独立1.863e-5対保存9.909e-5、全体相対差2.27e-7だった。保存の **numerical_unresolved** がこの弱方向の不確実性を捕捉している。

別bounded SLSQP 10件（通常full／弱ATM／sparse、およびν=0・truth・交差付近のprofile、各指定start）は全収束、保存Qとの差最大2.11e-9。β=1／ν=0の独立正規密度quad 3 strikeはBlackとの差最大7.11e-15。この解析極限以外のexact SABR検証には拡張しない。

native saved checkerはoptimizer/RNGを禁止してPASS。freshは12指定fit・32 master noise vectorsを再現し、追加検算を主推定へpoolしていない。全40 physical seedを再生成し一意性を確認した。独立式から全34 master quoteを再構成（最大差1.78e-14）し、102 groupのsubselectionを完全一致で確認した。

全102 slotについて独立Qから **全finite fit・870 feasible slice witness・truth点**を再監査し、dataset支持判定／全真値分類／finite訪問価格countが保存集約と一致した。真値参考線までの最小marginは.1071で転記差による分類反転はない。全96 noisy slotはconverged baselineを持ち、unsupported/unknownは0。各cellは元16分母を保ち、known-only Wilsonと元分母boundsを別表示する。noiselessのtruth profile全3軸は実施しておらず、そのunknownをnoisy分母へ混ぜない。

全24 curve、4 nuisance starts／point、全初期隣接crossing、境界打切り、全curve追加12点／bracket6点の上限、重複省略と全attempt割当を確認。未探索内部は未保証のまま保持する。

## 数値的に示せること

| 条件 | noisy最良解のJ未解決/16 | noisy holdout最大IV誤差 | noisy holdout最大価格誤差 |
|---|---:|---:|---:|
| 通常 full | 0 | .0017124 | .0338856 |
| 通常 ATM | 0 | .0883056 | 2.13619 |
| 通常 sparse | 0 | .0545437 | 1.20287 |
| 弱ν full | 2 | .0019901 | .0370223 |
| 弱ν ATM | 4 | .0954349 | 2.39471 |
| 弱ν sparse | 0 | .0269378 | .556141 |

Sparse noiselessはquote残差が約1e-15でも真値と異なるparameterを選び、第三零特異値とnullspaceを保持する。max IV residual<=1e-9かつΔQ<=1e-6を満たす有限converged訪問点だけでも、holdout価格幅最大は通常1.68548／弱ν1.65643。良いquote fitとparameter回復／未使用strike価格安定性を分ける教材として有用である。

元16反復のpointwise真値含有は14–16件。これは95%被覆の認定ではない。参考実用線IV10bp／価格/F2e-4に対して、fullでも各真値3/16がIV線、2/16が価格線を超える。ATM/sparseや弱νを万能な高精度較正法として採用する根拠はない。両fullの価格幅が小さいことも有限訪問点集合内の観測である。

## 原価・保存・表示

最大4830 budgetに対し4398 calls、432未使用。max_nfev400/250、実nfev合計86,611。440,061 residual呼出＋32,343診断呼出。独立metadata総和は全cost項目と一致し、原始Hagan scalar評価1,786,672／Black27,000、費用unknown0／例外0。noiseless weak ATMの5件max_nfev400失敗は全保存され、収束扱いされない。

主CLI196.74秒（user188.96／sys7.37）、内部invocation191.466秒、fit attempt20.381秒／solver18.588秒／checkpoint169.400秒、最終serialization4.427秒。内包関係のある時間を加算しない。全CLI receiptはrecord/sourceへbindし、保存前pending flagは変更せず完了receiptを別記している。実用速度の普遍的比較はしない。

primary／mirrorからrootが独立restoreした各copyを、本reviewerが別々にloadして全数値checkerを再実行、両方PASS。record／typed arrays／23,154,318-byte NPZ hashも一致した。今回はrestore済みcopyの再検査で、reviewerによる再restoreやphysical diskの新監査ではない。

current notebookは4 code cell実行済み、3 PNG、errors0／stderr0。3枚を目視し、notebook内PNGと確認用PNGのbyte hash一致を確認。固定rep0、profile／slice、zero singular value／full nullspace、元16分母、境界／未解決、pointwise reference、finite価格幅の表現を確認した。optimizer/RNG禁止は保存出力にも表示されている。

## 指摘と制限

- **解消 Important：図2のscalar対3step表示。** 最大相対J変化scalarを3点のxへ直接描いていた。current版は保存3行列から各stepの相対差を計算し、scalarの意味も本文に残す。実PNGで修正を確認。
- **解消 Minor：noiseless curveのΔQ-only表示。** IV誤差1e-9を超すQ-only点が通常ATM3／弱ATM7／弱full2あった。finite同等fit価格訪問範囲は当初から正しく除外。current curve/table出力は「ΔQ-only sampled components」と同等fitの追加IV基準を明示する。
- **Minor／root最終化対象：** 直前README/planの「main未完了」とliteral backslash-nは最終記録時に更新する。数値承認や金融sourceの変更は必要ない。
- TRF／SLSQP／有限multi-startと格子はlocal numerical evidence。未探索gap、大域profile最小値、固定bounds外、exactモデルの近似誤差、market noise／用途別許容差は未知。
- 関連全suite／release／main統合の実行結果はrootの別記録で確認する。本レビューはその通過を先取りしない。

Hagan式とSABR SDEの区別は[Hagan et al. (2002)](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf)、nuisance再最適化profileは[Raue et al. (2009)](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)、境界での非正則性は[Self & Liang (1987)](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf)に基づく。特定の混合χ²則を今回へ自動適用しない。
