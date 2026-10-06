# P4 ロジック先行の実装状態

更新2026-10-06。範囲：Ch10–21（台帳112項目）。原典の節メモに沿い、計算をprivate moduleへ実装し、本文数値と独立検証を対象テスト・ruffで確認する。

- 本人指示（2026-10-05）：受入作業はCh28を区切りに一時停止。P3はロジック36/37、正式受入8/37で保持し、次段階P4の実装を先行する。§33.2の入力不足は保留。
- 実装ブランチ：`codex/p4-logic`。既存`codex/p3-logic`の完成済み計算を引き継ぐ。新計算の公開API追加なし。節ごとにcommit/pushする。
- 正式受入：P4 0/112、全体33/306。説明・可視化・配布画面・台帳は受入再開時に確認する。
- 検証：変更モジュールのテストとruff。全suite・画面巡回・D1・保管庫復元は今回の実装段階の実行対象に含めない。

## 節別の実装

「ロジック完了」は表に記した計算範囲と対象検証の完了を示す。定性要求の説明・正式受入は後続。対象検証の件数は各モジュールのその時点の累計で、合算しない。最新はCh10 56 passed・Ch11 78 passed・Ch12 50 passed・Ch13 43 passed・Ch14 36 passed・Ch15 90 passed・Ch16 26 passed・Ch17 15 passed、ruff PASS（Linux/Python 3.12）。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 | 対象検証 |
|---|---|---|---|---|
| §10.1 | `_option_mechanics.py` | コール500/1500/1000、102で200/−300（不行使−500）、プット700/1500/800。独立Fractionの現物行使cash ledger、導出した損益分岐105/63 | ロジック完了。定義・行使スタイルの説明と教材は受入再開時 | 8 passed・ruff PASS |
| §10.2 | `_option_mechanics.py` | 本文4ポジション/売り手の最大利益5・7、Figure10.3/10.4の純益−10・−15・−8。min形の独立解析式、買い/売りcashflowのゼロサム | ロジック完了。Figure10.3–10.5の描画・説明は保留 | 16 passed・ruff PASS |
| §10.3 | `_option_mechanics.py` | 指数992・行使980・乗数100の現金決済1200（売り手−1200）。独立した市場価値と行使cash leg、符号付き先物価格の合成検証 | 計算部分完了。原資産の取引形態・行使後建玉の説明は保留 | 19 passed・ruff PASS |
| §10.4 | `_option_mechanics.py` | 40契約、2対1分割200株/15、20%株式配当5/6、25%配当125株/12、原典3限月列。Fractionの独立算術とdatetimeの独立暦列挙、本質価値/時間価値 | 計算部分完了。重複限月は近い2月より後のcycle月を採用した解釈。現行市場仕様・権利落ち・建玉制限の説明は保留 | 33 passed・ruff PASS |
| §10.6 | `_option_mechanics.py` | bid4/ask4.5→中値4.25・隠れコスト0.25/単位・25/契約。Decimalによる独立fill会計、固定＋契約fee、売却/行使の合成cash比較 | 計算部分完了。手数料はcaller入力。本文にない参照例は補わず、現行broker制度・説明は保留 | 42 passed・ruff PASS |
| §10.7 | `_option_mechanics.py` | Ex10.3：4240/3520/5040、premium credit2000→追加2240。独立Fraction/区分解析式、20%/15%切替境界、日次markと追証/引出cash保存、covered call/長期option借入限度 | 計算部分完了。原典時点の規則として実装、丁度9か月は全額払側。現行broker規制・本文説明は保留 | 56 passed・ruff PASS |
| §11.1 | `_option_properties.py` | 図11.1/11.2の基準7.116/4.677、5軸の全ゼロ端点、Table11.1の欧州5要因符号。独立lognormal payoff求積、満期逆転の合成2例、同一dt米国木とPDEの満期包含 | 計算部分完了。現金配当は日付固定escrowedモデル。米国6要因の符号は§11.5–11.7のCRR/PDEで補完。説明/図は保留。本文の満期反例には入力がなく合成例と区別 | 18 passed・ruff PASS |
| §11.3 | `_option_properties.py` | 本文11値（下限3.71/3.91/2.01/1.01、銀行17→18.79・借入38→38.96、裁定利益0.79/1.79/1.04/3.04）。独立Decimal現物行使会計とCRR欧州/米国価格の包含 | 計算部分完了。説明・上下限/裁定図・正式受入は保留。負金利では米国put上限をmax(K,PV(K))へ拡張し、原典の正金利結論と分離 | 32 passed・ruff PASS |
| §11.4 | `_option_properties.py` | 本文13値（32.26/33.25・受取30.25→31.02・利益1.02、32/借入29→29.73・利益0.27、Ex11.3の0.18/1/1.68/2.50）。独立Decimal行使会計、米国CRR/PDEで実際のC/P不等式、企業資産の状態別/求積価値保存 | 計算部分完了。米国parityの正金利前提を明記。説明・Table11.2/11.3・図・正式受入は保留。1.2593は本文32.26からの導出で印刷pinとは区別 | 43 passed・ruff PASS |
| §11.5 | `_option_properties.py` | 本文S70/K40/1か月の本質価値30（option価格とは区別）。金利繰延＋put保険の分解、無配当C=c、米国の株価/strike/r/vol符号。独立PDE・payoff求積と負金利の早期行使反例 | 計算部分完了。本文にr/vol/option価格がないため合成入力と明記。説明・模式図・受入は保留。exercise_nowはCRR格子上の判定 | 54 passed・ruff PASS |
| §11.6 | `_option_properties.py` | 本文K10・S→0の本質価値/米国極限10、欧州E=Ke^(-rT)。合成spot曲線で米国A<欧州B、実行使/本質価値割れを分離。独立PDE・格子細分・payoff求積、米国4要因符号と負金利反例 | 計算部分完了。A/Bは本文の模式ラベルで値のpinなし。返すのは現在spot軸の根判定で、時間別自由境界とは区別。説明・図・受入は保留 | 65 passed・ruff PASS |
| §11.7 | `_option_properties.py` | 本文は数値pinなし、式11.8–11.11の4式を実際のcash-dividend欧州/米国価格で検証。独立CN-PDE・格子細分・配当再投資の状態会計、call行使時点・米国の配当符号・満期配当順序 | 計算部分完了。escrowed配当モデル（σはS−PV(D)に適用）で実配当落ちを扱い、一般のcash-jump GBMやq換算と区別。ex-dateは選択した格子に整列が必要。説明・図・受入は保留 | 78 passed・ruff PASS |
| §12.1 | `_option_strategies.py` | 本文10関係：bond835.27/予算164.73、採算vol14.937164%（約15%）、call約221、3%の3/10/20年の予算86.07/259.18/451.19とcall約119/217/281。独立payoff積分/求根、無配当の採算不能 | 計算部分完了。参加率1の原典とcaller参加率を区別し、資金不足も返す。名目元本保護、信用リスク/機会費用・説明・図・受入は保留 | 10 passed・ruff PASS |
| §12.2 | `_option_strategies.py` | 本文の数値例なし。Figure12.1の4ポジションをmin/maxの独立区分式で検証。式12.1の初期費用・債券/配当資金、独立Decimal日付会計、short株の配当負担と満期後除外 | 計算部分完了。損益は初期費用の金利を加算しない。配当の再投資はcaller明示。式/4パネル説明・描画・受入は保留 | 18 passed・ruff PASS |
| §12.3 | `_option_strategies.py` | 本文31関係：Ex12.2/12.3の損益・分岐32/33、butterfly費用1/分岐56・64/最大4、BS12.1の欧州box4.93・米国構成価格と丸め後5.26。独立区分式/PDE、calendar/diagonal残存payoff求積 | 計算部分完了。米国boxの未丸め約5.267と丸め後5.26を分離。short米国の早期割当経路は計算していない。多満期はT1で長期をT2−T1でmark。説明・図・受入は保留 | 37 passed・ruff PASS |
| §12.4 | `_option_strategies.py` | 本文6関係：straddle費用7、S69給付1/損失6、S70損失7、S90利益13、S55利益8。独立区分式・傾き・数量、strangle中央域と分岐、top/bottom反転・premium変更 | 計算部分完了。分岐63/77等は導出値で印刷値と区別。short損失は上昇側が無限でS=0側は有限。イベント説明・図・受入は保留 | 44 passed・ruff PASS |
| §12.5 | `_option_strategies.py` | 本文の数値pinなし。幅h/高さhと1/h正規化、非等間隔・符号付き節点の独立線形補間、静的portfolioとpayoff積分。Gaussianのh5→2.5で誤差0.020115→0.005323、曲率上限内 | 計算部分完了。有限区間/zero ghost節点を明示し、境界の負ghost strikeはstock＋満期cashへ変換。全域の任意tail/不連続payoffの一様近似を保証しない。説明・図・受入は保留 | 50 passed・ruff PASS |
| §13.1 | `_binomial_foundations.py` | GEのΔ0.25、確定4.5、PV4.455、価格0.545、p0.5503、400契約/100株。独立2×2複製連立解、2状態の銀行借入収支・価格上下の裁定 | 計算部分完了。GE r4%とUS r12%を区別。表示する銀行残高は負なら借入。説明・図・受入は保留 | 3 passed・ruff PASS |
| §13.2 | `_binomial_foundations.py` | p(P)=0.6266、p(Q)=0.5503、価格0.545、オプションの要求利回り55.96% | Pの期待payoffをrで割り引くと誤価格。要求利回りは正の価格・期待値でのみ定義 | 6 passed・ruff PASS |
| §13.3 | `_binomial_foundations.py` | 終端株価24.2/19.8/16.2、payoff3.2/0/0、中間1.7433/0、価格0.9497。独立4経路と後退木で照合 | 計算部分完了。2経路の再結合重みを保持。説明・図・受入は保留 | 9 passed・ruff PASS |
| §13.4 | `_binomial_foundations.py` | 印刷p0.6282で全節点72/48/32、payoff0/4/20、中間1.4147/9.4636、価格4.1923。未丸め4.192654は独立3状態式・後退木・parityと一致 | 計算部分完了。印刷丸めの重みを明示して使用、厳密martingale/parityは未丸め側で確認。説明・図・受入は保留 | 12 passed・ruff PASS |
| §13.5 | `_binomial_foundations.py` | 全8停止方針の列挙：下側で12を行使、根は即時2より待機5.0894。未丸め5.089632は独立経路cash合計と後退木で一致 | 計算部分完了。列挙は再結合節点のMarkov方針・5段以下に限定。印刷丸めを区別。説明・図・受入は保留 | 15 passed・ruff PASS |
| §13.6 | `_binomial_foundations.py` | call delta0.25/0.4358/0.7273/0、put−0.4024/−0.1667/−1。節点ごと独立2×2解で銀行残高も照合 | 計算部分完了。put根は印刷子節点で−0.402445、未丸め−0.40245885。有限Nの割線deltaとspot微分を区別。説明・図・受入は保留 | 18 passed・ruff PASS |
| §13.7 | `_binomial_foundations.py` | 本文は数値pinなし。平均exp(drift Δt)厳密、分散σ²Δt一次一致。独立2点分布・TaylorのΔt²係数・P/Q極限で検証 | 計算部分完了。P/Qの有限ステップ分散は異なり、同じなのはσ・u/d・分散率の極限。説明・図・受入は保留 | 22 passed・ruff PASS |
| §13.8 | `_binomial_foundations.py` | u1.3499/d0.7408/a1.0513/p0.5097、Figure13.10の全株価・payoff・option節点、根7.43（未丸め7.428401903）。独立8停止方針・1段cash期待値 | 計算部分完了。σ30%のCRRと固定u1.2/d0.8の木は別入力として比較。説明・図・受入は保留 | 24 passed・ruff PASS |
| §13.9 | `_binomial_foundations.py` | 5段dt0.4/u1.2089/d0.8272/a1.0202/p0.5056、30段の31終端・1073741824経路。偶/奇100–2001段を独立payoff積分・BSM・直接二項和で検証 | 計算部分完了。欧州の偶奇別収束を検証し全Nの単調収束は仮定しない。米国型のBSM欧州への収束は主張しない。説明・図・受入は保留 | 27 passed・ruff PASS |
| §13.10 | `_binomial_foundations.py` | 米国2/5/500段7.428/7.671/7.47、欧州500段とBSM6.76。5段32768停止方針、500段は独立CN-PDE（許容0.01）で確認 | 数値部分完了。DerivaGem自体の操作・出版時UI説明、図・受入は保留。PDEは連続停止極限の別離散化として比較 | 30 passed・ruff PASS |
| §13.11 | `_binomial_foundations.py` | Ex13.1/13.2/13.3の係数・全stock/option節点、根53.39/0.019/2.84。全節点の独立二項和/停止方針、指数2000段の配当BSM、先物の国内割引で確認 | 計算部分完了。q配当・外国金利・q=rを成長率へ、国内rを割引へ適用。説明・図・受入は保留 | 35 passed・ruff PASS |
| §13.appendix | `_binomial_foundations.py` | 本文の記号式U1/U2を独立終端和・後退木で照合。厳密j>a（strike一致含む）、株式測度p*、4000段のd1/d2両tail・BSM極限 | 計算部分完了。整数閾値近傍16 ulpを境界へ寄せた後に厳密不等式を適用。§13.2の実確率と株式測度を区別。説明・図・受入は保留 | 43 passed・ruff PASS |
| §14.2 | `_stochastic_foundations.py` | Ex14.1の標準偏差1/2.236、Ex14.2の平均70/60・標準偏差30/21.21、本文√T。独立正規積分・固定seed MC、bridge条件分散・増分共分散、経路の全変動期待値 | 計算部分完了。bridgeは標準Brownian用、粗格子を保持。MCは6SE判定、経路長は縦増分の絶対値合計。説明・図・受入は保留 | 6 passed・ruff PASS |
| §14.3 | `_stochastic_foundations.py` | Ex14.3のdt0.0192/係数0.00288・0.0416、Table14.1の全22計算セルと10週終値111.54。独立Decimalループ、Euler積モーメントとMC、厳密GBMとの収束 | 計算部分完了。丸め係数＋全精度累積を明示。11行目の変化12.20は次週で10週終値に含めない。Eulerの負株価を切り捨てない。説明・図・受入は保留 | 10 passed・ruff PASS |
| §14.5 | `_stochastic_foundations.py` | 数値例なし。本文u/ρu+√(1−ρ²)v構成、分散Δt/共分散ρΔtを独立Choleskyと固定seed MC/Wishart SEで照合（ρ±1含む） | 計算部分完了。2変量の相関生成を追加。多変量は既存Choleskyを後続Ch21で確認。説明・図・受入は保留 | 16 passed・ruff PASS |
| §14.6 | `_stochastic_foundations.py` | 数値例なし。式14.12の局所係数、式14.15–16のF=S exp(r(T−t))、dF=(μ−r)Fdt+σFdz。独立正規積分・GBM経路のF変換とMC/SEで確認 | 計算部分完了。扱うのは無配当・一定金利のforward価格。契約価値とは区別。Qでlevel drift0、log drift−σ²/2。説明・図・受入は保留 | 19 passed・ruff PASS |
| §14.7 | `_stochastic_foundations.py` | 数値pinなし。式14.17–19のlog平均・分散とstockモーメント。独立stock Euler（8/512段・2万経路）でlog分散収束・平均/分散/3CDF点をMC6SE判定 | 計算部分完了。独立検証はlog生成器を使わずstock Eulerからlogを測定。負Euler標本を除外せず全標本の正値を確認。説明・図・受入は保留 | 22 passed・ruff PASS |
| §14.8 | `_stochastic_foundations.py` | 数値pinなし。式14.20、H0.9/0.5/0.1・100段fBM経路、H0.5→min(s,t)、隣接増分相関2^(2H−1)−1。独立fGn積分/固有値サンプル・MC6SE、Gaussian条件付き共分散 | 計算部分完了。Gaussian条件付き共分散でも非Markov性を区別。dense Choleskyは小格子向け、jitterなし。Figureの乱数軌跡を印刷pinにしない。説明・図・受入は保留 | 30 passed・ruff PASS |
| §14.appendix | `_stochastic_foundations.py` | Eε²=1/Varε²=2、累積二次変分Var=2b⁴TΔt、式14A.10–11の相関cross項。独立χ²法則/MC、2GBM積の期待値と多driverの等価分散 | 計算部分完了。単一ε²を1と置かず累積の分散収束を検証。多変量はB C Bᵀの共分散で扱う。説明・図・受入は保留 | 36 passed・ruff PASS |
| §15.1 | `_bsm_foundations.py` | Ex15.1 log平均3.759/分散0.02/SD0.141、印刷中間丸めの95%区間32.55–56.56（未丸め32.514742–56.603188）。Ex15.2価格平均24.43/分散103.54/SD10.18。独立密度積分とstock Euler/6SE | 計算部分完了。logのモーメントと価格のモーメント、中間丸めと未丸めを区別。z1.96は近似95%。説明・図・受入は保留 | 6 passed・ruff PASS |
| §15.2 | `_bsm_foundations.py` | Ex15.3：3年の平均連続複利年率15%/SD11.55%/95%区間−7.6%–37.6%。独立lognormal密度の変数変換積分とstock Euler/6SE | 計算部分完了。累積log収益のSDは√T、平均年率のSDは1/√T。T=0の平均年率は未定義として拒否。説明・図・受入は保留 | 9 passed・ruff PASS |
| §15.3 | `_bsm_foundations.py` | 本文5年return15/20/30/−20/25%：算術平均14%、100→179.40、14%固定なら192.54、幾何平均12.4%。独立Fractionの年次cash ledgerとGBMのJensen差の密度積分 | 計算部分完了。株価の期待成長率・実現連続年率・幾何平均を区別。投資額は自己資金、年ごとの単純return入力。説明・図・受入は保留 | 13 passed・ruff PASS |
| §15.4 | `_bsm_foundations.py` | Table15.1の全20相対価格/log return、Σu.09531/Σu².00326/s.01216/年率19.3%/SE3.1%、週次4.16%・2.08ドル。独立Decimalログ/展開標本分散、配当調整と時間規約 | 計算部分完了。n−1標本SD、SEは近似。時間はcallerの年単位、本文は252営業日。配当調整と観測除外を同一視しない。説明・図・受入は保留 | 19 passed・ruff PASS |
| §15.5 | `_bsm_foundations.py` | 本文100call売り/40株買い：株+.10/call+.04の損益−4/+4/0、delta.4→.5で10株追加。独立Fraction cash ledger、BSM曲率の有限変動残差 | 計算部分完了。rebalance cashと時価を分け、同時刻の売買は自己資金保存。有限変動のgamma残差はゼロとしない。説明・図・受入は保留 | 23 passed・ruff PASS |
| §15.6 | `_bsm_foundations.py` | 数値pinなし。本文forward S−Kexp(−rτ)、永久到達QS/H・Q(S/H)^(−2r/σ²)、逆数株価exp((σ²−2r)τ)/Sと不適なexp(S)。独立有限差分、first-passage/負モーメント密度積分、μ消去 | 計算部分完了。f_tは暦時刻微分、入力は残存τ。永久到達はr>0・σ>0、境界条件も確認。説明・図・受入は保留 | 34 passed・ruff PASS |
| §15.7 | `_bsm_foundations.py` | 数値pinなし。式15.18–19のexp(−rT)E_Q[ST−K]=S−Kexp(−rT)。独立lognormal積分/stock Euler 6SE・現物＋債券cash複製、Pの誤割引との対照 | 計算部分完了。§15.1/15.6の分布とforward価値を再利用。μとrを区別し、P期待値のr割引を価格としない。説明・図・受入は保留 | 39 passed・ruff PASS |
| §15.8 | `_bsm_foundations.py` | 数値pinなし。式15.20–22のcall価格、Q行使確率N(d2)、切断一次モーメントSexp(rT)N(d1)、条件付き期待値を分離。独立密度求積/1600段CRRとσ0/T0/K0境界 | 計算部分完了。N(d1)はstock weight。行使事象はST>K、退化ATMは確率0、条件付き期待値は事象確率0でNone。説明・図・受入は保留 | 49 passed・ruff PASS |
| §15.9 | `_bsm_foundations.py` | Ex15.6 d1.7693/d2.6278/PVK38.049、CDF.7791/.7349/補数.2209/.2651、call4.76/put.81、損益分岐変化+2.76/−2.81。独立正規密度積分（8σ tail含む）・既存cashflow | 計算部分完了。upper tailは1−CDFで差し引かず直接計算。分岐は印刷premium4.76/.81で、金利無視の名目損益。説明・図・受入は保留 | 55 passed・ruff PASS |
| §15.10 | `_bsm_foundations.py` | Ex15.7 call7.04/warrant5.87/費用1.17百万/発表後株38.83。Snapshot15.3 50→45/費用50万、満期100ならpayoff50。独立Fraction資本台帳・terminal payoff密度積分 | 計算部分完了。新規発行の非希薄化spotと発行発表済み市場spotを区別、二重希薄化なし。Ex15.7はHullの無便益の発行費用計算。ESO固有の条件はCh16、説明・図・受入は保留 | 62 passed・ruff PASS |
| §15.11 | `_bsm_foundations.py` | 本文σ20/30/25%でcall1.76/2.10/1.926831、価格1.875のIV23.5%（未丸め23.451291%）。独立Brent/1200段CRR再価格、Ex15.8 VIX18.5→19.3×1000=800・15points=15% | 計算部分完了。無裁定下限でIV0、上限は有限IVなし、T0のIVは未定義。VIX倍率は原典例の規約。説明・図・受入は保留 | 73 passed・ruff PASS |
| §15.12 | `_bsm_foundations.py` | Ex15.9 PV.9742/リスク株39.0258/d1.2020/d2−.0102/CDF.5800/.4959/call3.67。独立Decimal PV/密度積分/1000段配当木、本文の早期行使条件・Black2leg恒等式 | 計算部分完了。σはS−PV(D)のvol。同一escrowedモデルの固定行使日価値とBlack近似を分離。Blackは異なるrisk componentを使い単一モデルAmericanの下限とは主張しない。説明・図・受入は保留 | 81 passed・ruff PASS |
| §15.appendix | `_bsm_foundations.py` | 数値pinなし。15A.1–6の一般lognormal payoff・切断モーメント、m=lnE[V]−w²/2、Q平均Sexp(rT)/w=σ√TのBSM代入。独立株価密度/正規変換積分・4000段二項tail | 計算部分完了。wはlogのSD、E[V]は価格平均、payoff_meanは割引前。σ0/K0境界も検証。Ch15全13計算項目完了、説明・図・受入は保留 | 90 passed・ruff PASS |
| §16.3 | `_employee_options.py` | 本文指数2000→2200でstrike30→33、1700なら25.50。RSU1株、MSU株数ST/S0・価値ST²/S0。独立Fraction資本台帳とlognormal MSU期待値の求積 | 計算部分完了。指数連動strike/RSU/MSUの定義を実装。会計史・現行基準・IAS 2記載の確認、§16.1–2の説明・図・受入は保留 | 6 passed・ruff PASS |
| §16.4 | `_employee_options.py` | Ex16.1 unit6.31/1百万権利6.31百万。Ex16.2全15株価/option節点・根14.97/通常call17.98、D/G/H行使.43/.81/.335・継続11.05/106.64/24.95。独立全経路cash列挙/MC6SE/密度積分、倍率45・市場連動20/25 | 計算部分完了。原典の根を含む離職タイミングを明示。倍率は整列CRR格子を検証、一般格子では境界離散化誤差あり。倍率∞/離職0は欧州保持、無配当r≥0のcallではAmericanと同値。期待寿命BSMを理論的等価としない。説明・図・受入は保留 | 24 passed・ruff PASS |
| §16.5 | `_employee_options.py` | 本文4/30の株価50・4/3の42をstrikeにする例のintrinsic差8。既存award/cash関数を再利用し独立Fractionの行使支払・売却cash ledgerで照合 | 算術部分のみ完了。決定日と表示日・研究の論証・法制度は説明/受入へ保留。Ch16の計算3節完了、§16.1–2と会計史の説明は未実施 | 26 passed・ruff PASS |
| §17.1 | `_index_currency.py` | β1で5枚/K900/880時440000＋10000=450000。Table17.1全return、Table17.2全6価値570000–370000、β2で10枚/K960/補填80000、配当込K955。独立Fraction/CAPM cash ledger | 計算部分完了。CAPMは条件付き期待シナリオで、betaだけの確定保証を主張しない。premium/基差残差は別cash入力、契約倍率は原典例。説明・図・受入は保留 | 7 passed・ruff PASS |
| §17.2 | `_index_currency.py` | EUR call50000/AUD put300000、GBP forward1320000。range put0.027304826/call0.027292496（印刷0.0273、上strike丸めの残差を保持）、zero-cost上strike探索。独立Fractionの3領域cash・lognormal payoff求積 | 計算部分完了。外貨受取/支払の符号とnotionalを明示、印刷strikeの小さな費用と厳密zero-costを区別。市場説明・図・受入は保留 | 15 passed・ruff PASS |

## 次の実装

- Ch10–16の計算52項目を実装・push（Ch10：6、Ch11：6、Ch12：5、Ch13：11節＋付録、Ch14：7、Ch15：12節＋付録、Ch16：3）。Ch16.5は算術部分のみ。
- 今回（2026-10-06）の追加は16項目：Ch15の13項目とCh16の3項目。対象Ch15 90/Ch16 26 tests・ruff PASS。Ch10–14は今回再実行していない。
- 次はCh17 §17.3（配当利回りとcarry価格）。P4の計算は合計54節、正式受入は0/112のまま。
- 定性・説明要求は保留：Ch16 §16.1–2・会計史/研究の説明、Ch11 §11.2、Ch14 §14.1/14.4、Ch10 §10.5・10.8–10.12。§10.10の説明用の損失20ドルは下調べで算術確認済みだが、今回の新テストには含めていない。Ch10全12節の完了や正式受入を表すものではない。
