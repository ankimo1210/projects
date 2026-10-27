# DSINC 全体の独立レビュー

2026-10-27。branch `claude/dsinc-american` の全体を、opus が独立にレビューした（[実施計画](../../docs/superpowers/plans/2026-10-25-dsinc-american.md)のTask 8のStep 6にあたる）。レビュアーは実装者とは別のagent（opus）で、差分・run root・README・台帳を読み、一部を作業用に再計算した。

- 範囲：`cb39e4d5669fb85416cc77228e85aa309b4904c1..9b45bb82ad21607d33c94f8d7e5ca0e75e180ba2`。`cb39e4d5`はmainで、`9b45bb82`はmainの結果とREADMEの是正まで。
- レビューに渡した差分：`review-final-cb39e4d5..9b45bb82.diff`（8,164行。データ・PNG・上流原本は除き、統計だけを付けた）。sha256 `cde67f79356b61d8de695bff33441fe0632c919a70a38138c75d8ef7606cd06b`。
- 主run root：`/home/kazumasa/projects/_data/johnhull/DSINC/main-20261027T001446Z`。通ったpilot：`/home/kazumasa/projects/_data/johnhull/DSINC/pilot-20261026T235315Z`。どちらもGit管理外で、レビューも修正も読むだけで、書き換えていない。

## 判定

**With fixes**。致命的な指摘は0件、重要な指摘は3件、軽微な指摘は14件。凍結ファイル（`run.py`の`SOURCE_FILES`）の変更も、spectral・FDの再計算も要らない。直したのは、(1)費用の図のFDの線の順、(2)READMEの説明不足2点、(3)小さな文書の不一致である。修正はこの文書と同じコミットに入っている。

## レビューが再確認したこと

- 数式：減衰変換k=−ω−iχ、min(1,e^x)の変換−1/(s(1+s))と留数項、g·1{x≤b}−rdの変換、EEPの再帰（t_Nは半重み、t_0は重みなし、端点dt·g/4は境界の式だけ）、残差R_n。独立に導出して、実装と一致した。
- 根探し：計画のTask 5の擬似コードどおり（幅.1・.2・.3・.5、δ、最上位の+→−交差、ambiguous_contact、wrong_orientationで停止）。
- 独立FD：IE半歩4回＋CN、LU 1回、Ikonen–Toivanen。spectral側をimportしない。
- gates：純関数。D-3の参照、軸の収束、境界gate、D-7の`select_level`は計画どおり。
- 再現性：mainの`replay`は`{"match": true, "differences": []}`。`verify_freeze`はリポジトリとrun rootの両方のmanifestでOK（`d3685d17…`）で、`freeze_sha256`が一致。`results/results.json`はrun rootの`results.json`とバイト一致（export）。`SOURCE_FILES`は`7551a37f`から不変で、上流のhashもmanifestどおり。pilotとmainに共通のjob 28件は、価格28件と配列18組がどちらも一致。0化の有無で、S0のT=.5・T=1の配列とタイミング以外の診断がビット一致。
- 判定の再計算：recordsから再計算して一致した。`reproduction_label`は`constrained`、paper_matchの最大差は3.43e-7。T=.5はS0を採用（隣の段2.31e-6、独立FD 4.04e-6、感度2.23e-6、上下界の最小-1.54e-5・S/K=0.832）。T=1は採用なし。境界gateは両満期でpass（1.027セル・3888節点、0.511セル・7728節点）。FDのずれ1.0000000000000675は、上限1に許容1e-9を足した範囲の内。88件はok 63、`not_run_condition` 23、`pricing_failure` 2。jobのwall合計は781.8秒で、okの実測は見積もりの0.37〜0.87倍。
- 文書とテスト：READMEの約40か所の数値と、費用表のFDの行が一致。DSINCのテスト137件、`test_docstrings.py`と`test_model_index.py`の933件、`ruff check`・`ruff format --check`は、レビュー時点でクリーン。

## 指摘と対応

対応の区分：**修正**はこのコミットで直した、**文書**はREADMEなどに書いた（コードは変えない）、**既知**は直さずに記録した。

### 重要

| # | 指摘 | 対応 | 場所 |
| --- | --- | --- | --- |
| 1 | 費用の図でFDのx格子の線が誤った順（base→1921→481→961）に結ばれていた。`results.json`は`sort_keys=True`で保存されるので、dictの順がアルファベット順になる。READMEの説明（base、481、961、1921）とも合わず、テストでも検出できなかった。 | **修正**。FDはbaseの次にx節点数の昇順、spectralはS0・S1・S2の順に、`plot.py`で明示した。`plot.py`のdict順への依存を監査し、細分の図の行（感度の名前）も同じ原因でアルファベット順だったので、protocolの順にした。ほかの反復は`sorted`・リテラルのtuple・キー参照で、順に依存しない。`sort_keys=True`で保存した合成の結果で線と行の順を検査するテストを足した。3枚のPNGを`results/results.json`から描き直した（境界の図はバイト一致のまま、費用の図と細分の図が変わった）。run rootの`results.json`から描いても、3枚ともバイト一致。 | `plot.py:44-48`（`SENSITIVITIES`）、`:98-115`（`_numbered`、`_ladders`）、`:125`、`:342-343`。`test_dsinc_runner.py:399`。`figures/`。README「図」（:283-:295） |
| 2 | T=1の失敗の原因（S1が[640,1280]のパネルを12点で積分すること）がREADMEに書かれていない。load-bearing：yes（T=1の判定を決める）。ただし設計どおりの値で、凍結コードの欠陥ではない。 | **文書**（再実行なし）。仕組み、recordsの5つのjobの多重交差と交差の距離、14件がすべて12点の[640,1280]のパネルを持つこと、S1−S2の差とそのうち16点で消える分を、run rootの記録から再計算して書いた。D-1の影響は、S0は確かめた（crossing_lowerの差は0）、S1は未確認（jobの失敗）と書き分けた。Ruling T7R-bの「load-bearingなら再実行」は、機械的には当てはめない：設計の値の帰結で、欠陥ではない。変えるなら新しい逸脱（D-8）で、ユーザーの承認とpilot→freeze→mainのやり直しが要る（Ruling F-a・F-b）。 | README「T=1が未達になる理由」（:197-:217）、「未検証の範囲」のT=1（:301）と多重交差（:313）。「T=1への道」は下記 |
| 3 | T=.5の上下界のpassが分散格子の位置に依存するが、書かれていない。D-7は各段のbase jobにだけ上下界を当てる。 | **文書**。S0のT=.5の変種に`gates.bounds_check`を記録の価格で当て直し、offset_plus_half・offset_minus_halfが-2.606e-5（S/K=0.834、許容超え）、baseが-1.539e-5、time_x2が-7.10e-6、points_plus4が不変であることを書いた。T=.5の余裕は0.46e-5で、v0への補間のほか、分散格子の位置と時間刻みにも依存する。判定は変わらない。レビューが挙げた5.3e-10はoffset_plus_halfの値で、offset_minus_halfは5.76e-10。レビューが挙げていないvar_next（T=.5で-1.88e-5、許容との差1.2e-6）とT=1の変種（time_x2 -1.30e-5、var_next -1.76e-5は通る）も、同じ手順で再計算して足した。 | README :185、「未検証の範囲」の「境界近傍のspotでの補間誤差」（:303-:310） |

### 軽微

| # | 指摘 | 対応 | 場所 |
| --- | --- | --- | --- |
| 1 | READMEの「診断の全出力がビット一致」はタイミングの診断を含めると不成立。0化の時間は作業用の計測で、run rootにない。「0にして保存する」はディスクへの保存に読める。 | **修正**。「タイミング以外の診断」、「作業用の計測（記録なし）」と書き、「0に置き換え、以後の計算にはこの行列を使う」にした。 | README :55 |
| 2 | README「783秒」はcontrollerの作業用ログにしかない。 | **修正**。781.8秒（`accounting.wall_seconds`）を残し、783秒はrunnerが画面に出した値で記録にないと書いた。 | README :78 |
| 3 | 「独立レビューはこの後」が古い。 | **修正**。レビュー済み（With fixes）と、この文書へのリンクにした。 | README :5。設計の状態行、計画の状態行も同様 |
| 4 | Deltaの幅4.1e-7がどのspotか書かれていない。 | **修正**。S/K=.9の値で、S/K=1と1.1ではspectralが2.0e-6と2.0e-6（FDも2.0e-6と2.0e-6）と書いた。 | README :302 |
| 5 | ROADMAPのDSINCのテスト件数と全体の件数が古い。 | **修正**。全体のsuiteを修正後に走らせて、件数を写した。レビュー済みと、次はユーザーの統合の判断と任意のD-8であることも書いた。 | `ROADMAP.md` :26、:120 |
| 6 | 未実行の感度に×を描く変異が、既存のテストで生き残る。 | **修正**。左のパネルに×の線がないことを検査した。`if name not in found: continue`を外して欠けた値をなしとして描く変異は、追加前のテストでは通り、追加後は落ちる。 | `test_dsinc_runner.py:371-372` |
| 7 | 設計§1の「着手済みと扱わない」に、2026-10-25時点という限定がない。 | **修正**。2026-10-25時点の依頼範囲と、実装が2026-10-26に始まったことを足した。 | 設計 :7 |
| 8 | 計画の「従来どおり」に指す先がない。 | **修正**。直前の提案の規則（False・欠落・Noneは不合格）を指すようにした。 | 計画 :108 |
| 9 | 計画の「δはm点則より常に細かい」は誤り。 | 計画の文は**修正**。コードは**既知**。最初のbracketが0で切られてhi−loが.1をわずかに超えると、δはS1で最大1.22%、S2で最大0.61%粗い（最上位の節点をω_maxとすると0.75%と0.35%）。S0は影響なし。この数値は`protocol.json`のS1・S2の設定とGauss–Legendreの節点から再計算した。コード（`_dsinc_american.py:116-121`）は凍結で、load-bearing：no（下記「レビュー時の作業用の計測（記録なし）」の最後の項目）。 | 計画 :1230 |
| 10〜14 | 下記「既知の項目」 | **既知** | 下記 |

## 既知の項目（修正しない）

凍結ファイルは、Ruling T7R-bにより、load-bearingでなければ直さない。以下はどれも、判定にも、READMEの数値にも影響しない。

### 最終レビューの軽微な指摘 10〜14（凍結ファイル）

- 10：`run.py:1550-1567`の`replay`は、protocolと配列のhashは照合するが、`SOURCE_FILES`のhashと`freeze_sha256`は照合しない。`verify_freeze`で別に確認した。
- 11：`run.py:478-484`、`:779`。RSSは事後の`ru_maxrss`で判定する。最大は688 MiB、上限は2 GiBで、超過は起きていない。
- 12：境界gateの`max_root_residual`は、二分法の受理条件で上限が決まる量で、独立な検査ではない（台帳:102と同じ）。独立にするには、根で価値一致を`inverse_sum`から評価し直す。
- 13：`run.py:1335`。T=1の`independent_validated.boundary`の`"pass"`は、採用されていないS0の値である。READMEの「判定の要約」と「境界gate」に、採用段ではないと書いた。
- 14：T7R-dの凍結docstringの細部。`gates.py:241-243`（「, which names the level」の読み方があいまい）、`gates.py:221`（注釈がdictで、Mappingではない）、`_dsinc_spectral.py:226-227`（測定した1つの場合を、条件を付けずに述べている）。

### 台帳から持ち越した項目（トリアージはkeep as known）

行番号は[台帳](../../../.superpowers/sdd/2026-10-25-dsinc-american/progress.md)のもの。

- :59 `test_dsinc_types.py`：expiry=0・rf=0の受理、listからtupleへの変換、`canonical_digest`のndarrayとNumPyスカラの枝、`FAILURE_CODES`と`PricingResult`のフィールド名を固定するテストがない。
- :68〜:72 `heston_baseline.py`：(:68)出力の一部・clip_low・許容での停止・safe_nanの非有限側にテストがない。(:69)referenceのkeyの検証が両solverを走らせた後（:318-327、呼び出し:440）。(:70)上流`_heston_cf`の|lam1|<1e-12の置換を数えていない。(:71)カウンタの意味がレポートにしかない。(:72)adapterがT=0でValueErrorにし、`dsinc.extremes`を足す（ブリーフのkey一覧との差）。診断専用で、判定に使わない。
- :75 計画の件数：Ruling T2-bでTask 2が17件になり、計画の「残りの14件」「16」「99」が古い。
- :76 `heston_baseline`のdrift guardは、`# audit`の行そのものと、他の上流メソッドの新しいoverrideを見ない。
- :81・:82 Task 3のテスト：追加分（非一様・2次元の格子の拒否、fixtureの配列、expiry=0のbuild、読み取り専用の配列、T=0でpropagatorsを渡す場合）にテストがない。`test_european_rejects_bad_inputs`に`match=`がなく、strike=100のケースは例外が出ないことしか見ない。
- :89〜:91 FDのテスト：障害物のテストの断言が構成上ほぼ真で、厳密なamerican > europeanがない。`left`（x_min側だけと結合する最初の内部行の残差）とブリーフを超えた検証にテストがない。FDの解に`isfinite`の検査がない（NaNは伝わるが、gateが落とす。全FD jobはok）。`reference_fd.py:117`・`:240`が100字を超える。`size`が2つの意味で使われる（:236、:336）。
- :97 `scan_spacing`のコード（`_dsinc_american.py:116-121`）：δがm点則より粗くなる場合がある（上のMinor 9）。計画の文は直した。
- :98 S1・S2の多重交差の数：計画のD-1の数（3,016と3,861）と実装の数（T=.5で3,371と5,253）が違う。最大のvは1.87e-3と3.02e-3で、窓の下限0.01より下。S0は一致する（58）。S1・S2の数は、重要な指摘2の雑音で決まる。
- :102 境界の根の残差が独立でない（上のMinor 12）。
- :103 見積もりの範囲：同一設定の見積もりは、同じプロセスの中のsetup+solve（計画の式）で、インタプリタの起動・import・保存を含まない。S2のT=1の見積もり152秒は、見積もりの上限180秒まで約15%の余裕。実測は見積もりの0.37〜0.87倍だった。
- :104 のうちNaN・Infが0化で触れられないことを固定するテストがない（READMEの部分はMinor 1、docstringはT7R-aで直した）。
- :105・:106 `_dsinc_american`：一部だけ失敗するスライス、空のspots、`premium_with_boundary`の形の検査、`crossing="lower"`の通し、nonfiniteがambiguousより上位であること、bracket端と二分法での非有限、`_SliceResidual`と`inverse_sum`の一致にテストがない。`premium_with_boundary`が契約とpropagatorsの整合（dt·n_timeとexpiry）を検査しない。スライスごとに`at`の呼び出しが1回余る（:540）。ruffが折り返した行末コメントがある。
- :117 `gates.py`：追加分（`root_failure_in_window`、`fd_unconfirmed`、`no_targets`、`paper_match`が全部`not_available`のときのValueError、`bounds_check`の`*_spot`キー、`select_level`のNone・非有限の経路、`axis_convergence`の`order_out_of_range`）にテストがない。数値の文字列が`max_root_residual`の検証を通る。`select_level`の型ヒントがdocstringより狭い。`axis_convergence`のh検査が最初の要素だけを読む。`fd_reference`のndim検査は何もしない。`boundary_gate`のreasonsがpassでも空でないことがある（geometry_invalid）。判定は再計算で一致した。
- :125 `plot.py`が`gates`の`_edge_at`と幾何maskを複製している（図だけがずれる危険）。ほかに、子プロセスがrootを`--out`の2階層上から決めて`<root>/jobs`を確かめない（`run.py:1585`）、採用段がないときにS0の境界の配列を書き出す（図に必要）、`freeze_manifest.json`と`pilot_summary.json`がcompact JSONで1行、T6-bの147点bounds・`independent_validated`・`nonmonotone_effect`・`reproduction_label`の組み立て・`evaluate("pilot")`・`basis()`・`not_run_condition`だけの場合・実サブプロセスの`pricing_failure`のテストがない、1.0秒のfixture wallが負荷で不安定になりうる（`test_dsinc_runner.py:97`）、`plot.py`に100字を超える`# fmt: skip`の行がある、感度のpanelのリストをaliasで書き換える（`run.py:189, 200, 210`）。
- :129 freeze周り：`source_sha256`のないsummaryは照合されない（CLIのsummaryには必ず付く）。hashをrosterの後に取るので、600秒以内のpilot中の編集は見つからない。`try`が`_record`も囲むので、`_record`の不具合がlauncherの失敗として報告される。
- Parked 7R #6：S1の条件付き感度は、S1が上下界でも落ちるときも走る（予算だけの問題。D-5は変えない）。#7：runnerのテストが`arrays=None`を使う（boundsは記録の価格だけで決まる）。
- T7R-d：凍結docstringの細部（上のMinor 14）。
- T1-a：`51a79a3c`のトレーラーが、Sonnetが書いたコミットにOpusの行を付けている。直すには履歴の書き換えが要り、ユーザーの承認事項。

台帳のほかの項目は、直した、または解決済みである：:60は設計:7（Minor 7）、:61・:83はT7R-a、:84・:160は先のコミット、:175の5項目はMinor 1〜6。

## レビュー時の作業用の計測（記録なし）

レビュアーが、凍結したモジュールをimportし、1パネルの点数だけを変えて行った計測である。run rootにもリポジトリにも記録がない。値はレビューの報告から写したもので、このコミットでは再計算していない。READMEとROADMAPの数値には使わない（READMEは、recordsから再計算できる値だけで書き、この節を指す）。

- 節点0（v=2.0e-4）の最初の歩で、R(−0.1)=−1.5e-5、R(−0.2)=−1.1e-4。bracketの下端でRが負になる（正でなければならない）。
- bracketの幅が0.3まで広がり、そこに43個の交差がある。
- `crossing_lower`は遠い交差（−0.294、次に−0.589）を選び、3歩目で59節点が`wrong_orientation`になる。
- `time_x2`は、採用した根より0.125下の、雑音による零の連続で`ambiguous_contact`になる。
- 24点・48点で再計算すると、失敗した2本（`crossing_lower`、`time_x2`）はどちらも完走した。baseは12節点・spread 0.0037、`time_x2`は248節点・0.0135。`time_x2`とbaseの価格差は最大5.3e-7。24点と48点のどちらの値かは、レビューの報告に分けて書かれていない。
- 走査格子をずらしても、`crossing_lower`の失敗は再現した。失敗の原因は、走査の刻みδの粗さではない（Minor 9のload-bearing：noの根拠）。

## 判断しなかったこと（レビュアーが範囲外とした項目）

- 論文PDFの式との一字一句の対応。独立導出と、表との照合（最大差3.43e-7）で確認した範囲に限る。
- 閾値とD-1〜D-7の妥当性（ユーザー承認済み）。
- 上流Heston監査の網羅性。
- 全体テストの再実行。
- `ru_maxrss`のLinux以外での意味。
- 上流コードのMITライセンス。
- Codex側のbranch（Ruling P1）。
- パラメータの経済的な意味。
- 速度の主張（READMEは速度を主張していない）。
- v0補間の代替案で、境界近くの上下界のdipが消えるか。
- S1を16点・24点に変えたときに、T=1の全gateが通るか。計算したのは、失敗した2本とbaseだけである。

## T=1への道（ユーザーの判断）

- T=1の未達は、凍結した規則の下での正しい判定である。規則・閾値・根探しを変えて通すことはしない。T8-cで最後に示す予定だった「根探しの変更」は、雑音から決まった根をそのまま通すことになるので、示さない（Ruling F-b）。
- 通すには、S1の1パネルの点数を増やす（D-8、案。例：12→16または24）。設計§6のS1の設定の変更なので、新しい逸脱で、ユーザーの承認が要る。承認後に、pilot→freeze→mainをやり直す（READMEの「再実行」：pilot約5分、main約13分。S1の費用は点数とともに増えるので、mainの予算30分に収まるかは、新しいpilotの見積もりで決まる）。
- 手がかり：recordsでは、S1を16点にしたjob（points_plus4、T=1）の交差の距離は0.098で、12点の0.293より小さい。作業用の計測では、24点・48点でbaseの距離が0.0037になった。
- 確かめていないこと：16点・24点のS1が、T=1の全gate（隣の段、参照、感度11本、上下界）を通るか。通らなければ、D-8でもT=1は未達のまま残る。

## このコミットでの確認

- 費用の図のFDの線：`sort_keys=True`で保存した合成の結果で、旧`plot.py`では線がbase、1921、481、961の順になって落ちる。修正後は通る。細分の図の行がprotocolの順になることも、同じテストで見る。
- 3枚のPNGは、`results/results.json`とrun rootの`results.json`のどちらから描いても、バイト一致した。境界の図はこのコミットの前後でバイト一致で、費用の図と細分の図が変わった。
- DSINCのテスト（7ファイル）：138 passed（types 33、baseline 17、spectral 22、reference 11、american 18、gates 15、runner 22）。`test_model_index.py`と`test_docstrings.py`：933 passed。
- 全体：`pytest -q johnhull/hullkit/tests johnhull/report/tests`（RB-F04の`test_paths_match_the_rbf04_v1_simulators_at_every_observation`、`test_local_tangent_matches_a_finite_difference_of_the_scheme`、`test_small_run_hedges_better_with_more_frequent_rebalancing`の3件を`--deselect`。gitignoredな`reference.npz`がmainのcheckoutにしかない：Ruling P2）は、7880 passed、6 skipped、3 deselected、442.75秒。
- `ruff check`と`ruff format --check`は、変更したPythonファイル（`plot.py`、`test_dsinc_runner.py`）で問題なし。`git diff --check main...HEAD`は空白の警告なし。
- `SOURCE_FILES`は、このコミットで変えていない（`git diff --name-only 9b45bb82 HEAD`に含まれず、10本のhashはpilotが記録した値と一致する）。
