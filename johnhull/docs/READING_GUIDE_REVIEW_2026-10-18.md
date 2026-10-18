# 読むガイド T0・T1 の独立検証（2026-10-18、Claude）

- 対象：branch `codex/reading-guide` の e491b454（基点は main 7f668a39、T0 は 00b7f44d）。差分は12ファイル、+1900 −8。
- 原典：Hull 11e Global Edition（PDF の SHA-256 は記録と一致）。記号はページ画像（300 dpi）で照合した。pdftotext はギリシャ文字をラテン文字に落とす（α→a、σ→s、μ→m）。
- 結論：このままでは統合しない。統合の条件は、§2 の必須の修正（N1）とユーザーの読後判断。計画 §5-3 により、読みやすさの指摘も受け取る前に直す。
- 計画：[READING_GUIDE_PLAN_2026-10-18.md](READING_GUIDE_PLAN_2026-10-18.md)。検証の出力は `/home/kazumasa/projects/_data/johnhull/reading-guide/review-claude-20261018/`（Git 管理外）。

## 1. 再実行した検査

| 検査 | 結果 |
|---|---|
| import 先 | worktree の hullkit（`/home/kazumasa/worktrees/reading-guide/johnhull/hullkit/src/hullkit/__init__.py`） |
| numerics.json の参照テスト | 44 passed（記録と同じ集合） |
| Book 全ビルド | exit 0。警告は154件で、153 WARNING＋既存の ERROR 1件（`15_bsm_ch15.ipynb:10005`）。ガイド由来の警告は0。実装者の生成物と397ファイルが byte で一致 |
| `check_book_math.cjs` | PASS（31ページ） |
| `check_reading_guides.cjs` | PASS（1280px・390px。Ch13/Ch8 の描画数式 115/6、ローカルリンク 29/21） |
| 目視と幅の追加調査 | 360・375・390px ではみ出しなし。320px（要件外）では m(L) と Δ の式が式の内側で横にスクロールする |
| `shared_runtime.py --check` | PASS |
| `make hull-release-check HULL_RELEASE_FLAGS=--require-tracked` | PASS |
| `make lint` | PASS |
| `make test` | 11,907 passed / 76 skipped、exit 0（rootdir は worktree、単一スレッド BLAS） |
| 台帳の strict gate | exit 1、158件。基点を `git archive` で再構成しても同じ158件（追加0・消失0） |

原典との照合で一致した論点：Ch13 の金利4%、Q と P の確率と割引率、印刷値と丸めない値、米国型の行使判断、節点のデルタ、CRR の分散一致が近似であること、配当・外国金利・先物の成長率と割引、付録の p*。Ch8 の支払いと損失の順序、二段目の分母、89.75% と 10.25% の意味、AAA 比率と損失免除の区別、住宅・ローン・証券の損失の尺度、相関の上昇と完全相関の区別。原典の連続した翻訳や図表の再掲はない。

## 2. 直すこと（修正の回）

### 必須

- **N1** `ch13.md:191`、`validation/reading-guide/README.md:26`（GE pp.312–313）：付録の境界は j>α（ギリシャ文字）で、§13.8 の a=e^{rΔt} とは別の記号。「a の再利用」とする記述を直す。p* の再利用（p.294 と式13A.9）は正しいので残す。

### 正確さ

- **N2** `ch13.md:41`（pp.291–294）：式13.2〜13.4 は1期間の満期 T で書かれている。T で示し、多段の木では Δt に置き換えると書く。
- **N3** `ch13.md:81`（p.297）：プットへ移る理由を原典の意図として書かない。ガイドの読み方として書くか、削る。
- **N4** `ch13.md:31`：Δ の単位。分子は「オプション1単位あたりのドル」、分母は「1株あたりのドル」。
- **N5** `ch13.md:54`（p.294）：原典は現実の上昇確率を p* と書く、と §13.2 で紹介する。そうしないと :193 の「これも p*」が受けられない。
- **N7** `ch13.md:150`：偶数段と奇数段で価格が振動するという話は、GE 第13章にない。理由を一文で書いて出典を付けるか、削る。
- **N8** `ch13.md:172`（p.307）：先物で a=1 となる理由（先物を建てる費用はゼロなので、リスク中立の世界では先物価格の期待成長率がゼロ）を一文足す。
- **N13** `ch08.md:70`（p.209）：TED スプレッドは、3か月物ユーロダラー預金金利と3か月物米国債金利の差。平常時は30〜50bp、2008年10月に450bp を超えた。LIBOR–OIS は2008年10月に一時364bp。
- **N15** `ch08.md:94`：`https://www.bis.org/bcbs/publ/d462.pdf` は、2019年4月の統合バーゼル枠組みの市中協議文書のページ（`https://www.bis.org/publications/201904-consultation-consolidated-basel-framework`）へ転送される。リンク名を「市中協議文書（2019年4月）」に直し、転送先の URL を使う。

### 読みやすさ

分量は今の目安のまま、注意の文の一部を導出と具体例に置き換える。分量と文体の最終判断は、修正版を読んだあとにユーザーが行う。

- **N6** `ch13.md:132-134`（pp.300–301、式13.12〜13.13）：平均と分散を合わせる2式を示し、一次の近似で u=e^{σ√Δt} が出ることを2〜3行で書く。「拡散」は定義するか言い換える。
- **N9** `ch13.md:8`・`:16`：「無裁定」と「ペイオフ」を初出で定義する。「連続複利」を定義する。§13.2 で「リスク中立世界（risk-neutral world）」の語を示す。
- **N10** `ch13.md:85-87`・`:107`・`:160`：丸めについての注意を1か所（数値の読み方）にまとめる。
- **N11** `ch08.md:58-60`（pp.205–206）：サブプライム（subprime）、変動金利型ローン（adjustable-rate mortgage、ARM）、ティーザー金利（teaser rate）を、初出で名前を示して説明する。原典 p.206：典型的なティーザー金利は約6%、その期間の後は6か月 LIBOR＋6%。
- **N12** `ch08.md:68`（p.208）：ABX と TABX の要点を書く。ABX では、BBB 格だった層が2007年末までに価値の約80%を、2009年半ばまでに約97%を失った。TABX では、BBB 層から作った ABS CDO のうち AAA 格だった層が、2007年末までに約80%を失い、2009年半ばにはほぼ無価値になった。
- **N14** `ch08.md:80`（p.210）：原典の例（損失5〜6%を負う BBB 層。損失が5%未満なら無傷、6%を超えると全損）を、m(L) と同じ形で一文にする。

### 記録と道具

- **N16** `00_overview.md:20-21` の章の順を、`_toc.yml` と同じ Ch8→Ch13 にそろえる。
- **N17** `ROADMAP.md:30`、`READING_GUIDE_STATUS.md:9`・`:94`：「push は行わない」を「main への merge と main の push はしない（作業 branch は push 済み）」に直す。
- **N18** `shared-runtime.json` の `checks` に時刻と commit がない。今回は runtime ファイルを変えないので書き直さない。次に `--write` するとき（T2 で `_toc.yml` を変えるとき）に、各検査へ commit と時刻を入れる。
- **N19** `check_reading_guides.cjs:13`：`READING_GUIDE_OUTPUT_DIR` がなければ止める（既存の証跡を上書きしない）。`:47` のはみ出し検査が display の数式しか見ないことを、検証 README に書く。
- **N20** `numerics.json`：89.75% は `test_securitization_foundations_waterfall.py:14` が 90±0.5 でしか固定しない。80＋15×0.65 の恒等式であることを `numerics.json` に書く。
- N11・N12・N13 と下の Basel で新しく出す数値は、`numerics.json` の `non_example_numbers` に頁つきで登録する。

### 任意

- `ch08.md` §8.4：BS 8.1（p.212）の「Basel IV は2022〜2027年に実施」は刊行時点の予定である。BCBS は2020-03-27に、2017年12月に最終化した基準の実施を2023-01-01へ、output floor の経過措置を2028-01-01へ、それぞれ1年延ばした（https://www.bis.org/press/p200327.htm）。現在側として一文足すなら、確認日を付ける。

## 3. 今回は直さないこと（基点からの問題。別に判断する）

- **B1 台帳の strict gate（158件）**
  - 内訳：89件は 06・10・12 のページ全体の HTML の digest。69件は33記録の D1 fingerprint で、差は `book_assets` だけ（外部の jsdelivr mathjax@3 が同梱の mathjax-3.2.2 に替わった）。
  - EVIDENCE_POLICY（2026-10-17）は、共有ランタイムのハッシュを鮮度判定で比べないと定める。ところが検証器はまだ比べている。
  - ページ全体の HTML は nav を含むので、TOC を変えるたびに一致しなくなる。
  - 検証器を直す（article だけを比べる、`book_assets` を共有ランタイムの manifest で扱う）には別の承認が要る。ページ全体を pin し直すなら、ガイドの merge の後に行う。
- **B2 Book の ERROR**（`15_bsm_ch15.ipynb:10005`）：基点からある。ERROR が出ても build は exit 0 になる。
- **一般的なストーリーの厚さ**（Ch13 は2段落、Ch8 は1段落で、出典は Hull だけ）：Hull 以外の出典を足すかどうかは、ユーザーが読後に決める。

## 4. 修正後に回す検査

- numerics の参照テスト、Book 全ビルド（警告の件数が変わらないこと）、`check_book_math.cjs`、`check_reading_guides.cjs`（2幅。`READING_GUIDE_OUTPUT_DIR` は新しいディレクトリ）、390px での目視（数式の欠けがないこと）、`shared_runtime.py --check`、release `--require-tracked`、`make lint`、`make test`。
- 文字数を記録と同じ方法で数え直す。約物を含めた数と、数式を除いた可視文字の数も添える。作業時間と使用量も記録する。
- `ROADMAP.md` の「現在地」と `READING_GUIDE_STATUS.md` を同じ commit で更新する。
- merge と push はしない。修正を終えたら止めて報告する。Claude が差分を再検証し、そのあとユーザーが修正版を読んで分量と文体を決める。T2・B1 以降には進まない。

## 5. 修正 8e3cbe9d の再検証（2026-10-18、Claude）

- 対象：e491b454..8e3cbe9d（9ファイル）。結論は「受け取れる」。N1〜N20 は対応済みで、N18 は次の `shared_runtime.py --write` の要件として記録されている。重大な指摘はなく、残ったのは任意の7件だけ。
- 出力：`/home/kazumasa/projects/_data/johnhull/reading-guide/review-claude-20261018-r2/`（Git 管理外）。
- 再実行した検査は §4 の全項目。
  - numerics の参照テストは 44 passed。
  - Book 全ビルドは exit 0。警告は前回と同じ 153 WARNING と ERROR 1件で、ガイド由来は0。実装者の生成物と397ファイルが byte で一致した。
  - `check_book_math.cjs` は PASS。
  - `check_reading_guides.cjs` は PASS（新しい出力先、1280・390px）。描画数式は Ch13 133・Ch8 8。
  - 390px での目視、`shared_runtime.py --check`、release `--require-tracked`、`make lint` も PASS。
  - `make test` は 11,907 passed / 76 skipped。
- 文字数は記録と一致した。3通りの数え方で Ch13 が 10,330／11,359／12,582、Ch8 が 5,989／6,634／7,752。
  - 原典1頁あたりにすると、①（和文のみ）で Ch13 は約413字、Ch8 は約499字。
  - ②（約物を含む）では Ch8 が約553字で、目安の上限を超える。
- 読後判断（ユーザー、2026-10-18）：この形で進める。訳語は [READING_GUIDE_TERMS_2026-10-18.md](READING_GUIDE_TERMS_2026-10-18.md) に合わせて直す。

### T2 でパイロットを改訂するときに直すこと

Ch8 は分量の目安の上限付近にある。足す分は、筋に要らない細部を削って釣り合わせてよい（計画 §4）。

1. `ch13.md:136`（GE pp.300–301）：左辺の展開 $x^2+x^4/12+r\Delta t\,x^2-r^2\Delta t^2+\cdots$ を1式示し、$x^2$ 以外の項が $\Delta t^2$ 以上の大きさだと書く。
2. `ch13.md:127–134`（GE p.300、式13.12）：原典は分散を収益率 $u-1$・$d-1$ で書いている。各状態から同じ1を引いても分散は変わらない、と一句足す。
3. `ch13.md:89`：§13.10 の6.76ドルと、§13.8 の倍率に先回りしている。§13.10（`:169`）から「表示桁の読み方は §13.4」と戻れるようにする（計画 §4 のストーリーの規則）。
4. `ch08.md:72`（GE p.209）：bp の定義を LIBOR–OIS の文より前へ移す。ユーロダラー預金を「米国外の銀行に預けた米ドル預金」と説明する。
5. `ch08.md:60`（GE p.206）：ティーザー金利の期間「当初2〜3年」を書き、`numerics.json` の p.206 の項に足す。
6. `ch08.md:60`・`:72`（計画 §4 の時点の規則）：LIBOR が今は公表されていないことを、確認日つきで一文書く。FCA によれば、米ドル LIBOR のパネルは2023-06-30に終わった。最後まで残った合成の米ドル LIBOR（1・3・6か月）も、2024-09-30が最後の公表だった。出典は [LIBOR transition](https://www.fca.org.uk/markets/libor-transition) と [The US dollar LIBOR panel has now ceased](https://www.fca.org.uk/news/news-stories/us-dollar-libor-panel-has-now-ceased)（Claude が2026-10-18に確認）。
7. `ch08.md:82`（GE p.210）：「比べても」を「比べると」にする。
