# P3 原典入力回収 — 2026-10-04

## 結論

**旧Rotman URLのHTML障害を回避する公式保存庫を見つけ、TN14/TN19の全PDFとVasicekCIR原worksheetを回収した。** §31.4の歴史例は合成データを使わず、元8664観測、OLS、当日r0、全9fit点とlambdaを取り出して独立再現できた。flexicapの固定strike/対象datesは一次資料でなお不明。

調査対象 `/home/kazumasa/worktrees/m29/johnhull`。リポジトリ/Gitを変更していない。全取得物・抽出・試計算は `/tmp/p3-input-recovery/` に保存。実装、製品テスト、五軸受入gateは実行していない。原典入力回収の成功をsection acceptedと扱わない。

## 新しい一次配布先と固定版

[Rotman FinHubの著者公式教材保存庫](https://github.com/rotmanfinhub/john-hull-textbook-resources)はJohn C. Hullの補助教材を、FinHubと家族の許可で保存している。原URLのエラーページと取得PDFを区別する。archive README/LICENCEにCC BY-NC 4.0（個別指定が優先）、著者帰属、非商用利用を示す。README、LICENSE、repository tree、latest commit API応答を保存した。

- 配布元commit: **`9b8dbfe37661dbd3de65d3a1489dc1297e840de7`**。
- 各raw downloadはこのSHAをURLに指定（main可変参照でfixtureを固定しない）。
- `download-records.json`: 元URL、repository path、commit、git blob SHA、HTTP status/content-type、bytes、SHA256、magic。
- `artifact-manifest.json`: scratch成果ファイルのbytes/SHA256。
- raw response Content-Typeは `application/octet-stream`。本文magicとPopplerの解釈成功でPDF/XLSを判定した。
- 旧 `www-2.rotman.utoronto.ca/~hull/...` は今回web direct openでも404Handler HTML。PDF取得成功と扱っていない。

| 原ファイル | 内容/物理ページ | bytes | SHA256 |
|---|---|---:|---|
| TechnicalNote14.pdf | PDF1.4 / 4頁 | 68,956 | `9068c1d786837a5946fc7a3cd2114cafc4edb0293975f70508b4cadedc31af5f` |
| TechnicalNote19.pdf | PDF1.4 / 1頁 | 34,858 | `fbd0c0b8bb7051bb988f2a2add19dd41cba1b2a8366cb8e69a13f7e9ecb84356` |
| VasicekCIR.xls | OLE/BIFF8 workbook / 6 sheets | 1,044,992 | `f384c34b0bf745e2841eaae89d8fc06d84a41bf6cf754dd4a49a908f0d5229d5` |
| Ch33HullOFOD11thEdition.pptx | ZIP/PPTX / 22 slides+22notes | 288,107 | `4283cbc017b0a21afd68c71cf485a1901a1b7283ba256cf3c6812e936a1aad4c` |
| HullOFOD11eSolutionsCh31.pdf | PDF1.5 / official Global answers | 271,891 | `b95c721a29f943062f8ff76bce15d76f029e06e543e11bcfbed5c7a93ab13dd1` |
| HullOFOD11eSolutionsCh33.pdf | PDF1.5 / official Global answers | 198,208 | `a58115cbb5a39ec29e9dfaae5026f914a987bab06a6d28d808c602e5a5490a02` |
| Errata (11th  edition).pdf | PDF1.4 / 2頁 | 140,946 | `197cce401783dc947737bfec778a33fe428a1b7690642c523f4dd7b46a46576d` |

## §31.4 — 完全worksheet snapshotと独立再現

### 元観測と品質

`Data (See Section 31.4)`:

- A2:A8665: **1982-01-04〜2016-08-23、8664日付**、昇順・重複0。
- B2:B8665: header `3 mnth rate(%)`。すべて有限数値、欠測cell0、min0.01%、max15.49%。
- C2:C8665: `=B(row)/100`。decimal annual rate。最終C8665=.003。
- D2:D8664: `=C(row+1)-C(row)`。最終D8665は空欄。**8663回帰組**。
- 日付間隔分布（日数:回数）: 1:6756、2:99、3:1537、4:270、5:1。
- 休日/欠測日はsheetに行を持たず、**カレンダー日ではなく隣接観測差分**。各gapの休日/欠測理由まではworksheetから確定しない。
- 全C/D保存値とBから計算したdecimal/差分は一致（maxerror0）。
- 回帰の時間刻みは観測一組ごと **1/250年**、gap別にΔtを変えない。

`vasicek-original-series.csv` に日付・元percent・decimal・次差分を完全抽出。元XLSをcanonicalとし、このCSVのSHAもmanifestに保存。

### 元回帰と未丸めパラメータ

`Regression (See Section 31.4)`のExcel Analysis ToolPak結果は値で保存されている。

| 項目 | セル | 元保存値 |
|---|---|---:|
| OLS intercept | B17 | 0.000009146996484883016 |
| OLS slope | B18 | −0.0005446147281124214 |
| residual standard error | B7 | 0.0007540332971975618 |
| observation count | B8 | 8663 |
| residual df | B13 | 8661 = n−2 |
| a | L8 `=-B18*250` | 0.13615368202810535 |
| b* | L9 `=-B17/B18` | 0.016795352774585375 |
| sigma | L10 `=B7*SQRT(250)` | 0.01192231325375477 |

aは年−1、b*はannual rate decimal、sigmaはannual-rate decimal/√year。原典p727の0.00000915/−0.000545/.000754、a=.136,b*=.0168,sigma=.0119はこの丸めと一致する。公式解答31.15もa=.136,b*=.0168,sigma=.0119を支持。

### curve fitの完全入力

`Best fit lambda (Section 31.4)`:

- **D1 (trial lambda、保存Solver結果) = −0.1746227999177317**。
- C4:C6に未丸めP回帰値を**hardcode**（前sheetの値と一致）。
- C9=C4、C10=`C5-D1*C6/C4`、C11=C6。保存b_Q=.03208621888158632。
- **C12 (r_0) = .003**、hardcodeで最終観測と一致。
- B15:B23が年maturity、F15:F23が元market annual rates（decimal）。E15:E23はmodel continuous zero rate。
- Objective H15:H23=`(E(row)-F(row))^2`、H25=`SUM(H15:H23)`。**9点、等weight、zero-rate differenceの二乗和**。

| T年 | Market decimal | 元Model decimal | 印刷Model % |
|---:|---:|---:|---:|
| .5 | .0045 | .003962330144602321 | .40 |
| 1 | .0058 | .004871791829727102 | .49 |
| 2 | .0074 | .006546282851395623 | .65 |
| 3 | .0086 | .008049049822494641 | .80 |
| 5 | .0115 | .01062295580217554 | 1.06 |
| 7 | .0140 | .012731561527063773 | 1.27 |
| 10 | .0155 | .015237154155283527 | 1.52 |
| 20 | .0188 | .02020244595641615 | 2.02 |
| 30 | .0224 | .02262775217034321 | 2.26 |

C15=`(1/a)*(1-EXP(-a*T))`。
D15=`(B-T)*(a*a*b_Q-sigma*sigma/2)/(a*a)-sigma*sigma*B*B/(4*a)` = lnA。
E15=`-lnA/T+B*r0/T`。全rowへ同じ規則。

**式を読む注意:** xlrdのdecompile displayはDIV/MULの括弧を落とす、shared formulaを展開しない。この表示を実行式として使わない。`workbook-formulas.json`はwarning付きでraw BIFF tokensを保存。original XLSを変更せず、LibreOffice scratch copyをXLSX化してshared formulasを展開し、`workbook-converted-formulas.json`に正確な括弧付き式を保存した。再計算後のconverted cached valuesを元XLS cached valuesの代わりにはしていない。

### 独立検査（hullkit不使用）

`p3-workbook-check.py` / `vasicek-independent-check.json`:

1. 元percent÷100、隣接差分から中心化OLS、residual df=n−2、年250で独立計算。
2. 元保存lambdaでVasicek zero ratesを直接math/numpyで計算。
3. lambdaに対してmodel zero rateがaffineであることから、等weight二乗和の最適lambdaをclosed formで独立計算（Solver/実装library不使用）。

結果:

- OLS / a / b* / sigma の元保存値との差: **最大3.0808688933348094e−15**。
- 元lambdaで9 model ratesとの差: **最大6.765421556309548e−16**。
- analytic lambda optimum: **−0.17462279986916754**。元Solverとの差 **4.8564152699270835e−11**。
- 元lambdaの独立SSE: **6.648994683089822e−6**。元H25 **6.648994683090204e−6**。
- analytic optimum SSE **6.648994683089811e−6**。

### 残る限定と解決扱い

- 原データ・OLS・当日r0・curve全入力precision・fit点/weight・lambda出力の**取得不足は解決**。独立再現まで実施済み。
- 元worksheetは3month rateを示すだけで、外部のseries identifier/basis/取得版を記載しない。
- [FRED DTB3](https://fred.stlouisfed.org/series/DTB3)はdiscount basis、[FRED DGS3MO](https://fred.stlouisfed.org/series/DGS3MO)はconstant maturity investment basis。今回双方のhistorical CSV取得はtimeout。**どちらかに元worksheetを置換しない、外部series lineage同定は未完**。
- Market 9点を元worksheetのfit入力として扱う。市場データ業者/構築法/zero-vs-parの追加規約はworksheetから増補しない。
- 本文p727の `b=.168−...` は直前b*=.0168と不整合。元worksheetはunrounded .016795...を使い、本文printed9 model pointsを再現できる。原典の表記不整合を明示して採用値を区別する。
- 製品へのfixtures固定・provenance manifest・implementation/independent_validation/visualization/renderedの五軸検証は親作業で未実施。

## TN14 — 全Appendixを回収

TN14物理/印刷頁一致1–4。`TechnicalNote14.txt`と実PDF保存。p3/p4をPNGにrenderして目視照合した。

- p1: curve-fit thetaを持つ二因子risk-neutral model、u0=0、a/b/sigma1/sigma2定数、correlation rho。f(r)=rのB/C、zero-coupon bond call/put。
- p2: y=f(r)+u/(b−a)へ変数変換、sigma3とcorrelation、2D state tree。a≠b前提。
- **p3: lnA、eta、gamma1–gamma6、bond-option varianceの積分式、U/V定義**をすべて取得。gamma/etaのマイナス符号は画像と照合済み。
- **p4: option varianceの3閉形式成分、theta、phi**を取得。
- units: t/T年、short rate annual decimal、a/b年−1、sigma annual-decimal/√year、rho無次元、Pが1 currency支払のPV、bond-option principal L/strike Kは同一currency。

残る実装/数理確認:

1. §31.5本文のequilibrium theta=0 special caseとTN14 curve-fit versionのAを区別。
2. A/theta/varianceの独立Gaussian積分照合、a=b limit、single-factor limit、rho/PSD domain。
3. p4はF_t(0,t), phi_t(0,t)と印刷しsubscriptをpartial derivativeとだけ記す。time/maturity notationとの対応を導出で明示する必要があり、抽出で添字を勝手にTへ改訂しない。
4. Coupon bond optionのexact Jamshidian分解は2factorには成立しない。原noteのlognormal moment approximationとexact modelを区別。

**FullPDF/Appendixの取得不足は解決。** 上記数理照合/実装は未完。

## TN19 — 全1頁の複製導出を回収

TN19 p1、変数定義と式1/2・net swapの両符号を全取得し、`TechnicalNote19.txt`保存、PNG render済み。

- R0=前resetで決まったnext floating coupon、L=principal、tau0=全accrual、tau=残期間、E0=前reset index、E=現在index、R=残期間LIBOR。
- receive-equity net value `L*E/E0 − L*(1+R0*tau0)/(1+R*tau)`。
- receive-floatingは逆符号。L/E0 sharesと借入の複製によるnet swap MTM。
- ratesはsimple annual LIBOR、tauは年、E/E0は無次元、L/Vは同じcurrency。

**FullPDFの取得不足は解決。** 11e §34.4 SOFR契約へ適用する際の既観測overnight accrual、残期間projection/discount、total-return dividends、lag/calendar等の仕様と独立教師はまだ親実装で必要。LIBOR known couponをそのままSOFRへ置換しない。

## §33.2 / §33.3 — 未解決flexicap入力と添字の新証拠

詳しい画像照合・Tables33.1–33.5の全セル/単位は **`/tmp/p3-nyu-flexicap-recovery.md`**（補助エージェント調査）を参照。

今回確認した一次資料:

- 手元11e Global原本p759,761–764,772。
- Hull–White NYU FIN-00-023原著working paper（既回収SHA `a9350e94d15062019b63d1c7f5fab2e04e0019d40e7940aaf0356fb9c4b594b0`）。
- 回収公式Ch33 PPTX、Global解答Ch33、2頁11e Errata。

結果:

- flexi first5 ITM強制行使、1/2/3factor printed3.43/3.58/3.61は確認。
- ratchet/stickyはstart1..10年→pay2..11年を表から確定。**flexiのeligible datesへ無条件転記しない。**
- fixed flexicap strike/独自reset-payment windowは11e原本でもNYUでも未掲載。PPTXslide18はjoint distribution/因子依存だけ、解答33.14も選択型の説明/価格順位だけ。
- NYU p28は具体計算をHull (2000)=第4版へ参照する。未回収第4版本文に入力があるかは不明。
- 33.19のlower index k=nは公式解答33.13でも再掲。NYU原著Eq24/25ではswap starts at t_nとしてnが定義されている。**11eでT0/T1..TNへ記号変更した際にnが残った可能性は推論**。公式ErrataにCh33/33.19修正なし。
- 固定strike/対象dateを価格3つへfitする、syntheticをoriginal fixtureへ昇格する、取得不足をN/Aとする方法は採らない。

## 停止条件と次に必要な作業

旧URL/NYUだけを繰り返す手法を見直した結果、公式移転archiveを発見し、3つの入力不足を大幅に解消した。flexiについては原本/NYU/公式slides/solutions/errataから新しい契約数値が得られず、同じ資料への反復検索はここで止める。

親へ渡す主な作業:

1. 源泉PDF/XLSの保管庫収録、元bytes/hash/sourcecommit/利用条件をprovenance固定。
2. §31.4には回収原worksheetのnumeric fixtureを使い、今回の独立計算を正式検証へ取り込む。
3. TN14 Appendixを独立Gaussian導出と照合し、theta=0/curve-fitを明示。
4. TN19と11e RFR契約の差を定義して独立複製検証。
5. flexicap strike/scheduleはpending維持。Hull第4版または著者由来の別原計算記録が必要（今回はなし）。
### 追加の式33.18/33.19照合

補助調査最終記録: NYU p16のswap start t_n..t_{N+1} とEq24/25のk=n..Nは旧記法で整合する。11eはT0/T1..TN、33.18 k=0..N−1。M=1への縮約から33.19下限0が整合する校正候補。ただし著者の公式訂正としては扱わない。

別の表記差: book p765 gamma_k分母最後のproduct上限 **N**、著者解答33.12物理p4は **N−1**。後者はannuity定義域と整合する。画像両方を保存、公式Errataでは訂正なし。実装段階で式の導出・M=1/finite-tenor検証によりどの表現を採るか明示する必要がある。
## 引継ぎ用の明示参照パスと今回の境界

原bytes（変換前、canonical）:

- TN14: `/tmp/p3-input-recovery/TechnicalNote14.pdf` — [Windows/WSLで開く](//wsl.localhost/Ubuntu/tmp/p3-input-recovery/TechnicalNote14.pdf)
- TN19: `/tmp/p3-input-recovery/TechnicalNote19.pdf` — [Windows/WSLで開く](//wsl.localhost/Ubuntu/tmp/p3-input-recovery/TechnicalNote19.pdf)
- 原worksheet: `/tmp/p3-input-recovery/VasicekCIR.xls` — [Windows/WSLで開く](//wsl.localhost/Ubuntu/tmp/p3-input-recovery/VasicekCIR.xls)
- provenance: `/tmp/p3-input-recovery/download-records.json`、`/tmp/p3-input-recovery/artifact-manifest.json`
- 元observations: `/tmp/p3-input-recovery/vasicek-original-series.csv`
- 独立計算: `/tmp/p3-input-recovery/p3-workbook-check.py`、`/tmp/p3-input-recovery/vasicek-independent-check.json`
- 数式: `/tmp/p3-input-recovery/workbook-converted-formulas.json`（展開済み括弧付き、scratch変換版）。`workbook-formulas.json`のraw BIFF tokensで元式へ遡れる。

本turnで実行: 一次archiveのWeb確認、SHA固定raw download、magic/Poppler type確認、XLS全cached cells/BIFF tokens抽出、元データの品質検査、独立OLS、保存lambdaで全9zero rates、closed-form lambda optimum、TN14 Appendix/Ch33関連頁の画像照合、著者slides/solutions/errata照合。元XLS/PDFは変更していない。

未実行: Excel Solverの再起動/replay、TN14全式の独立数学的検証、TN19のSOFR版教師、製品コード変更、製品suite、ブラウザ受入、D1、正式five-axis acceptance。今回Solverの**保存出力**を取得し、別手法で最適化を照合した。元market data provider/外部series metadata、flexicap fixed strike/eligible dates、公式33.19訂正は未確認のまま保持する。