> 未受入の準備資料。原典回収とscratchの結果であり、製品実装・全5軸の正式受入は別途必要。

# P3 §33.2 flexicap — 追加の一次資料回収（1回の限定調査）

確認日: 2026-10-04。親依頼による読み取り専用の追加調査。
結論: **固定strikeとeligible fixing/payment datesを確定する新しい一次根拠は取得できなかった。**
印刷価格 **3.43 / 3.58 / 3.61** は入力不足のためpendingのまま保持する。
ユーザーは追補資料を持っていないと回答済み。追加の資料提出を今回要求しない。
repository/Git/API/製品gate・数値価格合わせ・再シミュレーションは実施していない。

## 1. 既調査の境界を先に確認

今回の追加検索前に以下を読んだ。

- `/tmp/p3-ch33-source-design.md`
- `/tmp/p3-ch33-lmm-mc-notes.md`
- `/tmp/p3-nyu-flexicap-recovery.md`
- `/tmp/p3-input-recovery/p3-nyu-flexicap-recovery.md`
- `/tmp/p3-input-recovery/README.md`
- 公式slides/solutions/errataの既抽出記録
- `/tmp/p3-input-recovery/nyu.txt` のp.28と文献Hull (2000)、既保存原PDF `/tmp/hull_lmm_nyu_2000.pdf`

既に確定していること:

| 項目 | 確定した原典内容 |
|---|---|
| 11e GE p.763 | 元本100、annual-pay、flat5% curve、Tables33.1/4/5のvol、first5 ITM caplet、1/2/3F価格3.43/3.58/3.61 |
| Problem33.14 / 公式解答 | chronological first N ITMは強制行使。自由選択・開始日選択型と別契約 |
| Ratchet/sticky | start1..10/pay2..11はその表の契約として確定。flexicap固有日付への転用は禁止 |
| NYU FIN-00-023 p.28 | 非標準capの具体例はHull (2000)へ参照 |
| NYU文献p.32 | Hull (2000)=Options, Futures, and Other Derivatives, Fourth Edition, Prentice Hall |
| 11e補助資料 | slides18はjoint distributionの説明、解答33.14は契約差/順位、errataには不足入力の補完なし |

既資料を再取得・再解釈して入力が増えたとは扱わない。
今回の追加探索対象は、**第4版の正規preview、掲載論文別version、著者公開計算入力**。

## 2. 追加の取得経路と結果

### 2.1 論文掲載版のDOIを新たに同定

出版社提供Crossref metadataから、次の掲載版を同定した。

- Hull/White, *Forward Rate Volatilities, Swap Rate Volatilities, and Implementation of the LIBOR Market Model*
- *The Journal of Fixed Income*, **10(2), 46–62**, 2000-09-30。
- DOI: **`10.3905/jfi.2000.319268`**。
- [DOI](https://doi.org/10.3905/jfi.2000.319268)
- [出版社ページ](https://www.pm-research.com/content/iijfixinc/10/2/46)
- publisher metadata endpoint: <https://api.crossref.org/works?query.title=Forward%20Rate%20Volatilities%20Swap%20Rate%20Volatilities%20and%20the%20Implementation%20of%20the%20LIBOR%20Market%20Model&rows=2>

**新しく確定できたのは掲載版の識別情報まで。**
web toolではDOIが取得不可、出版社ページは403。
直接HTTP取得では両者がredirect loopとなり、本文bytesを取得できなかった。
正規アクセス制約を迂回していない。購読版に入力がある/ないとは判断できない。

Crossrefの`link`にはsimilarity-checking用HighWire syndicationが載るが、一般読者用の公開本文/計算入力ではないため取得経路に使っていない。
検索に現れた第三者再配布サイト、関連論文、学生教材の価格/strikeを当該例の根拠にしていない。

### 2.2 著者公開の1999版候補

一次検索では著者Rotman URLのindexed内容にAugust1999と表示され、NYU版とは異なる表番号を持つ候補が現れた。

- <https://www-2.rotman.utoronto.ca/~hull/DownloadablePublications/libormktmodel.pdf>
- 既存NYU: <https://archive.nyu.edu/handle/2451/26689>

しかし現在の直接取得はHTTP200でも**text/htmlの404Handler、1651bytes**。
PDF magicがないので原典PDFとして扱わない。返されたHTMLを`rotman-author-error.html`として保存。
著者publicationsページも同一error HTMLを返す。
検索cacheにあるflexicap段落はHull (2000)の紹介までで、明示strike/datesがない。
検索cacheから全文versionの実在・内容差・当該入力の欠落を確定したとは扱わない。

**新しいauthor-version bytesの回収は失敗**。既存NYUの40頁PDFを別versionとして数えない。

### 2.3 第4版の正規preview

第4版候補ISBNのGoogle Books経路を一度確認。

- ISBN候補 `0130224448` のGoogle Books view API:
  <https://books.google.com/books?jscmd=viewapi&bibkeys=ISBN0130224448>
- 応答は **`var _GBSBookInfo = {};`**（22bytes）。利用可能なpreview recordを返さなかった。
- Google Books v1 ISBN APIは429。再試行や別のquota回避は行っていない。
- title/editionの一次検索で得られた4e正規記録は **学生用Solutions Manual**:
  [Google Books](https://books.google.com/books?id=PESeQgAACAAJ)
  - John Hull、Prentice Hall、2000、edition4、162頁、ISBN0130148199/9780130148193。
  - 取得HTMLは書誌情報と著者紹介のみ。当該章・解答本文のpage previewがない。
  - 本文の第4版720頁bookと、162頁solutionsを取り違えない。

Google Booksの正規書誌recordは取得できたが、**第4版のflexicap該当本文/解答は回収できなかった**。
ISBN候補の外部catalogは探索の手がかりに限り、契約条件の一次根拠にはしない。
今回の検索で当該章を含む出版社提供の合法preview PDFは見つからなかった。
これは「第4版にも入力がない」という証明ではない。

### 2.4 著者公式教材保存庫の対象版

既保存の公式Rotman FinHub固定treeを追加検索し、第4版・LMM/flexicap計算入力の候補を確認した。

- <https://github.com/rotmanfinhub/john-hull-textbook-resources>
- 固定commit: `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`
- `Options, Futures, and Other Derivatives`は11th Editionのtree。
- tree内の`4th Edition`は別書籍 *Machine Learning in Business* で、Hull derivatives第4版ではない。
- flexi/LIBOR market例固有の原計算入力は見つからなかった。

既存11e PPTX/solutions/errataを同じ方法で再検索する作業は行っていない。

## 3. 取得bytes/hash

成功・失敗のHTTP結果、解決URL、content-type、size、SHA256は
`/tmp/p3-flexicap-additional/download-records.json`へ保存。
保存ファイルのmanifestは`/tmp/p3-flexicap-additional/manifest.json`。

| 取得物 | bytes | SHA256 | 確定できたこと |
|---|---:|---|---|
| Crossref metadata `crossref-title.json` | 4719 | `06000c15b95840c1c8541a9a0cf0cf6ee1c98a465abf4bc6e1184906f5b79cc0` | 掲載版DOI/巻号/頁。契約入力なし |
| 著者旧PDF URLのerror HTML `rotman-author-error.html` | 1651 | `3303594563bd104b0417095af543b070d20f1dc4d66f45f01444cb9b99ece4ea` | 取得失敗の証拠。原典PDFではない |
| 著者publications error HTML | 1651 | 同上 | 取得失敗の証拠 |
| Google Books ISBN view API | 22 | `95f2401aa91f749880e09e5193051330774649b26c16c79e5a9aefb50dee1f68` | 空のpreview record |
| 第4版solutions正規record HTML | 83570 | `16c56c73ea04fc9406bc9aed17f12a8aad6ff1fdd4eba848a44567a4934d785c` | 4e solutions書誌情報のみ |

429/403/redirect-loopは本文未取得なので原典本文のhashを付けない。
Google Books HTMLは解決先`books.google.co.jp`の今回snapshot。元PDFの固定hashと同等の版固定情報ではない。

既回収原典のhashは再利用:

- 11e GE PDF: `8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482`
- NYU working paper: `a9350e94d15062019b63d1c7f5fab2e04e0019d40e7940aaf0356fb9c4b594b0`

これらを今回の「新しい入力回収」と数えない。

## 4. 確定 / 未確定と停止判断

| 項目 | 今回の状態 |
|---|---|
| first5 ITMのchronological forcedexercise | 既一次資料で確定、変更なし |
| 3.43/3.58/3.61 | 印刷値として確定、元入力再現は未完 |
| 固定strike数値とcompounding | **未確定** |
| 最初/最後のeligible fixing、payment、対象caplet数 | **未確定** |
| flexi5%のcurve compoundingの明示 | **未確定**（隣接契約からの推測と区別） |
| 掲載論文の正式DOI | **新たに確定** |
| 第4版本文/解答の該当page、著者の計算input | **今回の公開経路では未取得** |

新たな契約数値の根拠が増えなかったため、この追加回収をここで終了する。
第4版・購読論文に不足値が存在しないとは断言しない。
再開の根拠は、それらの該当ページまたは著者由来の具体計算inputが実際に得られたとき。
同じ一次資料の再検索、3価格からのinverse fit、ATMを原strikeとして採用、ratchet/sticky日付の転用を行わない。

P3の他要求を進めても、このflexicap原典価格入力はpendingを維持する。
全P3の完了宣言や§33.2の全原典要件acceptedは、この取得失敗だけでは正当化されない。