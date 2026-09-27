# johnhull 実装再開前の準備

- 更新日：2026-09-27。照合した製品コード：`7c4bb109`。
- 作業ブランチ：`claude/johnhull-prep`。
- 状態：**準備文書完成**。37章292節、65出典、設計・再確認メモ9本を統合・検査・独立レビュー済み。
- 目的：未評価の全292節について次に必要な作業を具体化し、研究候補の根拠と実装順を確かめる。
- 完了条件：292節の記録、S001–S062・L01–L03の65記録、下記設計、参照・件数検査、独立レビュー、研究計画とROADMAPの更新。
- 収録：準備文書49ファイル（章別37・出典2・設計等9・本README1）。中断前の成果を引き継いで補完した。

これは**準備文書**であり、節の受入や研究モデルの性能承認ではない。
製品コード・notebook・配布データ・依存・受入台帳は変更していない。独立計算はGit管理外のscratchに置いた。
台帳は**受入14／未評価292、全306項目**のまま。[現在地と全体計画](../../ROADMAP.md)を正本とする。

## 決定済みのこと

利用者の2026-09-27の回答を[研究計画 §8](../superpowers/plans/2026-09-27-research-backlog.md#8-利用者の判断2026-09-27-決定済み)に反映した。

1. 研究教材・記録は `johnhull/research/<RB-ID>/`、計算は hullkit の非公開モジュールに置く。公開APIへの昇格は別承認。
2. 実装再開は、johnhullに必要な保管庫と作業分離が整った時点。ワークスペース全体の移行完了は待たない。
3. M15（§27.6）と研究第1候補RB-F07は、いずれも **D1-preflightの検証完了後**に着手する。

保管庫・復元器・新しいmanifestはこの準備作業では作っていない。D1の検証完了を推定して実装へ進まない。

## 読み方

| 目的 | 入口 |
|---|---|
| 次の節に必要な本文・数値・図・コードを知る | 下の章別文書。各節に原典の要点、要求の下書き、印刷値と照合結果、既存実装、不足、独立参照、図、依存、規模を記載 |
| 外部提案94件の扱いと研究順を知る | [研究計画](../superpowers/plans/2026-09-27-research-backlog.md)、[保存した提案書](../RESEARCH_HANDOFF_2026-09-27.md) |
| 論文・企業資料が何を裏付けるか調べる | [S001–S031](sources/sources_S001-S031.md)、[S032–S062・L01–L03](sources/sources_S032-S062_L01-L03.md) |
| M15前の基盤作業を具体化する | [D1-preflight](design/D1_PREFLIGHT_PLAN.md) |
| 未解決の監査所見を再確認する | [P8再確認](design/P8_RECHECK.md) |
| 金利編の順番・検証方法を決める | [P3設計](design/P3_DESIGN.md) |
| 定性節の受入負担を下げる | [D3案](design/D3_LIGHT_ACCEPTANCE.md)。現行の画面確認は保持する |

「印刷値一致」は記載した入力と丸め桁での下調べ結果。節全体の正しさや受入を意味しない。
「未再計算」「要確認」は残作業であり、原典の誤りと確定していない。市場統計・制度・契約例の入力値を計算結果のピンと混同しない。
種別と規模S/M/Lは着手前の見積もりで、日数や最終的な台帳分類ではない。

## 章別の下調べ

対象は台帳で未評価の項目だけ。Ch26は§26.1–8、Ch27は§27.6–8。受入済み14節は重複作成しない。
付録は台帳にあるものを1項目として数える。

| 章 | 文書 | 対象節数 | 段階 |
|---|---|---:|---|
| 1 | [Introduction](sections/ch01.md) | 10 | P6 |
| 2 | [Futures Markets and Central Counterparties](sections/ch02.md) | 11 | P6 |
| 3 | [Hedging Strategies Using Futures](sections/ch03.md) | 7 | P6 |
| 4 | [Interest Rates](sections/ch04.md) | 12 | P6 |
| 5 | [Forward and Futures Prices](sections/ch05.md) | 14 | P6 |
| 6 | [Interest Rate Futures](sections/ch06.md) | 5 | P6 |
| 7 | [Swaps](sections/ch07.md) | 13 | P6 |
| 8 | [Securitization and the Financial Crisis](sections/ch08.md) | 4 | P6 |
| 9 | [XVA](sections/ch09.md) | 4 | P6 |
| 10 | [Mechanics of Options Markets](sections/ch10.md) | 12 | P4 |
| 11 | [Properties of Stock Options](sections/ch11.md) | 7 | P4 |
| 12 | [Trading Strategies Involving Options](sections/ch12.md) | 5 | P4 |
| 13 | [Binomial Trees](sections/ch13.md) | 12 | P4 |
| 14 | [Wiener Processes and Itô's Lemma](sections/ch14.md) | 9 | P4 |
| 15 | [The Black–Scholes–Merton Model](sections/ch15.md) | 13 | P4 |
| 16 | [Employee Stock Options](sections/ch16.md) | 5 | P4 |
| 17 | [Options on Stock Indices and Currencies](sections/ch17.md) | 6 | P4 |
| 18 | [Futures Options and Black's Model](sections/ch18.md) | 11 | P4 |
| 19 | [The Greek Letters](sections/ch19.md) | 15 | P4 |
| 20 | [Volatility Smiles](sections/ch20.md) | 9 | P4 |
| 21 | [Basic Numerical Procedures](sections/ch21.md) | 8 | P4 |
| 22 | [VaR and Expected Shortfall](sections/ch22.md) | 9 | P5 |
| 23 | [Volatility and Correlation Estimation](sections/ch23.md) | 7 | P5 |
| 24 | [Credit Risk](sections/ch24.md) | 9 | P5 |
| 25 | [Credit Derivatives](sections/ch25.md) | 11 | P5 |
| 26 | [Exotic Options：未受入の8節](sections/ch26.md) | 8 | P2 |
| 27 | [More on Models and Numerical Procedures：残り3節](sections/ch27.md) | 3 | P1 |
| 28 | [Martingales and Measures](sections/ch28.md) | 8 | P3 |
| 29 | [Interest Rate Derivatives: Standard Market Models](sections/ch29.md) | 4 | P3 |
| 30 | [Convexity, Timing, and Quanto Adjustments](sections/ch30.md) | 4 | P3 |
| 31 | [Equilibrium Models of the Short Rate](sections/ch31.md) | 5 | P3 |
| 32 | [No-Arbitrage Models of the Short Rate](sections/ch32.md) | 7 | P3 |
| 33 | [Forward Rate Models](sections/ch33.md) | 3 | P3 |
| 34 | [Swaps Revisited](sections/ch34.md) | 6 | P3 |
| 35 | [Commodity Derivatives](sections/ch35.md) | 8 | P7 |
| 36 | [Real Options](sections/ch36.md) | 5 | P7 |
| 37 | [Derivatives Mishaps](sections/ch37.md) | 3 | P7 |
| **合計** | **37章** | **292** | **準備対象** |

## 設計メモ9本

| 文書 | 最小範囲と着手条件 |
|---|---|
| [RB-F07](design/RB-F07_DESIGN.md) | 単一曲線の預金・FRA・スワップ較正と市場クオート感応度。手計算、別解法の再較正、座標・残差の不変性を試作で確認。D1後の研究第1候補 |
| [RB-F05](design/RB-F05_DESIGN.md) | digitalの解析価格・Greekを基準にscore教師とDifferential MLを比較。教師の分散・費用も含む。barrierはM15後 |
| [RB-F04](design/RB-F04_DESIGN.md) | HestonとDupire local volが同じvanilla面を価格付けしても、Asian価格・同じ実現経路上のヘッジが異なり得ることを検証 |
| [RB-F08](design/RB-F08_DESIGN.md) | GBM Eulerと強い解析基準からMLMC/RQMCを比較。離散化と標本誤差、独立レベル・scrambleを区別 |
| [RB-F06](design/RB-F06_DESIGN.md) | beta固定SABRの3パラメータから、複数初期値・弱い方向・ノイズ感度を調べる。Hestonは後段 |
| [P3](design/P3_DESIGN.md) | 測度と契約規約→HW/BKの木と曲線適合→European→Bermudan→多因子。既存MC近似を厳密解と扱わない |
| [D1-preflight](design/D1_PREFLIGHT_PLAN.md) | 依存指紋、画像参照、旧形式互換、全再描画との比較、欠損・改ざん・復元の検査。実装・検証は未実施 |
| [D3](design/D3_LIGHT_ACCEPTANCE.md) | 定性節でも説明とrenderedを保持し、buildと画面検査の作業を章で共有する案。規約変更は未承認 |
| [P8](design/P8_RECHECK.md) | R1–R4・R6・R11と保存値依存5項目の現在の状態・独立試算・修正順。製品側は未修正 |

## 判断に効く発見

- **R11は資金繰り規約の違い。** 原典のTables19.1/19.4は利息・割引を除外する。同じ20万パスでその規約を使うと12個の印刷値の丸めに一致した。ライブラリの資金繰り計算を誤りとして削除せず、原典との比較規約を分ける。
- **R1は教師の標本誤差だけでは説明できない。** 次の時点の情報を使う分散更新と補償項を切り分けた。独立参照との差を教師のSEで正当化しない。再確認時はantithetic pairを独立単位にしてSEを計算した。
- **外部資料の式も無条件には転記できない。** S002の2式には不整合があり、F05の教師は解析的な別計算で検証する。S003のIFTは正方・局所可逆、S020/S021の有限標本区間は既知の有界性など、適用条件を設計へ戻した。独立レビューではS005の先物換算係数、S007の凸性、S019/S031の密度・累積分布・調整済みデータの扱いを明確にした。
- **LLMの評価期間にも漏洩確認が必要。** S043の論文が使うGemini 2.5 Proの学習期限は、Google公式model cardのJanuary 2025と不一致。2023年の事例を「学習していない期間」とする主張は支持できない。RNNの評価とは分け、企業の効果報告も独立な性能実証として扱わない。
- **軽量化しても配布画面の確認は残る。** 現行台帳の必須項目にrenderedがある。D3を承認済みとみなして省略しない。

原典の印刷値の差異は各節に記録した。出版社の公式訂正を確認していないものは、その旨を残し、期待値の強制や許容差の拡大で隠さない。

## 検証と限界

2026-09-27の最終検査結果：

| 検査 | 結果 |
|---|---|
| 未評価節との対応 | **292/292、PASS**。欠落・対象外・重複IDなし。READMEの章別件数も台帳と一致 |
| 出典の記録 | **65/65、PASS**。必須項目を持つYAMLと一覧表のID・判定が一致。支持23件・部分確認42件 |
| 明示した関数参照 | **469箇所、解決不能0**。prep内のhullkitへの `module:symbol` 形式をASTと照合 |
| 相対Markdownリンク | **参照先ファイルの存在確認PASS**。見出しanchorの描画結果は対象外 |
| 受入台帳 | **PASS**、306項目・受入14。`artifacts_checked=false` |

出典の「支持」は読んだ範囲の主張への判定で、独立な実験再現や製品性能の承認ではない。使用した検査の範囲は次のとおり。

- `check_prep.py`：未評価292 IDの見出し・重複・既存シンボル参照。
- `scratch/codex_integration/validate_prep.py`：バッククォートのない明示的な関数参照（例：`hullkit.rates:zero_interp`）も含め、各節の必要項目、相対ファイルリンク、65出典のYAMLとIDを追加検査。
- `verify_section_ledger.py`：台帳の整合性。`artifacts_checked=false`の検査なので画像・releaseの再検証ではない。
- RB-F07、P8および各章の独立計算：数値結果・計算規約を記録。scratchは補助資料であり、受入用スクリプトや正式fixtureの代わりではない。

独立レビューは設計9本・S001–S031・研究計画を対象に実施した。指摘5群（F07の三角性と条件数、S005のCF/レバレッジ、S007の凸性、S019の密度/CDF、S031の二重調整）を修正し、再読で残る阻害事項なし。章の追加照合はCh4のSARON、Ch24の格付け区間・丸め残差、Ch31のVasicek係数、Ch35のExample35.3を対象にした。論文の全証明・全実験性能や、292節すべての二重再計算は検証範囲に含めていない。

補助検査・試作の実体は `/home/kazumasa/projects/tmp/johnhull-prep/`。Git管理外のため、このコミット単体から同じscratchを実行できるとは主張しない。
研究や各節を実装するときに、必要な入力・独立参照・検査を管理対象の正式ファイルとして作る。
今回の文書だけの変更では、製品の全pytest・book/report build・ブラウザ検査・release gateは再実行していない。

## 次に進める順番

1. 承認済み方針に沿い、johnhullに必要な保管庫と作業分離が準備できたことを確認する。
2. D1-preflightを実装し、旧証跡互換・依存変更伝播・全再描画との比較・2コピーからの復元を検証する。
3. PASS後にM15とRB-F07を既存計画の範囲で進める。研究は同時1本。D3の規約変更と公開API昇格は別判断。

本準備の完成を、上記基盤の検証完了やremoteへの公開と読み替えない。
