# P3 完了に向けた実装状態

更新2026-10-05。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- main：§28.1–28.5受入、P3 5/37、全30/276。M30 `5c8bcbde` をFF統合/push、main fresh4223/6・台帳成果物/release/両保管庫PASS。Important1を固定seed消費時replayで4回帰RED→GREEN修正、Minor2保留。
- 現在：本人指示（2026-10-04）でロジック先行へ変更。`codex/p3-logic` に節ごとに実装・本文数値再現・独立検証をcommit/pushし、受入は章末にまとめる。Ch28のロジック8/8（既受入5＋今回3）完了・章末まとめ受入待ち。Ch29のロジック4/4完了・章末まとめ受入待ち。Ch30のロジック4/4完了・章末まとめ受入待ち。Ch31のロジック5/5完了・章末まとめ受入待ち。Ch32のロジック7/7完了・章末まとめ受入待ち。Ch33は§33.1/33.3のロジック完了、§33.2は入力不足で保留。次はCh34。P3ロジック30/37、正式受入5/37。
- 正式受入未完了：§28.6–28.8、Ch29–34（計32節）。多因子測度、市場式、convexity/timing/quanto、短期金利、HW/BK木/curve fit/時間依存sigma/Bermudan/較正、HJM/LMM、非標準swapの本文要件。
- 並行準備：M30多因子の原典/独立132条件付きfixture、TN14/TN19完全PDF/元XLSの回収、31.4回帰と全9点の独立再現。正式受入とは区別する。
- 章末：D3軽量受入（本人承認2026-10-03、PR #11は反映用のopen PR）。共通設定ツールで5軸受入、explanation/rendered必須、章内build/画面確認共有、依存変更節だけD1、全suite1回。節ごとは変更モジュールのtests/ruffのみ。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。TN14/19と31.4元worksheetの取得不足は回収記録で解消。正式数理/実装受入は未完、flexicapのstrike/date不足は保持。HW Q OU/bond式整合はM29で独立RED→GREEN。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）はM29の通常状態更新で未受入33へ整合。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDFとTable31.1完全較正入力の取得不足は[回収記録](prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)で解消。正式受入とflexicapのstrike/対象期間はpending。合成例で代替受入しない。

- M29独立レビュー：96tests/4checksと追加probe PASS。Minor3はportal練習文/極小accrual/極大aの境界として記録し、正式修正は後続。

- 後続準備：Black再訪/交換契約の原典名・独立求積・zero-hit MCのimportance sampling、TN14のequilibrium/curve fit/全Appendix・a=b/rho端/u0/微分方向をscratch照合。正式受入とは区別。

- 後続Ch29–30/Ch32/Ch34の原典全要求と独立scratchをdocs/prep/designへ保存。Ch32は著者DG201の終端1日規約でTable32.3とFig32.9を再現しsigma_R補正案を撤回。正式製品tree/較正/Bermudanは未完、Ch33 flexicap入力不足は保持。

## ロジック先行の進捗（正式受入とは別）

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 |
|---|---|---|---|
| §28.5 互換修正 | `_multi_factor_lesson.py` | teacher/固定seed MCの1e-15差を許容、既存の数値改変拒否も保持 | 章末に配布画面・依存節を再確認 |
| §28.6 | `_forward_black.py` | 印刷例なし。式28.26–29、7市場42価格のQ/T求積・raw MC、rare call 7.1683521394e-8 | ロジック完了。教材・正式受入は章末 |
| §28.7 | `_exchange_measure.py` | 印刷例なし。式28.30–32、33ケース独立求積、配当再投資密度と確率金利4条件MC | ロジック完了。教材・正式受入は章末 |
| §28.8 | `_numeraire_change.py` | 印刷例なし。式28.33–35、9相関条件、TN20 chain rule、独立求積・raw密度MC | ロジック完了。Ch28の章末まとめ受入待ち |
| §29.1 | `_bond_market.py` | Ex29.1: 9.49/7.97、Ex29.2: 122.82/2.36/1.74、独立求積・OU分散MC | ロジック完了。半年複利＋修正duration規約、教材・受入は章末 |
| §29.2 | `_cap_floor_market.py` | Ex29.3: 0.00519百万ドル、d1/d2、25,000/12,500、6支払期間、92/360、独立求積・flat strip・支払測度/日次RFR MC | ロジック完了。RFR midpointのモデル依存バイアスを明示、教材・受入は章末 |
| §29.3 | `_swaption_market.py` | Ex29.4: 2.19百万ドル、A=2.0035（切捨て）、6.194%、d1/d2、184/365、独立求積・annuity測度Q MC | ロジック完了。forwardと割引カーブを分離、教材・受入は章末 |
| §29.4 | `_ir_hedging.py` | 10クオート55 gamma、同一cap/swaptionの4 delta、解析微分・独立SVD、bump縮小で高次差収束 | ロジック完了。有限bumpのdelta合計は一次一致、Ch29受入は章末 |
| §30.1 | `_yield_convexity.py` | Ex30.1: G′−2.6730/G″9.8910、6.097%、5.27/5.18、逆価格求積の二次近似誤差収束 | ロジック完了。CMSのpar bond同一視は局所近似、教材・受入は章末 |
| §30.2 | `_timing_adjustment.py` | Ex30.2: 1.00535/1206.42/0.6302/760.25、8条件の独立求積・raw密度固定seed MC | ロジック完了。constant Gaussianは厳密、rate→ratio loadingは凍結近似、教材・受入は章末 |
| §30.3 | `_quanto.py` | Ex30.3: 15,150.75→15,260.23、Ex30.4: 0.006/0.029/179.83、独立給付求積・raw FX密度MC・American PDE | ロジック完了。Y/XのFX、forward/spotと100段/収束価格を区別、教材・受入は章末 |
| Ch30付録 | `_yield_convexity.py` | 印刷例なし。E[(y−yF)²]=Var+bias²、price平均・Taylor一次/二次/省略項を独立逆価格求積で検証 | ロジック完了。vol/time縮小の高次残差収束、Ch30受入は章末 |
| §31.1 | `_short_rate_pde.py` | 印刷例なし。式31.1–5、定数rate/terminal、Gaussian割引MC・独立PDE微分、flat stochastic curve残差 | ロジック完了。経路積分は台形近似、教材・受入は章末 |
| §31.2 | `_short_rate_models.py` | Ex31.1: 3.30/0.33%、CIR vol0.05、Vas Gaussian求積/CIR Riccati・χ²求積/厳密時点MC/RB独立PDE | ロジック完了。CIR zero atom・Feller/Euler反射bias、RB/CIR経路割引は時間近似、教材・受入は章末 |
| §31.3 | `_short_rate_measure.py` | 印刷例なし。式31.13・CIR ab不変、P/Q往復、独立Gaussian求積/raw MC・P bond returnの有限差分PDE | ロジック完了。a=0はconstant driftで保持、risk price符号は本文の仮定、教材・受入は章末 |
| §31.4 | `_short_rate_estimation.py`、`tests/data/hull_31_4_rates.csv` | 元8664観測/8663pair、0.136/0.0168/0.0119、λ−0.175/Table31.1全9点、独立OLS/求積/optimizer | ロジック完了。外部series/basis未同定、p727/補助CIR worksheet式差を保持、教材・受入は章末 |
| §31.5 | `_two_factor_rates.py` | 印刷価格なし。式31.14/TN14全6gamma・eta・theta・option variance、独立block指数/求積/MC、coupon近似9.91208≠厳密9.88683 | ロジック完了。native a=b・rho±1、curve fitとequilibrium・微分方向を明示、Ch31受入は章末 |
| §32.1 | `_fitted_short_rate.py` | 印刷例なし。式32.1–8、Ho–Lee/HW curve fit・極限、独立Gaussian θ核求積/PDE/MC、BDT a=−σ′/σ・BK正値step | ロジック完了。smooth曲線のmaturity微分、対数とGaussian θを分離、教材・受入は章末 |
| §32.2 | `_short_rate_bond_options.py` | 本文印刷例なし。式32.10/Ho–Lee極限、TN15 r*=0.10952/配賦K、0.8751256、独立Gaussian/CIR求積・raw Q MC | ロジック完了。TN15掲載合計0.8752との差・df0 atom・Jamshidian単調性条件を保持、教材・受入は章末 |
| §32.3 | `_forward_rate_volatility.py` | Fig32.3は印刷数値なし。同一3か月tenorでflat/低下/hump、独立block指数・bond比shock MC | ロジック完了。normal/Black換算/瞬間forward/implied capの単位を区別、教材・受入は章末 |
| §32.4 | `_rate_tree.py` | Fig32.4: B1.11/C0.23/A0.35、独立9経路列挙、3branchのmoment・原確率・exercise obstacle | ロジック完了。節点の期間rateで割引、後継indexは昇順、教材・受入は章末 |
| §32.5 | `_calibrated_rate_tree.py` | Fig32.6–8全node/Q、Table32.3全6価格・解析1.8093、Fig32.9全75項目/0.671933/0.703、小木経路列挙・HW解析/期間変換 | ロジック完了。DG201の1日終端/別rate-date、actual coupon/accrual、shifted BKのfloorを明示、教材・受入は章末 |
| §32.6 | `_short_rate_calibration.py` | 5×5/6×4/7×3/8×2/9×1、σ(t)/a回復・penalty・独立Gaussian求積/held-out、Black→HW σ往復、Bermudan行使順序 | ロジック完了。市場価格は本文にないため合成例、single curve/last σ flat延長、教材・受入は章末 |
| §32.7 | `_outside_model_hedging.py` | 印刷例なし。1因子price/複数curve・vol bucket、解析PV01/gamma・独立Gaussian給付求積、σ=0の片側vega | ロジック完了。curve bumpでa/σ固定、quote再較正riskとは別、Ch32受入は章末 |
| §33.1 | `_hjm_forward.py` | 印刷例なし。signed v/瞬間・有限forward drift、独立Gaussian解析対HJM MC、時間刻み収束、同じrの2履歴で異なるdrift | ロジック完了。batched pathはdeterministic vol、一般履歴依存HJMの少数状態保証なし、教材・受入は章末 |
| §33.2 | 未実装（下調べ・独立scratchあり） | Ex33.1/Table33.1と60条件付きMCは準備済み、製品ロジック完了には数えない | flexicap strike/reset・payment日とsticky K0未確定。本人指示に従い節を飛ばし§33.3へ |
| §33.3 | `_mortgage_cashflows.py` | 本文CMO 400/300/100・100/200/500（計800）、独立30年償却/PV閉形式、IO/PO方向性・principal保存・Gaussian割引MC・OAS逆算 | ロジック完了。返済は明示したpool生存モデル＋任意SMM、原pool/市場価格なし、実証較正とは別。教材・受入は章末 |
