# P3 原資料不足の調査引継ぎ — 2026-10-04


## 更新：公式保存庫による回収（M29準備時点）

初回調査の取得不足は[回収記録](P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md)の固定commit/hashで更新。TN14全4頁/TN19全1頁/VasicekCIR元XLSを取得し、§31.4の8664元観測/8663回帰組と全9較正点を独立再計算。OLS最大差3.08e−15、元lambdaでzero rate差6.77e−16。取得不足は解消、正式実装/五軸受入は未完。外部series IDは未同定、原worksheetをcanonicalとする。flexicapのstrike/eligible datesは引き続き未確定。下の初回調査は過去時点の結果として保持する。

## 初回調査の範囲と結論

読み取り専用の対象は `/home/kazumasa/worktrees/m28/johnhull`。プロジェクト/Gitファイルを変更していない。監査記録 `docs/P3_REQUIREMENT_AUDIT_2026-10-04.md` と prep Ch31/33/34、ローカル原典の関連頁、著者公式検索索引を照合した。調査は親エージェントの指示でこの時点に終了し、追加検索・新しい検査を行っていない。

- **TN14 は二因子 Hull–White、TN19 は equity swap。** 依頼時のGARCH／bond futures・quantoの対応は親エージェントが記載誤りと確認。11e索引と本文参照の対応を採用する。
- **flexicap の原文は p.763。** prepのp.765はこの段落の頁と一致しない。初回5個のITMを必ず行使する条件はProblem33.14で明確化できたが、strikeと対象期間の始終は未確定。
- **§31.4 は原データ＋worksheetの指定URLを同定。** 現行URLはHTMLエラーで取得不能。OLSの元系列・欠測処理・当日r0・λ最適化の完全入力は未取得。
- TN14/TN19の現行ダウンロードはHTML200。公式検索索引による内容確認と、完全なPDF取得を区別する。未完要求をN/A/acceptedに変更しない。

## ローカル原典と作業記録

原典: `/home/kazumasa/worktrees/m28/johnhull/options, futures and other derivatives 11th.pdf`。
`pdfinfo`で題名 `Options, Futures, and Other Derivatives, 11/e, Global Edition`、著者John C. Hull、880頁、13,144,440bytes、PDF1.6を確認。今回の該当頁ではPDF物理頁と印刷頁が一致した。

実行した抽出は `pdftotext -layout`。以下はGit管理外の抜粋:

- `/tmp/p3-ch31-source.txt`: pp.727–728。
- `/tmp/p3-ch33-source.txt`: pp.761–768。
- `/tmp/p3-flexicap-source.txt`: pp.763–764。
- `/tmp/p3-equity-source.txt`: pp.778–779。
- `/tmp/p3-problem3314.txt`: p.772、Problem33.14。

今回の調査は文章・式・表の読み取り。新たな数値価格再計算、OLS、MC、PDF図の目視、製品テスト、受入gateは実行していない。既存prepの再計算結果を今回の新計算として扱わない。

## 公式Technical Notesの対応と取得状態

[11e著者公式索引](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/)の検索索引は14=`The Hull-White Two-Factor Model`、19=`Valuation of an Equity Swap`を明示。両PDFをWeb direct openするとContent-Type=text/html、404Handlerのエラー本文。先行監査のWSL直接取得もHTML200/%PDFなしだった。今回それをPDF成功に変更する根拠は得ていない。

### TN14 — §31.5の二因子モデル

[公式TN14](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/TechnicalNote14.pdf)の検索索引で、初頁のモデル・規約・bond式を確認:

\[
df(r)=[\theta(t)+u-af(r)]dt+\sigma_1dz_1,\qquad du=-bu\,dt+\sigma_2dz_2.
\]

uの初期値0、a/b/σ1/σ2は定数、Brownian増分の瞬間相関ρ。θ(t)は初期term structureに合うよう選ぶ。f(r)=rの解析bondは

\[
P(t,T)=A(t,T)e^{-B(t,T)r-C(t,T)u},\quad B=\frac{1-e^{-a(T-t)}}a,
\]
\[
C=\frac{e^{-a(T-t)}}{a(a-b)}-\frac{e^{-b(T-t)}}{b(a-b)}+\frac1{ab}.
\]

ローカル本文p.728の§31.5はθ項を持たないequilibrium特殊形で、Cは式31.14、AはTN14参照。**従って初期curve fit付きTN14のAを本文に無条件転記できない。θ=0への対応を確定する必要がある。**

確認できた初頁ではAとbond-option variance σPをAppendixへ委ねる。**Appendix全式の取得・照合は未完**。full acceptanceには、θ/初期curve/ρ/u初期値の仕様、Gaussian積分からのAの独立構成、TN14 Appendixとの対応、a=bの除去可能特異点、解析bond/独立Gaussian教師の検証が必要。検索索引の初頁を完全PDF取得と扱わない。

### TN19 — §34.4の途中equity swap

[公式TN19](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/TechnicalNote19.pdf)の検索索引では、LIBOR設定でR0（前resetで決まった次coupon金利）、L、τ0（全期間）、τ（残期間）、E0/E（前reset/現在total-return指数）、R（残期間LIBOR）を定義。receive-equityの途中net MTMは

\[
V_{eq}=L\frac E{E_0}-L\frac{1+R_0\tau_0}{1+R\tau},\quad V_{float}=-V_{eq}.
\]

根拠は指数投資と残期間の借入を用いた複製。**この結果はnet swapであり、単独equity cashflowのPVと同一ではない。** 索引にはこの導出が現れるが、現行PDFは未取得。

ローカルp.778はBusiness Snapshot34.3をSOFRへ更新し、次floatingを既観測overnight ratesと残期間SOFR forwardで評価すると記述。同頁のequity cashflow文には L(E−E0)/E0 と印刷。本文とlegacy LIBOR TN19の整合確認を未完のまま保持する。

独立に整えるべき仕様: total-return indexの配当再投資、receive/pay、Lとreset shares、既観測RFR accrual factor、残期間discount/projection、支払/観測ラグ。単独equity legのPV L[E/E0−P(t,T)] とnet financingの式を区別し、即時支払後のnet0を複製で示す。LIBORのknown coupon式をSOFR couponへそのまま置換しない。

p.778で確認できたBS34.3条件: trade2021-01-04、effective2021-01-11、termination2026-01-11、U.S. calendar/Following、USD100M、Total Return S&P500、各4/7/10/1月11日の四半期支払（最初2021-04-11）、floatingはUSD3-month compounded SOFR、ACT360。**厳密なholiday set/観測ラグはこのsnapshotだけから確定しない。**

## §31.4 — データとTable31.1の正確な入力

### 原典で確認できた入力と位置

p.727は米国3-month Treasury ratesの日次データ期間を **1982-01-04〜2016-08-23**、データ＋analysis worksheetを **[著者VasicekCIR](https://www-2.rotman.utoronto.ca/~hull/VasicekCIR)** と指定する。

原典回帰は ri+1−ri を ri に回帰し、切片0.00000915、傾き−0.000545、standard error0.000754。約250観測/年、Δt=1/250。本文換算はa=.136、b*=.0168、σ=.0119。PからQへはb=b*−λσ/a。p.727のQ段落は b=.168−.0119λ/a と印刷され、直前の.0168と不整合。**今回もテキスト上.168を確認。prepは以前PDF描画で確認済みとしているが、今回の新目視検証とは区別する。**

同頁: trial λごとに式31.7/31.8/31.10からmodel zero ratesを求め、市場との差の平方和をSolverで最小化。最適λ=−.175と印刷。回帰とcurve fitは二段階で、全時点のterm structureにfitしたものではない。

p.728 Table31.1は **2016-08-23**。単位は年/%:

| Maturity | Model | Market |
|---:|---:|---:|
| .5 | .40 | .45 |
| 1 | .49 | .58 |
| 2 | .65 | .74 |
| 3 | .80 | .86 |
| 5 | 1.06 | 1.15 |
| 7 | 1.27 | 1.40 |
| 10 | 1.52 | 1.55 |
| 20 | 2.02 | 1.88 |
| 30 | 2.26 | 2.24 |

### 取得結果と残る不足

WSL urllibで著者 `/VasicekCIR`、`/VasicekCIR/` を直接確認。両方HTTP200、text/html、404Handler本文。候補 `/VasicekCIR.xlsx` と `.xls` も同じHTML。**候補ファイル名は原典で確認された名前ではなく、取得できたworkbookはない。**

一次データ候補の定義だけは公式FRED索引で確認した:

- [DTB3](https://fred.stlouisfed.org/series/DTB3): 3-Month Treasury Bill Secondary Market Rate, **Discount Basis**、日次/%、FRB H.15。
- [DGS3MO](https://fred.stlouisfed.org/series/DGS3MO): 3-Month Treasury **Constant Maturity/Investment Basis**、日次/%、FRB H.15。

**どちらがHull worksheetの元系列かを確認できていない。FREDデータを取得していないし、OLSを比較していない。** 単に同じ3か月という理由で置換しない。

full acceptanceに必要な未取得/未確定入力:

1. 著者の原worksheetと時系列snapshot、元系列の定義・版・利用条件。
2. 休日/欠測日の除去方法、隣接差分の作り方、date order、percent→decimal、regression残差の分母/定義。
3. 当日 **r0**。本文pp.727–728/Table31.1に明示されていない。
4. curve全入力、複利/zero vs parの定義、使用する原precision、fit対象点/weight。
5. unrounded P推定値を用いたのか本文round値を用いたのか、λの実際の最小化出力。
6. 元OLS、λ=−.175、9個のmodel ratesの独立再現と残差。

印刷係数の換算や合成OUパラメータ回復だけでは、1–6の歴史例の再現を閉じられない。公開データによる別snapshotを導入する場合も原worksheetの完全再現と明確に分ける。

## §33.2 — flexicapと印刷MC表の条件

### 原典で確定したこと

**pp.762–763**のratchet/sticky: principal100、discount/payoffともflat5% continuously compounded（annual単利5.127%）、annual reset、spread25bpはannually compounded rateへ適用。Table33.1のcaplet vols、Table33.4/33.5のfactor splitsを使う。100,000 MC simulations、antithetic、価格SE約.001。ratchet Kj+1=Rj+s、sticky Kj+1=min(Rj,Kj)+s。

**p.763 flexi段落**: annual-pay、principal100、flat5%、Tables33.1/33.4/33.5のcap vols、ITM capletを最大5回行使。1/2/3factor price **3.43/3.58/3.61**。**この段落にはcap strikeと最初/最後の対象期間が明示されていない。** flat5%の前段文脈から連続複利を採る場合も、strike=5%かannual5.127%かは別問題。

**p.772 Problem33.14**は本文のflexiを「最初のN個のITM capletを必ず行使、以降は行使不能」と明確化（本文N=5）。従って本文印刷価格は選択的な最適停止を伴うflexiの価格と同じではない。問題は別契約として(a)任意のcapletを選択して最大N回、(b)開始を選択し開始後はITMを最大N回まで必ず行使、を挙げる。問題33.14は主対象の章末問題外だが、本文の契約定義を確認する補足原資料として読んだ。

### 残る不足と受入条件

- flexicapの **fixed strike K**、rate compounding、**eligible caplet reset dates/payment dates**（初回/最終）を一次資料で確定する。表がstart1–10であることだけでflexiの全tenorを断定しない。
- seed/MC末尾桁へfitしない。factor splitの丸めによるcaplet marginal volsの差を許容理由付きで扱い、まずplain caplet Black整合を検証する。
- 本文必須の行使順はchronological first5 ITM。LSMを必要とする選択的flexi契約へ変更して3価格を再現したと主張しない。
- Ratchet/sticky Tables33.2/33.3の60価格、flexi3価格は **未再計算**。antithetic pair単位SEと離散化差を示す独立参照が必要。
- pp.765–766の式33.19はOCR崩れあり。今回text抽出は行ったが **原図の積/添字の目視確認は実施していない**。数式原典確認pendingを解除しない。

### 入手できた関連一次論文（内容未調査）

Hull–White, *Forward Rate Volatilities, Swap Rate Volatilities, and the Implementation of the LIBOR Market Model*, NYU FIN-00-023（2000）の大学アーカイブ版を取得できた。

- [NYU著者working paper PDF](https://w4.stern.nyu.edu/finance/docs/WP/2000/pdf/wpa00023.pdf)
- [NYU Libraries原記録](https://archive.nyu.edu/handle/2451/26689)
- [同アーカイブPDF](https://archive.nyu.edu/bitstream/2451/26689/2/FIN-00-023.pdf)
- 保存 `/tmp/hull_lmm_nyu_2000.pdf`、同一版 `/tmp/hull_lmm_nyu_archive_2000.pdf`。
- HTTP200、application/pdf、%PDF magic、222,995bytes、両者SHA256 `a9350e94d15062019b63d1c7f5fab2e04e0019d40e7940aaf0356fb9c4b594b0`。

著者サイト [1999稿候補](https://www-2.rotman.utoronto.ca/~hull/DownloadablePublications/libormktmodel.pdf) はHTML200、1,651bytes、PDF magicなし。**NYU版本文はまだ抽出/通読していないため、flexicap入力の解決源とは判定していない。** 出版版/1999稿/2000working paperの版差を次回照合する。

## P3継続への扱い

先行可能なのは明示仕様に基づく独立教師とprivate lesson、説明/数式/単位の整備。歴史入力・原契約・原導出照合の不足は要求単位でpendingに維持する。合成例を印刷数値の代替教師へ昇格しない。全受入にはimplementation/independent_validation/visualization/renderedの証跡も必要で、今回原資料調査のみでは節のaccepted判定を行えない。
