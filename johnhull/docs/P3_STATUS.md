# P3 完了に向けた実装状態

更新2026-10-05。目標：Ch28–34の台帳37節を原典要求/実装/独立検証/可視化/配布画面の5軸で受け入れる。設計はprep/design/P3_DESIGN.md、節要求はprep/sections/ch28.md–ch34.md。残り要件をN/Aへ置き換えたり、簡易モデルだけで完了としない。

- 正式受入：Ch28全8節、P3 8/37（21.6%）、全33受入・273未評価。§28.6–28.8を[D3章末まとめ受入](CHAPTER_28_ACCEPTANCE_2026-10-05.md)。42価格の独立求積、共有6図/24表示状態、依存変更2節（28.2/28.5）のD1、28不変節の直接基点再利用、両保管庫復元、台帳成果物検査を確認。
- ロジック：`codex/p3-logic`に36/37（97.3%）を節ごとcommit/push済み。Ch28 8/8、Ch29 4/4、Ch30 4/4、Ch31 5/5、Ch32 7/7、Ch33 2/3、Ch34 6/6。新計算はprivate moduleで、本文の数値例＋独立検証を対象tests/ruffで確認。§33.2はflexicap strike/reset・payment日とsticky K0不足で保留。
- 次：Ch29全4節の章末まとめ受入。共通設定ツールで説明・rendered必須の5軸を確認し、build/画面巡回を章内共有、依存変更節だけD1、全suiteは章ごと1回。Ch29–34の教材・台帳・正式受入は未完了（29節、うち入力不足1節）。mainには章受入後に統合する。
- Ch28検証：全suite1回は4,436 passed・6 skipped・3 failed（234.02s）。3件は索引/図件数/台帳の更新漏れで、修正後の対象70 testsがPASS。全体4,439件を初回＋修正対象の再検査で確認し、最初の失敗記録も保持。[記録](validation/chapter-28/full-suite.json)。検証環境はLinux/Python 3.12。Python 3.13での新規実行はしていない。
- 既知の互換修正：§28.5のteacher/固定seed MCを許容誤差付きで比較し、数値digest照合を廃止。誤値の拒否は独立参照・固定seed再計算で保持。公開APIへの追加なし。
- 章末：D3本人承認2026-10-03、PR #11。設定は`docs/acceptance/chapters/ch28.json`、共通ツールは`scripts/chapter_acceptance.py`。Claudeによる数式レビューは後追いで、今回新しい独立レビューパッケージを作成していない。
- 公開API/production依存の追加は避け、計算をprivate moduleへ置く。既存公開契約を保持。

- [要求監査表](P3_REQUIREMENT_AUDIT_2026-10-04.md)：残35節の118草稿要求を全件保持。TN14/19と31.4元worksheetの取得不足は回収記録で解消。正式数理/実装受入は未完、flexicapのstrike/date不足は保持。HW Q OU/bond式整合はM29で独立RED→GREEN。

- [M29設計](prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md)：原典12要求/式28.16–28.25、確率金利の同一給付価格・条件付き支払測度・annuity2曲線、既存HW state/bond式の整合検査。

- M28最終レビューI1：datetime/timedeltaの単位喪失を新private入口で拒否。60回帰RED52→GREEN83、全suite4046/6。Minor1（ROADMAP旧段落の残35）はM29の通常状態更新で未受入33へ整合。
- [不足原典の調査](prep/design/P3_SOURCE_GAPS_2026-10-04.md)：TN14/19 PDFとTable31.1完全較正入力の取得不足は[回収記録](prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)で解消。正式受入とflexicapのstrike/対象期間はpending。合成例で代替受入しない。

- M29独立レビュー：96tests/4checksと追加probe PASS。Minor3はportal練習文/極小accrual/極大aの境界として記録し、正式修正は後続。

- 後続準備：Black再訪/交換契約の原典名・独立求積・zero-hit MCのimportance sampling、TN14のequilibrium/curve fit/全Appendix・a=b/rho端/u0/微分方向をscratch照合。正式受入とは区別。

- 後続Ch29–30/Ch32/Ch34の原典全要求と独立scratchをdocs/prep/designへ保存。Ch32は著者DG201の終端1日規約でTable32.3とFig32.9を再現しsigma_R補正案を撤回。tree/較正/Bermudanのロジックはbranchで完了、正式受入は未完、Ch33 flexicap入力不足は保持。

## ロジック先行の進捗

Ch28は正式受入済み。Ch29–34の実装ファイルは`codex/p3-logic`上のもの。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 |
|---|---|---|---|
| §28.5 互換修正 | `_multi_factor_lesson.py` | teacher/固定seed MCの1e-15差を許容、既存の数値改変拒否も保持 | 修正・章末再検査完了 |
| §28.6 | `_forward_black.py` | 印刷例なし。式28.26–29、7市場42価格のQ/T求積・raw MC、rare call 7.1683521394e-8 | 正式受入済み（Ch28共通記録） |
| §28.7 | `_exchange_measure.py` | 印刷例なし。式28.30–32、33ケース独立求積、配当再投資密度と確率金利4条件MC | 正式受入済み（Ch28共通記録） |
| §28.8 | `_numeraire_change.py` | 印刷例なし。式28.33–35、9相関条件、TN20 chain rule、独立求積・raw密度MC | 正式受入済み（Ch28共通記録） |
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
| §34.1 | `_nonstandard_legs.py` | BS34.1: raw10/20期間・100M/120M・2%・ACT365/360、独立cashflow/PV telescope/日次RFR積、元本列・known fixing | ロジック完了。具体U.S.休日未確定、caller calendarのFollowing、adjusted source pinなし。教材・受入は章末 |
| §34.2 | `_compounding_swaps.py` | Ex34.1全残高・精密2.895848743/表示値経路2.895、BS34.2の20期間、独立積の和/8経路木のspread厳密条件 | ロジック完了。一般forward実現は近似、additive spread誤差と表示切捨てを保持。教材・受入は章末 |
| §34.3 | `_cross_currency_swaps.py` | 印刷例なし。通貨leg/FX forward等価・反転・coupon spread較正、convexity/timing/quanto個別極限・独立Gaussian tilt | ロジック完了。spot domestic/foreignとquanto forward foreign/domesticを分離、local/frozen近似。教材・受入は章末 |
| §34.4 | `_equity_swaps.py` | TN19 net式/独立Gaussian求積、TR配当再投資/reset・pending、既知RFR×残growth、相関stochastic bank/equity MC（basis有無） | ロジック完了。本文指数/価格pinなし。leg PVとnet/lag・予測期待値入力を分離。教材・受入は章末 |
| §34.5 | `_embedded_swap_options.py` | trigger2%・6×4 payer/2–5年short receiver、独立binary積分、plain/複利解約を全64方策と照合、同じrでも異なる残高を保持 | ロジック完了。full-history小木16期間まで、4step spreadは近似/large実市場Bermudanとは別。教材・受入は章末 |
| §34.6 | `_other_swap_payoffs.py` | 本文50 USD/bbl・CP6%/spread10%→15.25%、P&G初回0/後9回、独立Gaussian正部分期待値/MC・元本保存 | ロジック完了。歴史的指標/価格なし、payoffとvaluationを区別。Ch34受入は章末 |
