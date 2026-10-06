# P4 ロジック先行の実装状態

更新2026-10-06。範囲：Ch10–21（台帳112項目）。原典の節メモに沿い、計算をprivate moduleへ実装し、本文数値と独立検証を対象テスト・ruffで確認する。

- 本人指示（2026-10-05）：受入作業はCh28を区切りに一時停止。P3はロジック36/37、正式受入8/37で保持し、次段階P4の実装を先行する。§33.2の入力不足は保留。
- 実装ブランチ：`codex/p4-logic`。既存`codex/p3-logic`の完成済み計算を引き継ぐ。新計算の公開API追加なし。節ごとにcommit/pushする。
- 正式受入：P4 0/112、全体33/306。説明・可視化・配布画面・台帳は受入再開時に確認する。
- 検証：変更モジュールのテストとruff check（lint）。全suite・画面巡回・D1・保管庫復元は今回の実装段階の実行対象に含めない。

## 節別の実装

「ロジック完了」は表に記した計算範囲と対象検証の完了を示す。定性要求の説明・正式受入は後続。対象検証の件数は各モジュールのその時点の累計で、合算しない。最新はCh10 56 passed・Ch11 78 passed・Ch12 50 passed・Ch13 43 passed・Ch14 36 passed・Ch15 90 passed・Ch16 26 passed・Ch17 54 passed・Ch18 78 passed・Ch19 92 passed・Ch20 84 passed・Ch21 37 passed、ruff PASS（Linux/Python 3.12）。

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
| §17.2 | `_index_currency.py` | EUR call50000/AUD put300000、GBP forward1320000。range put0.027304826/call0.027292496（印刷0.0273、上strike丸めの残差を保持）、zero-cost上strike探索。独立Fractionの3領域cash・lognormal payoff求積 | 計算部分完了。外貨受取/支払の符号とnotionalを明示、印刷strikeの小さな費用と厳密zero-costを区別。forward一致境界の求根丸めを修正。市場説明・図・受入は保留 | 15 passed・ruff PASS |
| §17.3 | `_index_currency.py` | 式17.1–5の下限/parity/配当spot変換、配当込みPDEと米国差額不等式。本文に数値例なし。独立lognormal payoff求積、再投資台帳、数値微分PDE・CRRで照合 | 計算部分完了。spot縮小は欧州限定、米国差額不等式は本文のr/q非負前提を明示。説明・図・受入は保留 | 26 passed・ruff PASS |
| §17.4 | `_index_currency.py` | Ex17.1 c51.83/契約5183、d1印刷0.5444は切捨て相当（未丸め0.544478575）、d2/N再現。Snapshot put169.7、forward/配当利回り逆算。独立CRR・payoff積分 | 計算部分完了。契約5183は丸めた価格の100倍で未丸め5183.2957と区別、同一満期の理論quotesを逆算。説明・図・受入は保留 | 32 passed・ruff PASS |
| §17.5 | `_index_currency.py` | Ex17.2 σ20%→0.0639、10%→0.0285、c0.043→IV14.1%（未丸め14.111938%）。通貨反転call/putの数量Kと価格係数S×K。独立payoff積分によるIV求根・満期換算台帳、微小価格の回帰 | 計算部分完了。国内/外貨の単位とnumeraire反転を明示、T=.3333は4/12の表示丸め。微小価格をゼロIVにしないBrent幅収束へ修正。説明・図・受入は保留 | 54 passed・ruff check PASS（境界回帰後） |
| §17.6 | `_index_currency.py` | Ch13参照の米国為替call0.019・全option節点、成長a0.9983/p0.4673。独立停止方針列挙・CN-PDE、外国金利別の行使premium、ゼロvol/満期境界 | 計算部分完了。国内rで割引しr−qで成長、米国>=欧州、行使判定は指定格子上の厳密優越。説明・図・受入は保留 | 48 passed・ruff PASS |
| §18.1 | `_futures_options.py` | 銅2500+250=2750、corn1050−50=1000、SOFR0.65%/premium125/payoff500/profit375、国債96-09/1-04/利益937.50。独立Fractionの2脚決済・符号付き価格cash | 計算部分完了。先物建玉と清算cashを分離、倍率は本文例のcaller入力。市場の現行制度・定性説明・図・受入は保留 | 8 passed・ruff PASS |
| §18.3 | `_futures_options.py` | 本文に数値例なし。満期一致ならF_T=S_T、spotと先物の欧州call/put一致。独立spot payoff求積・terminal cashと満期ずれの反例 | 計算部分完了。確定carryと満期一致を明示、米国型へ等価性を拡張しない。§18.2定性・説明・図・受入は保留 | 15 passed・ruff PASS |
| §18.4 | `_futures_options.py` | Ex18.5 call0.56→put1.04（未丸め1.035614712）、式18.1/18.2。独立Fractionの2portfolio終端cashと米国CRRの差額上下限 | 計算部分完了。本文の複製は満期清算に簡略化した議論で、実際の日々清算再投資と区別。米国差額上下限は非負金利。説明・図・受入は保留 | 23 passed・ruff PASS |
| §18.5 | `_futures_options.py` | 本文に数値例なし。式18.3/18.4の割引本質価値下限・米国即時本質価値下限、ゼロvol/ATM等号とdeep ITM極限。独立密度求積/Jensen・米国CRR | 計算部分完了。大小関係は等号を含む。説明・下限図・受入は保留 | 31 passed・ruff PASS |
| §18.6 | `_futures_options.py` | 本文に数値例なし。式18.5/18.6のQ drift0・log drift−σ²/2・条件付き平均F・先物PDE。独立密度求積/stock Euler MC固定seed6SE・価格数値微分 | 計算部分完了。futuresはmoney-market測度、forwardは満期債測度と区別。Black/PDE価格検証は確定r。説明・図・受入は保留 | 39 passed・ruff PASS |
| §18.7 | `_futures_options.py` | Ex18.6 put1.12（未丸め1.116641457）、d1印刷0.07216は切捨て相当/d2−0.07216/N−d1=0.4712/N−d2=0.5288。独立payoff積分・先物CRRとゼロvol/満期境界 | 計算部分完了。既存の共通Black入口を使用、正のlognormal Fのみ。負価格モデルRB-H18は範囲外。説明・図・受入は保留 | 47 passed・ruff PASS |
| §18.8 | `_futures_options.py` | Ex18.7 gold call88.37、d1=0.3026/d2=0.1611。spot/carryとforward/満期discountの入力一致、独立spot/forward payoff積分 | 計算部分完了。市場discount入力は満期債測度でforwardがlognormalという仮定が必要。確率金利でfuturesへ置換する主張なし。説明・図・受入は保留 | 53 passed・ruff PASS |
| §18.9 | `_futures_options.py` | F30→33/28、Δ0.8、確定cash−1.6/PV−1.592、p0.4、option1.592019967。Ch13参照の米国put2.84。独立2×2複製連立解・全停止方針 | 計算部分完了。先物entry価値0/初期portfolio−f、清算をステップ末へ近似する本文の留保を明示。説明・図・受入は保留 | 62 passed・ruff PASS |
| §18.10 | `_futures_options.py` | 本文に数値例なし。normal/inverted/zero carryの米国call/put大小関係、満期一致の欧州等価と後月先物の差。独立CN-PDEで4契約・ゼロvol境界を検証 | 計算部分完了。大小関係は確定carry/r>0の本文前提、後月ほど差が広がる点は合成例の確認で普遍単調性を主張しない。説明・図・受入は保留 | 69 passed・ruff PASS |
| §18.11 | `_futures_options.py` | 本文に数値例なし。無割引Black気配=e^(rT)×通常価格、p+F=c+K、金利独立、早期行使の優越なし。独立求積/全停止方針/Fraction清算cash、1.1506は合成値と明示 | 計算部分完了。気配は先払いpremiumではなく清算基準、initial premium0/担保と清算cash利息は範囲外。§18.2定性・説明・図・受入は保留 | 78 passed・ruff PASS |
| §19.1 | `_greeks_hedging.py` | 通し例call2.40・理論総額約240000・売却300000との差約60000（未丸め2.400461/240046/59954）。独立Q payoff積分、P drift13%と価格r5%を区別 | 計算部分完了。売却差額は時点0の理論価値との差で将来の確定利益ではない。定性説明・図・受入は保留 | 5 passed・ruff PASS |
| §19.2 | `_greeks_hedging.py` | naked S60支払1000000、covered49→40の株式損失900000、閾値1往復2ε。Table19.1全6成績を固定seed MC/6SE＋表示丸め幅で確認。同一パスの無利息/資金口座会計と独立discounted gains | 計算部分完了。本文の成績は利息/割引を除外し、資金繰り付きPV費用と別欄。MCの印刷値一致は統計的確認。説明・図・受入は保留 | 12 passed・ruff PASS |
| §19.4 | `_greeks_hedging.py` | Ex19.1 delta0.522、1200株＋再調整100株、book hedge14900株。Tables19.2/3全21行の取引/利息/表示帳簿、19.2費用263338.49、Table19.4全6成績(MC6SE)、週9価格414.5k・純変化−4.1k。独立density delta/discounted gains | 計算部分完了。Table19.3表示S/Δの精密会計256337.59と本文256600に262.41差、元の非丸め入力不明として保留。原典成績は無利息費用。定性/受入は保留 | 20 passed・ruff PASS |
| §19.5 | `_greeks_hedging.py` | Ex19.2 theta−4.31/年、−.0118/暦日、−.0171/営業日。独立Q payoff積分のremaining-time中央差分、call/put parity、正thetaの本文例外 | 計算部分完了。thetaは暦時間微分でremaining T微分の負号、365/252単位を明記。説明・図・受入は保留 | 27 passed・ruff PASS |
| §19.6 | `_greeks_hedging.py` | Ex19.3 ±2の二次損失−20000、gamma hedge2000 options/−1240株、Ex19.4 Γ.066。独立Q密度価格二階差分とdelta hedge残差の三次収束 | 計算部分完了。株式gammaは0、gamma0のヘッジ商品は不可。説明・図・受入は保留 | 35 passed・ruff PASS |
| §19.7 | `_greeks_hedging.py` | Eq19.4 theta+rSdelta+σ²S²gamma/2=rΠ、q版・stock/bank込みdelta中立book。独立CN grid/time差分の残差2e−6以内・格子倍密で縮小（数値例なし） | 計算部分完了。thetaはcalendar-timeで、stock/bankもbook価値と時間微分へ算入。説明・図・受入は保留 | 40 passed・ruff PASS |
| §19.8 | `_greeks_hedging.py` | Ex19.5 vegaのみ4000 options/−2400株・残Γ−3000、同時中立400/6000 options/−3240株。Ex19.6 vega12.1/単位・.121/vol point。独立有理数消去とQ密度vol差分 | 計算部分完了。vega中立はparallel IV shiftを前提、vol surfaceの個別変化は未ヘッジ。説明・図・受入は保留 | 48 passed・ruff PASS |
| §19.9 | `_greeks_hedging.py` | Ex19.7 rho8.91/金利単位・.0891/1% point。spot/q固定の独立Q密度国内金利差分4例、rho parity・完全再評価の二次誤差 | 計算部分完了。金利の絶対変化1.0/.01/.0001を区別、先物固定Fのrhoは§19.12で別扱い。説明・受入は保留 | 56 passed・ruff PASS |
| §19.11 | `_greeks_hedging.py` | Table19.5の21表示値・最大損失−90mを読取り（再価格計算ではない）。2週・7×3の合成FX bookを独立Q密度積分で完全再評価、short butterflyの内点最大損失、IV10%→12% | 計算部品完了。Table19.5はbook/strike/maturity不明のため価格再現は入力不足で飛ばす。合成book検証と引用値読取りを区別。説明・受入は保留 | 64 passed・ruff PASS |
| §19.12 | `_greeks_hedging.py` | Table19.6全Greeks/qと外国rhoを独立密度差分、固定F futures rho=−TV、forward/futures delta差。Ex19.8精密468421.81GBP・factor表示丸め468442GBP、契約7枚 | 計算部分完了。futures rhoはq=rを連動させ固定Fを保持、通貨rhoは国内/外国を分離。Ex19.8の21GBP差はfactor4桁丸めで再現可能と注記（原著の中間精度は不明）。説明・受入は保留 | 77 passed・ruff PASS |
| §19.13 | `_greeks_hedging.py` | Ex19.9 d1.4499・売却32.15%・表示差4.64/4.28%、Ex19.10 122.96→123 short futures。独立密度put delta、同一初期premiumの離散replication帳簿とgap-floor破れ | 計算部分完了。Ex19.9の88mは符号欠落/残存.5で一致、92mは1日経過で一致：同一時間規約での厳密一致は保留。index-mirror/beta1限定。説明・歴史・受入は保留 | 85 passed・ruff PASS |
| §19.appendix | `_greeks_hedging.py` | Eq19A.1とspot/IV二変数Taylor（vega/vanna/vomma）。独立payoff求積の混合微分2経路・vol二階差分、完全再評価との差の三次縮小、ΔS∝√Δt時のgamma/θ次数（数値例なし） | 計算部分完了。並行IV shock・金利/q固定、時間cross項など高次は省略。定性・説明/図/受入は保留 | 92 passed・ruff PASS |
| §20.1 | `_smile_surface.py` | Ex20.1 put.0419・IV14.5%（未丸め.04192291/.14511006）、Eq20.2 dollar誤差3例。独立Q payoff積分＋二分逆算、丸めquoteのIV差と微小正価格 | 計算部分完了。欧州parity前提、丸めputの残差とIV差を消さない。有限IV arb bounds、極端ITM側の価格桁落ちによる識別限界を区別。説明・受入は保留 | 10 passed・ruff PASS |
| §20.2 | `_smile_surface.py` | Table20.1正規列31.73/4.55/.27/.01/.00/.00%を独立求積。合成Q混合とlognormalの平均/分散を一致させ、両OTM価格上昇・U字IV・parityを直接terminal密度積分で確認 | 計算部分完了。2005–2015実測列の原データなし、実測再現は飛ばす。合成Q mixtureは経験P分布・現行市場smileとは区別。歴史説明・受入は保留 | 19 passed・ruff PASS |
| §20.4 | `_smile_surface.py` | 本文50-delta±.5定義、K・K/S・K/F・spot delta軸の往復とATM spot/forward/50deltaの差。独立terminal payoff積分のspot差分と通貨単位不変性（固有数値例なし） | 計算部分完了。spot deltaはpremium未調整、qで±.5が範囲外になる場合は不可。premium-adjusted FX delta・定性説明・図・受入は保留 | 32 passed・ruff PASS |
| §20.5 | `_smile_surface.py` | Table20.2全30IV・9月13.7%・1.5年/.925で14.525%。独立Fraction4隅重み・双線形多項式、ln(K/F)/√T軸。価格凸性/calendar違反を補間とは別に検出する合成例 | 計算部分完了。IVを補間しtotal varianceへ置換しない。範囲外はエラー、無裁定修復/市場surface推定は別研究。説明・図・受入は保留 | 45 passed・ruff PASS |
| §20.6 | `_smile_surface.py` | ΔMV=ΔBSM+vega×条件付きIV応答。独立Q payoff完全再評価の連鎖微分、合成2因子4状態Cov(ΔV,ΔS)/Var(ΔS)と最小分散、非線形再評価の局所極限（本文数値例なし） | 計算部分完了。応答は条件付き時間方向の入力で横断smile傾きと別。実データ推定/モデル較正はRB-H20、局所一次式の精度を超える保証なし。説明・受入は保留 | 57 passed・ruff PASS |
| §20.8 | `_smile_surface.py` | Table20.3 call/put全9行、p=.53140677、端点IV=0とfrown。印刷callから内点IV58.85004/66.62438/69.51882/69.16508/66.09182/59.97265/49.88574%、独立2状態複製・Q密度再評価 | 計算部分完了。K56印刷IV49.0%は丸めcallから49.88574%、未丸めモデルから49.93360%で不一致を保存。本文数値を改変せず誤植候補として記録、説明・受入は保留 | 69 passed・ruff PASS |
| §20.appendix | `_smile_surface.py` | Ex20A.1 call4.045/3.549/3.055、全8密度.0057/.0444/.1545/.2781/.2813/.1659/.0573/.0113、面積.998473283/残差.001526717、平坦26%区間確率.0031/.0167。独立payoff/三角butterfly積分・対数正規密度への二次収束 | 計算部分完了。丸めた3価格ではg1≈.00806になり、未丸め価格を使用。区間質量は中点則の推定で尾部を直接観測したものではない。負密度・質量残差を保存し正規化/修復はしない。説明・受入は保留 | 84 passed・ruff PASS |
| §21.1 | `_numerical_trees.py` | Ex21.1 N5価格4.49、N30/50/100/500は4.263/4.272/4.278/4.283、Fig21.3全21節点。Ex21.2 Δ−.415/Γ.034/Θ−.0117日、vega.123/rho−.072 per point。独立全停止方針/FD/欧州BSM | 計算部分完了。Greekの推定時点Δt/2Δtと単位を明示。bump固定N・Δσ/Δr=1e−4、元のDerivaGem bump幅は不明。説明・受入は保留 | 12 passed・ruff PASS |
| §21.2 | `_numerical_trees.py` | Ex21.3 futures19.16/20.18/20.22、Ex21.4 FX.0710/.0738、Figs21.5/6全30節点。q=r/q=rf/q=dividend yield、独立全停止方針・FD・欧州BSM | 計算部分完了。先物成長0でも国内金利割引を保持。定性説明・教材・受入は保留 | 26 passed・ruff PASS |
| §21.3 | `_numerical_trees.py` | Ex21.5 4.44/4.208/4.214、Fig21.9全21節点、S*=49.999218/PV2.000782。CV未丸め4.2454208/表示4.25。独立全停止方針・配当PDE・欧州BSM、割合配当の複合縮小 | 計算部分完了。σはS*へ適用。N5のex日3.5月は格子外で行使は月次のみと明示し、aligned時はex前後を比較。CV改善の普遍保証なし。説明・受入は保留 | 37 passed・ruff PASS |

## 次の実装

- Ch10–20の計算87項目の部品を実装・push。Ch10：6、Ch11：6、Ch12：5、Ch13：11節＋付録、Ch14：7、Ch15：12節＋付録、Ch16：3、Ch17：6、Ch18：10、Ch19：11節＋付録、Ch20：6節＋付録。Ch16.5は算術部分のみ、§19.11は合成bookの計算部品まで。
- 直近はCh20の7計算項目（§20.1/2/4/5/6/8/付録）。対象84 tests・ruff check/format check PASS（2026-10-06）。Ch10–19と全suiteはこのまとまりでは再実行していない。
- 次はCh21 §21.4（p=.5木・三項木）。P4の計算は合計90節、正式受入は0/112のまま。
- Ch20の保留：2005–2015の実測FX列は原データなし。Table20.3 K56のIV49.0%は印刷callから49.88574%で不一致。付録の価格3桁丸めはg1を.0057から約.00806へ変えるため未丸め価格を使う。surfaceの無裁定修復と条件付きIV応答の実データ推定は別研究、§20.3/7の定性説明・章の受入は保留。
- Ch19の保留：Table19.3の精密再計算256337.59と印刷256600の差262.41ドル、Table19.5のbook入力欠落、Ex19.9の88/92百万で厳密な時間規約が揃わないこと。Ex19.8の21GBP差は係数4桁丸めで再現可能だが原著の中間精度は不明。成績Tables19.1/4は無利息・無割引の規約を固定seed MC/6SEで確認し、資金口座付き費用と区別する。
- 定性・説明要求は保留：Ch19 §19.3/10/14、Ch18 §18.2、Ch16 §16.1–2・会計史/研究の説明、Ch11 §11.2、Ch14 §14.1/14.4、Ch10 §10.5・10.8–10.12。§10.10の説明用の損失20ドルは下調べで算術確認済み。計算部品の完成は章の正式受入を表さない。
- [Claudeの既存Ch10–16レビュー](P4_REVIEW_NOTES.md)は別管理。Ch17の為替IVはR-07を引き継がない求根へ変更済み。既存Ch15のR-07、権利確定日R-02、tail境界R-08、docstring R-01等は未修正。既存ファイルのformat・全suite・正式受入は再開時の確認事項。

## 再現コマンド

今回のCh20対象84 testsとlint/format確認。Python/ruffはルートの共有venvを使い、PYTHONPATHでロジックworktreeを明示する。release/全suite/正式受入は未実行。

```bash
cd /home/kazumasa/worktrees/m29
export PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/johnhull/report:$PWD"
/home/kazumasa/projects/.venv/bin/python -m pytest -q johnhull/hullkit/tests/test_smile_surface_*.py
/home/kazumasa/projects/.venv/bin/ruff check \
  johnhull/hullkit/src/hullkit/_smile_surface.py \
  johnhull/hullkit/tests/test_smile_surface_*.py
/home/kazumasa/projects/.venv/bin/ruff format --check \
  johnhull/hullkit/src/hullkit/_smile_surface.py \
  johnhull/hullkit/tests/test_smile_surface_*.py
```
