# 短期・同日満期 DML v1 — 結果と採否

2026-10-09。合成同日欧州cash callの固定実験。数値・保存物・実3図の検証済み、関連3suite7998 PASS/6 skip、19Python ruff/format PASS。tracked release/最終独立208checks PASS・Critical/Important0。main未反映。main統合は未実施。

## 結論

**Delta-DMLは全3 paired seedで誤差を改善したが、NNの標準高速器採用は不成立。** 独立参照に対する固定336点の価格・Delta・物理Gammaの同時精度条件を、raw/safeの全6 fitが満たさなかった。Hermite補間は全336点を通過した。精度を満たさないNNについて、同等精度の速度優位・費用回収Qを計算しない。負の結果も教材として保持する。

| 判断 | 結果 | 範囲 |
|---|---|---|
| 条件付き教師 | 支持 | 固定640教師のprecision/rare gate、独立級数・密度・追加raw検算 |
| Delta-DMLの改善 | 支持 | 固定3 paired seedのraw RMSEの記述的比較 |
| NN Gammaの利用 | 不支持 | 全元点の固定精度未達。Gamma lossは使っていない |
| NN標準高速器 | 不採用 | raw/safeとも精度未達。安全経路も未知のGreek誤差を検知できない |
| 研究教材の保持 | 受入 | 原始配列・失敗・unknown・費用・3図を保存 |

## 固定した問題

- S/Kの価格単位は通貨、K=100、r=.03、q=0、2026-10-08 16:00 America/New_York満期の合成契約。
- carryはUTC ACT365、分散は252 sessions/yearの別時計。U字時計の重み(2,.5,2)、境界(0,.15,.85,1)、vol .20。
- 15:30–16:00に複合Poisson pulse。log jump mean −.05/std .10、full intensity .028。no-eventはintensity=0。
- 主領域は残り1–390分。spot Delta/GammaはK・時計・満期・Q jump lawを固定した微分。
- no-event教師は解析的に退化し、MC drawを生成していない。event教師は全IID分母N=1048576のゼロcountを含むcompact保存。
- 512train/128validation、336固定test、price-only/Delta-DML×seed11/29/47、同initialization/batches、各512updates。main後の再選択・追学習・許容差変更はない。
- 金融source10件・条件・3870予約seedを、正式pilotの独立承認後に固定。予約件数と観測件数を区別する。

## 教師と参照

正式pilotは84条件×3 streams、4つのnested-prefix N候補。N262144は235/252 ready、最大価格SE .00216235で規定 .002を超えた。N1048576は252/252 ready、event active最低905、最大価格SE .00106944。条件を削らず最小の全点ready Nを固定した。

主640教師は320 analytic/320 ready。独立reviewは全教師・全336参照・全4680 Hermite node・全6 fitを検算した。追加freshは事前宣言したATM12条件×N1048576、15推定量を別seedで生成。全180元slotを保持し、150 supported、18 analytic deterministic、12 naive Gamma負対照と記録した。追加標本をmain教師や選択へ混ぜていない。

Poisson tailの上界、QUADPACKの誤差推定、MCの6SE診断を区別する。6SE比較は同時被覆保証・一般的不偏性の証明ではない。tiny-h Gamma差分には価格roundoffの増幅が入り、finite-h biasを純粋な離散化biasと呼ばない。

## NNと強い基準器

価格・Delta・K Gammaの固定同時条件：
price absolute .01、Delta absolute .005、K Gamma absolute .05 + relative .05。

| seed | price-only raw Delta RMSE | DML raw Delta RMSE | raw同時PASS点 price-only / DML | safe同時PASS点 price-only / DML |
|---:|---:|---:|---:|---:|
| 11 | .18492999 | .06315641 | 0 / 0 | 193 / 156 |
| 29 | .21094848 | .07351568 | 0 / 0 | 191 / 190 |
| 47 | .19411079 | .04649242 | 0 / 4 | 182 / 169 |

各分母は336。safeの通過点の多くはmixtureへのfallbackであり、raw NNの精度保証ではない。全raw価格・物理Delta/Gamma、48 time/event/ATM bucket、失敗、10契約境界/OOD診断を保持する。満期ATMの通常Delta/GammaはNaNと理由を保持する。

Hermiteは同じ価格をspotで2回微分するC² quintic、spot65/time36相当（33基本nodeと時計/pulse境界）。全336点が各成分・同時条件を満たした。価格最大誤差 .00046117、Delta最大 .00055332、K Gamma最大1.24608。Gammaは相対項を含む各点の許容差で判定し、最大誤差だけを絶対閾値 .05と比べない。

[採否と全fit精度](assessment.json)／[主独立レビュー](MAIN_REVIEW.md)。

## 実測費用

| 観測 | 秒 | 定義 |
|---|---:|---|
| 正式pilot CLI | 12.60960 | 全pilot生成・検算・保存を含む |
| 主実験 construction CLI | 46.08508 | import、pilot再検査、全教師、6 fits、比較、計時、検算、保存 |
| 主カテゴリ合計 | 39.22017 | 上のCLI内の測定カテゴリ。CLIへ加算しない |
| 主serialization | 4.18468 | 上のCLI内の保存。カテゴリとは別、CLIへ加算しない |
| 新規プロセス artifact-backed pipeline | 18.15101 | import、実pilot検査、archive読込、全saved数値検査、準備、固定2点の全Greeks返却 |
| 上のarchive読込 | .89992 | pipeline内の成分 |
| 追加fresh CLI | 26.44445 | startup・12条件全推定量・検算・保存 |
| 追加fresh function | 26.15482 | fresh CLI内の成分、serialization3.79527を含む |
| fresh saved replay | 14.59934 | 生成とは別プロセス、乱数/学習禁止の再検査 |
| 失敗したcold collector | 18.02682 | root計測collectorのschema KeyError。独立した研究費用として保持 |

新規プロセスの観測は**保存物からの検査付き利用**であり、OS disk cacheをflushした測定ではない。offline教師/学習を毎回作り直すcoldと同一視しない。主construction CLIは別に実測済み。主費用の約29秒はvalidationとgeometry内の繰り返しpilot検査で、教師・学習時間だけをCLI全体と呼ばない。

元recordのpending5とacceptedFalse/teachingAcceptanceFalseは不変。[外部assessment](assessment.json)に実receipt・採否をbindして解消を表示する。元JSONを書き換えて成功扱いしない。外部5IDの解消はpilot初回生成・独立review・archive復元等の全研究費が確定した意味ではない。coldのpilot_freezeは当該プロセス内の再検証費用だけであり、全研究費総額を捏造しない。scalar価格だけを返す処理とprice/全Greeks/routesを返す処理の速度を比べない。

保存されたwarmup1/7 repetitions、batch1/32の全448 timing slotを検査した。精度同等性が成立しない全NN fitのpaybackはeligible=False、Q=unknown/未定義。費用からQを推定していない。

## 保存・再利用

| 配列 | bytes | 各保管庫の独立復元 |
|---|---:|---|
| pilot | 341054854 | 両copy数値PASS |
| main | 177133184 | 両copy数値PASS |
| fresh | 193825173 | 両copy数値PASS |

[主manifest](reference_manifest.json)／[fresh manifest](fresh_manifest.json)／[pilot manifest](pilot_manifest.json)。
[主復元](main_cas_validation.json)／[fresh復元](fresh_cas_validation.json)／[pilot復元](pilot_cas_validation.json)。
SHAは原始保存物のidentity用。金融値の一致は許容誤差つきで検算する。

[実notebook](short_maturity_dml.ipynb)は保存物だけを読み、乱数・optimizer・訓練・networkを禁止したkernelで3図を生成。実3PNGを目視し、labels・元分母・単位・全fit・unknown・外部採否の表示を確認した。
[実行receipt](notebook_execution.json)／[表示確認](NOTEBOOK_VISUAL_REVIEW.json)。

重いNPZをGitへ追加していない。両保管庫からmanifestを使って復元する。fresh helperを別checkoutで使う場合、保存源に明示的な `--source` を渡す。計測stopwatchの実測時byteは別TXTで保持した。

## 検証の範囲と次

[主数値review](MAIN_REVIEW.json)、[pilot承認](PILOT_REVIEW.json)、[金融source固定](freeze_check.json)、[最終ruff](FINAL_RUFF.json)を保持する。最終関連3suite7998 PASS/6 skip（443.32秒）、19Python ruff/format PASS。[実測](FULL_SUITE.json)。tracked release/最終独立208checks PASS・重要0。[最終受入](validation.json)／[独立最終レビュー](REVIEW.json)。main反映は未実施。

本v1は実市場のSPX/SPXW、official holiday/early-close calendar、Bates/PIDE/rough、Gamma loss、vol/quote Greeks、動的ヘッジを承認していない。次は[同一較正条件の動的モデル横断ヘッジ](../../RB-F04/dynamic_hedging/README.md)、その後は多曲線risk/P&Lと増分XVA＋IM・資本。短期v1完了で全研究ロードマップの完了とはしない。
