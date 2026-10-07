# P7 ロジック先行の実装状態

## 最終統合（2026-10-08）

統合構成でP7 **16/16 accepted**、全体**306/306・未評価0**。
最新の開発修正と正式受入を合流し、全体suite `full run: 6640 passed, 2 catalogue failures, 6 skipped; catalogue-only repair: 764 passed; combined unique checks: 6649 passed, 6 skipped`、全306節native artifacts、変更Pythonのruff/formatを確認。
原典の入力不足・未再現値とcaller条件の検証範囲を保持する。main反映・最終レビューは[統合記録](FINAL_INTEGRATION_2026-10-08.md)を参照。

## 実装と受入の履歴

以下の別branch・未統合・検証件数は各工程の実施時点の記録。現在の判定は上記と[生成台帳](SECTION_LEDGER.md)。

更新2026-10-08。目的：Ch35–37（台帳16項目）の本文計算をprivate moduleに実装し、本文例と独立参照を検証する。下調べは計算11・説明中心5（旧監査の定性6とは分類基準が異なる）。別受入branchで16/16 accepted、main統合は未実施。

- 完了条件：既存節メモの式/例を確認、計画を数行追記、private計算部品と本文/独立検証をそろえ、変更モジュールのtests/ruffを通す。入力不足は明示して次の節へ進む。
- 1節1コミット（P7 §xx.y）、codex/p7-logicへ節ごとpush。公開API・依存・台帳を変更しない。教材・画面・章受入・全suite・D1/保管庫は保留。
- 正式受入：mainはP7 0/16・全体33/306。別受入branch `cef7cea1` はP7 16/16・全体306/306 accepted、未評価0。コミット済み台帳と受入記録を照合。main統合は未実施。この作業では別受入worktreeの台帳/教材を編集しない。
- 現在：開発branchの計算10/11に加え、別受入branchで§36.4 `_business_valuation_lesson.py`を補完。P4レビュー修正/P8と受入成果の合流・検証・main統合が残る。RB-F07 v1・RB-F05 digital v1はmainへ反映済み。研究の次は離散バリア。

## 別セッションの最終受入（2026-10-08）

- 実装`5a2b72c9`・確認記録`cef7cea1`。P7 private3モジュール/10 testsを`b8ea5695`から取り込み、新private BGM/business modelを補完。旧261受入の台帳行は不変。受入側の新2モデル48 testsを含む対象389＋台帳41、全45画面/598数式/22表/9画像、全306 native artifacts、strict tracked release PASS、独立review C/I/未解決Minor 0の記録を確認。開発側では再実行していない。
- §36.4は原論文から回収した四半期パラメータで売上log Euler・growth OU・税損失繰越・cash/倒産/終価とcaller指定資本構成を検証。会計の売上/終価利益時点・employee option条件が未確定で、原著5457M・倒産27.9%・株価12.42は未再現。期首売上/quarterly終価利益の100,000 pathsは8387.42M（SE51.14）・倒産30.729%（SE.1088 percentage point）。原著との差を保持する。
- 正本は別受入branchの`docs/CHAPTERS_29_37_ACCEPTANCE_2026-10-08.md`と`docs/validation/fast-ch29-37/`。以下の節別件数・履歴は開発時点の記録を保持する。

## 節別の実装

対象検証は当該節完了時のモジュール累計で、合算しない。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 制限・未解決 | 状態・対象検証 |
|---|---|---|---|---|
| §35.4 | `_commodity_foundations.py` | Ex35.1 .034/20.4%、Ex35.2 17.729k、季節6値、Fig35.1/2の分岐/shift/価格、Fig35.3中間値とD/H/I行使。独立全経路とOU密度積分・jump MC | 計算完了。原典root1.48対1.501100501、年2最下11.10対11.094790584、I8.90対8.905209416は表示精度で不一致。複雑モデルの全面較正は範囲外。 | ロジック完了・6 passed・ruff check/format PASS |
| §35.5 | `_commodity_foundations.py` | 56°F/HDD9/CDD0、HDD820→1.2M/cap1.5M/upper850。独立日別台帳とcall spread/温度換算 | 計算完了。観測期間/stationはcaller入力、Celsius換算ではbase/tickも変える。市場仕様は原典時点。 | ロジック完了・8 passed・ruff check/format PASS |
| §35.6 | `_commodity_foundations.py` | 100M exposure→retained30M、loss50M→15M、30–40M layer10MとCAT principal10M。独立3領域台帳/call spread | 計算完了。原典reinsurerのlong/short文は不整合、protection買い手の受取とwriterの逆符号を固定。triggerはcaller入力。 | ロジック完了・10 passed・ruff check/format PASS |
| §35.7 | `_commodity_foundations.py` | d1 .2376/d2 .1676、250900/243400、mean697→180400/175100。独立密度積分/MCと支払割引 | 計算完了。非取引指数・系統リスク0の本文仮定に条件付き、trend原データはなく697を本文入力として使う。log-SDへ√年数を掛けない。 | ロジック完了・12 passed・ruff check/format PASS |
| §35.8 | `_commodity_foundations.py` | 本文にデータ/数値なし。合成a+bP+cT、独立共分散正規方程式とtrain/holdoutの単独/共同hedge | 計算完了。rank不足では一意な契約数が出ないため拒否。train推定をholdoutで固定し、Q pricing/完全hedgeを主張しない。 | ロジック完了・14 passed・ruff check/format PASS |
| §36.1 | `_real_options_foundations.py` | NPV−11.53M、call.545、要求call55.96%/put−70.4%。独立cash再投資/線形replication/root | 計算完了。P期待CFをrequired rateで割引、optionとbaseの割引率を同一視しない。比較企業betaの推定は本文データなし。 | ロジック完了・2 passed・ruff check/format PASS |
| §36.2 | `_real_options_foundations.py` | A4.5355/Q drift6%/E rent33.82/expected1.5015M/PV1.3586M。独立lognormal密度/前払CF | 計算完了。λはcaller仮定/推定、非取引資産から無裁定だけでは一意でない。annuityはt=2時点、optionと二重割引しない。 | ロジック完了・5 passed・ruff check/format PASS |
| §36.3 | `_real_options_foundations.py` | ρ.3/market vol20%/premium5%→λ.075。独立OLSと共分散、quarterly→annual4 | 計算完了。sales原データ/proxy推定の検証ではない。market premiumとvolの年率/期間単位を合わせる。 | ロジック完了・7 passed・ruff check/format PASS |
| §36.4 | `_business_valuation_lesson.py`（別受入branch） | 回収した四半期parameter、独立OU求積/会計CFを検証。caller条件100,000 pathsの8387.42M/倒産30.729%を保存 | 原著5457M/27.9%/12.42は会計/ESO時点不足で未再現。逆合わせしない。 | 別branchでモデル補完・正式受入、main未統合 |
| §36.5 | `_real_options_foundations.py` | CF4/6/8M、PV14.46M/NPV−.54M、撤退1.94M/NPV1.40M、拡張1.06M/NPV.52Mと全節点。独立512方策×27経路、複合4状態。共同option3.217896Mは追加検算 | 計算完了。当年CF後/不可逆4状態/非比例費用を明示。単独印刷値は一致。共同3.217896M・初期拡張は独立方策でも一致し、p812脚注の相互作用なしを再現できない。縮小/延期/寿命延長は本文入力なし。 | ロジック完了・11 passed・ruff check/format PASS |
| §37.1 | `_mishap_foundations.py` | 4連勝1/16・16人の期待人数1、20株平均10%/vol14.7%。追加any-success .64392587、独立二項列挙/共分散行列/MC6SE | 計算完了。独立trial/等相関・同vol・等weightの条件付き。期待人数1は成功者1人の保証ではない。歴史的損失/和解/支援は集計せず、§37.2–3の統制説明は保留。 | ロジック完了・3 passed・ruff check/format PASS |

## 対象と保留

- 計算対象：§35.4–35.8、§36.1–36.5、§37.1。§36.4は別受入branchでcaller条件のモデルを補完し、原著株価12.42の未再現を保持する。
- 説明中心5項目：§35.1–35.3、§37.2–37.3も別受入branchで受入済み。mainへの教材・受入成果の統合は未実施。
- 商品のEuler三項木はCh32の分岐部品を共有するが、通常到達確率でfutures期待値へ較正する。割引state priceを商品futures較正に使わない。

## 最終照合（2026-10-06）

- 下調べ/台帳16項目はIDが一致。計算11行＝実装10＋入力不足§36.4、説明中心5項目は保留。正式台帳は未変更（P7 0/16、全体33/306）。
- P7差分はprivate 3モジュール・tests 10ファイル・文書6ファイル。公開API/依存/教材/画面/台帳の変更はない。計算コードはcodex/p7-logicに置き、mainへは進捗文書のみ反映する。
- 対象28 tests PASS、3モジュールのdocstring/索引6 tests PASS、ruff check/format check PASS。対象ファイルを明示して実行。全suite/章受入/D1/保管庫/ブラウザはこの作業で実行していない。
- §36.5単独optionの本文値と全行使集合は一致。共同4状態のPV17.676176037M/option3.217896081Mは独立方策・非再結合履歴で一致。初期拡張後の撤退権があるため、単独optionの和3.000467371Mより大きくなり、p812脚注の相互作用なしを再現できない。脚注へ合わせて状態を省かない。
- §36.4再開にはσ(t)/η(t)/κ/初期・長期growth/λR/r/株数と転換・従業員option/会計条件が必要。BS36.1の12.42は未再現で、架空入力のMCを原典再現と呼ばない。
- 次：RB-F07 v1（較正を通した市場クオート感応度）はmainへ反映済み。研究のRB-F05 digital v1は実装・対象検証・独立レビュー修正を完了。次は離散バリアの契約/参照を固定。教材/正式受入は別の専用worktreeで進行中で、この実装branchとは分離する。

## 開発ブランチへの修正反映（2026-10-07）

- `codex/p7-logic`へP4レビュー修正18コミット（`00d8a651`まで）とP8（`ce801e48`まで）を通常merge。両commitの祖先包含を確認。既存P3–P7ロジックを保持し、未受入ロジックはmainへ入れていない。
- 統合前の主要3モジュール対象224 tests PASS。統合後の変更テスト81ファイル＋docstring/索引2ファイルは1,727 passed、変更Python108ファイルのruff check/format check PASS。全suite・教材再生成・D1再撮影は繰り返していない。
- 別受入worktreeは`cef7cea1`で306/306 accepted、未評価0。基点`0d07def7`の旧261台帳行は不変。このブランチの正式台帳はmainの33/306を維持。受入成果と開発側修正の合流・検証・main統合が残る。

- RB-F07 v1は`origin/main`の`3ac3e00c`へ反映済み。private計算・24 tests・研究3図、関連649 tests、独立レビュー指摘0、tracked release/33節台帳PASS。詳細は [研究資料](../research/RB-F07/README.md)。
- RB-F07を集約開発branchへ通常merge。P3–P7のprivate索引を保持し、RB-F07＋索引/docstringの858 testsと独立数値参照の再生成checkはPASS。競合は索引・ロードマップ・状態文書の3件だけで、計算ファイルは自動merge。
- 受入branch `cef7cea1` の `_futures_options.py`・`_index_currency.py`・`_greeks_hedging.py` はP4最新review branch `00d8a651` とblobが異なり、origin/mainも祖先に含まない。P4レビュー修正/P8の取り込みと受入成果の整合を統合時に確認する。別セッションの作業tree・台帳はこの開発作業では変更しない。

## RB-F05 digital v1（2026-10-07）

- hullkit非公開teacherとdeep_hedge_price非公開CPU学習、独立参照・3seedのprice-only/DML・研究3図を実装。新規32/関連807 tests、ruff、artifact-only実行/目視、保存重み/指標/費用/4種改竄検査PASS。独立レビューImportant1修正済み（Critical/Minor0）。
- DMLは3seedすべてで改善したが、解析/補間のほうが高精度/高速。速度で標準器へ昇格せず、教師/比較資料を採用。正式受入件数と別受入branchの台帳には変更なし。[研究資料](../research/RB-F05/README.md)。
- `097d4c8d`までをmainへpushし、集約開発branchへ通常merge（`4ed33c79`）。F05/F07と両package索引/docstringを含む1,019 tests PASS。root mainでも新規32 tests・cached/fresh独立参照check PASS。未受入P3–P7の計算コードは開発branchに保持し、mainへは入れていない。
