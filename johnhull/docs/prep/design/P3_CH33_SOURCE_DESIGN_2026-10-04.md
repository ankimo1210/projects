> 未受入の準備資料。原典回収とscratchの結果であり、製品実装・全5軸の正式受入は別途必要。

# P3 Ch33 — 原典・記法・独立数値準備

更新: 2026-10-04。**実装前の準備。節の受入・製品検証ではない。** 原典と既存コードの読み取り、および `/tmp` の独立 scratch のみを実施した。repo/Git/公開 API/製品 pytest/browser/D1 は操作していない。

## 1. 到達点と実際の章単位

- GE の Ch33 本文は **§33.1–33.3、pp.755–770**。771–772 は要約・文献・章末問題。**専用 Appendix はない**。
- 読み取った台帳には **33.1/33.2/33.3 の 3 単位**があり、すべて `unreviewed`、`requirements=[]`。下調べの **11 要件 (3+5+3) は draft** で、台帳に登録済みの正式要件ではない。補助 TN17/TN31/TN14 を新しい台帳単位に数えない。
- Ex33.1 と **Ex33.2**、Tables33.1–5 の全セルを確認。Ex33.2 は Table33.1 の hump の説明なので落とさない。Table33.5 の原典頁は **764**、flexicap 段落は **763**（旧下調べの p765 を訂正する候補）。原本の添字を画像で確認した既回収記録も再利用した。
- Ex33.1/Table33.1 は独立差分分散で表示丸め内に再現。Tables33.4/5 は全20行で component の丸め区間と total norm の丸め区間が交差する。未丸め因子入力を回収したわけではない。
- Ratchet/sticky の 60 caplet は raw 因子で独立 MC を行い、原典の「SE 約 .001」に基づく参考帯に入った。**Sticky の初期 strike 未明示という条件付き結果**であり、原典 seed/丸め前因子/continuous-time 厳密値の再現とは扱わない。
- HJM の符号・Gaussian martingale/債券 option、測度別 LMM drift、異 tenor swaption Jacobian、CEV χ²/α=.5 別導出、合成 cap/swaption calibration、合成償却/CMO/OAS を独立計算した。
- 未解決: **flexicap 固定 strike と対象 reset/payment 日**、sticky 初期 K0、Eq33.19 の未定義下限 n、γ 分母の積上限の版内差。合成入力や掲載価格からの逆推定で埋めない。

読み取り snapshot: `docs/section_ledger.json` SHA256 `c8ee0ede6954e3bc0dfcdb4d15f7a66658ed3068c7ce16eea70ffd63a8639e35`。親の並行開発で将来変わり得るので、今後の作業は現在台帳と再照合する。

## 2. 原典・一次資料・固定 provenance

### 2.1 ライセンス原本と著者の公式保存庫

| 資料 | 参照範囲 / 種別 | 保存パス | SHA256 |
|---|---|---|---|
| Hull 11e GE | Ch33 本文755–770、問題771–772、880頁 PDF。物理頁と印刷頁が一致 | `/home/kazumasa/projects/johnhull/options, futures and other derivatives 11th.pdf` | `8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482` |
| Technical Note 17 | 全1頁、HJM の短期金利過程の導出。補助ノート | `/tmp/p3-ch33/TechnicalNote17.pdf` | `be272e39a7a98eacfce8ff9284506055c664d9992c6ff026ff1f6fad8b1edd6a` |
| Ch33 slides | 全22 slide + 全22 notes XML、関連18–19。notes は slide 番号のみ | `/tmp/p3-input-recovery/Ch33HullOFOD11thEdition.pptx` | `4283cbc017b0a21afd68c71cf485a1901a1b7283ba256cf3c6812e936a1aad4c` |
| Ch33 solutions GE | 全5頁。33.12/33.13/33.14、physical p4–5 | `/tmp/p3-input-recovery/HullOFOD11eSolutionsCh33.pdf` | `a58115cbb5a39ec29e9dfaae5026f914a987bab06a6d28d808c602e5a5490a02` |
| 11e errata | 全2頁、保存 snapshot 2026-08-06。Ch33 の項目はない | `/tmp/p3-input-recovery/Errata (11th  edition).pdf` | `197cce401783dc947737bfec778a33fe428a1b7690642c523f4dd7b46a46576d` |
| Hull–White 2000 author paper | 40頁 NYU working paper。旧記法24/25、CEV26–31、Table1–4 | `/tmp/hull_lmm_nyu_2000.pdf` | `a9350e94d15062019b63d1c7f5fab2e04e0019d40e7940aaf0356fb9c4b594b0` |
| TN31 | 全5頁の HJM→Ho–Lee/HW 特殊例。Ch32 準備から再利用 | `/tmp/p3-ch32/TechnicalNote31.pdf` | `43f5c0b6e1a48339214a3f7357e506176b5366ba1140883e0856218508a1b58a` |
| TN14 | 全4頁、二因子 HW とその Appendix。Ch31 準備から再利用 | `/tmp/p3-input-recovery/TechnicalNote14.pdf` | `9068c1d786837a5946fc7a3cd2114cafc4edb0293975f70508b4cadedc31af5f` |

著者 archive は [Rotman FinHub](https://github.com/rotmanfinhub/john-hull-textbook-resources)。固定 full commit **`9b8dbfe37661dbd3de65d3a1489dc1297e840de7`**。短縮 SHA、変動 main、tree SHA と混同しない。実 PDF magic と Poppler の type/pagecount を確認した既回収物を再利用し、TN17 は本作業で固定 raw URL より新規取得して Git blob `6a404850be5617b8e7d921a4a744ed567f685671` も照合した。原 Rotman の HTML error を PDF として扱わない。

固定 raw URLs:

- [TN17](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote17.pdf)
- [Ch33 slides](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Download%20PowerPoint%20Slides/Ch33HullOFOD11thEdition.pptx)
- [Ch33 GE solutions](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Answers%20to%20End%20of%20Chapter%20Questions/Answers%20to%20End%20of%20Chapter%20Questions%20in%20Global%20Edition/HullOFOD11eSolutionsCh33.pdf)
- [11e errata](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Errata%20%2811th%20%20edition%29.pdf)
- [TN31](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote31.pdf)
- [TN14](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote14.pdf)
- [NYU author copy](https://w4.stern.nyu.edu/finance/docs/WP/2000/pdf/wpa00023.pdf)、[NYU archive record](https://archive.nyu.edu/handle/2451/26689)、[同 PDF](https://archive.nyu.edu/bitstream/2451/26689/2/FIN-00-023.pdf)。PDF 内の title/author を確認。FIN 番号は原 PDF 本文に見つからないため、archive の識別子と本文表示を区別する。

取得記録: `/tmp/p3-input-recovery/download-records.json`、`/tmp/p3-ch33/source-downloads.json`、`/tmp/p3-ch32/source-downloads.json`。raw byte/hash/URL/固定 commit/blob を記録。個別著作権表記は archive 総則より優先し、原典 PDF 自体を repo へ新規収録しない。

### 2.2 読み取り docs と旧準備の扱い

`docs/prep/sections/ch33.md`、`docs/prep/design/P3_TREE_LMM_IMPLEMENTATION_2026-10-04.md`、`P3_LMM_ORIGINAL_NOTATION_2026-10-04.md`、`P3_SOURCE_GAPS_2026-10-04.md`、`docs/prep/sources/sources_S001-S031.md` と `sources_S032-S062_L01-L03.md` を照合。旧「60値未再計算」は今回の独立 scratch で前進したが、正式受入・原 sticky 初期条件の完全回収とは区別する。

既回収の `/tmp/p3-nyu-flexicap-recovery.md`（原図照合）、`/tmp/p3-input-recovery.md`、`/tmp/p3-two-factor-design.md`、`/tmp/p3-ch32-source-design.md` を再利用した。NYU Table4 (1999-08-12 の CEV calibration) を GE flexicap の fixture に置換しない。公式 archive のファイル一覧および既抽出 DG201/DG400 VBA を flexi/ratchet/sticky/LMM で確認したが、この例の追加 strike/date/workbook は得られなかった。同じ資料の反復取得で新証拠が増えなくなったため、未解決条件を保持する。

## 3. 全 draft 要件と後続受入に必要なもの

| Draft ID | GE 頁と要点 | 今回の独立準備 | 後続の必要証拠・不足 |
|---|---|---|---|
| D33.1-01 | 755–757: bond→finite forward→instantaneous、v(t,t)=0、Itô 符号、33.1–4 | Signed v の導出、Gaussian kernels、bond option 別積分 | Lesson/導出/有限満期差・時間刻み/実装照合 |
| D33.1-02 | 757: 独立多因子 HJM drift、33.5–6 | 1/2因子 discounted bond の exact Gaussian moment | 製品への独立 oracle、correlation factorization、rendered |
| D33.1-03 | 757–758: Ho–Lee/HW 特殊例、一般履歴依存/非Markov/計算量 | 2^30、同 r で異 drift の2履歴、Ho–Lee/HW variance limit | 有限因子数≠scalar Markov、任意 HJM を説明のみに縮小しない |
| D33.2-01 | 758–765: simple F/actual-actual、payment numeraire、rolling drift、33.7–10/12/15/16 | Spot/terminal drift 別導出、MC numeraires/last-forward | Event/curve/measure/discount 契約、零vol・相関・高vol mutation |
| D33.2-02 | 760–761: stationary Λ、33.11、Ex33.1/2/Table33.1 | Exact bootstrap、全セル、negative incremental variance 方針 | tenor・vol-time shape、quote入力品質、正式 pin |
| D33.2-03 | 761–764: Euler、fixing、discount、ratchet/sticky/flexi、Tables33.2–5 | 60 MC、raw/normalized、scheme refinement、factor丸め区間 | Sticky K0、flexi strike/dates 未取得。joint engine と3契約を保持 |
| D33.2-04 | 764–767: swaption frozen variance、異tenor、PCA/calibration、33.17–20 | All-period Jacobian/complex step、合成 price fit/SVD | n/γ表記差保持、joint MC swaption/近似誤差、実入力未指定 |
| D33.2-05 | 767–768: CEV、33.21、χ² skew、Bermudan LSM/boundary、因子数論点 | CEV analytic/BES0/α1極限、LSM reuse境界 | Joint CEV boundary scheme、Bermudan policy train/eval＋oracle |
| D33.3-01 | 768–769: guarantee/prepayment、pass-through/CMO/IO/PO | 元本800・2配分、合成 waterfall/principal保存 | 原典時点の保証説明、信用と返済オプション、説明/rendered |
| D33.3-02 | 769–770: monthly curve history→prepay→CF→Treasury+spread | 合成 deterministic amortization、SMM例 | 原 pool/prepay関数なし。stochasticモデルの実データ完了と呼ばない |
| D33.3-03 | 770: OAS price inverse と model/pool dependence | Fixed CF OAS inverse/単調性 | 任意 prepay/market price を原典数値に昇格しない |

ここでの完成は source/design scratch の完成であり、11 draft の正式受入完了ではない。§33.3 の D3（説明＋rendered）候補は構造説明部分で、OAS 計算まで受け入れたことにはならない。

## 4. 原典の全数値 pin 候補

### 4.1 Ex33.1/2、Table33.1 (p760–761)

時間は年、rate/vol はコード内では小数。以下の vol は **%表示**、2 decimal% の half unit は `.005 percentage point = .00005`。

Ex33.1: spot `[24,22,20]%` → Λ `[24,19.7989898732,15.2315462117]%` → 掲載 `[24,19.80,15.23]%`。Ex33.2 は次表の hump で、forward vol の hump が spot より強いという説明を保持する。

| k | spot% | Λ掲載% | spotから exact bootstrap% | raw2F norm% | raw3F norm% |
|---:|---:|---:|---:|---:|---:|
| 1 |15.50|15.50|15.50000000|15.50524105|15.50235466|
| 2 |18.25|20.64|20.63673908|20.63783903|20.64125238|
| 3 |17.91|17.21|17.20986055|17.21377355|17.20587109|
| 4 |17.74|17.22|17.21993322|17.22189595|17.21872237|
| 5 |17.27|15.25|15.24578958|15.25000000|15.25002951|
| 6 |16.79|14.15|14.14779488|14.15187973|14.14621858|
| 7 |16.30|12.98|12.97711062|12.97592386|12.97596625|
| 8 |16.01|13.81|13.81053221|13.80702720|13.81231697|
| 9 |15.76|13.60|13.59549926|13.59014717|13.59694819|
|10 |15.54|13.40|13.39841782|13.39699220|13.39560002|

### 4.2 Tables33.4/5 の全 loading (p764)

| 年 |2F q1%|2F q2%|3F q1%|3F q2%|3F q3%|
|---:|---:|---:|---:|---:|---:|
|1|14.10|-6.45|13.65|-6.62|3.19|
|2|19.52|-6.70|19.28|-7.02|2.25|
|3|16.78|-3.84|16.72|-4.06|0|
|4|17.11|-1.96|16.98|-2.06|-1.98|
|5|15.25|0|14.85|0|-3.47|
|6|14.06|1.61|13.95|1.69|-1.63|
|7|12.65|2.89|12.61|3.06|0|
|8|13.06|4.48|12.90|4.70|1.51|
|9|12.36|5.65|11.97|5.81|2.80|
|10|11.63|6.65|10.97|6.66|3.84|

2F 年1の norm は15.50524105% 対 total15.50%、年9は13.59014717% 対13.60%。しかし component 自体が丸められている。全成分を±.005ppとした norm 区間は、年1 `[15.4986144542,15.5118680371]%`、年9 `[13.5835212666,13.5967735143]%`。どちらも total ±.005pp 区間と交差する。全20行で交差するため誤植とは断定しない。

**Raw** は掲載 component をそのまま価格入力にしたもの。**Normalized** は方向を保ち、Table33.1 の spot から復元した exact norm へ row を scale する別の感応度実験。元の未丸め factor を回収したこと、raw と同じ入力であること、掲載価格の正解入力であることを意味しない。

### 4.3 Tables33.2/3 全60価格 (p763)

元本100、annual accrual、start1..10年→payment2..11年、continuous flat5% の単一曲線、annual simple R0=`exp(.05)-1=.05127109637602404`。Spread25bp=`.0025` はこの年単利へ加算する。

| start |Ratchet1F|2F|3F|Sticky1F|2F|3F|
|---:|---:|---:|---:|---:|---:|---:|
|1|.196|.194|.195|.196|.194|.195|
|2|.207|.207|.209|.336|.334|.336|
|3|.201|.205|.210|.412|.413|.418|
|4|.194|.198|.205|.458|.462|.472|
|5|.187|.193|.201|.484|.492|.506|
|6|.180|.189|.193|.498|.512|.524|
|7|.172|.180|.188|.502|.520|.533|
|8|.167|.174|.182|.501|.523|.537|
|9|.160|.168|.175|.497|.523|.537|
|10|.153|.162|.169|.488|.519|.534|

- Ratchet: `K_j=R_(j-1)+s`、100δ max(R_j−K_j,0) at t_(j+1)。K1=.05377109637602404 は既知 R0 とルールから導く。
- Sticky: `K_(j+1)=min(R_j,K_j)+s`。原典 K0 は明示されない。今回は **capped R0=R0、すなわち K0>=R0（例 K0=R0）** という明示仮定を置いた結果。First caplet から逆較正していない。
- 原典は100,000 simulations、antithetic、各 caplet SE約.001。Seed、simulation数がpathかpairか、factor未丸め値、厳密なscheme/原典 covariance は不明。末尾桁を確定 pin にしない。

### 4.4 Flexicap とその他の数値

Flexicap p763 は annual-pay、元本100、flat5%、Tables33.1/4/5の vol、**最初の5個の ITM caplet を行使**、1/2/3F価格 **3.43/3.58/3.61**。p772 問題33.14 は first N ITM の強制行使と、自由行使/開始日選択型を区別する。

**固定 strike、eligible first/last reset/payment dates は未掲載**。5%曲線をstrikeに置換せず、周囲のstart1..10/pay2..11をflexi固有の指定と断定しない。Flexi段落では5%の compounding と MC数/SEも再掲されないので、周辺契約の明示条件と区別する。権利を事後に大きいpayoff上位5個へ配分する先読みは不可。入力回収までは3価格をpendingのまま残す。

他の original 数値: quarterly40本=10年、t24=6年時点のremaining4年はindex例（価格pinなし）。§33.1 2^30=1,073,741,824 は計算量。§33.3 30年mortgage、tranches400/300/100 と100/200/500はいずれも元本800の構造pin。原 pool/prepay式/market calibration quote/履歴PCA行列/ MBS価格/OAS価格はない。

## 5. §33.1 HJM と補助ノートの全導出境界

### 5.1 符号・単位・Eq33.1–6

Bond は signed vector v（単位 year^-1/2）で `dP/P=r dt+v·dW`。満期境界v(t,t)=0。瞬間 forward は `f_inst(t,T)=-∂T log P`（year^-1）、simple tenor F_k と同じ記号に混ぜない。

Finite continuously compounded forward は33.2 `(log P1−log P2)/(T2−T1)`。33.3 drift は `(||v2||²−||v1||²)/(2ΔT)`、noise `(v1−v2)/ΔT`。ΔT→0 で33.4:

\[
 df_{inst}(t,T)=v(t,T)\cdot\partial_Tv(t,T)dt-\partial_Tv(t,T)\cdot dW_t.
\]

Forward diffusion σ=−v_T、v=−∫_t^Tσ(t,u)du。したがって33.5–6の multi independent factor drift:

\[
 \mu(t,T)=\sum_q\sigma_q(t,T)\int_t^T\sigma_q(t,u)du.
\]

相関Brownianなら σ^T C ∫σ。Independent factorization を行えば内積になる。原式の積を componentwise で置換し、相関を落とさない。σは absolute forward-rate diffusion（rate/year^1/2）、LMM relative λ はyear^-1/2で単位が違う。

### 5.2 TN17 全1頁と「Appendix」境界

TN17 の短期金利 r=f_inst(t,t) を終点で微分すると、book signed-v 規約では:

\[
 r(t)=f_{inst}(0,t)+\int_0^t v(\tau,t)v_T(\tau,t)d\tau-\int_0^t v_T(\tau,t)dW_\tau,
\]
\[
 dr=\left[f'_{inst}(0,t)+\int_0^t(vv_{TT}+v_T^2)d\tau-\int_0^t v_{TT}dW_\tau\right]dt-v_T(t,t)dW_t.
\]

TN17 掲載の noise integrals は **plus v_t/v_tt**、book33.4は **minus v_T**。TN17 自体は signed bond SDE を再掲しないので、`v_note=-v_book` と記号をmappingすれば drift vv_T は保ち noise が一致する。このmappingを明記して独立導出に使う。著者が訂正を出したとは言わず、同名vを無断で両式に代入しない。Suffix t は TN17 の maturity argument（ここではT）で、Brownian integration time τ の微分ではない。

同じrでも履歴積分が異なれば future driftが変わる。有限Brownian因子数はr一変数のMarkov性を保証しない。Scratchはσ(s,T)=.01[1+.8(T−s)]、t1、shock times .25/.75、履歴 `[0,0]` と `[1,-4/3]` を置き、r random partがともに0でもfuture driftは0と−.0026666667。これは追加状態を加えれば有限次元Markovになる特殊例で、すべての一般HJMが無限次元でなければならないという主張ではない。

TN31 の Ho–Lee/HW 特殊例、TN14 の **Ch31二因子HW Appendix** は参照可能だが、Ch33固有Appendix/新台帳単位ではない。TN14全式の既準備は `/tmp/p3-two-factor-design.md` とfixturesに委譲し重複実装しない。

### 5.3 独立 Gaussian checks

Synthetic f0(T)=.03+.002T、t2/T6、σ=.01のHo–Lee(a0)/HW(a.12)、独立2F(a.12/.5,σ.01/.006)。Forward driftを積分してlog discountとlog bond meanを作り、全Gaussian kernelのvarianceを別積分。`E[D(0,t)P(t,T)]=P(0,T)` は3例ともdouble表示差0。Discount noise+conditional bond noise=full bond kernelもmachine precision。

Bond option expiry t2/underlyingT6/K.9: expiry-measure ratio variance `∫||v(s,T)-v(s,t)||²ds` と独立 Ho–Lee/HW閉式 `Σσq² B(aq,T−t)²[1−exp(−2aqt)]/(2aq)` を比較。a0 branchはt。Gaussian closed price と threshold分割したpayoff quadratureを比較し、結果はJSONに保存。印刷価格pinはない。

未来の一般HJM離散化では time/maturity refinement、v(t,t)=0、discounted martingale、Ho–Lee/HWの解析bond/optionとの比較が必要。任意履歴volの完全製品engineは今回未実装。

## 6. §33.2 LMM の正規仕様候補

### 6.1 Tenor、curve、measure、33.7–10/15

`t0=0<t1<...<tN`、δk=t_(k+1)−tk（原典actual/actual）。Fk=(P(t,tk)/P(t,t_(k+1))−1)/δk。F0はt0で既fix。Forwardλk vectorはrelative log diffusion、c_ki=λk·λi、w_i=δiFi/(1+δiFi)。Live mは次reset。

- Pay-date forward measure Q^(k+1): `dFk/Fk=λk·dW`、martingale (33.7)。Vanilla caplet Black の基準。
- Rolling spot/CD measure: **μk=+Σ_(i=m..k) w_i c_ki**。Self含む。33.8のnumeraire drift shiftと33.9の `v_i−v_(i+1)=w_i λi` から33.10/15を導く。
- Terminal tN measure: **μk=−Σ_(i=k+1..N−1) w_i c_ki**。Selfなし、last forwardのdrift0。Book rolling式の符号をterminalへそのまま使わない。
- Scratchではlive4本/unequalδ/2Fを用い、log bond-ratio productsの独立 finite derivative から driftを再導出。Spot差5.42e−13、terminal差8.04e−13。MC別実装の直接二重和との drift差は≤3.47e−18。
- δ→0でabsolute LMM diffusion Fiλi=σに固定するとHJM driftへ収束。λ=σ/Fiという単位mappingが必要。

State inputはcurve discount factorsからsimpleFへ変換する。P0>0、δ>0、1+δF>0を確認。**通常lognormal baselineはF>0**。Signed zero curveからnegative Fが出る場合はモデル不適合を記録し、silent clamp/abs/shiftで原モデルを変えない。Negative-rate対応のnormal/shifted/CEVは別仕様。Correlation PSD、loading dimensions、zero vol、ρ±1/rank deficiencyはfactorizationと数値検証に残す。

### 6.2 Vol-time、bootstrap、33.11–16

Stationary schedule: λk(t)=row_(k−m(t))。Reset eventをrecord→freeze→mをadvanceという一意順序にする。原典 m=min{index:t≤t_m} はreset equalityを含むため、右連続simulation intervalでは `[t_j,t_(j+1))` の m=j+1 を明示。Brownian coordinatesは各stepで全alive ratesに共有する。

33.11: `σ_k² tk=Σ_(i=1..k) Λ_(k−i)² δ_(i−1)`。Equalannualなら `Λ_(k−1)²=kσ_k²−(k−1)σ_(k−1)²`。Unequalδはlower triangular system。Negative incremental varianceはinput inconsistency、暗黙max(.,0)不可。

33.12はrolling relative dynamics、33.13はItô log dynamics。33.14の1F、33.16のmultiF log Eulerは現在resetのdriftを1区間内で凍結:
`Fnew=Fold exp[(μold−||λ||²/2)dt+λ·ΔW]`。初期Fだけで全将来driftを凍結する方法ではない。Predictor-correctorは同じΔWで予測stateのdriftを再計算し平均する別scheme。要件には原Euler、refinedPC、biasの区別を残す。

### 6.3 支払・discount・stub・OIS

Tenor eventでrolling B(t_(j+1))=B(t_j)(1+δjRj)。Caplet payoffHをfix tkで評価したとき:

\[
 PV_{spot}=E\left[\frac{H}{B(t_k)(1+\delta_kR_k)}\right],\quad
 PV_N=P(0,t_N)E_N\left[H\prod_{i=k+1}^{N-1}(1+\delta_iF_i(t_k))\right].
\]

Fixing=tk、payment=tk+1を混ぜない。Reset後rateを更新せず、strikeは既知historyのみ。Substepでfuture bond ratiosは分かるが、**非tenorのstub bond絶対価格/rolling Bはlive Fだけでは指定されない**。最小候補はeventsをtenor上に置く。任意非tenor exercise/payment対応には追加stub dynamicsが必要。

原 Tableの最小baselineは **single curve**。OIS discountと別projection Fを持たせるなら追加joint dynamics/covarianceが必要。p760脚注8はOISについて33.11を **tk..tk+1のovernight不確実性** に合わせて変更すると述べる。Term fixing型の Fk(tk) を realized compounded overnight couponへ流用しない。M29のprivate exact conditional payment/annuity mixtureはflatHW＋deterministic additive simple-rate projection basisで、full stochastic multi-curve LMMの完成証拠ではない。

## 7. 非標準 cap の独立 MC と不確実性

実行済scratch: `/tmp/p3-ch33-lmm-mc.py/json`、詳細 `/tmp/p3-ch33-lmm-mc-notes.md`。7configs×3factors=**21 runs**、約74.24秒。Python3.12.3/numpy2.4.6/scipy1.17.1。各run100,000paths=50,000独立antithetic pairs。SEはpair meanのSD/√pairs。事前seed73017/210041。Priceにfitするseed選別なし。

Configs: rawspotEuler1、rawspotPC1/4/16、rawterminalPC16、normalizedspotPC16、rawspotPC16別seed。16fine Brownian incrementsをaggregateして粗いstepを作り、paired差を測定。Pooled referenceはrawspotPC16の2seeds全量、各factor **200,000 paths=100,000独立pairs**。

| factor | Ratchet合計 | SE | 掲載行和 | Sticky合計 | SE | 掲載行和 |
|---:|---:|---:|---:|---:|---:|---:|
|1|1.814822138|.002495747|1.817|4.364634783|.008864009|4.372|
|2|1.865928937|.002559304|1.870|4.488841890|.008845748|4.492|
|3|1.923319421|.002610384|1.927|4.584244881|.008773589|4.592|

合計SEはpath別10caplet sumのpair statisticsで計算。各caplet SEを合算しない。掲載行和は別の原典printedcap-totalではなく表10行の和。Covariance of meanも保存した。

60caplet最大combined standardized残差1.957234。参考同時帯は `z(1-.05/(2*60))*sqrt(ownSE²+.001²)+.0005`。全60行以内だが、source SEは「約」でcovariance/丸め前input不明。厳密coverage保証、末尾桁pin、受入宣言に使わない。StickyはK0仮定付き。

- AnnualEuler1−PC16: ratchet合計−.004023/−.003898/−.003861、sticky−.014333/−.013566/−.013134。Paired SEより明確に大きい。原式の離散化誤差を丸め合わせで消さない。
- PC4−PC16最大合計差: ratchet7.32e−7、sticky7.48e−6でpairedSEと比較し小さい。PC16がcontinuous-time厳密解であるという断定はしない。
- Terminal−spot差はpairedSE内。Normalized−raw差も別保存（例1F ratchet−.000186、sticky−.000521）。Norm調整を掲載価格再現の隠れた補正にしない。
- Pooled30 vanilla caplet vs integratedvariance Black: max|z|1.6253。Numeraire martingale max|z|1.7273、weightedlastforward max|z|2.4401、terminal logpairmean error≤3.11e−15。個別30/60検査の2SE超過を即欠陥と判断しない。

未来の受入では deterministic pin／model-input uncertainty／MC sampling／scheme bias を別軸にする。原典を厳密seedで再現する要求は作らず、事前tolerance/paths/refinementを固定。Highvol・irregulartenor・別curve・payoff order・leakage mutationは今回未実行。

## 8. Swaption、PCA、curve/calibration

### 8.1 Eq33.17–19 の独立式

Expiry T0、pay T1..TN、Gk単利coarseforward、τk。U=Π_(j=0..N−1)(1+τjGj)、D=Σ_(i=0..N−1)τiΠ_(j=i+1..N−1)(1+τjGj)、swap S=(U−1)/D。

\[
 \gamma_k=\frac{U}{U-1}-\frac{\sum_{i=0}^{k-1}\tau_i\prod_{j=i+1}^{N-1}(1+\tau_jG_j)}{D},\qquad
 \partial_{G_k}\log S=\frac{\tau_k\gamma_k}{1+\tau_kG_k}.
\]

Relative factor diffusion `ηq=Σk Jk Gk βkq`。**33.17 V(t)=Σηq² はrelativevariance rate**。Bookの「variance of swap rate」という表現だけからabsolute varianceをBlackvolへ代入しない。33.18のBlackvolは `sqrt(∫_0^T0 V(t)dt/T0)`、frozen-forward `Gk(t)=Gk(0)`。Dynamic joint modelのexactswapvolではない。

異tenor: `1+τkGk=Πm(1+δkmFkm)`、fineJacobian `∂_(Fkm)logS=δkmγk/(1+δkmFkm)`。これを全k,mに加算して33.19候補を得る。

- **原本/公式解答33.13とも33.19下限k=nで、11e局所0開始のnが未定義**。NYU旧24/25はswapstart t_nと定義するのでnが整合。局所allperiod lower0はM=1→33.18とchainruleからの数学的推論で、公式errataではない。
- **γ denominatorの最終product上限はbook画像N、公式解答33.12はN−1**。Definitions/annuityからN−1が整合。この差は33.19下限と別の問題。
- Synthetic unequal coarse3periods＋2subperiodsでdiscountproductsからswaprateを計算。Complexstep Jacobian差はcoarse2.84e−14/fine7.11e−15、centralFDは1e−8台。M1reduction差0。正variance .03190976686647、誤ってfirstperiodを落とすと .01549448599466。Oneperiodswaption=caplet価格も一致。
- 未来はjointMC European swaptionを別oracleにして、frozen approximation errorをvol/correlation/expiry/tenorで測る。Synthetic quoteを同じ近似式でfitできてもjointMC正しさの証明にはならない。

### 8.2 PCA33.20 と calibration

歴史PCAの loading方向a_jq、scoreSDs_qから:
`λjq=Λj*s_q*a_jq / sqrt(Σ_r(s_r*a_jr)²)`。
Λ>0でdenom0は不適合、Λ0はzero row許容。Globalorthogonalrotation/列sign反転はcovariance保持。単一maturityrowの符号反転はcorrelationを変える。原典discussionの**absolute ΔFのPCAとrelative/logdiffusion λの単位**を明示し、単なるeigenvector転記をモデル較正と呼ばない。

Quotesはcaps/European swaptionsの**価格**。Blackvol→priceの入力curve/strike/annuity/daycountを固定。最小目的は `Σ(Ui−Vi)²+Σw1(Λi+1−Λi)²+Σw2(Λi+1+Λi−1−2Λi)²`、LM等。LogpositiveparameterはΛ0を表せないためzero branchを別に用意。Quote数≥unknown数だけでなくquote-onlyJacobian rank/SVD/multistart/heldoutを保存し、penaltyによるaugmentedrankをmarket識別性と混同しない。

Scratchの **合成truth** Λ[.18,.23,.17]、方向angles[-.2,.1,.45]、singlecurveflat5%、annualcaps(1/2/3resets)と2x2European frozenapproxを用いる。No penaltyの2初期値は価格残差≤2.22e−16、quote-onlysingularvalues[6.20622,1.90882,.354842]。Penalty .001/.1ではmaxpriceerror .00986/.02373。Heldoutstrike.06も別保存。これは原典marketdatasetではない。

PCA scratchのraw配列は **明示したsynthetic directions** で、実歴史covarianceの固有ベクトルを回収したものではない。正規化・rotation不変性・onerowsignmutationの数学を確認した。現実のPCA/calibrationdataの日付/provider/fullmatrixは未指定のまま。

## 9. CEV33.21 と Bermudan

### 9.1 Diffusion と χ² keyword mapping

CEV `dFi=b_i dt+η_i·dW`、η_i=z_i Fi^α。Bookは0<α<1、α1をlognormal limitに用いる。z単位はrate^(1−α)/sqrt(year)でBlackrelativevolと異なる。Absolute driftは:
`b_terminal,k=-ηk·Σ_(i>k)δiηi/(1+δiFi)`、
`b_spot,k=+ηk·Σ_(i=m..k)δiηi/(1+δiFi)`。
普通logEulerをF^αに代入するだけではzero境界・ドリフトを保証しない。

Payforwardmeasureのβ=1−α、J=∫||z||²dt、x=F0^(2β)/(2β²J)、y=K^(2β)/(2β²J):

\[
 c=F_0\operatorname{ncx2.sf}(2y,\ df=2+1/\beta,\ nc=2x)
   -K\operatorname{ncx2.cdf}(2x,\ df=1/\beta,\ nc=2y).
\]

Caplet PVはnotionalδP(0,pay)*c、floorはput-callparity。**NYU p22のχ²説明proseはdegree/noncentralityの順序が式と読み違えられる**ので、df/ncをkeywordで固定し独立BES0で照合する。公式訂正と断定しない。α>1のNYU別式はbookbaseline外の追加研究で、暗黙にscopeを広げない。

α1はBlack別branch、J0はintrinsic、F0=0はabsorbing boundary。α→1のχ²引数巨大化は数値安定性を測り、根拠ないthresholdでmodelをsilent変更しない。NegativeFの分数冪は通常CEVbaseline不適合。

Synthetic F0=.05/E3、初期relativeσ=.2、z=.2F0^(1−α)、strikes.03..07、α=.5/.8/.95/.99/.999/1。ImpliedBlackskewは低strikeで高く、α1でflat.2へ戻る。ATMforwardcall .00688382234576(α.5)→.00687548849320(α1)。α.5のexactBES0Poissonmixture（centralχ²＋zeroatom）との別計算差≤4.03e−16。Absorptionmassを保存。GeneraljointCEVscheme/PDE/Bermudanは未実装。

### 9.2 Bermudan を縮小しない設計境界

Bookのexerciseはswap paymentdatesの一部/全部。Aliveforwardvector/annuity/MTM/factorsをstate候補にし、exercise-dateのみdecision、複数行使不可、continuationは適切numeraireへ正規化する。Training/evaluationpathsを分け、方策固定後のheldout評価をlowerboundとしてSE付きで記録。Regressionrank/lowITM/feature scaling/無行使branch、boundarypolicy比較、小規模independenttree/PDE/dual候補を保持する。1Floadingでも全F群は一般にHW1Dと同一ではない。

**§27.8 LSM/American MCは M17 で受入**。M9は§26.17staticreplication。`hullkit.american_mc` はNDstatesとtrain/applypolicyを持つが、現APIdiscountはconstant float `rate`。Randomnumeraire/pathdiscountをそのまま受け取れず、privateadapter/別kernel候補が必要。公的API変更は今回提案・実施しない。Onefactoraccuracyの実務論点/対立文献を結果保証へ置換しない。

Bookflexi first5ITMはchronological forcedexerciseで、Bermudan LSM/optimalquotaの契約とは異なる。自由行使flexiを研究する場合はremainingrightsをstateに含め、book3pricesの原契約へ混ぜない。

## 10. §33.3 MBS、IO/PO、OAS

本文の保証説明は**2021版の記述**として保持。現在のagency制度や個別legalguaranteeをこの章の説明で保証しない。本調査は現在法の助言ではないため新しい法規調査はしていない。Investor defaultprotectionとborrower prepaymentoptionを分ける。

Monthly手順: yieldcurve/history/poolfeatures→prepayfunction→scheduledprincipal/prepaidprincipal/interest→CMOwaterfall→Treasuryrate+spreaddiscount→averagePV。Prepayはrefinanceだけでなく転居等を含み、最適行使金利だけで機械決定する仕様を本文が与えるわけではない。

No-prepay amortization baseline: principalL、monthlycouponi、n360、payment `Li/(1-(1+i)^-n)`、interest=i*balance、scheduled=min(balance,payment−interest)、prepay=SMM*(balance−scheduled)。同月のinterest/返済/fee/seasoningの規約を明記する。CPR→SMM=1−(1−CPR)^(1/12)は追加モデルを置く場合の単位変換、今回は固定SMMの合成例。

CMOは各月principalをA→B→Cへ満額順配分し、negativebalance/overpayを禁止。IOはinterestだけ、POはprincipalだけ。PositiveTreasurydiscountの同一仮定なら返済増加でPO前倒し/IO減少、固定CFではspread増加でPV減少。一般のnegative-rateやspread依存prepayを含むと追加条件が必要。

Syntheticfixture: originalstructureL800/n360、mortgage6%nominalmonthly、Treasury5%continuous（後者2条件は**合成**）。Monthlypayment4.79640420122。

| SMM | 最終返済月 | IO | PO | Pass-through |
|---:|---:|---:|---:|---:|
|0|360|560.376326414|332.045499797|892.421826211|
|.01|122|188.585626131|642.517450752|831.103076884|

原2tranche配分で元本800保存、monthwaterfall誤差≤1.43e−13。合成OAStruth.0123（123bp continuousadditivespread）は逆算差≤5e−17。**固定CFの単調root**を検算しただけで、原marketprice/実poolprepaycalibration/stochasticOASの検証ではない。原典に追加数値がないことをN/A要件の削除と混同せず、必要説明と合成独立baselineを保持する。

## 11. 既存 coverage と private 候補

| 既存部品 | 利用できる範囲 | 今回の境界 |
|---|---|---|
| `hullkit.ir_options` | Black caplet/cap/swaption、静的marginaloracle | JointLMM、factorcorr、非標準cap、CEV、exerciseengineではない |
| `hullkit.hull_white` | HW解析bond/ZCBoption、path、curvefitの部品 | GeneralHJM/wholeLMMと同一視しない |
| `hullkit._numeraire_choices` (M29) | FlatHW exactGaussian conditionalpayment/annuitymixture、deterministic additive simpleprojectionbasis | Full stochastic multi-curveLMM、historyprepayではない |
| `hullkit.american_mc` (M17) | NDstate polynomialLSM/boundary、別policy評価 | Constant rate discount、LMMpathnumeraireadapter未実装 |
| legacy `interest_rate_models/build_ir_models_notebook.py` | HJMcurve/Blackcaplet/initialcurve examples | GeneralHJM/LMM製品helperとは扱わない |
| `hullkit.mc.price_american_lsm` | 旧GBM scalarAmerican | 金利多factor版へ無条件流用不可 |

Public HJM/LMM/CEVcaplet/MBS 専用APIはこの読み取り範囲では見つからなかった。新規候補は **private module**: tenor/curve/factor/measure schema、joint LMM paths、numeraires/fixings、ratchet/sticky/forcedflexi、swaption frozenapprox＋independentjointMC、CEVanalytic/privatepolicyadapter、monthlycashflow/waterfall/OAS。今回はファイルもAPIも作らず、公開変更・新依存の判断は別途ユーザー承認の対象。

Field候補: `tenor_years,accruals,initial_discount,initial_simple_forward,loading_by_remaining_period,measure,event_order,scheme,substeps,seed,path_count,pair_count`、outputに`fixings,discount_weights,path_payoffs,pair_covariance,stderr`。実際のcurve/projection/numeraireを型/metadataに保持。入力が不足するflexiはprice関数へ便宜defaultstrikeを付けない。

## 12. 独立検証・再実行・残り

保存物:

- `/tmp/p3-ch33-fixtures.py` → `/tmp/p3-ch33-fixtures.json`: no hullkitimports。SourcefileSHA/officialmetadata、actual3ledgerunits、11draft IDs、HJM/numeraire/swaptionJac/calibration/CEV/MBS、MC参照hashを保存。
- `/tmp/p3-ch33-lmm-mc.py/json` と `/tmp/p3-ch33-lmm-mc-notes.md`: 21MCruns、60価格、allfactorcomponents/roundingintervals、vanilla/martingale、pairedrefinement。主JSONは参照・pooled入力/出力を統合し、refresh時にMCを再実行しない。
- `/tmp/p3-ch33-original.txt` / `primary-pages.txt`、`/tmp/p3-ch33/TN17.txt`: 原典抽出。数学の結論は抽出だけでなく既回収原図・著者解答・独立式と照合。
- `/tmp/p3-ch33-audit.json`: filehash/sourcehash/requirementcount/numericerror/finiteness audit（作成時snapshot）。正式repositoryacceptancegateではない。

再実行（製品コードをimportしない）:

```bash
/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch33-fixtures.py
/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch33-lmm-mc.py --pairs 50000
```

今回実行済: 主analytic/synthetic scratch、子の21MC、separate complexstep/drift/BES0/payoffintegral、sourcehash/全JSON数値finite照合。今回未実行: productpytest/ruff/release/ledgercheck/browser/D1、realmarketPCA/calibration、full stochastic multi-curve/OIS overnightLMM、jointCEV/LSM/Bermudanswaption/MBSprepay、任意tenor高volmutation。製品受入へ進むときは独立validation/visualization/renderedも必要。

後続の順序候補:

1. 3actualunitsに11draftを原典から正式登録・scope確認。Ch33Appendixを新設しない。
2. HJMsignednotation/特殊例・TN17mappingを教材と独立検証へ採用。
3. Positiverate singlecurve LMM→vanillaBlack/numeraires→timevariance/factorraw→ratchet、stickyの明示初期条件→jointswaption。
4. γ/nの公式未解決と数学的candidateを併記。Frozenvariance calibrationとjointMCを別oracleで検証。Vol/curve/data/measureを追跡。
5. CEVanalytic/zero boundary、LMMBermudanpolicy/independentheldoutを完成。M17のNDstate部品利用とconstantdiscount制約を保持。
6. MBS説明＋deterministicCF/OASbaseline。Originalprice入力なしはそのまま扱う。
7. Flexicap original strike/eligible datesを一次資料で取得した後、forcedfirst5ITM contractと3価格を検査。未取得なら要求単位pendingを保持し、wholeP3完了を宣言しない。

新証拠が得られないときは原典第4版/著者の当該例input/明示errataなど別一次資料の取得可否を再評価する。価格3.43/3.58/3.61に合わせてstrike/tenor/seedを選ぶ作業は行わない。