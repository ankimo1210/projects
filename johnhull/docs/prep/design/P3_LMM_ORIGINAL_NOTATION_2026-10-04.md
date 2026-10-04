# P3 primary input recovery: NYU論文とHull 11e原本

確認日: 2026-10-04。読み取り専用の調査。リポジトリ/Gitは変更していない。

## 結論

Hull 11e Global Editionの原本で、flexi capの価格3.43 / 3.58 / 3.61、元本$100、annual-pay、flat 5% term structure、最初の5個のITM capletを強制行使する規則、1/2/3因子のvolatility成分表を確認した。ただし、そのflexi cap例の固定strikeと最初/最後の対象reset日は本文に明記されていない。NYU論文は例の詳細をHull (2000)、つまり教科書第4版へ参照するのみで、この不足を補わない。価格からの逆算や代替入力は行っていない。

## 使用した一次資料とページ

- Hull and White, Forward Rate Volatilities, Swap Rate Volatilities, and the Implementation of the LIBOR Market Model。親依頼でNYU FIN-00-023とされたPDF: `/tmp/hull_lmm_nyu_2000.pdf`、40ページ。内部のタイトル/著者表示を確認。物理ページ=印刷ページ: 4, 9, 13, 28, 32。PDF本文にFIN番号の表示は見つからない。
- Hull, Options, Futures, and Other Derivatives, 11/e, Global Edition: `/home/kazumasa/worktrees/m29/johnhull/options, futures and other derivatives 11th.pdf`、880ページ。物理ページ=印刷ページ: 759, 761, 762, 763, 764, 772。
- 全文layout抽出: `/tmp/p3-input-recovery/nyu.txt`, `/tmp/p3-input-recovery/hull11e.txt`。上記の関連ページをPNGへrenderして目視照合した。NYU Tables 1-4の見出し/説明も抽出確認済み。

## NYU論文で確定すること

- p4, equation (1): capはreset t_1,...,t_N、最終支払t_{N+1}。delta_i=t_{i+1}-t_i。時点t_iで観測する期間delta_iの金利R_iは、compounding periodもdelta_i。支払はt_{i+1}にL_c delta_i max(R_i-R_c,0)。これは一般capの定義で、flexi例の具体日付/strikeではない。
- p9: F_i(t)も期間(t_i,t_{i+1})、compounding period delta_i。独立因子。numeraireは各reset日で再投資するmoney market account。
- p13, equation (19): PCA成分を各期限の総volatility Lambda_jに合わせてscaleする。論文の分析は3因子。平行移動、twist、bowingを想定し、scale後のvariance寄与は概ね87% / 10% / 3%。**期限別のlambda_j,q数値表は掲載されていない。**この比率だけから11eのfactor tableは復元できない。
- p28: ratchetは前resetのLIBOR + spread、stickyは前resetのcapped LIBOR + spread。flexiは行使caplet数に上限がある。非標準capを計算したのはHull (2000)で、式(22)のMCを用いたと述べる。固定strike、対象reset/pay date、5個上限、価格3.43/3.58/3.61はこの論文には掲載されていない。
- p32: Hull (2000)はOptions, Futures, and Other Derivatives, Fourth Edition, Prentice Hall (2000)。11版との具体的な契約差異は、第4版原本がこの調査範囲にないため未確認。
- 論文Table 1 (p33)はcapletのspot-volatility誤差、Table 2 (p34)は5x5 swaptionのvolatility誤差、Table 3 (p35)はCEV skew下の3x3 swaption誤差。Table 4 (p36)は1999-08-12のCEV calibration、alpha=0.716、元本$1,000、delta_j=0.25のLambda推定表。いずれも11e flexi cap入力表/価格表ではない。

## Hull 11eで確定する契約/計算条件

- p759: F_kは(t_k,t_{k+1})のrate、compounding period delta_k、actual/actual day count。一般モデルではt_0=0。
- p762: ratchet K_{j+1}=R_j+s。sticky K_{j+1}=min(R_j,K_j)+s。
- p762-763: ratchet/stickyは元本$100。割引とpayoffのterm structureはともに年率5% continuously compounded（同値のannually compounded rate 5.127%）。annual reset、spreadはannual-compounding rateに25bpを加える。100,000 MC simulations、antithetic technique、各caplet価格のSEは約0.001。
- Table 33.2/33.3のcaplet start timeは明記された1,2,...,10年。1年間のcapletなので一般定義と合わせると対応pay dateは2,3,...,11年。これは**ratchet/sticky表のschedule**として確定する。
- p763 flexi cap段落: 元本$100、annual-pay、flat 5% term structure、volatilityはTables 33.1/33.4/33.5。ITM capletを最大5個まで行使。1/2/3因子の価格がそれぞれ3.43 / 3.58 / 3.61。価格は元本$100の価値なので通貨単位は$と解されるが、価格直前に単位記号は再掲されていない。
- p772, Problem 33.14: この例では最初のN個のITM capletを行使する義務があり、その後は行使不可、例ではN=5。行使選択を最適化するflexiとは異なる契約であることが明確。
- flexi段落の5%にはcompoundingが再掲されていない。隣接するratchet/stickyの5% continuously compoundedを引き継ぐ解釈は自然だが、flexi段落だけの明示条件としてはflat 5%まで。
- flexiの**固定strike数値は未掲載**。flexi段落ではcap rate/strikeを定義せず、5% term structureはstrikeではない。5%、exp(0.05)-1、25bp上乗せ等で補ってはならない。
- flexiの**eligible reset datesと最終pay dateの具体数値は未掲載**。Tables 33.1/33.4/33.5が1-10年のvolatilityを持つこと、隣のratchet/stickyがstart 1-10年であることは文脈上の根拠にはなるが、flexiのstart=1..10/pay=2..11を直接指定した文ではない。
- p763の100,000/antithetic/SE約0.001はratchet/sticky表を説明する段落にある。flexi価格のMC試行数/SEを明示した記述とは区別する。

## Table 33.1 (p761): 全セル

Accrual period = 1 year。以下は全て%（実装decimalにするなら100で割る）。sigma_kはBlack caplet spot volatility。Lambda_{k-1}はwhole accrual periodsを引数にするforward volatility。

| Year k | sigma_k (%) | Lambda_{k-1} (%) = 1-factor lambda_{k-1,1} |
|---:|---:|---:|
| 1 | 15.50 | 15.50 |
| 2 | 18.25 | 20.64 |
| 3 | 17.91 | 17.21 |
| 4 | 17.74 | 17.22 |
| 5 | 17.27 | 15.25 |
| 6 | 16.79 | 14.15 |
| 7 | 16.30 | 12.98 |
| 8 | 16.01 | 13.81 |
| 9 | 15.76 | 13.60 |
| 10 | 15.54 | 13.40 |

## Tables 33.4/33.5 (p764): 全セル

全て%。左の2列が2因子lambda_{k-1,1/2}、次の3列が3因子lambda_{k-1,1/2/3}。符号は原本どおり。Total volatility列は両表で同じ。値は小数2桁に丸められた掲載値であり、総volatilityへの再正規化は行わない。

| k | 2F q1 | 2F q2 | 3F q1 | 3F q2 | 3F q3 | Total (%) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14.10 | -6.45 | 13.65 | -6.62 | 3.19 | 15.50 |
| 2 | 19.52 | -6.70 | 19.28 | -7.02 | 2.25 | 20.64 |
| 3 | 16.78 | -3.84 | 16.72 | -4.06 | 0.00 | 17.21 |
| 4 | 17.11 | -1.96 | 16.98 | -2.06 | -1.98 | 17.22 |
| 5 | 15.25 | 0.00 | 14.85 | 0.00 | -3.47 | 15.25 |
| 6 | 14.06 | 1.61 | 13.95 | 1.69 | -1.63 | 14.15 |
| 7 | 12.65 | 2.89 | 12.61 | 3.06 | 0.00 | 12.98 |
| 8 | 13.06 | 4.48 | 12.90 | 4.70 | 1.51 | 13.81 |
| 9 | 12.36 | 5.65 | 11.97 | 5.81 | 2.80 | 13.60 |
| 10 | 11.63 | 6.65 | 10.97 | 6.66 | 3.84 | 13.40 |

## Tables 33.2/33.3 (p763): 全価格セル

元本$100のcaplet価値。左3列=ratchet、右3列=sticky、因子順1/2/3。時刻は年。

| Caplet start | Ratchet 1F | Ratchet 2F | Ratchet 3F | Sticky 1F | Sticky 2F | Sticky 3F |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.196 | 0.194 | 0.195 | 0.196 | 0.194 | 0.195 |
| 2 | 0.207 | 0.207 | 0.209 | 0.336 | 0.334 | 0.336 |
| 3 | 0.201 | 0.205 | 0.210 | 0.412 | 0.413 | 0.418 |
| 4 | 0.194 | 0.198 | 0.205 | 0.458 | 0.462 | 0.472 |
| 5 | 0.187 | 0.193 | 0.201 | 0.484 | 0.492 | 0.506 |
| 6 | 0.180 | 0.189 | 0.193 | 0.498 | 0.512 | 0.524 |
| 7 | 0.172 | 0.180 | 0.188 | 0.502 | 0.520 | 0.533 |
| 8 | 0.167 | 0.174 | 0.182 | 0.501 | 0.523 | 0.537 |
| 9 | 0.160 | 0.168 | 0.175 | 0.497 | 0.523 | 0.537 |
| 10 | 0.153 | 0.162 | 0.169 | 0.488 | 0.519 | 0.534 |

## 残る不足と次に必要な一次情報

1. flexi fixed strikeの数値とそのcompounding convention。
2. flexiの最初/最後のeligible reset/pay date、caplet個数。
3. flexi段落の5%が前段のcontinuous 5%を明示的に引き継ぐか。
4. NYU論文が参照する教科書第4版の該当原本、または著者の当該例入力/errata。第4版本文に条件があれば版差・後続版の省略を確認できる。現時点で版差があったと断定できない。

未確定項目を補わず、表の復元と強制行使規則の確定までを成果とする。
## 追加調査: 著者の11e補助教材 (2026-10-04)

出典archive: https://github.com/rotmanfinhub/john-hull-textbook-resources 。親依頼の固定commitは `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`。公開READMEを確認し、John C. Hullの補助教材をRotman FinHubが保存するarchiveであることを確認した。以下のダウンロード済み原本を読み取り専用で調査した。

| 原本 (全て /tmp/p3-input-recovery/) | 範囲/関連位置 | 結果 |
|---|---|---|
| Ch33HullOFOD11thEdition.pptx | 全22 slide XML + 全22 notes XMLを抽出。関連slide18、swaption slide19をrender確認 | slide18は非標準capが複数forward ratesのjoint distributionに依存する説明のみ。固定strike、eligible dates、flexi価格の入力は追加されない。slide19はswaption analytic approximationがあるとの説明のみ、33.19の式そのものなし。notesはslide番号以外の内容なし。 |
| HullOFOD11eSolutionsCh33.pdf | 全5ページの本文抽出、関連physical p4-5をrender確認。本文に印刷ページ番号なし。 | 解答33.14は自由行使型/開始日選択型の難しさと価格順位だけで、例の固定strike/eligible datesを補わない。解答33.13の式33.19再掲にも下限 k=n がある。 |
| Errata (11th  edition).pdf | 全2ページの本文/画像を確認。ブラウザ印刷footer 1/2, 2/2。保存snapshotの日付は2026-08-06（PDF creation metadataは2026-08-07 JST） | Global Edition 52,58,83,84,111,163,330,519,521,567ページの訂正のみ。Chapter 33、p763、p765、式33.19の訂正項目はない。flexiの不足条件も追加されない。 |

抽出テキスト: `ch33-slides-xml.txt`, `solutions-ch33.txt`, `errata-11e.txt`。PPTXをLibreOffice wrapperで一時PDFへ変換してslide18/19を照合した。XML抽出はnative textを対象とするが、関連slideの画像確認でも追加契約条件は見つからない。元PPTX/PDFは編集していない。

### 式33.19の添字: 公式訂正と数学上の整合性を区別

- 11e原本p765式(33.19)は `sum_{k=n}^{N-1} sum_{m=1}^M`。画像で下限の小文字nを確認した。
- 同じページの式(33.17)/(33.18)は `sum_{k=0}^{N-1}`。p764ではswap option maturityをT_0、payment datesをT_1,...,T_N、swap periodsを(T_j,T_{j+1})と定義し、nをswap開始indexとして定義していない。
- 著者解答集physical p4の33.13は、subperiodsの積の恒等式とそのlogを使い、各dz_qの係数を等置した後に式(33.19)を再掲する。この再掲も `k=n`。著者解答集が訂正を示しているとは言えない。
- 元NYU論文physical/printed p16はswap期間を `t_n`から`t_{N+1}`、reset datesを`t_n,...,t_N`、swap rateをS_{n,N}(t)と定義する。p17式(24)・p18式(25)の `sum_{k=n}^N`はその定義と整合する。
- **推論（公式errataによる訂正ではない）:** 11eではswap期間を0開始の局所indexへ変更したため、式(33.19)の下限も0が整合する。とくにM=1なら33.19は33.18に戻らなければならず、33.18の下限0と一致する。旧NYU記法のnが残った可能性を説明できる。ただし、このarchiveの正誤表には著者による `n -> 0` の明示訂正はない。

付随して発見した別の表記差（修正なし）: 11e p765のgamma_k(t)分母第2項の最終積の上限は画像ではN、一方で著者解答33.12 physical p4の対応式はN-1。11eの定義域/分母annuityからはN-1が整合する。これは式33.19下限とは別件として記録する。

### 追加調査後の到達点

flexiの固定strikeと固有eligible reset/pay dateは依然として一次情報が不足する。著者PPTX/解答集/保存された11e正誤表にも条件がなく、synthetic assumptionsで補わない。式33.19の下限については原本・解答集が同じnを保持すること、および0開始の11eの定義/式33.18との数学上の不整合を確認できた。公式errata訂正済みと表現しない。