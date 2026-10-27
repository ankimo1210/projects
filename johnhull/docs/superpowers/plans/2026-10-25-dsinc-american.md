# DSINC American Put Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 市場データを使わずに、公開Heston版DSINCを監査し、論文の3/2モデルAmerican put（European・EEP・行使境界）を固定周波数spectral法で実装して、論文の印刷値と独立FDの両方に照らして機械判定する。

**Architecture:** hullkitにprivateモジュールを3つ置く（入力型、固定周波数の伝播とEuropean、EEP再帰と節点境界）。`johnhull/research/DSINC/` には、上流原本・監査adapter・独立FD・判定関数・予算付きrunnerを置く。独立FDはspectral側をimportしない。pilotで費用と達成性を測ってfreezeし、mainはfreezeを検証してから実行する。

**Tech Stack:** Python ≥3.12、既存のNumPy 2.4.6 / SciPy 1.17.1（依存は追加しない）、pytest、Matplotlib（図のみ）。float64/complex128、CPU 1 thread。

**Spec:** [2026-10-25-dsinc-american-design.md](../specs/2026-10-25-dsinc-american-design.md)。本計画は設計からの逸脱D-1〜D-7を記録する（§1。D-6・D-7はpilotが判断点で止まった後に追加した）。

**状態（2026-10-27）:** 計画を2026-10-26に全面改訂した。旧版は概要版で、Opus承認時のsha256は677bfdb2…、承認後の追記版は2ba13c82…。D-1〜D-5は2026-10-26にユーザーが承認した（改訂版のOpus再レビューなし）。設計本文への反映はTask 1で行った。実装は2026-10-26に始まり、Task 1〜6は完了した。Task 7のpilotは2026-10-26に判断点で止まった（`mandatory_jobs_ok`だけが落ち、S0のdomain_expandが根のbracket幅の外で`missing_sign_change`になった。S0のT=1ではboundsも不合格）。ユーザーは2026-10-27にD-6・D-7を承認し、実装した（Task 7R）。pilotは2026-10-27にやり直して通り（UTC 2026-10-26 23:53のrun、42件すべてok）、mainのprotocolをfreezeした（Task 7は完了）。mainは2026-10-27に実行した（88件、jobのwall合計781.8秒。T=.5はS0を採用、T=1は採用段なし、`reproduction_label`は`constrained`）。独立レビュー（Task 8のStep 6）は2026-10-27に受け、判定はWith fixes（致命的な指摘は0件）で、指摘は同日のコミットで直すか記録した（[REVIEW.md](../../../research/DSINC/REVIEW.md)）。次はユーザーによる統合の判断（Step 8）。任意で、T=1のためのD-8（S1の1パネルの点数を増やし、pilot→freeze→mainをやり直す案）がある。実行方法はsubagent-driven。[レビュー記録](../reviews/2026-10-25-dsinc-american-opus.md)。

## 0. 計画前に確かめたこと

使い捨てのspike（研究コードではない。scratchpadに置き、repoには入れない）で、論文値の再現、テストの閾値、費用を実測した。

| 項目 | 実測 | 計画での扱い |
|---|---|---|
| S0、T=.5 | European [.10255734, .04722426, .01910466]、American [.10760094, .04866224, .01949905]。Table 3(b)・Table 4と6桁で一致 | Task 5のsmoke、Task 7のgate |
| 時間2倍（N=200） | [.107599, .048660, .019497]と6桁で一致 | 診断 |
| S0、T=1 | American ATM .06366789（Table 9は.063668） | gate |
| S0のexp(A₀Δt) | 最小成分−0.0316、行和誤差3.9e-15。Pe=\|b\|h/a²の最大14.4、Pe>1は45節点 | scheme_nonmonotoneは必ず記録される |
| 境界の多重交差 | 下記D-1 | D-1 |
| FDの各軸 | 下記D-2・D-3 | D-2、D-3 |
| 境界照合 | 下記D-4 | D-4 |
| 費用（naive実装、T=.5） | S0 9.2秒（setup 3.8秒）、S1 34秒、S2 127秒（setup 30秒）。FD (1921,101,150) 5.7秒/786 MiB、T=1のFD (1921,101,300) 11.5秒、(961,101,1200) 18秒 | ベクトル化が必須。D-5 |
| 制御計算 | CIR平均の相対誤差6.57e-5/2.91e-5/1.63e-5（次数2.0）。Heston制御≤2.1e-7（ρの符号を反転すると3.9e-3）。定数分散European: χ=.5で≤4e-8、χ=.25/.75で≤2e-6。payoff変換≤1.5e-9。平坦境界EEP≤2.4e-7。2段American: 根≤7.1e-7、価格≤4.1e-8。FD定数分散: EU≤2.2e-6、AM≤4.0e-6（CRR 4000段比）。Neumann行の次数1.997。FD作用素の次数1.986 | テストの閾値 |
| 上流Heston | DSINC既定1.1秒、FD既定5.5秒。H00の結果はDSINC 13.663324/13.685393、FD 13.662246/13.683896。Nom=120ではraw K·EEP=−0.0778が0に切り上げられ、PA=PEになる | Task 2の監査テスト |
| 境界近傍でのv0補間 | S0で、American−payoffの最小値が−1.54e-5（S/K=.832）。小設定では−1.0e-4 | Review Focus 1 |
| 短満期 | cutoff 40ではT=.01でEuropeanが−1.1e-3（負の価格）になる。S0のパネルなら−3e-8 | Review Focus 4 |
| 論文の格子のFD | (241,101,150) [.10757492, .04861749, .01946947]、(481,201,300) [.10759252, .04864814, .01948956]。Table 4のFD列と≤5.1e-7・≤4.8e-7で一致 | Task 7の診断 |
| 計画を書いた後の確認（spike10） | 小設定T=.01・N=1: European [.09910161, .00902134, −.00109279]、下限との差の最小はS/K=1.1の−1.093e-3、境界は24節点ともsingle。小設定でroot幅を1e-4だけにすると、最初の時刻で24節点ともsign changeなし。S0の走査126点（S/K .70〜.95）でAmerican−payoffの最小−1.539e-5（S/K=.832）、価格は単調減少。CIRの相対誤差6.574e-5/2.910e-5/1.634e-5。Task 4の仕様どおりに組んだFDのbase水準は計画の値と≤4.6e-9で一致。障害物のテスト設定で相補性の積0・解の残差5.6e-16。接触端は暦の行0〜7で単調、行8はNaN | Task 3〜6のテストの値 |

## 1. 設計からの逸脱（2026-10-26にユーザーが承認）

### D-1 境界の多重交差は失敗にせず、最上位の交差を採る

- 設計§4: bracket内に複数の符号変化があればmultiple_rootsとして失敗にする。
- 証拠: S0（T=.5）では、16,000 node-stepのうち58件でbracket内に交差が3つあった。いずれもv≤6.75e-4、満期直前の数step、交差の間隔≤.0094（Gibbs振動の尺度π/640=.0049の約2倍）。最初に計算するstep（n=99）から起きるので、設計の規則のままではS0が1歩目で止まり、論文値と6桁で一致する設定を評価できない。最下位の交差を選んでも価格の差は1e-8未満。S1（12点）では48,000件中3,016件（v≤1.94e-3、間隔は最大.37）、S2では128,000件中3,861件（v≤3.0e-3）。逆向き・符号変化なし・零の平坦部は、すべての設定で0件だった。
- 提案: putの行使域はx≤x*なので、x*を「残差Rが正である最上位の点」、つまり最上位の+→−交差と定義する。状態は`multiple_crossings`として記録し、失敗にしない。代わりに次の歯止めを置く。
  1. 最下位の交差を選ぶ個別感度`crossing_lower`を、他の感度と同じ5e-6のgateにする。
  2. 境界照合の窓（t/T∈[.1,.9]、v∈[.01,.16]）の中に`multiple_crossings`が1点でもあれば、境界gateをFAILにする。
  3. `ambiguous_contact`は、|R|≤root_residual_tolの走査点が2点以上続く場合に限る。交差点上の零が1点だけなら交差として扱う。
  4. 逆向き・符号変化なし・非finite・反復上限は、設計どおり失敗にする。
- 影響: 失敗の範囲が狭まる（緩和）。価格への影響は1.のgateで測る。

### D-2 独立FDのx軸を4水準にする

- 設計§6: x={241,481,961}。
- 証拠（T=.5、広い分散領域、他の軸はbase）: Americanの変化は、241→481が[2.0e-5, 3.1e-5, 1.9e-5]、481→961が[5.2e-6, 7.6e-6, 4.7e-6]で、最終差が基準の5e-6を超える。1921を足すと、961→1921は[9.0e-7, 1.9e-6, 1.2e-6]（観測次数2.5/2.0/2.0）。Europeanの最終差も1.7e-6以下。費用は(1921,101,150)で5.7秒・786 MiB、T=1で11.5秒。
- 提案: x={241,481,961,1921}とし、次数は最後の3水準から求める。
- 影響: 厳格化。x=1921のAmericanはT=.5で5.7秒、T=1で11.5秒（実測）。

### D-3 参照値の作り方と収束判定を決める

- 設計§5/§6は「軸別に3水準」と「reference最終細分差≤5e-6」を定めるが、参照値の作り方と次数の扱いは定めていない。
- 証拠: 分散軸の変化は、101→151が[1.9e-6, 3.2e-7, 6.1e-7]、151→201が[2.0e-7, 4e-8, 2.4e-7]。観測次数は5.3/5.0/1.7とばらつく。変化が基準の1/20以下と小さく、v0への補間位置の影響が見えるため。時間軸は[8.3e-7, 4.9e-7, 7.4e-7]→[1.9e-7, 2.0e-7, 2.7e-7]（次数2.1/1.3/1.5）。x領域を広げたときの差は0。
- 提案:
  - 参照値はP_ref = P_B + Σ_軸(P_軸の最細水準 − P_B)とする（Bは(241,101,300T)）。
  - 各軸は、最終差≤5e-6で、かつ次のどちらかを満たせば収束とする。
    - 最終差≤5e-7（基準の1/10で、判定を動かさない大きさ）。
    - 変化が縮小し（|最終差|<|前の差|）、観測次数が[1,3]に入る。
  - 領域を広げたときの差も≤5e-6とする。
  - 次数は、等比でない刻みhについては根を解いて求める。外挿値は診断としてだけ出す。
- 試算: T=.5のP_refは、American [.10759984, .04865818, .01949554]、European [.10255711, .04722374, .01910423]。S0との差はAmericanで≤4.1e-6、Europeanで≤5.2e-7。
- 影響: 判定できるように定義を足す（緩和ではない）。

### D-4 境界gateは専用の細かい時間刻みのFDで判定する

- 設計§5: 収束を確認したFD格子のbracketから2dx以内。
- 証拠:
  - S0とFD (961,101,300T)の比較では、最大の外れが.0092（3.7dx）、2dx以内は96.5%だった。spectralの境界は常に下側にあり、FDの時間方向の遅れによる。
  - FDの時間刻みを600T/1200T/2400Tにすると、最大の外れは.0047/.00257/.00114で、すべて2dx以内に入る。
  - FDの境界の移動は、600T↔1200Tでも1200T↔2400Tでも1セル（.0025）。spectralのN100↔N200では8e-5。
- 提案: 境界gate専用に、American FD (961,101,1200T)を主、(961,101,600T)を確認用として走らせる。dx=.0025、許容は2dx=.005。窓の中で確認用との接触端の差が1セル以下なら「収束確認済み」とする。比較する時刻は、k·N_fdがN_specで割り切れる時刻だけ。
- 影響: 判定できるようにするための追加（厳格化）。主の(961,101,1200T)はT=1で18秒（実測）。確認用は時間刻みが半分なので、その約半分。

### D-5 S1候補の個別感度は条件付きで走らせる

- 設計§6: mainの各候補に必要な全ジョブをfreezeする。推定した全費用（実測の2倍で見積もる）が30分を超えるならmainに進まない。
- 証拠（naive実装の実測からの見積もり）:
  - S0/S1/S2、S0の個別感度11本、FD、採用段の計時だけで約17分、2倍則で約34分になる。30分に収めるには、根の計算のベクトル化で再帰を縮める必要がある（§0）。
  - S1候補の個別感度11本を足すと約27分、2倍則で約55分になる。
  - naiveのS2はT=.5で127秒。T=1は再帰が倍になるので約220秒の見込みで、1本180秒を超える。ベクトル化した後に2倍則で180秒以内に入るかは、pilotで測るまで分からない。入らなければfreezeで止まる。
  - ベクトル化でどこまで縮むかもpilotまで分からない。S1候補の感度を必ず走るジョブに入れると、必要な短縮がさらに大きくなる。
- 提案:
  - S1候補の個別感度11本は、その満期でS0が採用されなかった場合だけ実行する。この規則をfreezeに含める。
  - 採用段の計時（4本）も条件付きにする。どの段が採用されるかはmainの途中で決まるため。
  - 30分の推定gateは、必ず走るジョブにだけ適用する。
  - 条件付きのジョブは、推定がその時点の残り予算に収まるときだけ走らせる。収まらなければ`not_achieved_budget`として記録する。
  - 予算と許容差は自動では増やさない。
- 影響: 予算gateの適用対象が変わる。ジョブを選ぶ規則は事前に固定する。

### D-6 根を探す幅に予備の0.5を足す

- 設計§4: [p−.1, min(0,p+.1)]→幅.2→幅.3の順にbracketを作り、幅.3までで符号変化がなければ`missing_sign_change`で失敗にする。Task 1は`SpectralConfig.root_widths`の既定値を`(0.1, 0.2, 0.3)`とした。D-6はこの既定値を置き換える（Task 1の本文のコードとテストは書き換えない）。
- 証拠（2026-10-26のpilot）: S0の`domain_expand`（分散格子を両側に12節点ずつ広げ、上端v≈4.0）が、T=.5の最初の逆向きstep（t=.495）で、上端5節点（index 179〜183、v 3.18〜4.01）の`missing_sign_change`により止まった。満期の境界x*=0から始まるbracket[−w, 0]に対し、これらの節点のx*は−0.30〜−0.32にある。幅.5を足した作業用の再計算（リポジトリは変更していない）では、5節点とも`single`、根の残差2.4e-11、S0 baseとの価格差は主3 spotで≤2.2e-10。pilotの他のspectral 14ジョブは、すべて.3までで根が見つかっている。
- 提案（2026-10-27にユーザーが承認）: `root_widths`の既定値を`(0.1, 0.2, 0.3, 0.5)`にする。他の既定値は変えない。走査の刻み`scan_spacing`は`root_widths[0]`を使うので変わらない。幅は小さい順に試し、見つかった節点はそこで確定する（`_dsinc_american.py`の`for half_width in config.root_widths`のloop）。.5は、.3までで`missing_sign_change`になる節点にしか効かない。.3までの幅で符号変化が見つかる節点は従来と同じbracketを採るので、結果は変わらない。
- 影響: 失敗の範囲が狭まる（緩和）。bracketを選んだ後の走査・交差の数え方・二分法の許容は従来と同じ。閾値と予算は変えない。

### D-7 上下界を通らない段は採用しない

- 設計§6: 最初の隣接差≤5e-6、独立FD差≤2e-5、個別感度gate成立を満たす粗い側を採用する。上下界は`gates.bounds_check`の5つで、American≥European、American≥payoff、American≤K、Europeanの下限max(e^{−rd·T}−(S/K)e^{−rf·T}, 0)と上限e^{−rd·T}。これらは、採用した後の価格検証（`independent_validated`）でだけ見ていた。許容は`protocol.json`の`thresholds.bounds`（2e-5·K）で、`bounds_check`が5つすべてに適用する。設計§5の94行目と計画§2が2e-5を述べているのは、3つのAmerican側（American≥European、American≥payoff、American≤K）だけである。計画のTask 6は`select_level(levels, reference, sensitivities, thresholds)`を`bounds`なしの形で定め、そのテストもこの形で書いた。D-7はこれを置き換える（Task 6の本文のシグネチャとテストは書き換えない）。
- 証拠（pilotの検査項目ではない）: S0のT=1では、走査点S/K≈0.8でAmerican−payoffの最小が−2.36e-5で、許容2e-5を超える（Task 5で測り、2026-10-26のpilotも同じ値）。同じT=1で、S1は−8.3e-6、S2は−4.8e-6（Task 5の実測、走査126点）。T=.5のS0は−1.54e-5で通る。従来の規則ではT=1でS0が採用されて価格検証が不合格になり、S0が採用されるのでS1のT=1の感度は走らない（D-5）。計画§2の独立gateには上下界が含まれており、段の採用もその読みに揃える。
- 提案（2026-10-27にユーザーが承認）: `gates.select_level(levels, reference, sensitivities, thresholds, *, bounds=None)`とする。`bounds`は段名（S0, S1）→その段の上下界の合否（bool）のdictで、与えられたとき、候補の段の値がTrueでなければ（False・欠落・None）その候補は不合格にする。結果は`checks[level]["bounds"]`に残す。予算で感度が未実行の段を待たせる扱い（`not_achieved_budget`）は従来どおりで、上下界で落ちた候補は待たせない。`bounds=None`なら従来どおり。runnerのmainでは、各満期でS0・S1のbase jobが価格を出した全spot（主3＋bump 18＋走査126の147点）に`gates.bounds_check`を適用し、その`pass`を`bounds`として渡す。base jobが価格を出していない段はFalse。条件付きジョブの判定（`condition_met`が読む途中の選択）も同じ規則で作る。
- 実装の細部（Task 7Rのレビューで2026-10-27に追加した。ユーザーが承認した内容には含まれない）: `select_level`は、`bounds`が与えられてmappingでなければ、またS0・S1の値がbool（`numpy.bool_`を含む）でもNoneでもなければ、ValueErrorにする（`gates.py`の規則：解釈できない引数はValueError）。欠落とNoneは、直前の提案の規則（False・欠落・Noneは不合格）どおり不合格にする。
- 影響: 厳格化（採用の条件が増える）。許容2e-5は変えない。pilotのestimatesでは、T=.5でS0、T=1でS1を採用した場合の必須と条件付きの合計は約1733秒（予算1800秒）。条件付きジョブは、その時点の残り予算に収まる見積もりのときだけ走る（D-5、変更なし）。

## 2. Global Constraints

- 研究用のprivate実装だけを作る。新しいproduction依存、既存の公開APIの変更、本編・サイトへの組込み、市場データの取得はしない。
- 入力範囲: S,K>0、T≥0、rd>rf≥0、kappa,theta,v0,xi>0、|rho|<1。3/2は`rho*xi <= kappa + xi**2/2`。T=0はexact payoffを返す。負のT・NaN/Inf・無効な格子や減衰はValueError。xi=0はunsupported。
- 単位: 時間は年、金利は連続複利の年率。比較は価格/Kで行い、生の価格も保存する。v,thetaは分散率。
- chi=.5で、正減衰の留数を含める。満期での境界はx*=0。数値の失敗をclipや代用値で隠さない。
- 3/2の主ケース: rd=.05, rf=.02, K=1, kappa=20, theta=v0=.04, xi=4, rho=−.5、T∈{.5,1}×S/K∈{.9,1,1.1}。
- 文献gate（paper_match）: S0のspectral値を、Table 4のAmerican 3点、Table 3(b)のEuropean 3点、Table 9のT=1 ATMと比べ、|差|/K≤6e-6で判定する。EEP列、N=200列、論文のFD値は診断だけに使う。T=1の非ATMはnot_available。
- 独立gate（価格/K）: European・American・EEPのそれぞれで|spectral−reference|≤2e-5。reference最終細分差≤5e-6。spectralの隣接段の差と個別感度≤5e-6。American≥European、American≥payoff、American≤K（いずれも許容2e-5）。
- 境界gate: 窓はt/T∈[.1,.9]、v∈[.01,.16]。x端から4セル以内はmaskする。有効なcoverage≥90%、外れ≤2dx、価値一致の残差≤1e-8。
- 予算: solver subprocessは1方式×1満期×1設定（3spotを一括）で、wall 180秒・peak RSS 2 GiB。pilot合計10分、main合計30分。見積もりは2倍で取る。反復計時はspectralだけ（1 warmup+3回）、FDは1回。`OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`。
- 保存: 1回の実行につき`/home/kazumasa/projects/_data/johnhull/DSINC/<run-id>/`を1つ使う。伝播行列、FDの全面、中間配列は保存しない。保存量の目標は50 MiB以下、研究ディレクトリへ追加するファイルは1つ2,000,000 bytes以下。Git管理外のデータはworktreeの中に置かない。
- 上流原本は改変しない。ruff/formatの対象から外し、`benchmark.py`はimportしない。`sys.path`を変更しない。
- 各タスクは、失敗するテスト→実装→局所検証の順に進める。全ジョブを元の件数のまま会計する。失敗・時間切れ・予算超過もnullと理由で残す。
- hullkitの公開名にはdocstringを付ける（`test_docstrings.py`）。計画のテストとコードは、`ruff format`（line-length 100）と`ruff check --fix`で整えてからcommitする。
- ROADMAPは、着手・段階の完了・計画の変更と同じコミットで更新する。push・公開・deployはしない。コミットメッセージの末尾には、そのセッションで指定された帰属行を付ける。

## 3. Review Focus

1. **行使境界の近くのspot**（S/K≈.83、T=.5）: v0への補間が行使節点と継続節点を混ぜるため、S0でAmerican−payoffが−1.54e-5になる。期待される振る舞いは、clipせずに診断へ出し、許容2e-5の中に収めること。→ Task 5 `test_prices_near_the_boundary_stay_within_the_bound_tolerance`。runnerは境界の走査spotを全spectral/FDジョブで評価し、最小のgapを報告する（Task 6）。
2. **設計範囲外の入力を上流adapterに渡す場合**（READMEの例rd=.025<rf=.05）: 期待はValueError。上流は終端境界xT=log(rd/rf)のまま黙って計算する。→ Task 2 `test_out_of_scope_rates_are_rejected`。
3. **既存の出力rootへの再実行**: 期待は拒否（別の実行の結果が混ざるのを防ぐ）。→ Task 6 `test_output_root_must_be_new`。
4. **短満期に対して周波数cutoffが足りない設定**（T=.01、cutoff 40）: 負のEuropean価格を黙って返さず、下限違反を診断に出す。→ Task 5 `test_bound_violations_are_reported_not_clipped`。
5. **分散格子の端にあるv0、FDのx領域の外のspot**: 端は受け付け、外は外挿せずにValueErrorにする。→ Task 3 `test_variance_interpolation_is_not_a_knot_and_refuses_extrapolation`、Task 4 `test_reference_rejects_unsupported_inputs`。

## 4. 実行環境

```bash
WT=/home/kazumasa/worktrees/dsinc
PY="env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=$WT/johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python"
RUFF=/home/kazumasa/projects/.venv/bin/ruff
DATA=/home/kazumasa/projects/_data/johnhull/DSINC
```

- worktreeの中では`uv`を使わない。空の`.venv`ができ、hullkitがmainのsrcを指してしまう。テストは`cd $WT && $PY -m pytest -q <file>`で走らせる。
- 研究モジュール同士の読み込みは`importlib.util.spec_from_file_location`で行い、`exec_module`の前に`sys.modules`へ`dsinc_<name>`として登録する（登録しないと、文字列の注釈を持つdataclassの定義が失敗する）。テストのfixtureも同じようにする。

## 5. ファイル構成

| ファイル | 責任 |
|---|---|
| `johnhull/hullkit/src/hullkit/_dsinc_types.py` | 入力型、検証、境界の状態code、構造化した失敗、digest |
| `johnhull/hullkit/src/hullkit/_dsinc_spectral.py` | 周波数則、作用素、伝播、European、v0補間、診断 |
| `johnhull/hullkit/src/hullkit/_dsinc_american.py` | payoff変換、境界root、EEP再帰、American |
| `johnhull/research/DSINC/upstream/{dsinc_pricer.py,fd_adi_pricer.py,benchmark.py,LICENSE}` | 上流原本（改変しない） |
| `johnhull/research/DSINC/upstream_manifest.json` | URL、commit、Git blob、sha256、bytes、ライセンス |
| `johnhull/research/DSINC/heston_baseline.py` | 上流の読み込み、観測用サブクラス、Hestonの比較 |
| `johnhull/research/DSINC/cases.json` | 論文の印刷値、上流のHestonケース |
| `johnhull/research/DSINC/reference_fd.py` | 独立した3/2 FD |
| `johnhull/research/DSINC/protocol.json` | 全設定、閾値、roster、予算（freezeの対象） |
| `johnhull/research/DSINC/gates.py` | 判定関数（純関数） |
| `johnhull/research/DSINC/run.py` | pilot / freeze / main / solve-job / replay / export |
| `johnhull/research/DSINC/plot.py` | 保存した結果から3図を描く |
| `johnhull/research/DSINC/{freeze_manifest.json,pilot_summary.json,results/,figures/,README.md,REVIEW.md}` | pilot後・main後の成果 |
| `johnhull/hullkit/tests/test_dsinc_{types,baseline,spectral,reference,american,gates,runner}.py` | テスト |
| `pyproject.toml`（root） | ruffの`extend-exclude`にupstreamを足す |
| `johnhull/MODEL_INDEX.md`、`johnhull/ROADMAP.md`、設計 | 索引、現在地、承認された逸脱の反映 |

---

### Task 1: 入力型と検証

**Files:**
- Create: `johnhull/hullkit/src/hullkit/_dsinc_types.py`
- Test: `johnhull/hullkit/tests/test_dsinc_types.py`
- Modify: `johnhull/MODEL_INDEX.md`（RB-F06の節の後に新しい節）、`johnhull/ROADMAP.md`（現在地のDSINCの2行）、`johnhull/docs/superpowers/specs/2026-10-25-dsinc-american-design.md`（承認されたD-1〜D-5を§4〜§6に反映）

**Interfaces:**
- Consumes: なし
- Produces:

```python
@dataclass(frozen=True)
class PutContract:
    strike: float
    expiry: float
    domestic_rate: float
    foreign_rate: float

@dataclass(frozen=True)
class VarianceModel:
    kind: Literal["heston", "three_halves"]
    kappa: float
    theta: float
    xi: float
    rho: float
    v0: float

@dataclass(frozen=True)
class SpectralConfig:
    n_time: int
    n_var: int
    log_var_bounds: tuple[float, float]
    chi: float
    panels: tuple[float, ...]
    points_per_panel: int
    root_widths: tuple[float, ...] = (0.1, 0.2, 0.3)
    root_x_tol: float = 1e-10
    root_residual_tol: float = 1e-8
    root_maxiter: int = 60
    crossing: Literal["upper", "lower"] = "upper"

BOUNDARY_STATUS: dict[str, int]   # 値はテストで固定
FAILURE_CODES: frozenset[int]     # {2, 3, 4, 5, 6}

class PricingFailure(Exception):
    def __init__(self, code: str, message: str, details: dict) -> None: ...
    # attributes: code, message, details

@dataclass(frozen=True)
class PricingResult:
    european: np.ndarray                # (n_spots,) 価格/K、入力順
    american: np.ndarray
    early_exercise_premium: np.ndarray
    times: np.ndarray                   # (n_time+1,) t_n = n*T/n_time。T=0では(0,)
    log_variances: np.ndarray           # (n_var,)。T=0では(0,)
    log_boundary: np.ndarray            # (n_time+1, n_var) x*。T=0では(0, 0)
    boundary_status: np.ndarray         # int8、log_boundaryと同じ形
    diagnostics: dict                   # JSONにできるscalar/listだけ

def canonical_digest(*parts: object) -> str: ...   # sha256の16進
```

- [ ] **Step 1: worktreeを作る**

`superpowers:using-git-worktrees`に従い、mainから`/home/kazumasa/worktrees/dsinc`にbranch `claude/dsinc-american`を作る。前提として、本計画と、設計・レビュー記録・ROADMAPの状態の行がmainにcommit済みであること（未commitの変更はworktreeに入らない）。

Run: `git -C /home/kazumasa/projects worktree list`
Expected: `/home/kazumasa/worktrees/dsinc` が `[claude/dsinc-american]` で表示される。

- [ ] **Step 2: 失敗するテストを書く**

```python
"""DSINC input contracts, validation, status codes and digests."""

import math

import pytest
from hullkit._dsinc_types import (
    BOUNDARY_STATUS,
    PricingFailure,
    PutContract,
    SpectralConfig,
    VarianceModel,
    canonical_digest,
)

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
BOUNDS = (math.log(2e-4), math.log(2.0))
CONTRACT = dict(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = dict(kind="three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)


def s0(**changes):
    base = dict(n_time=100, n_var=160, log_var_bounds=BOUNDS, chi=0.5, panels=PANELS, points_per_panel=12)
    return SpectralConfig(**(base | changes))


def test_paper_inputs_are_accepted():
    PutContract(**CONTRACT)
    VarianceModel(**MODEL)
    VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
    config = s0()
    assert config.root_widths == (0.1, 0.2, 0.3) and config.crossing == "upper"
    assert (config.root_x_tol, config.root_residual_tol, config.root_maxiter) == (1e-10, 1e-8, 60)


@pytest.mark.parametrize(
    "field, value",
    [("strike", 0.0), ("strike", -1.0), ("strike", math.nan), ("expiry", -0.1),
     ("expiry", math.inf), ("domestic_rate", 0.02), ("foreign_rate", -0.01), ("foreign_rate", math.nan)],
)
def test_invalid_contract_is_rejected(field, value):
    with pytest.raises(ValueError):
        PutContract(**(CONTRACT | {field: value}))


@pytest.mark.parametrize(
    "field, value",
    [("kappa", 0.0), ("theta", -0.04), ("xi", 0.0), ("rho", 1.0), ("rho", -1.0),
     ("v0", 0.0), ("v0", math.nan), ("kind", "sabr")],
)
def test_invalid_model_is_rejected(field, value):
    with pytest.raises(ValueError):
        VarianceModel(**(MODEL | {field: value}))


def test_three_halves_martingale_condition_includes_equality():
    VarianceModel("three_halves", kappa=0.25, theta=0.04, xi=1.0, rho=0.75, v0=0.04)  # rho*xi == kappa + xi**2/2
    VarianceModel("heston", kappa=0.125, theta=0.04, xi=1.0, rho=0.75, v0=0.04)
    with pytest.raises(ValueError, match="martingale"):
        VarianceModel("three_halves", kappa=0.125, theta=0.04, xi=1.0, rho=0.75, v0=0.04)


@pytest.mark.parametrize(
    "changes",
    [dict(chi=0.0), dict(chi=1.0), dict(n_time=0), dict(n_time=True), dict(n_var=3),
     dict(log_var_bounds=(0.0, -1.0)), dict(panels=(1.0, 2.0)), dict(panels=(0.0, 5.0, 5.0)),
     dict(points_per_panel=0), dict(root_widths=(0.2, 0.1)), dict(root_maxiter=0), dict(crossing="middle")],
)
def test_invalid_spectral_config_is_rejected(changes):
    with pytest.raises(ValueError):
        s0(**changes)


def test_boundary_status_codes_are_fixed():
    assert BOUNDARY_STATUS == {
        "not_run": -1, "single": 0, "multiple_crossings": 1, "missing_sign_change": 2,
        "wrong_orientation": 3, "ambiguous_contact": 4, "nonfinite": 5, "maxiter": 6, "terminal": 7,
    }


def test_pricing_failure_keeps_code_and_details():
    error = PricingFailure("boundary_failure", "no sign change", {"time_index": 98})
    assert (error.code, error.message, error.details) == ("boundary_failure", "no sign change", {"time_index": 98})
    assert "boundary_failure" in str(error)


def test_digest_tracks_every_field():
    parts = (PutContract(**CONTRACT), VarianceModel(**MODEL), s0())
    base = canonical_digest(*parts)
    assert base == canonical_digest(PutContract(**CONTRACT), VarianceModel(**MODEL), s0())
    changed = [
        (PutContract(**(CONTRACT | {"expiry": 1.0})), parts[1], parts[2]),
        (parts[0], VarianceModel(**(MODEL | {"rho": -0.4})), parts[2]),
        (parts[0], parts[1], s0(chi=0.25)),
        (parts[0], parts[1], s0(panels=(*PANELS, 1280.0))),
    ]
    assert all(canonical_digest(*c) != base for c in changed)
    assert canonical_digest({"a": (1.0, 2.0), "b": None}) == canonical_digest({"b": None, "a": [1.0, 2.0]})
    with pytest.raises(ValueError):
        canonical_digest({"a": math.nan})
```

- [ ] **Step 3: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_types.py`
Expected: FAIL（`ModuleNotFoundError: No module named 'hullkit._dsinc_types'`）

- [ ] **Step 4: `_dsinc_types.py`を実装する**

- 検証は`__post_init__`で行う。floatはすべてfiniteであることを確かめる。
  - PutContract: strike>0、expiry≥0、domestic_rate>foreign_rate≥0。
  - VarianceModel: kindは2種類のどちらか。kappa・theta・xi・v0>0、|rho|<1。three_halvesでは`rho*xi <= kappa + xi**2/2`を満たさなければ、"martingale"を含むメッセージでValueErrorにする。
  - SpectralConfig: n_time・n_var・points_per_panel・root_maxiterはintで、boolは拒否する。n_time≥1、n_var≥4、boundsはfiniteで昇順、0<chi<1、panelsは0から始まり狭義に増加して長さ≥2、root_widthsは空でなく正で狭義に増加、許容値>0、crossingは{"upper","lower"}のどちらか。
  - listで渡された値はfloatのtupleにそろえる（`object.__setattr__`を使う）。
- `BOUNDARY_STATUS`はテストの値にする。`FAILURE_CODES = frozenset({2, 3, 4, 5, 6})`。
- `canonical_digest`は、`json.dumps(..., sort_keys=True, allow_nan=False)`のsha256を返す。入力は次のように変換する。
  - dataclass → `{"__type__": クラス名, 各field}`
  - dict → keyをstrにしたdict（値は再帰的に変換）
  - tuple/list → list
  - numpy配列 → `{"dtype", "shape", "sha256": バイト列のsha256}`
  - numpyのscalar → Pythonの値
  - str/int/float/bool/None → そのまま（NaN/InfはValueError）
- 公開名すべてにdocstringを付ける（`test_docstrings.py`）。

- [ ] **Step 5: 通ることを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_types.py`
Expected: `33 passed`

- [ ] **Step 6: 索引・現在地・設計を更新する**

- `MODEL_INDEX.md`のRB-F06の節の後に`## DSINC research: American put by fixed-frequency spectral recursion`と表`| Module | Contracts | Verification |`を作り、次の行を足す。

  `` | `hullkit._dsinc_types` | Private `hullkit._dsinc_types:PutContract`, `hullkit._dsinc_types:VarianceModel`, `hullkit._dsinc_types:SpectralConfig`, `hullkit._dsinc_types:PricingFailure`, `hullkit._dsinc_types:PricingResult`, `hullkit._dsinc_types:canonical_digest` | v1 input scope (rd>rf>=0, 3/2 true martingale rho*xi<=kappa+xi^2/2), ValueError on invalid inputs, fixed boundary status codes and structured failures; test_dsinc_types.py; research/DSINC/ in progress | ``
- ROADMAPの「現在地」のDSINCの2行を「実装開始（branch `claude/dsinc-american`）。Task 1（入力型）完了。D-1〜D-5は2026-10-26に承認」に改める。
- 設計§4の境界規則、§5の参照値と境界FD、§6のx水準と条件付きジョブに、承認された逸脱を反映する。設計の中にある旧計画のタスク番号（Task 2/4/5のsmoke・正式判定）も、本計画の番号（Task 3/5のsmoke、Task 7の正式判定）に直す。冒頭の状態の行も更新する。

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_types.py johnhull/hullkit/tests/test_model_index.py johnhull/hullkit/tests/test_docstrings.py`
Expected: すべてPASS（0 failed）

- [ ] **Step 7: Commit**

```bash
git -C $WT add johnhull/hullkit/src/hullkit/_dsinc_types.py johnhull/hullkit/tests/test_dsinc_types.py johnhull/MODEL_INDEX.md johnhull/ROADMAP.md johnhull/docs/superpowers/specs/2026-10-25-dsinc-american-design.md
git -C $WT commit -m "Add DSINC input contracts and record the approved plan deviations"
```

---

### Task 2: 上流の固定、Hestonの比較、ケース表

**Files:**
- Create: `johnhull/research/DSINC/upstream/{dsinc_pricer.py,fd_adi_pricer.py,benchmark.py,LICENSE}`（取得したまま）、`johnhull/research/DSINC/upstream_manifest.json`、`johnhull/research/DSINC/heston_baseline.py`、`johnhull/research/DSINC/cases.json`
- Test: `johnhull/hullkit/tests/test_dsinc_baseline.py`
- Modify: `pyproject.toml`（root）。`[tool.ruff] extend-exclude`に`"johnhull/research/DSINC/upstream"`を足し、「固定commitの原本で、整形すると監査対象が変わる」という1行のコメントを付ける。

**Interfaces:**
- Consumes: Task 1の`PutContract`、`VarianceModel`（入力の検証に使う）
- Produces:

```python
UPSTREAM_DIR: Path      # research/DSINC/upstream
MANIFEST: Path          # research/DSINC/upstream_manifest.json
def load_upstream(name: Literal["dsinc_pricer", "fd_adi_pricer"]) -> ModuleType
def observed_classes() -> tuple[type, type]   # (ObservedDSINCPut, ObservedFDSolver)
def run_heston_baseline(case: dict, *, dsinc_settings: dict | None = None, fd_settings: dict | None = None) -> dict
```

`run_heston_baseline`の戻り値（JSONにできる値だけ）:
- `case_id`、`inputs`
- `dsinc`: `parameters`（上流に渡したdict）、`settings`（Nv・Nt・Nom・om_max・mode・chi）、`european`、`american`、`eep`、`final`（`european_raw`・`eep_raw`・`american_raw`）、`counts`、`post_processing`（price()で適用されたfloorの名前のlist）、`seconds`（init・price）
- `fd`: `parameters`、`settings`（N・m1・B・Smax_mult・Vmax・theta_mcs・policy・rho_AM・pp_maxiter）、`docstring_policy_default`（0）、`european`、`american`、`policy_stop_reasons`、`policy_solves`、`seconds`（init・european・american）
- `reference`、`differences`
- `certified`: 常にFalse

- [ ] **Step 1: 原本を取得して照合する**

```bash
mkdir -p $WT/johnhull/research/DSINC/upstream && cd $WT/johnhull/research/DSINC/upstream
BASE=https://raw.githubusercontent.com/rakhymzhan11/DSINC-AMERICAN-HESTON/20cfb802673b0a792984d25e1f45cd09d37e8c07
for f in dsinc_pricer.py fd_adi_pricer.py benchmark.py LICENSE; do curl -fsSL "$BASE/$f" -o "$f"; done
sha256sum dsinc_pricer.py fd_adi_pricer.py benchmark.py LICENSE && git hash-object dsinc_pricer.py fd_adi_pricer.py benchmark.py LICENSE
```

Expected:
```
7ce004ae819252e98cc287c06acc74be6ee57216d2ab09aac8b49f1f66fae927  dsinc_pricer.py
535d8da63827be1eb977312042e52204d2cf863a57219b1217bdd534fbf8b12c  fd_adi_pricer.py
35eba4f34f2690091518e2e3e801d317d54f8ee1ec5e155e0e8334d1ebd89a35  benchmark.py
028d0ca606b35b691ec82fda12fae43370bee49548a37f3f8b97ce15dbb7202b  LICENSE
33d4d6a78f63d89025786fe75a774d565ba5a9dc
3518f6b1979f7856f1c9825ba37446e7849b6e85
59b7f490942b7099abf1a90c0987f1c08603416a
04fabfeb16dba4d1179fe3337d27be15019b50a9
```
1つでも違えば止める（原本を編集しない）。

- [ ] **Step 2: manifestとケース表を書く**

`upstream_manifest.json`:

```json
{
  "repository": "https://github.com/rakhymzhan11/DSINC-AMERICAN-HESTON",
  "commit": "20cfb802673b0a792984d25e1f45cd09d37e8c07",
  "license": "MIT",
  "copyright_line": "Copyright (c) 2026 <COPYRIGHT HOLDER>",
  "files": {
    "dsinc_pricer.py": {"git_blob": "33d4d6a78f63d89025786fe75a774d565ba5a9dc", "sha256": "7ce004ae819252e98cc287c06acc74be6ee57216d2ab09aac8b49f1f66fae927", "bytes": 15973},
    "fd_adi_pricer.py": {"git_blob": "3518f6b1979f7856f1c9825ba37446e7849b6e85", "sha256": "535d8da63827be1eb977312042e52204d2cf863a57219b1217bdd534fbf8b12c", "bytes": 18243},
    "benchmark.py": {"git_blob": "59b7f490942b7099abf1a90c0987f1c08603416a", "sha256": "35eba4f34f2690091518e2e3e801d317d54f8ee1ec5e155e0e8334d1ebd89a35", "bytes": 3294},
    "LICENSE": {"git_blob": "04fabfeb16dba4d1179fe3337d27be15019b50a9", "sha256": "028d0ca606b35b691ec82fda12fae43370bee49548a37f3f8b97ce15dbb7202b", "bytes": 1075}
  },
  "import_policy": "load dsinc_pricer.py and fd_adi_pricer.py by file path after the sha256 check; never import benchmark.py; never modify sys.path"
}
```

`cases.json`:
- `"schema": "DSINC-cases-v1"`
- `three_halves_paper`:
  - `source`: `"arXiv:2610.28847v1 Section 5.4-5.5, Tables 3(b), 4, 9"`
  - `parameters`: rd .05、rf .02、strike 1、kappa 20、theta .04、xi 4、rho −.5、v0 .04
  - `spots`: [.9,1,1.1]、`units`: `"price/K"`、`rounding`: 1e-6
  - `T0.5`と`T1`は下のテストのとおり
  - `roles.gate`: `["T0.5.american_n100", "T0.5.european", "T1.american_atm"]`
  - `roles.diagnostic`: 残りの列
- `heston_upstream`:
  - `source`: `"upstream benchmark.py at commit 20cfb802 (transcribed, not imported)"`、`units`: `"raw price"`
  - `cases`: H00と10件。10件はK=10、T=.25、rd=.1、rf=0、theta=.16、xi=.9、rho=.1、kappa=5。v0∈{.0625,.25}×S∈{8,9,10,11,12}の順に並べ、`case_id`は`"HT-v0.0625-S8"`の形にする。`reference.american`はテストの値。

- [ ] **Step 3: 失敗するテストを書く**

```python
"""Pinned upstream Heston DSINC/FD code: provenance, input mapping and observed branches."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2] / "research/DSINC"
H00 = {"case_id": "H00", "S": 100.0, "K": 100.0, "T": 0.25, "rd": 0.03, "rf": 0.025,
       "theta": 0.6, "xi": 0.8, "rho": -0.4, "v0": 0.5, "kappa": 0.5}
TINY_FD = {"N": 20, "m1": 40}
FD_PARAMS = {"K": 100.0, "T2": 0.25, "rd": 0.03, "rf": 0.025, "theta": 0.6, "xi": 0.8, "rho": -0.4, "kappa": 0.5} | TINY_FD


@pytest.fixture(scope="module")
def baseline():
    spec = importlib.util.spec_from_file_location("dsinc_heston_baseline_tests", ROOT / "heston_baseline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def dsinc_params(**settings):
    keys = ("S", "K", "T", "rd", "rf", "theta", "rho", "v0", "kappa")
    return {k: H00[k] for k in keys} | {"sigma": H00["xi"]} | settings


def test_manifest_pins_the_four_upstream_files():
    manifest = json.loads((ROOT / "upstream_manifest.json").read_text())
    assert manifest["commit"] == "20cfb802673b0a792984d25e1f45cd09d37e8c07"
    expected = {
        "dsinc_pricer.py": ("7ce004ae819252e98cc287c06acc74be6ee57216d2ab09aac8b49f1f66fae927", 15973),
        "fd_adi_pricer.py": ("535d8da63827be1eb977312042e52204d2cf863a57219b1217bdd534fbf8b12c", 18243),
        "benchmark.py": ("35eba4f34f2690091518e2e3e801d317d54f8ee1ec5e155e0e8334d1ebd89a35", 3294),
        "LICENSE": ("028d0ca606b35b691ec82fda12fae43370bee49548a37f3f8b97ce15dbb7202b", 1075),
    }
    for name, (sha, size) in expected.items():
        data = (ROOT / "upstream" / name).read_bytes()
        assert (hashlib.sha256(data).hexdigest(), len(data)) == (sha, size)
        assert (manifest["files"][name]["sha256"], manifest["files"][name]["bytes"]) == (sha, size)
    assert "Copyright (c) 2026 <COPYRIGHT HOLDER>" in (ROOT / "upstream/LICENSE").read_text()


def test_load_upstream_rejects_modified_bytes_and_benchmark(baseline, tmp_path, monkeypatch):
    for name in ("dsinc_pricer.py", "fd_adi_pricer.py"):
        (tmp_path / name).write_bytes((ROOT / "upstream" / name).read_bytes())
    (tmp_path / "dsinc_pricer.py").write_bytes((tmp_path / "dsinc_pricer.py").read_bytes() + b"\n")
    monkeypatch.setattr(baseline, "UPSTREAM_DIR", tmp_path)
    with pytest.raises(ValueError, match="sha256"):
        baseline.load_upstream("dsinc_pricer")
    with pytest.raises(ValueError, match="benchmark"):
        baseline.load_upstream("benchmark")


def test_load_upstream_leaves_sys_path_alone(baseline):
    before = list(sys.path)
    baseline.load_upstream("fd_adi_pricer")
    assert sys.path == before


def test_one_normalized_input_reaches_both_solvers(baseline):
    out = baseline.run_heston_baseline(H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 600}, fd_settings=TINY_FD)
    d, f = out["dsinc"]["parameters"], out["fd"]["parameters"]
    assert (d["sigma"], d["kappa"], d["T"], d["v0"]) == (0.8, 0.5, 0.25, 0.5)
    assert (f["xi"], f["kappa"], f["T2"]) == (0.8, 0.5, 0.25) and "v0" not in f
    assert out["dsinc"]["settings"]["chi"] == -1.0
    assert (out["fd"]["settings"]["policy"], out["fd"]["docstring_policy_default"]) == (1, 0)
    assert out["certified"] is False


def test_observed_classes_return_the_upstream_values(baseline):
    dsinc, fd = baseline.load_upstream("dsinc_pricer"), baseline.load_upstream("fd_adi_pricer")
    observed_dsinc, observed_fd = baseline.observed_classes()
    plain, seen = dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=600)), observed_dsinc(dsinc_params(Nv=6, Nt=8, Nom=600))
    assert plain.price() == seen.price()
    np.testing.assert_array_equal(plain.xstar, seen.xstar)
    a, b = fd.HestonFDSolver(FD_PARAMS), observed_fd(FD_PARAMS)
    assert [a.price(100.0, 0.5, k) for k in (0, 1)] == [b.price(100.0, 0.5, k) for k in (0, 1)]


def test_upstream_eep_floor_is_observed_and_not_certified(baseline):
    low = baseline.run_heston_baseline(H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 120}, fd_settings=TINY_FD)
    assert low["dsinc"]["final"]["eep_raw"] == pytest.approx(-0.0778381085, abs=1e-9)
    assert low["dsinc"]["eep"] == 0.0 and low["dsinc"]["american"] == low["dsinc"]["european"]
    assert "eep_floor" in low["dsinc"]["post_processing"]
    ok = baseline.run_heston_baseline(H00, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 600}, fd_settings=TINY_FD)
    assert ok["dsinc"]["final"]["eep_raw"] == pytest.approx(0.0255717953, abs=1e-9)
    assert "eep_floor" not in ok["dsinc"]["post_processing"]


@pytest.mark.parametrize(
    "residual, x0, path, expected",
    [
        (lambda x: 0.0, -0.2, "exact_zero", -0.2),
        (lambda x: -(x + 0.1), -0.09, "local_bracket", -0.1),
        (lambda x: 1.0 if -6.0 <= x <= -5.9 else -1.0, 0.0, "wide_scan", -6.0),
        (lambda x: (x + 3.0) ** 2 + 1e-3, 0.0, "min_residual", -2.9525),
    ],
)
def test_boundary_paths_are_classified(baseline, residual, x0, path, expected):
    dsinc = baseline.load_upstream("dsinc_pricer")
    observed, _ = baseline.observed_classes()
    plain, seen = dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=120)), observed(dsinc_params(Nv=6, Nt=8, Nom=120))
    value = seen._solve_boundary(residual, x0)
    assert value == plain._solve_boundary(residual, x0) and value == pytest.approx(expected, abs=1e-4)
    assert seen.counts[path] == 1


def test_clip_and_safe_nan_are_counted(baseline):
    observed, _ = baseline.observed_classes()
    seen = observed(dsinc_params(Nv=6, Nt=8, Nom=120))
    assert seen._solve_boundary(lambda x: -(x + 0.1), 1.0) == pytest.approx(-0.1)
    assert seen.counts["clip_high"] == 1

    def fragile(x):
        if x < -0.095:
            raise ValueError("outside")
        return -(x + 0.1)

    assert seen._solve_boundary(fragile, -0.09) == pytest.approx(0.02)  # every scan point but the last raises
    assert seen.counts["safe_nan"] >= 1 and seen.counts["min_residual"] == 1


def test_cf_replacement_and_european_floor_are_counted(baseline):
    dsinc = baseline.load_upstream("dsinc_pricer")
    observed, _ = baseline.observed_classes()
    plain, seen = dsinc.DSINCPut(dsinc_params(Nv=6, Nt=8, Nom=120)), observed(dsinc_params(Nv=6, Nt=8, Nom=120))
    u = np.array([0.5, np.inf])
    with np.errstate(all="ignore"):
        np.testing.assert_array_equal(seen._heston_cf(u, 0.25, 0.5), plain._heston_cf(u, 0.25, 0.5))
    assert seen.counts["cf_nonfinite"] == 1
    coeffs = (0.0, np.array([0.0]), np.array([-1.0 + 0.0j]), 100.0)
    assert seen._european_value(0.0, coeffs) == plain._european_value(0.0, coeffs) == 0.0
    assert seen.counts["european_floor"] == 1 and seen.extremes["european_min_raw"] == pytest.approx(-100.0)


def test_price_floor_is_recorded(baseline, monkeypatch):
    observed, _ = baseline.observed_classes()
    put = observed(dsinc_params(Nv=6, Nt=8, Nom=120) | {"S": 50.0})
    monkeypatch.setattr(put, "_backward_solve", lambda: 0.0)
    monkeypatch.setattr(put, "_european_value", lambda x, coeffs: 40.0)
    assert put.price() == (40.0, 50.0, 0.0)
    assert put.final["american_raw"] == 40.0 and "american_floor" in put.post_processing


def test_penalty_stop_reasons_are_counted(baseline):
    _, observed_fd = baseline.observed_classes()
    solver = observed_fd(FD_PARAMS | {"pp_maxiter": 1})
    solver.price(100.0, 0.5, 1)
    assert sum(solver.policy_stop_reasons.values()) == 20 and solver.policy_stop_reasons["maxiter"] >= 1
    assert solver.policy_solves == 20


def test_cases_transcribe_the_paper_and_upstream_tables():
    cases = json.loads((ROOT / "cases.json").read_text())
    paper = cases["three_halves_paper"]
    assert paper["T0.5"] == {
        "american_n100": [0.107601, 0.048662, 0.019499], "european": [0.102557, 0.047224, 0.019105],
        "eep": [0.005044, 0.001438, 0.000394], "american_n200": [0.107599, 0.048660, 0.019497],
        "fd_coarse": [0.107575, 0.048618, 0.019469], "fd_fine": [0.107593, 0.048648, 0.019490],
    }
    assert paper["T1"] == {"american_atm": 0.063668, "fd_fine_atm": 0.063658, "non_atm": "not_available"}
    assert paper["roles"]["gate"] == ["T0.5.american_n100", "T0.5.european", "T1.american_atm"]
    heston = cases["heston_upstream"]["cases"]
    assert heston[0] == H00 | {"reference": {"ie_european": 13.6633, "ie_american": 13.6749, "fd_european": 13.6611, "fd_american": 13.6837}}
    assert [c["reference"]["american"] for c in heston[1:]] == [
        2.0000, 1.1076, 0.5199, 0.2135, 0.0820, 2.0785, 1.3336, 0.7959, 0.4482, 0.2427]


def test_out_of_scope_rates_are_rejected(baseline):
    with pytest.raises(ValueError):
        baseline.run_heston_baseline(H00 | {"rd": 0.025, "rf": 0.05}, dsinc_settings={"Nv": 6, "Nt": 8, "Nom": 120}, fd_settings=TINY_FD)
```

- [ ] **Step 4: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_baseline.py`
Expected: fixtureを使わない`test_manifest_pins_the_four_upstream_files`と`test_cases_transcribe_the_paper_and_upstream_tables`の2件はPASS。残りの14件は`heston_baseline.py`がないためERROR（`FileNotFoundError`）。

- [ ] **Step 5: `heston_baseline.py`を実装する**

- `load_upstream`:
  - "benchmark"が渡されたら、"benchmark.py is never imported"でValueErrorにする。
  - それ以外の名前は2種類だけを受け付ける。
  - `UPSTREAM_DIR`のバイト列を読み、manifestのsha256・bytesと照合する。合わなければ"sha256"を含むValueErrorにする。
  - `spec_from_file_location(f"dsinc_upstream_{name}", path)`で読み込み、(path, sha)をkeyにcacheする。`sys.path`には触らない。
- `observed_classes`:
  - 読み込んだモジュールのクラスからサブクラスを1回だけ作ってcacheする。
  - 観測用の属性は`super().__init__`より前に初期化する。上流の`__init__`は注釈付きの名前だけをparamsとして受け付けるので、観測用の属性には注釈を付けない。
  - ObservedDSINCPutの属性:
    - `counts`: clip_low, clip_high, exact_zero, local_bracket, wide_scan, min_residual, safe_nan, cf_nonfinite, european_floor
    - `extremes`: european_min_raw
    - `final`、`post_processing`
  - `_safe`・`_solve_boundary`・`_heston_cf`・`_european_value`・`_final_eep`・`price`は、上流の制御の流れを1行ずつ写し、分岐の数と加工前の値を記録する。clipは、`np.clip`が値を変えたときだけ数える。
  - ObservedFDSolverは`_policy_iteration`を写す。停止の理由（`crit < tol`はtolerance、active setが変わらなければactive_set_stable、反復を使い切ればmaxiter）と、`splu`の回数を数える。
- `run_heston_baseline`:
  - 先に`PutContract(K, T, rd, rf)`と`VarianceModel("heston", kappa, theta, xi, rho, v0)`で検証し、S>0も確かめる。
  - DSINCには`sigma=xi`を、FDには`T2=T`を渡す。FDの価格は`price(S, v0, amer)`で取る。
  - `certified`は常にFalseにする。

- [ ] **Step 6: 通ることとH00のsmokeを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_baseline.py`
Expected: `16 passed`

Run: `cd $WT && $PY -c "import importlib.util as u, json, sys; s=u.spec_from_file_location('b','johnhull/research/DSINC/heston_baseline.py'); m=u.module_from_spec(s); sys.modules['b']=m; s.loader.exec_module(m); c=json.load(open('johnhull/research/DSINC/cases.json'))['heston_upstream']['cases'][0]; r=m.run_heston_baseline(c); print(*(round(r[k][p],6) for k in ('dsinc','fd') for p in ('european','american')))"`
Expected: `13.663324 13.685393 13.662246 13.683896`（約7秒）

Run: `cd $WT && $RUFF format johnhull/research/DSINC johnhull/hullkit/tests/test_dsinc_baseline.py && $RUFF check --fix johnhull/research/DSINC johnhull/hullkit/tests/test_dsinc_baseline.py && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_baseline.py::test_manifest_pins_the_four_upstream_files`
Expected: `All checks passed!`と`1 passed`（upstream/は整形の対象外なので、原本のsha256は変わらない）。

- [ ] **Step 7: Commit**

```bash
git -C $WT add pyproject.toml johnhull/research/DSINC/upstream johnhull/research/DSINC/upstream_manifest.json johnhull/research/DSINC/heston_baseline.py johnhull/research/DSINC/cases.json johnhull/hullkit/tests/test_dsinc_baseline.py
git -C $WT commit -m "Pin the upstream Heston DSINC code and audit its fallbacks"
```

---

### Task 3: 固定周波数の伝播とEuropean

**Files:**
- Create: `johnhull/hullkit/src/hullkit/_dsinc_spectral.py`、`johnhull/research/DSINC/README.md`（「目的と範囲」「方法と出典」「再実行」の節）
- Test: `johnhull/hullkit/tests/test_dsinc_spectral.py`
- Modify: `johnhull/MODEL_INDEX.md`（DSINCの節に1行）

**Interfaces:**
- Consumes: Task 1の型と`canonical_digest`
- Produces:

```python
def frequency_rule(config: SpectralConfig) -> tuple[np.ndarray, np.ndarray]          # (omega, weights)、昇順
def variance_grid(config: SpectralConfig) -> np.ndarray                               # linspace(lo, hi, n_var)
def coefficient_arrays(model: VarianceModel, variance: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]  # (a, b, sqrt_v_a)
def _assemble_generator(log_variances, a, b, sqrt_v_a, variance, frequency: complex,
                        domestic_rate: float, foreign_rate: float, rho: float) -> np.ndarray
def frequency_generator(contract: PutContract, model: VarianceModel, log_variances: np.ndarray, frequency: complex) -> np.ndarray

@dataclass(frozen=True)
class Propagators:
    omega: np.ndarray
    weights: np.ndarray
    chi: float
    log_variances: np.ndarray
    variance: np.ndarray
    dt: float
    n_time: int
    matrices: np.ndarray        # (n_omega, n_var, n_var) complex128 = expm(dt * A_k)、k = -omega - i*chi
    coefficients_tag: str       # "model" または "fixture:<4配列のsha256>"
    digest: str
    setup_seconds: float
    nbytes: int

def build_propagators(contract, model, config, *, coefficients: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None) -> Propagators
def check_propagators(propagators: Propagators, contract, model, config) -> None      # 不一致はValueError("propagators were built for different inputs")
def inverse_sum(propagators: Propagators, log_spots: np.ndarray, coefficients: np.ndarray) -> np.ndarray   # (len(x), n_var)
def interpolate_at_variance(node_values: np.ndarray, log_variances: np.ndarray, v0: float) -> np.ndarray
def european_put(contract, model, spots, config, *, propagators: Propagators | None = None) -> np.ndarray   # 価格/K
def generator_diagnostics(contract, model, config) -> dict
```

- [ ] **Step 1: 失敗するテストを書く**

```python
"""DSINC fixed-frequency propagation and European prices (3/2 and Heston controls)."""

import math
from dataclasses import replace

import numpy as np
import pytest
from hullkit import bsm
from hullkit._dsinc_spectral import (
    _assemble_generator,
    build_propagators,
    coefficient_arrays,
    european_put,
    frequency_generator,
    frequency_rule,
    generator_diagnostics,
    interpolate_at_variance,
    variance_grid,
)
from hullkit._dsinc_types import PutContract, SpectralConfig, VarianceModel
from hullkit.stochastic_volatility import heston_price
from scipy.interpolate import CubicSpline
from scipy.linalg import expm

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
THREE_HALVES = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
HESTON = VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
HESTON_BOUNDS = (math.log(0.002), math.log(0.4))


def config(n_var=160, bounds=(math.log(2e-4), math.log(2.0)), **changes):
    base = dict(n_time=100, n_var=n_var, log_var_bounds=bounds, chi=0.5, panels=PANELS, points_per_panel=12)
    return SpectralConfig(**(base | changes))


def constant_variance(cfg, variance=0.04):
    zero = np.zeros(cfg.n_var)
    return build_propagators(CONTRACT, THREE_HALVES, cfg, coefficients=(zero, zero, zero, np.full(cfg.n_var, variance)))


@pytest.fixture(scope="module")
def heston_base():
    return european_put(CONTRACT, HESTON, SPOTS, config(bounds=HESTON_BOUNDS))


def test_frequency_rule_is_panelwise_gauss_legendre():
    omega, weights = frequency_rule(config())
    assert omega.shape == weights.shape == (108,) and np.all(np.diff(omega) > 0)
    assert weights.sum() == pytest.approx(640.0, rel=1e-13)
    omega, weights = frequency_rule(config(panels=(0.0, 2.0, 5.0), points_per_panel=4))
    assert np.sum(weights * omega**7) == pytest.approx(5.0**8 / 8, rel=1e-12)


def test_log_variance_coefficients_follow_ito():
    v = np.geomspace(1e-3, 2.0, 7)
    cases = ((THREE_HALVES, 20.0 * v * (0.04 - v), 4.0 * v**1.5), (HESTON, 2.0 * (0.04 - v), 0.2 * np.sqrt(v)))
    for model, drift, diffusion in cases:  # dv = drift dt + diffusion dW, zeta = log v
        a, b, sqrt_v_a = coefficient_arrays(model, v)
        np.testing.assert_allclose(a, diffusion / v, rtol=1e-14)
        np.testing.assert_allclose(b, drift / v - diffusion**2 / (2 * v**2), rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(sqrt_v_a, np.sqrt(v) * a, rtol=1e-14)


def test_both_models_share_one_generator_path():
    z = variance_grid(config(n_var=12))
    for model in (THREE_HALVES, HESTON):
        k = -3.0 - 0.5j
        direct = _assemble_generator(z, *coefficient_arrays(model, np.exp(z)), np.exp(z), k, 0.05, 0.02, model.rho)
        np.testing.assert_array_equal(frequency_generator(CONTRACT, model, z, k), direct)


def test_constant_variance_generator_is_the_bsm_exponent():
    z, zero, v = variance_grid(config(n_var=6)), np.zeros(6), np.full(6, 0.04)
    for omega in (0.5, 7.0, 300.0):
        k = -omega - 0.5j
        exponent = 1j * k * (0.05 - 0.02 - 0.04 / 2) - 0.5 * k * k * 0.04  # log E exp(ik dX) / dt for the BSM log-spot
        m = expm(0.005 * _assemble_generator(z, zero, zero, zero, v, k, 0.05, 0.02, -0.5))
        np.testing.assert_allclose(m, np.exp(0.005 * exponent) * np.eye(6), rtol=0, atol=1e-11)


def test_zero_frequency_preserves_constants():
    for model, cfg in ((THREE_HALVES, config()), (HESTON, config(bounds=HESTON_BOUNDS))):
        z = variance_grid(cfg)
        m = expm(0.005 * frequency_generator(CONTRACT, model, z, 0.0))
        np.testing.assert_allclose(m @ np.ones(z.size), 1.0, rtol=0, atol=1e-12)


def test_neumann_ghost_rows_are_second_order():
    errors = []
    for n in (41, 81):
        z = variance_grid(config(n_var=n, bounds=(math.log(0.01), math.log(0.5))))
        w = math.pi / (z[-1] - z[0])
        f, fp, fpp = np.cos(w * (z - z[0])), -w * np.sin(w * (z - z[0])), -(w**2) * np.cos(w * (z - z[0]))
        a, b, _ = coefficient_arrays(THREE_HALVES, np.exp(z))
        applied = frequency_generator(CONTRACT, THREE_HALVES, z, 0.0).real @ f
        errors.append(np.max(np.abs(applied - (0.5 * a**2 * fpp + b * fp))))
    assert 1.8 < math.log2(errors[0] / errors[1]) < 2.2  # planning run: 1.997


def test_reciprocal_variance_mean_matches_cir():
    tau = 0.5
    exact = math.exp(-0.8 * tau) / 0.04 + 45.0 * (1.0 - math.exp(-0.8 * tau))  # u = 1/v is CIR: du = (36 - 0.8u)dt - 4 sqrt(u) dW
    errors, steps = [], []
    for n in (160, 240, 320):
        z = variance_grid(config(n_var=n))
        u = expm(tau * frequency_generator(CONTRACT, THREE_HALVES, z, 0.0).real) @ np.exp(-z)
        errors.append(abs(CubicSpline(z, u)(math.log(0.04)) - exact) / exact)
        steps.append(z[1] - z[0])
    orders = [math.log(errors[i] / errors[i + 1]) / math.log(steps[i] / steps[i + 1]) for i in range(2)]
    assert errors[-1] <= 1e-4 and all(1.5 <= p <= 2.5 for p in orders)  # planning run: 6.57e-5, 2.91e-5, 1.63e-5


def test_heston_european_matches_the_existing_cf_pricer(heston_base):
    reference = [heston_price(s, 1.0, 0.05, 0.5, 0.04, 2.0, 0.04, 0.2, -0.5, dividend_yield=0.02, kind="put") for s in SPOTS]
    np.testing.assert_allclose(heston_base, reference, rtol=0, atol=2e-5)  # planning run: <= 2.1e-7
    flipped = european_put(CONTRACT, replace(HESTON, rho=0.5), SPOTS, config(bounds=HESTON_BOUNDS))
    assert np.max(np.abs(flipped - reference)) > 1e-4  # a mixed-term sign error cannot pass (planning run: 3.9e-3)


@pytest.mark.parametrize("chi, tol", [(0.5, 1e-7), (0.25, 5e-6), (0.75, 5e-6)])
def test_constant_variance_european_matches_bsm(chi, tol):
    cfg = config(n_var=8, chi=chi)
    got = european_put(CONTRACT, THREE_HALVES, SPOTS, cfg, propagators=constant_variance(cfg))
    reference = [bsm.put_price(s, 1.0, 0.05, 0.2, 0.5, q=0.02) for s in SPOTS]
    np.testing.assert_allclose(got, reference, rtol=0, atol=tol)  # planning run: 4e-8 (chi=.5), 2e-6 (.25, .75)


def test_variance_interpolation_is_not_a_knot_and_refuses_extrapolation():
    z = np.linspace(-3.0, -1.0, 21)
    values = np.vstack([np.sin(3.0 * z), np.exp(z)])
    got = interpolate_at_variance(values, z, math.exp(-1.73))
    np.testing.assert_allclose(got, CubicSpline(z, values, axis=1, bc_type="not-a-knot")(-1.73), rtol=0, atol=1e-15)
    np.testing.assert_allclose(interpolate_at_variance(values, z, math.exp(z[0])), values[:, 0], rtol=0, atol=1e-12)
    for outside in (math.exp(z[0] - 1e-9), math.exp(z[-1] + 1e-9)):
        with pytest.raises(ValueError, match="outside"):
            interpolate_at_variance(values, z, outside)


def test_heston_european_is_insensitive_to_a_half_cell_offset(heston_base):
    h = (HESTON_BOUNDS[1] - HESTON_BOUNDS[0]) / 159
    moved = european_put(CONTRACT, HESTON, SPOTS, config(bounds=(HESTON_BOUNDS[0] + h / 2, HESTON_BOUNDS[1] + h / 2)))
    assert np.max(np.abs(moved - heston_base)) <= 1e-7  # planning run: 7.3e-9


@pytest.mark.parametrize(
    "spots, bounds",
    [(SPOTS, (math.log(0.05), math.log(2.0))), (np.array([0.9, -1.0]), None),
     (np.array([[1.0]]), None), (np.array([math.nan]), None)],
)
def test_european_rejects_bad_inputs(spots, bounds):
    cfg = config(n_var=8) if bounds is None else config(n_var=8, bounds=bounds)
    with pytest.raises(ValueError):
        european_put(CONTRACT, THREE_HALVES, spots, cfg)


def test_propagators_are_bound_to_their_inputs():
    cfg = config(n_var=8)
    prop = build_propagators(CONTRACT, THREE_HALVES, cfg)
    european_put(CONTRACT, THREE_HALVES, SPOTS, cfg, propagators=prop)
    european_put(replace(CONTRACT, strike=100.0), THREE_HALVES, 100.0 * SPOTS, cfg, propagators=prop)  # strike is not bound
    mismatches = [
        (replace(CONTRACT, domestic_rate=0.06), THREE_HALVES, cfg),
        (replace(CONTRACT, foreign_rate=0.01), THREE_HALVES, cfg),
        (replace(CONTRACT, expiry=1.0), THREE_HALVES, cfg),
        (CONTRACT, replace(THREE_HALVES, xi=3.9), cfg),
        (CONTRACT, THREE_HALVES, replace(cfg, chi=0.25)),
    ]
    for contract, model, other in mismatches:
        with pytest.raises(ValueError, match="propagators"):
            european_put(contract, model, SPOTS, other, propagators=prop)


def test_s0_generator_diagnostics_record_the_nonmonotone_scheme():
    d = generator_diagnostics(CONTRACT, THREE_HALVES, config())
    assert d["scheme_nonmonotone"] is True and d["zero_frequency_min_entry"] == pytest.approx(-0.0316, abs=5e-4)
    assert d["zero_frequency_row_sum_error"] <= 1e-12
    assert 14.0 < d["peclet_max"] < 15.0 and d["peclet_above_one"] == 45


def test_s0_european_matches_table_3b():
    got = european_put(CONTRACT, THREE_HALVES, SPOTS, config())
    np.testing.assert_allclose(got, [0.102557, 0.047224, 0.019105], rtol=0, atol=6e-6)  # planning run: <= 3.4e-7


def test_zero_expiry_european_is_the_payoff():
    got = european_put(replace(CONTRACT, expiry=0.0), THREE_HALVES, SPOTS, config(n_var=8))
    np.testing.assert_array_equal(got, np.maximum(1.0 - SPOTS, 0.0))
```

- [ ] **Step 2: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_spectral.py`
Expected: FAIL（`ModuleNotFoundError: No module named 'hullkit._dsinc_spectral'`）

- [ ] **Step 3: `_dsinc_spectral.py`を実装する**

- 周波数: 各パネル[p_q, p_{q+1}]に`numpy.polynomial.legendre.leggauss(points_per_panel)`を写す。ω=½(p_{q+1}−p_q)g+½(p_{q+1}+p_q)、ϖ=½(p_{q+1}−p_q)w。
- 係数: 3/2はa=ξ√v、b=κθ−(κ+ξ²/2)v、√v·a=ξv。Hestonはa=ξ/√v、b=κθ/v−κ−ξ²/(2v)、√v·a=ξ。
- 作用素（割引の−rdは入れない）: d=½a²、c=b+ikρ·sqrt_v_a、z=ik(rd−rf)−½(k²+ik)v。
  - 内部の行: A[i,i−1]=d/h²−c/(2h)、A[i,i]=−2d/h²+z、A[i,i+1]=d/h²+c/(2h)。
  - 両端（ghost反射）: A[0,0]=−2d₀/h²+z₀、A[0,1]=2d₀/h²、上端も対称に置く。
- 伝播: k_j=−ω_j−iχ、M_j=`scipy.linalg.expm(dt*A_{k_j})`、dt=T/n_time。fixture（`coefficients`を渡した場合）では、`variance`を節点のvとしてzに使う。
- digest: `canonical_digest(rd, rf, T, model, config, coefficients_tag)`。strikeは含めない。`check_propagators`は、保存したtagで同じdigestを計算し直して比べる。
- European（Eq.(61)）: E=M^N·1をN回の一括積で作る。s=iω−χとして、節点値=e^{−rdT}[1+(1/π)Re Σ_j ϖ_j e^{(χ−iω_j)x}E_j/(s_j(1+s_j))]。最後にv0で補間する。
- `inverse_sum`: (1/π)Re((exp(outer(x, χ−iω))·ϖ) @ C)。
- 補間: `CubicSpline(log_variances, node_values, axis=-1, bc_type="not-a-knot")`をlog v0で評価する。log v0がz[0]−1e-12より下か、z[−1]+1e-12より上なら、"outside the variance grid"でValueErrorにする。
- 入力の検証: spotsは1次元・finite・正。v0の範囲は伝播を作る前に確かめる。T=0なら伝播を作らずにmax(1−S/K,0)を返す。
- 診断:
  - Pe=\|b\|h/a²の最大値（`peclet_max`）と、Pe>1の節点数（`peclet_above_one`）。
  - M₀=expm(dt·A₀).realの最小成分（`zero_frequency_min_entry`）と、max\|M₀·1−1\|（`zero_frequency_row_sum_error`）。
  - `scheme_nonmonotone = min_entry < -1e-10`。
  - 値はPythonのfloat/int/boolで返す。

- [ ] **Step 4: 通ることを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_spectral.py`
Expected: `21 passed`（約25秒）

- [ ] **Step 5: READMEと索引を書く**

- `research/DSINC/README.md`に「目的と範囲」「方法と出典」「再実行」を書く。「方法と出典」の表は次のとおり。
  - 論文由来: 作用素Eq.(53)、3/2の係数（Itôで導出し直したもの）、ζ格子[log 2e-4, log 2]と160節点、パネル{0,…,640}の各12点、反射周波数とχ=.5、n_time=200T、端点の半重み。
  - 独自の選択: ghost反射のNeumann、not-a-knotによるv0補間、根の走査と最上位の交差（D-1）、独立FD。
- `MODEL_INDEX.md`のDSINCの節に次の行を足す。

  `` | `hullkit._dsinc_spectral` | Private `hullkit._dsinc_spectral:frequency_rule`, `hullkit._dsinc_spectral:coefficient_arrays`, `hullkit._dsinc_spectral:frequency_generator`, `hullkit._dsinc_spectral:build_propagators`, `hullkit._dsinc_spectral:european_put`, `hullkit._dsinc_spectral:interpolate_at_variance`, `hullkit._dsinc_spectral:generator_diagnostics` | Panel Gauss-Legendre reflected frequencies, central differences with ghost-reflection Neumann ends, expm propagators bound to their inputs, Eq. (61) European; Ito coefficients, BSM exponent, CIR mean of 1/v (order 2), existing Heston CF control, BSM chi sweep, offset and Table 3(b) tests in test_dsinc_spectral.py | ``

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_model_index.py johnhull/hullkit/tests/test_docstrings.py`
Expected: すべてPASS

- [ ] **Step 6: Commit**

```bash
git -C $WT add johnhull/hullkit/src/hullkit/_dsinc_spectral.py johnhull/hullkit/tests/test_dsinc_spectral.py johnhull/research/DSINC/README.md johnhull/MODEL_INDEX.md
git -C $WT commit -m "Add the DSINC fixed-frequency propagators and European put"
```

---

### Task 4: 独立した3/2のFD参照

**Files:**
- Create: `johnhull/research/DSINC/reference_fd.py`
- Test: `johnhull/hullkit/tests/test_dsinc_reference.py`

**Interfaces:**
- Consumes: Task 1の`PutContract`、`VarianceModel`だけ（spectralのモジュールはimportしない）
- Produces:

```python
@dataclass(frozen=True)
class FDConfig:
    n_x: int
    n_var: int
    n_time: int
    log_spot_bounds: tuple[float, float]
    log_var_bounds: tuple[float, float]
    exercises: tuple[str, ...] = ("european", "american")
    record_boundary: bool = False

@dataclass(frozen=True)
class FDCoefficients:
    variance: np.ndarray        # x方向の項に使うv（n_var,）
    var_drift: np.ndarray       # V_zetaの係数
    var_diffusion: np.ndarray   # V_zeta_zetaの係数
    cross: np.ndarray           # V_x_zetaの係数

def three_halves_coefficients(model: VarianceModel, log_variances: np.ndarray) -> FDCoefficients
def assemble_operator(contract: PutContract, coefficients: FDCoefficients, log_spots: np.ndarray,
                      log_variances: np.ndarray) -> tuple[scipy.sparse.csc_matrix, np.ndarray, np.ndarray]   # (A, left, right)

@dataclass(frozen=True)
class FDResult:
    european: np.ndarray | None        # 価格/K
    american: np.ndarray | None
    log_spots: np.ndarray
    log_variances: np.ndarray
    contact_edge: np.ndarray | None    # (n_time+1, n_var)、暦のindex k（t_k = k*T/n_time）。記録しない・接触なしはNaN
    complementarity: dict              # min_payoff_gap, min_multiplier, max_complementarity_product, solve_residual
    setup_seconds: float
    solve_seconds: dict[str, float]
    lu_nnz: int
    maxrss_bytes: int

def reference_put(contract, model, spots, config, *, coefficients: FDCoefficients | None = None) -> FDResult
```

- [ ] **Step 1: 失敗するテストを書く**

```python
"""Independent 3/2 finite-difference reference (no spectral imports)."""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit import bsm, trees
from hullkit._dsinc_types import PutContract, VarianceModel

PATH = Path(__file__).resolve().parents[2] / "research/DSINC/reference_fd.py"
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
WIDE = (math.log(1e-5), math.log(8.0))
NARROW = (math.log(0.02), math.log(0.08))


@pytest.fixture(scope="module")
def fd():
    spec = importlib.util.spec_from_file_location("dsinc_reference_fd_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def constant(fd, n_var=4, variance=0.04):
    zero = np.zeros(n_var)
    return fd.FDCoefficients(variance=np.full(n_var, variance), var_drift=zero, var_diffusion=zero, cross=zero)


def test_reference_does_not_import_the_spectral_modules():
    text = PATH.read_text()
    assert "_dsinc_spectral" not in text and "_dsinc_american" not in text


def test_operator_matches_the_three_halves_generator(fd):
    errors = []
    for nx, nv in ((41, 21), (81, 41)):
        x, z = np.linspace(-0.6, 0.6, nx), np.linspace(math.log(0.01), math.log(0.5), nv)
        A, _, _ = fd.assemble_operator(CONTRACT, fd.three_halves_coefficients(MODEL, z), x, z)
        X, Z = np.meshgrid(x, z, indexing="ij")
        w = math.pi / (z[-1] - z[0])
        f = np.exp(0.3 * X) * np.cos(w * (Z - z[0]))
        fz = -w * np.exp(0.3 * X) * np.sin(w * (Z - z[0]))
        v = np.exp(Z)
        exact = ((0.05 - 0.02 - v / 2) * 0.3 * f + 0.5 * v * 0.09 * f + (0.8 - 28.0 * v) * fz
                 + (-0.5 * 4.0 * v) * 0.3 * fz + 8.0 * v * (-(w**2) * f) - 0.05 * f)
        applied = (A @ f[1:-1].ravel()).reshape(nx - 2, nv)
        errors.append(np.max(np.abs(applied[1:-1] - exact[2:-2])))  # rows whose x-neighbours are unknowns
    assert 1.8 < math.log2(errors[0] / errors[1]) < 2.2  # planning run: 1.986 (flipping rho gives an error of 0.14)


def test_constant_variance_fixture_matches_bsm_and_crr(fd):
    cfg = fd.FDConfig(n_x=961, n_var=4, n_time=300, log_spot_bounds=(-1.2, 1.2), log_var_bounds=NARROW)
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg, coefficients=constant(fd))
    eu = [bsm.put_price(s, 1.0, 0.05, 0.2, 0.5, q=0.02) for s in SPOTS]
    am = [trees.crr_price(s, 1.0, 0.05, 0.2, 0.5, 4000, q=0.02, kind="put", american=True) for s in SPOTS]
    np.testing.assert_allclose(out.european, eu, rtol=0, atol=5e-6)  # planning run: 2.2e-6
    np.testing.assert_allclose(out.american, am, rtol=0, atol=2e-5)  # planning run: 4.0e-6


def test_american_solution_satisfies_the_obstacle(fd):
    cfg = fd.FDConfig(n_x=121, n_var=41, n_time=60, log_spot_bounds=(-1.2, 1.2), log_var_bounds=WIDE)
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg)
    c = out.complementarity
    assert c["min_payoff_gap"] >= 0.0 and c["min_multiplier"] >= 0.0
    assert c["max_complementarity_product"] <= 1e-14 and c["solve_residual"] <= 1e-10
    assert np.all(out.american >= out.european)


def test_contact_edges_are_indexed_by_calendar_step(fd):
    cfg = fd.FDConfig(n_x=241, n_var=4, n_time=8, log_spot_bounds=(-1.2, 1.2), log_var_bounds=NARROW,
                      exercises=("american",), record_boundary=True)
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg, coefficients=constant(fd))
    edge = out.contact_edge
    assert edge.shape == (9, 4) and np.all(np.isnan(edge[8])) and np.all(np.isfinite(edge[:8]))
    assert np.all(np.diff(edge[:8, 0]) >= 0.0)  # the put boundary rises towards expiry
    np.testing.assert_array_equal(edge[:, 0], edge[:, 3])  # zero variance coefficients decouple the rows
    assert out.european is None


def test_wide_domain_base_level_matches_the_planning_run(fd):
    cfg = fd.FDConfig(n_x=241, n_var=101, n_time=150, log_spot_bounds=(-1.2, 1.2), log_var_bounds=WIDE)
    out = fd.reference_put(CONTRACT, MODEL, SPOTS, cfg)
    np.testing.assert_allclose(out.european, [0.10253835, 0.04718844, 0.01908019], rtol=0, atol=1e-8)
    np.testing.assert_allclose(out.american, [0.10757684, 0.04861780, 0.01946888], rtol=0, atol=1e-8)


@pytest.mark.parametrize("bad", ["heston", "spot", "variance", "expiry", "boundary_without_american"])
def test_reference_rejects_unsupported_inputs(fd, bad):
    def call():
        model, spots, contract, bounds, exercises = MODEL, SPOTS, CONTRACT, WIDE, ("european", "american")
        if bad == "heston":
            model = VarianceModel("heston", kappa=2.0, theta=0.04, xi=0.2, rho=-0.5, v0=0.04)
        elif bad == "spot":
            spots = np.array([0.25])  # log(0.25) < -1.2: outside the x domain, never extrapolated
        elif bad == "variance":
            bounds = (math.log(0.05), math.log(8.0))
        elif bad == "expiry":
            contract = PutContract(strike=1.0, expiry=0.0, domestic_rate=0.05, foreign_rate=0.02)
        else:
            exercises = ("european",)
        cfg = fd.FDConfig(n_x=41, n_var=11, n_time=10, log_spot_bounds=(-1.2, 1.2), log_var_bounds=bounds,
                          exercises=exercises, record_boundary=bad == "boundary_without_american")
        return fd.reference_put(contract, model, spots, cfg)

    with pytest.raises(ValueError):
        call()
```

- [ ] **Step 2: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_reference.py`
Expected: importのテストはFAIL（ファイルがない）、残りはERROR（`FileNotFoundError`）

- [ ] **Step 3: `reference_fd.py`を実装する**

- 格子と未知数: x=linspace(log_spot_bounds, n_x)、ζ=linspace(log_var_bounds, n_var)。未知数はxの内部節点（1..n_x−2）×ζの全節点で、index=i·n_var+j（ζを内側）。
- 3/2の係数: variance=e^ζ、var_drift=κθ−(κ+ξ²/2)v、var_diffusion=½ξ²v、cross=ρξv。
- 作用素: (rd−rf−v/2)∂x+½v∂xx+var_drift∂ζ+var_diffusion∂ζζ+cross∂xζ−rdを中心差分で作る。混合項は(V_{i+1,j+1}−V_{i+1,j−1}−V_{i−1,j+1}+V_{i−1,j−1})/(4dx·h)。
  - ζの両端: ghost反射。∂ζ=0なのでvar_driftと混合項は消え、∂ζζは2(V_隣−V_端)/h²になる。
  - xの両端: Dirichlet。`left`は左端の値に掛かる係数のベクトル。右端の値は0。左端の値はζによらないので、混合項からの寄与は打ち消し合う。
- 時間（τ=満期までの時間）: dτ=T/n_time。陰的Eulerの半ステップ（k=dτ/2）を4回行ってから、Crank–Nicolsonを(n_time−2)回行う。どちらも行列は(I−½dτA)で、LUは1つで足りる。
  - IE: rhs=V+k·left·g_L(τ+k)
  - CN: rhs=V+½k·A V+½k·left·(g_L(τ)+g_L(τ+k))
  - European: V=LU⁻¹rhs
  - American（Ikonen–Toivanen）: Ṽ=LU⁻¹(rhs+kλ)、V=max(Ṽ−kλ, g)、λ=max(0, λ+(g−Ṽ)/k)
  - 左端の値g_L: Europeanはmax(e^{−rdτ}−e^{x_min}e^{−rfτ}, 0)、Americanは1−e^{x_min}。初期値はV=g=max(1−e^x, 0)、λ=0。
- 境界の記録（Americanで`record_boundary`のとき）:
  - IEの半ステップの2回目と4回目の後、およびCNの各ステップの後を、水準m=1,2,3,…,n_timeとし、暦のk=n_time−mに記録する。
  - 接触は(λ>1e-10)かつ(\|V−g\|≤1e-8)。各ζ行で接触している最大のxを端とし、接触がなければNaNにする。
- 最終ステップの相補性: `min_payoff_gap`=min(V−g)、`min_multiplier`=min(λ)、`max_complementarity_product`=max(λ(V−g))、`solve_residual`=‖(I−½dτA)Ṽ−(rhs+kλ_old)‖∞/max(1,‖rhs‖∞)。
- 価格: 境界の値を含めた全格子で、まずζ方向に`CubicSpline(not-a-knot)`をlog v0で評価し、次にx方向の`CubicSpline`をlog(S/K)で評価する。
- 検証:
  - `coefficients`がなければmodel.kindは"three_halves"に限る。
  - T>0。spotsは1次元・正・finiteで、xの範囲の内側にあること。log v0はζの範囲内（±1e-12）。
  - FDConfigは`__post_init__`で検証する: n_x≥5、n_var≥4、n_time≥3、boundsはfiniteで昇順、exercisesは{"european","american"}の空でない部分集合、`record_boundary`には"american"が必要。JSONから来たlistはtupleにそろえる。
- 価格の境界の値: 全格子の左端の行はg_L(T)、右端の行は0（Step 1の`test_wide_domain_base_level_matches_the_planning_run`の値はこの組み方で再現した）。
- 計時と記録: setup（作用素とLU）と、exerciseごとの解の秒数を分けて測る。`lu_nnz`=L.nnz+U.nnz、`maxrss_bytes`=ru_maxrss·1024。

- [ ] **Step 4: 通ることを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_reference.py`
Expected: `11 passed`（約6秒）

- [ ] **Step 5: Commit**

```bash
git -C $WT add johnhull/research/DSINC/reference_fd.py johnhull/hullkit/tests/test_dsinc_reference.py
git -C $WT commit -m "Add the independent 3/2 finite-difference reference"
```

---

### Task 5: EEPの再帰と節点ごとの行使境界

**Files:**
- Create: `johnhull/hullkit/src/hullkit/_dsinc_american.py`
- Test: `johnhull/hullkit/tests/test_dsinc_american.py`
- Modify: `johnhull/MODEL_INDEX.md`（DSINCの節に1行）

**Interfaces:**
- Consumes: Task 1の型・`BOUNDARY_STATUS`・`FAILURE_CODES`・`PricingFailure`・`PricingResult`。Task 3の`build_propagators`・`check_propagators`・`inverse_sum`・`interpolate_at_variance`・`generator_diagnostics`・`Propagators`
- Produces:

```python
def payoff_transform(omega: np.ndarray, chi: float, log_boundary: np.ndarray, contract: PutContract) -> np.ndarray   # (n_omega, n_var)

class BoundaryResidual(Protocol):
    def at(self, x: np.ndarray) -> np.ndarray: ...        # (n_var,) -> (n_var,)、節点iのx[i]での残差
    def on_grid(self, grid: np.ndarray) -> np.ndarray: ... # (m,) -> (m, n_var)

@dataclass(frozen=True)
class BoundarySlice:
    roots: np.ndarray        # (n_var,)、失敗した節点はNaN
    status: np.ndarray       # int8、BOUNDARY_STATUSのcode
    crossings: np.ndarray    # int16、採用したbracket内の符号変化の数（bracketがなければ0）
    spread: np.ndarray       # 最下位と最上位の+→−交差の距離（交差が1つなら0）
    width: np.ndarray        # 採用した半幅（なければNaN）
    iterations: np.ndarray   # int16、二分法の反復数

def scan_spacing(config: SpectralConfig) -> float          # min(pi / (2 * panels[-1]), root_widths[0] / 64)
def local_boundary(residual: BoundaryResidual, predictor: np.ndarray, config: SpectralConfig) -> BoundarySlice
def premium_with_boundary(contract: PutContract, propagators: Propagators, log_boundary: np.ndarray,
                          spots: np.ndarray) -> np.ndarray  # (n_spots, n_var)、与えた境界でのt0のEEP/K
def american_put(contract, model, spots, config, *, propagators: Propagators | None = None) -> PricingResult
```

`scan_spacing`の刻みδは、設計§4のm点則（各bracketでm=max(65, ceil(2ω_max(hi−lo)/π)+1)点、刻み(hi−lo)/(m−1)）より常に細かいわけではない。S0はδ=root_widths[0]/64で、m点則の刻み以下になり、影響を受けない。S1・S2はδ=π/(2·panels[−1])で、ceilの切り上げが効く：最初のbracket（半幅.1）が0で切られてhi−loが.1をわずかに超えると、m点則の刻みがδを下回り、δのほうが粗くなる。粗くなる割合は、ω_maxをcutoffとしてS1で最大1.22%、S2で最大0.61%（最上位の節点をω_maxとするとS1で0.75%、S2で0.35%）。コード（`_dsinc_american.py:116-121`）は凍結済みで変えない。既知の点として[REVIEW.md](../../../research/DSINC/REVIEW.md)に記録した。

`PricingResult.diagnostics`のkey:
- `boundary_status`（"ok"または"not_applicable"）、`status_counts`、`multiple_crossings_max_variance`、`max_crossing_spread`、`scan_spacing`、`max_root_residual`
- `generator`（`generator_diagnostics`の結果）
- `bounds`: `american_minus_payoff_min`、`american_minus_european_min`、`american_minus_strike_max`（A−1の最大値）、`european_lower_gap_min`（E−max(e^{−rdT}−(S/K)e^{−rfT}, 0)の最小値）、`european_upper_gap_max`（E−e^{−rdT}の最大値）
- `setup_seconds`、`recursion_seconds`、`query_seconds`、`propagator_bytes`

- [ ] **Step 1: 失敗するテストを書く**

```python
"""DSINC American recursion: payoff transform, time quadrature, boundary roots and paper anchors."""

import math
from dataclasses import replace

import numpy as np
import pytest
from hullkit._dsinc_american import american_put, local_boundary, payoff_transform, premium_with_boundary, scan_spacing
from hullkit._dsinc_spectral import build_propagators, european_put
from hullkit._dsinc_types import BOUNDARY_STATUS, PricingFailure, PutContract, SpectralConfig, VarianceModel
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm

PANELS = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0, 640.0)
CONTRACT = PutContract(strike=1.0, expiry=0.5, domestic_rate=0.05, foreign_rate=0.02)
MODEL = VarianceModel("three_halves", kappa=20.0, theta=0.04, xi=4.0, rho=-0.5, v0=0.04)
SPOTS = np.array([0.9, 1.0, 1.1])
SCAN = np.linspace(0.70, 0.95, 126)
S0 = SpectralConfig(n_time=100, n_var=160, log_var_bounds=(math.log(2e-4), math.log(2.0)), chi=0.5, panels=PANELS, points_per_panel=12)
SMALL = SpectralConfig(n_time=40, n_var=24, log_var_bounds=(math.log(0.005), math.log(0.3)), chi=0.5,
                       panels=(0.0, 2.0, 5.0, 10.0, 20.0, 40.0), points_per_panel=4)
CONSTANT = SpectralConfig(n_time=2, n_var=4, log_var_bounds=(math.log(0.02), math.log(0.08)), chi=0.5, panels=PANELS, points_per_panel=12)
RD, RF, VAR = 0.05, 0.02, 0.04


def code(name):
    return BOUNDARY_STATUS[name]


def constant_propagators(cfg):
    zero = np.zeros(cfg.n_var)
    return build_propagators(CONTRACT, MODEL, cfg, coefficients=(zero, zero, zero, np.full(cfg.n_var, VAR)))


def j_term(x, tau, c):
    """E[(rd - rf e^X) 1{X <= c}] for X ~ N(x + (rd - rf - v/2) tau, v tau)."""
    m, s = x + (RD - RF - VAR / 2) * tau, math.sqrt(VAR * tau)
    return RD * norm.cdf((c - m) / s) - RF * math.exp(m + s * s / 2) * norm.cdf((c - m - s * s) / s)


def bsm_put(x, tau):
    s = math.sqrt(VAR * tau)
    d1 = (x + (RD - RF + VAR / 2) * tau) / s
    return math.exp(-RD * tau) * norm.cdf(s - d1) - math.exp(x - RF * tau) * norm.cdf(-d1)


class Shifted:
    """R_i(x) = g(x - shift_i): one residual profile moved by a node shift."""

    def __init__(self, g, shifts):
        self.g, self.shifts = g, np.asarray(shifts, float)

    def at(self, x):
        return self.g(np.asarray(x, float) - self.shifts)

    def on_grid(self, grid):
        return self.g(np.asarray(grid, float)[:, None] - self.shifts[None, :])


@pytest.fixture(scope="module")
def s0_propagators():
    return build_propagators(CONTRACT, MODEL, S0)


@pytest.fixture(scope="module")
def s0_result(s0_propagators):
    return american_put(CONTRACT, MODEL, np.r_[SPOTS, SCAN], S0, propagators=s0_propagators)


@pytest.mark.parametrize("omega", [0.5, 3.0, 17.0])
def test_payoff_transform_matches_quadrature(omega):
    s, c = 1j * omega - 0.5, -0.2

    def part(x, imag):
        value = (((RD - RF * math.exp(x)) if x <= c else 0.0) - RD) * np.exp(s * x)
        return value.imag if imag else value.real

    expected = sum((1j if imag else 1.0) * quad(part, lo, hi, args=(imag,), limit=400)[0]
                   for imag in (False, True) for lo, hi in ((-60.0, c), (c, 60.0)))
    got = payoff_transform(np.array([omega]), 0.5, np.array([c]), CONTRACT)
    assert got.shape == (1, 1) and abs(got[0, 0] - expected) <= 1e-8  # planning run: 1.5e-9


def test_flat_boundary_premium_matches_the_trapezoid_sum():
    cfg = replace(CONSTANT, n_time=100)
    got = premium_with_boundary(CONTRACT, constant_propagators(cfg), np.full((101, 4), -0.25), SPOTS)[:, 0]
    dt = 0.5 / 100
    weights = np.r_[np.full(99, dt), dt / 2]  # t_1 .. t_N; t_0 lies outside the exercise region for these spots
    expected = [sum(w * math.exp(-RD * k * dt) * j_term(math.log(s), k * dt, -0.25) for k, w in zip(range(1, 101), weights, strict=True)) for s in SPOTS]
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-6)  # planning run: 2.4e-7


def two_step_reference():
    """Boundaries and t0 prices for T = .5, N = 2 from explicit normal integrals."""
    dt = 0.25

    def residual(x, later):
        rhs = bsm_put(x, 2 * dt - later * dt) + dt / 4 * (RD - RF * math.exp(x))
        return 1.0 - math.exp(x) - rhs - later_terms(x, later)

    def later_terms(x, later):
        if later == 1:  # boundary at t_1: only t_2 (weight dt/2, boundary 0) follows
            return dt / 2 * math.exp(-RD * dt) * j_term(x, dt, 0.0)
        return dt * math.exp(-RD * dt) * j_term(x, dt, x1) + dt / 2 * math.exp(-2 * RD * dt) * j_term(x, 2 * dt, 0.0)

    x1 = brentq(lambda x: residual(x, 1), -1.0, -1e-9, xtol=1e-14)
    x0 = brentq(lambda x: residual(x, 0), -1.0, -1e-9, xtol=1e-14)
    prices = [bsm_put(math.log(s), 2 * dt) + later_terms(math.log(s), 0) for s in SPOTS]  # no t_0 endpoint term
    return (x0, x1), prices


def test_two_step_american_matches_explicit_sums():
    (x0, x1), prices = two_step_reference()  # planning run: x*_0 = -0.20568247, x*_1 = -0.16491088
    out = american_put(CONTRACT, MODEL, SPOTS, CONSTANT, propagators=constant_propagators(CONSTANT))
    np.testing.assert_allclose(out.log_boundary[:, 0], [x0, x1, 0.0], rtol=0, atol=2e-6)  # planning run: 7.1e-7
    np.testing.assert_allclose(out.american, prices, rtol=0, atol=2e-7)  # planning run: 4.1e-8


def test_single_crossing_root():
    out = local_boundary(Shifted(lambda u: -u, [-0.15, -0.05]), np.array([-0.1, -0.1]), S0)
    np.testing.assert_allclose(out.roots, [-0.15, -0.05], rtol=0, atol=1e-10)
    assert list(out.status) == [code("single")] * 2 and list(out.width) == [0.1, 0.1]


def test_missing_and_reversed_brackets_fail():
    flat = local_boundary(Shifted(lambda u: -1.0 + 0.0 * u, [0.0]), np.array([-0.1]), S0)
    reversed_ = local_boundary(Shifted(lambda u: u, [-0.15]), np.array([-0.1]), S0)
    assert flat.status[0] == code("missing_sign_change") and np.isnan(flat.roots[0])
    assert reversed_.status[0] == code("wrong_orientation") and np.isnan(reversed_.roots[0])


def test_multiple_crossings_choose_upper_or_lower():
    def g(u):  # crossings at x = -0.15 (+ to -), -0.12 (- to +), -0.09 (+ to -) for a shift of -0.12
        return -1e3 * (u + 0.03) * u * (u - 0.03)

    for crossing, root in (("upper", -0.09), ("lower", -0.15)):
        out = local_boundary(Shifted(g, [-0.12]), np.array([-0.1]), replace(S0, crossing=crossing))
        assert out.status[0] == code("multiple_crossings") and out.crossings[0] == 3
        assert out.roots[0] == pytest.approx(root, abs=1e-10)
        assert out.spread[0] == pytest.approx(0.06, abs=2 * scan_spacing(S0))


def test_zero_runs_are_ambiguous_but_a_single_zero_is_a_crossing():
    def flat(u):  # exact zeros on [-0.05, 0.05]
        return np.where(u < -0.05, 1.0, np.where(u > 0.05, -1.0, 0.0))

    assert local_boundary(Shifted(flat, [-0.1]), np.array([-0.1]), S0).status[0] == code("ambiguous_contact")
    delta = scan_spacing(S0)
    on_grid = local_boundary(Shifted(lambda u: -u, [-80 * delta]), np.array([-0.1]), S0)  # root exactly on a scan point
    assert on_grid.status[0] == code("single") and on_grid.roots[0] == pytest.approx(-80 * delta, abs=1e-10)


def test_nonfinite_and_maxiter_fail():
    def holed(u):
        return np.where(np.abs(u) < 0.01, np.nan, -u)

    def jump(u):  # a sign change with no zero: bisection never reaches |R| <= tol
        return np.where(u < 0.0, 1.0, -1.0)

    assert local_boundary(Shifted(holed, [-0.12]), np.array([-0.1]), S0).status[0] == code("nonfinite")
    maxiter = local_boundary(Shifted(jump, [-0.12]), np.array([-0.1]), S0)
    assert maxiter.status[0] == code("maxiter") and maxiter.iterations[0] == 60


def test_failure_records_the_whole_time_slice():
    with pytest.raises(PricingFailure) as info:
        american_put(CONTRACT, MODEL, SPOTS, replace(SMALL, root_widths=(1e-4,)))
    details = info.value.details
    status = np.asarray(details["boundary_status"])
    assert info.value.code == "boundary_failure" and details["time_index"] == 39
    assert np.all(status[39] == code("missing_sign_change")) and np.all(status[:39] == code("not_run"))
    assert np.all(status[40] == code("terminal")) and np.all(np.isnan(np.asarray(details["log_boundary"])[:40]))
    assert details["last_completed_time_index"] == 40


def test_zero_expiry_returns_the_payoff_without_a_boundary():
    out = american_put(replace(CONTRACT, expiry=0.0), MODEL, SPOTS, SMALL)
    payoff = np.maximum(1.0 - SPOTS, 0.0)
    np.testing.assert_array_equal(out.american, payoff)
    np.testing.assert_array_equal(out.european, payoff)
    np.testing.assert_array_equal(out.early_exercise_premium, np.zeros(3))
    assert out.times.shape == (0,) and out.log_variances.shape == (0,)
    assert out.log_boundary.shape == out.boundary_status.shape == (0, 0)
    assert out.diagnostics["boundary_status"] == "not_applicable"


def test_spot_order_and_strike_homogeneity():
    base = american_put(CONTRACT, MODEL, SPOTS, SMALL)
    shuffled = american_put(CONTRACT, MODEL, np.array([1.1, 0.9, 1.0, 0.9]), SMALL)
    np.testing.assert_allclose(shuffled.american, base.american[[2, 0, 1, 0]], rtol=0, atol=1e-15)
    scaled = american_put(replace(CONTRACT, strike=100.0), MODEL, 100.0 * SPOTS, SMALL)
    np.testing.assert_allclose(scaled.american, base.american, rtol=0, atol=1e-15)
    deep = american_put(CONTRACT, MODEL, np.array([0.55, 0.6]), SMALL)  # below every node's t0 boundary (min -0.38)
    np.testing.assert_allclose(deep.american, [0.45, 0.4], rtol=0, atol=1e-14)


def test_prices_near_the_boundary_stay_within_the_bound_tolerance(s0_result):
    gap = s0_result.american[3:] - np.maximum(1.0 - SCAN, 0.0)
    assert gap.min() >= -2e-5  # planning run: -1.54e-5 at S/K = 0.832 (the v0 spline mixes exercised and continuation nodes)
    assert s0_result.diagnostics["bounds"]["american_minus_payoff_min"] == pytest.approx(gap.min(), abs=1e-15)
    assert np.all(np.diff(s0_result.american[3:]) < 0.0)


def test_bound_violations_are_reported_not_clipped():
    out = american_put(replace(CONTRACT, expiry=0.01), MODEL, SPOTS, replace(SMALL, n_time=1))
    assert out.european[2] < -1e-3  # cutoff 40 cannot resolve T = .01 (planning run: -1.09e-3); the raw value is kept
    assert out.diagnostics["bounds"]["european_lower_gap_min"] == pytest.approx(out.european[2], abs=1e-12)


def test_s0_reproduces_tables_3b_and_4(s0_result):
    np.testing.assert_allclose(s0_result.american[:3], [0.107601, 0.048662, 0.019499], rtol=0, atol=6e-6)
    np.testing.assert_allclose(s0_result.european[:3], [0.102557, 0.047224, 0.019105], rtol=0, atol=6e-6)
    np.testing.assert_allclose(s0_result.early_exercise_premium[:3], [0.005044, 0.001438, 0.000394], rtol=0, atol=6e-6)


def test_s0_boundary_status_and_residuals(s0_result):
    status = s0_result.boundary_status
    assert status.shape == (101, 160) and np.all(status[-1] == code("terminal"))
    assert not np.isin(status[:-1], [-1, 2, 3, 4, 5, 6]).any()
    rows, cols = np.nonzero(status == code("multiple_crossings"))
    assert rows.size > 0 and np.exp(s0_result.log_variances[cols]).max() < 0.01  # planning run: 58 cases, v <= 6.75e-4
    assert np.all(s0_result.log_boundary[-1] == 0.0) and s0_result.diagnostics["max_root_residual"] <= 1e-8
    assert s0_result.diagnostics["generator"]["scheme_nonmonotone"] is True


def test_american_and_european_paths_share_the_european_leg(s0_result, s0_propagators):
    alone = european_put(CONTRACT, MODEL, SPOTS, S0, propagators=s0_propagators)
    np.testing.assert_allclose(s0_result.european[:3], alone, rtol=0, atol=1e-13)
```

- [ ] **Step 2: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_american.py`
Expected: FAIL（`ModuleNotFoundError: No module named 'hullkit._dsinc_american'`）

- [ ] **Step 3: `_dsinc_american.py`を実装する**

payoff変換（Eq.(6)）は、s=iω−χ、Kbを境界として`exp(s*Kb) * (rd/s - rf*exp(Kb)/(1+s))`。

再帰（Eq.(57)/(58)）はテストだけでは決まらないので、次の順序で実装する。

```text
初期値: Q_N = 0, E_N = 1, D_N = 0, x*_N = 0, status_N = terminal
n = N-1, ..., 0:
  w = dt/2 if n+1 == N else dt
  [Q_n, E_n] = M @ [w * P̃(x*_{n+1}) + Q_{n+1}, E_{n+1}]   # 最後の軸が2の一括matmulを1回
  Q_n *= exp(-rd dt);  D_n = exp(-rd dt) * (rd w + D_{n+1})
  W_n = exp(-rd (T - t_n)) * E_n / (s (1+s)) + Q_n
  R_n(x) = (1 - e^x) - [exp(-rd (T - t_n)) + D_n + dt (rd - rf e^x) / 4 + inverse_sum(x, W_n)]
  slice = local_boundary(R_n, x*_{n+1}, config)
  slice.statusにFAILURE_CODESがあれば、行nを記録し、n未満の行をnot_run(-1)・NaNにしてから
    PricingFailure("boundary_failure", ..., {time_index, boundary_status, log_boundary, status_counts,
                    last_completed_time_index = n+1})を送出する（Q_{n-1}は作らない）
t0: 節点の値 = 1 - S/K（x ≤ x*_0(ζ_i)のとき）、それ以外は exp(-rd T) + D_0 + inverse_sum(x, W_0)（端点項なし）
European: exp(-rd T) * (1 + inverse_sum(x, E_0 / (s (1+s))))
両方をinterpolate_at_varianceでv0に補間し、EEP = American - European とする
```

`premium_with_boundary`は同じstep関数を、与えた境界で回す。行Nは与えた終端境界にする。

根の決め方（D-1を反映。節点についてはベクトル化する）:

```text
for w in root_widths:
    lo = p - w, hi = min(0, p + w); r_lo, r_hi = R.at(lo), R.at(hi)
    非finite → nonfinite
    r_lo > tol かつ r_hi < -tol → このwで採用
    r_lo < -tol かつ r_hi > tol → wrong_orientation
    それ以外 → 次のw
どのwでも採用されなければ missing_sign_change
δ = scan_spacing(config); grid = δ * arange(floor(min(採用したlo) / δ), 1)
R.on_grid(grid)は1つのsliceにつき1回（Re/Imに分けた実数のGEMM 2回で計算する）
各節点の標本 = [lo, grid ∩ (lo, hi), hi]。|R| ≤ tol は符号0とする
符号0が2点続けば ambiguous_contact。標本に非finiteがあれば nonfinite
符号0の標本を除いた並びで符号変化の数cを数える（両端が+と−なのでcは奇数）
この並びで隣り合う+→−の2標本をcellとし、crossingに従って最後(upper)か最初(lower)のcellを選ぶ
c == 1 なら single、c ≥ 3 なら multiple_crossings。spread = 選ばれうる最上位と最下位のcellの距離
選んだcell [a, b] で二分法: mid = (a+b)/2; R(mid) > 0 なら a = mid、そうでなければ b = mid
  b - a ≤ root_x_tol かつ |R(mid)| ≤ root_residual_tol で終了し、根 = mid
  root_maxiter回で終わらなければ maxiter
```

- 性能（Task 7で予算gateにかかる）: [Q,E]の伝播はstepごとに一括matmul 1回、走査は実数のGEMM 2回、二分法は節点についてベクトル化する。(走査点×n_var×n_omega)の配列は作らない。
- 診断の`bounds`は、問い合わせたspotすべての生の値から作る。clipしない。

- [ ] **Step 4: 通ることを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_american.py`
Expected: `18 passed`（S0の伝播を1回作るので約10秒）

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_types.py johnhull/hullkit/tests/test_dsinc_baseline.py johnhull/hullkit/tests/test_dsinc_spectral.py johnhull/hullkit/tests/test_dsinc_reference.py johnhull/hullkit/tests/test_dsinc_american.py`
Expected: `99 passed`（60秒以内）

- [ ] **Step 5: 索引を足してCommitする**

`MODEL_INDEX.md`のDSINCの節に次の行を足す。

`` | `hullkit._dsinc_american` | Private `hullkit._dsinc_american:payoff_transform`, `hullkit._dsinc_american:local_boundary`, `hullkit._dsinc_american:premium_with_boundary`, `hullkit._dsinc_american:american_put` | Eq. (57)-(58) recursion with terminal half weight and boundary-only dt*g/4, oriented local root scan with uppermost-crossing rule and structured whole-slice failures; quadrature, trapezoid, two-step closed form, synthetic root, bound-diagnostic and Table 3(b)/4 tests in test_dsinc_american.py | ``

```bash
git -C $WT add johnhull/hullkit/src/hullkit/_dsinc_american.py johnhull/hullkit/tests/test_dsinc_american.py johnhull/MODEL_INDEX.md
git -C $WT commit -m "Add the DSINC early-exercise recursion and nodal boundary solver"
```

---

### Task 6: protocol、判定関数、runner、図

**Files:**
- Create: `johnhull/research/DSINC/protocol.json`、`johnhull/research/DSINC/gates.py`、`johnhull/research/DSINC/run.py`、`johnhull/research/DSINC/plot.py`
- Test: `johnhull/hullkit/tests/test_dsinc_gates.py`、`johnhull/hullkit/tests/test_dsinc_runner.py`

**Interfaces:**
- Consumes: Tasks 1–5の全Produces、`heston_baseline.run_heston_baseline`、`reference_fd.reference_put`、`cases.json`
- Produces（`gates.py`、すべて純関数）:

```python
def order_from_levels(h: np.ndarray, values: np.ndarray) -> float | None
def axis_convergence(h: np.ndarray, values: np.ndarray, thresholds: dict) -> dict
    # values: (n_levels, n_quantities)。返り値: status ∈ {converged, below_resolution, final_change_too_large,
    #   not_contracting, order_out_of_range}、converged、final_change、previous_change、orders（最後の3水準、量ごと）
def fd_reference(base: np.ndarray, finest: dict[str, np.ndarray]) -> np.ndarray
def reference_verdict(axes: dict[str, dict], domain_change: float, thresholds: dict) -> dict   # {converged, reasons}
def select_level(levels: dict[str, dict[str, np.ndarray]], reference: dict[str, np.ndarray],
                 sensitivities: dict[str, dict[str, dict[str, np.ndarray]] | None], thresholds: dict) -> dict
    # 返り値: adopted ∈ {"S0", "S1", None}、status ∈ {adopted, not_achieved, not_achieved_budget}、checks
def boundary_gate(*, spectral_log_var, spectral_boundary, spectral_status, fd_log_var, fd_primary, fd_check,
                  fd_dx, fd_x_bounds, thresholds) -> dict
    # 返り値: status ∈ {pass, fail, unsupported}、coverage、valid、targets、max_deviation_cells、fd_shift_cells、
    #   multiple_in_window、reasons
def bounds_check(european, american, spots, contract: dict, tol: float) -> dict
def paper_match(values: dict, anchors: dict, tol: float) -> dict
    # {pass, status ∈ {pass, paper_mismatch}, failed, not_available, differences}。印刷値が"not_available"のanchorは比べずに数える
def estimate_seconds(method: str, measured: dict | None, job: dict, factor: float) -> dict   # {status, seconds, formula, coefficients}
def reproduction_label(paper: dict, validated: dict[str, dict]) -> str  # reproduced | constrained | not_reproduced
def deltas(up: np.ndarray, down: np.ndarray, bump: float) -> np.ndarray
```

- Produces（`run.py`）:

```python
HERE: Path
SOURCE_FILES: tuple[str, ...]   # freezeでhashするrepo相対パス: hullkitの_dsinc_*.py 3本と、research/DSINCの
                                # heston_baseline.py, reference_fd.py, gates.py, run.py, protocol.json, cases.json, upstream_manifest.json
def load_protocol() -> dict
def load_cases() -> dict
def write_json(path: Path, obj) -> None                 # sort_keys、allow_nan=False、一時ファイルからreplace
def build_roster(protocol: dict, phase: Literal["pilot", "main"]) -> list[dict]
def check_job_in_roster(job: dict, roster: list[dict]) -> None   # idがない・内容が違えばValueError("... roster")
def execute_roster(roster: list[dict], root: Path, budget: dict, *, launcher=None, clock=time.monotonic,
                   should_run=None) -> list[dict]
    # budget: {"job_wall_seconds", "job_rss_bytes", "total_seconds"}
    # launcher(job, root, timeout) -> dict（既定はlaunch_subprocess）、should_run(job, records) -> bool
def launch_subprocess(job: dict, root: Path, timeout: float) -> dict
def solve_job(job: dict, root: Path) -> dict            # 子プロセス側: spectral | fd | heston_upstream | fixture
def evaluate(phase: str, records: list[dict], root: Path, protocol: dict, cases: dict) -> dict
def condition_met(condition: str, selections: dict[str, dict]) -> bool   # selectionsは満期ごとのselect_levelの結果
def write_results(root: Path, phase: str, records: list[dict], protocol: dict, cases: dict) -> Path
def make_freeze_manifest(protocol: dict, pilot_summary: dict, estimates: list[dict]) -> dict
def verify_freeze(path: Path) -> dict
def replay(results_path: Path) -> dict                  # {match, differences}
def export(results_path: Path, target: Path, limit_bytes: int) -> dict
def main(argv: list[str] | None = None) -> int          # 引数: pilot | freeze | main | solve-job | replay | export
```

- jobのfield:
  - `job_id`: `<method>-<level or grid>-<variant>-T<expiry>`（例: `spectral-S0-base-T1.0`、`spectral-S0-chi_0.25-T0.5`、`fd-independent-x961-T0.5`、`fd-boundary-primary-T1.0`、`spectral-S1-timing2-T0.5`）。Hestonは`heston-<case_id>`。1つのphaseの中で一意
  - `phase`、`method`、`expiry`、`level`、`variant`
  - `role`: ladder | sensitivity | reference | boundary | paper_fd | cost_probe | timing | heston
  - `config`、`spots`（main 3点＋bump 18点＋境界走査126点）、`condition`（Noneか条件の文字列）、`repeat`
  - mainのjobは、freezeの見積もり`estimate_seconds`も持つ。pilotのHeston残り10本は`optional: true`
- recordのfield:
  - jobのfieldすべて
  - `status`: ok | error | timeout | memory_exceeded | nonfinite | pricing_failure | not_run_budget | not_run_condition
  - `reason`、`prices`（成功以外はNone）、`raw`（launcherの返り値そのまま）、`timing`、`sizes`、`diagnostics`、`arrays`（相対パスとsha256）、`wall_seconds`
- 計時のjobは、採用段と同じ設定を4回（1回目はwarmup）別々のsubprocessで解く。各回でsetup（伝播の構築）とquery（再帰と価格）を分けて測る。

`protocol.json`:

```json
{
  "schema": "DSINC-protocol-v1",
  "cases_file": "cases.json",
  "contract": {"strike": 1.0, "domestic_rate": 0.05, "foreign_rate": 0.02},
  "model": {"kind": "three_halves", "kappa": 20.0, "theta": 0.04, "xi": 4.0, "rho": -0.5, "v0": 0.04},
  "expiries": [0.5, 1.0],
  "spots": [0.9, 1.0, 1.1],
  "delta_bumps": [0.001, 0.0005, 0.00025],
  "boundary_scan_spots": {"start": 0.70, "stop": 0.95, "count": 126},
  "spectral": {
    "log_var_bounds": [-8.517193191416238, 0.6931471805599453],
    "chi": 0.5,
    "base_panels": [0, 2, 5, 10, 20, 40, 80, 160, 320, 640],
    "levels": {
      "S0": {"steps_per_year": 200, "n_var": 160, "cutoff": 640, "points_per_panel": 12},
      "S1": {"steps_per_year": 400, "n_var": 240, "cutoff": 1280, "points_per_panel": 12},
      "S2": {"steps_per_year": 800, "n_var": 320, "cutoff": 2560, "points_per_panel": 16}
    },
    "var_ladder": [160, 240, 320],
    "candidates": ["S0", "S1"],
    "conditional_candidates": ["S1"],
    "sensitivities": ["crossing_lower", "time_x2", "time_x2_cutoff_x2", "var_next", "points_plus4", "cutoff_x2",
                      "chi_0.25", "chi_0.75", "domain_expand", "offset_plus_half", "offset_minus_half"]
  },
  "fd": {
    "log_spot_bounds": [-1.2, 1.2],
    "paper": {"log_var_bounds": [-8.517193191416238, 0.6931471805599453], "grids": [[241, 101, 300], [481, 201, 600]]},
    "independent": {"log_var_bounds": [-11.512925464970229, 2.0794415416798357], "base": [241, 101, 300],
                    "x": [241, 481, 961, 1921], "var": [101, 151, 201], "time": [300, 600, 1200],
                    "domain": {"log_spot_bounds": [-2.4, 2.4], "n_x": 481}},
    "boundary": {"log_var_bounds": [-11.512925464970229, 2.0794415416798357], "primary": [961, 101, 1200], "check": [961, 101, 600]}
  },
  "thresholds": {
    "paper_match": 6e-6, "independent": 2e-5, "adjacent": 5e-6, "sensitivity": 5e-6,
    "reference_final_change": 5e-6, "reference_resolution": 5e-7, "reference_order_range": [1.0, 3.0],
    "bounds": 2e-5, "nonmonotone_min_entry": -1e-10,
    "boundary": {"time_window": [0.1, 0.9], "variance_window": [0.01, 0.16], "edge_cells": 4, "coverage": 0.9,
                 "max_cells": 2.0, "fd_shift_cells": 1.0, "root_residual": 1e-8}
  },
  "budget": {"job_wall_seconds": 180, "job_rss_bytes": 2147483648, "pilot_seconds": 600, "main_seconds": 1800,
             "estimate_factor": 2.0, "timing_warmup": 1, "timing_repeats": 3,
             "thread_variables": ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]},
  "storage": {"run_root": "/home/kazumasa/projects/_data/johnhull/DSINC", "target_bytes": 52428800, "export_file_bytes": 2000000}
}
```

FDのgridの3つ組は(n_x, n_var, steps_per_year)で、n_time=round(steps_per_year·T)。spectralのn_timeもround(steps_per_year·T)。

感度は、起点の段Lから1軸だけ変えて作る。
- `crossing_lower`: crossing="lower"
- `time_x2`: steps×2（パネルはそのまま）
- `time_x2_cutoff_x2`: steps×2で、パネルの末尾に2·cutoffを足す
- `var_next`: var_ladderの次の節点数
- `points_plus4`: 各パネルの点数+4
- `cutoff_x2`: パネルの末尾に2·cutoffを足す
- `chi_0.25` / `chi_0.75`: chiを変える
- `domain_expand`: hを固定し、両側にm=ceil(log 2/h)節点ずつ足す（S0ではm=12、n_var=184）
- `offset_plus_half` / `offset_minus_half`: boundsを±h/2ずらす

rosterの規則:
- pilotの必須32本（この順に実行）:
  - Heston H00
  - spectral S0（T=.5とT=1）
  - S0の感度11本（T=.5）
  - S1、S2（T=.5）
  - FD paperの2格子（T=.5）とpaper fine（T=1、Americanのみ）
  - FD independentの9本（T=.5）: base、x 481/961/1921、var 151/201、time 600/1200、domain
  - FD boundaryのcheckとprimary（T=.5）
  - 費用の測定（T=1）: x1921（両exercise）と境界primary
- pilotの任意10本: Hestonの残りのケース。必須を終えて予算が残っているときだけ走らせる。
- mainの必須50本: 各満期でspectral S0/S1/S2、S0の感度11本、FD independent 9本、FD boundary 2本。
- mainの条件付き38本: 各満期でS1の感度11本（条件`S0_not_adopted:T`）と、採用段の計時4本×2候補（条件`adopted:S0:T`・`adopted:S1:T`）。
- mainは必須の50本を先に、条件付きの38本を後に並べる（S1の感度、計時の順）。条件は、その時点までのrecordから`evaluate`で作った満期ごとの選択を`condition_met`で読む。

- [ ] **Step 1: 判定関数の失敗するテストを書く**

```python
"""DSINC decision rules: reference construction, level selection, boundary, bounds and paper gates."""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[2] / "research/DSINC/gates.py"
REF = {"reference_final_change": 5e-6, "reference_resolution": 5e-7, "reference_order_range": [1.0, 3.0]}
TH = {"adjacent": 5e-6, "independent": 2e-5, "sensitivity": 5e-6}
BOUNDARY = {"time_window": [0.1, 0.9], "variance_window": [0.01, 0.16], "edge_cells": 4, "coverage": 0.9,
            "max_cells": 2.0, "fd_shift_cells": 1.0, "root_residual": 1e-8}
SENSITIVITIES = ("crossing_lower", "time_x2", "time_x2_cutoff_x2", "var_next", "points_plus4", "cutoff_x2",
                 "chi_0.25", "chi_0.75", "domain_expand", "offset_plus_half", "offset_minus_half")
# planning-run American prices at T = .5 on the wide variance domain (rows: levels, columns: S/K .9, 1, 1.1)
X = np.array([[0.10757684, 0.04861780, 0.01946888], [0.10759692, 0.04864835, 0.01948780],
              [0.10760209, 0.04865596, 0.01949251], [0.10760299, 0.04865785, 0.01949368]])
VAR = np.array([[0.10757684, 0.04861780, 0.01946888], [0.10757491, 0.04861748, 0.01946949], [0.10757471, 0.04861744, 0.01946973]])
TIME = np.array([[0.10757684, 0.04861780, 0.01946888], [0.10757601, 0.04861829, 0.01946962], [0.10757582, 0.04861849, 0.01946989]])


@pytest.fixture(scope="module")
def gates():
    spec = importlib.util.spec_from_file_location("dsinc_gates_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def level(value):
    return {q: np.full(3, value) for q in ("european", "american", "eep")}


def test_order_is_fitted_on_actual_step_sizes(gates):
    for h in (np.array([0.02, 0.01, 0.005]), 1.0 / np.array([100.0, 150.0, 200.0])):
        assert gates.order_from_levels(h, 1.0 + 3.0 * h**2) == pytest.approx(2.0, abs=1e-9)
    assert gates.order_from_levels(np.array([0.02, 0.01, 0.005]), np.array([1.0, 1.0 + 1e-6, 1.0])) is None


def test_axis_convergence_on_the_planning_ladders(gates):
    x = gates.axis_convergence(1.0 / np.array([240.0, 480.0, 960.0, 1920.0]), X, REF)
    assert x["status"] == "converged" and x["final_change"] == pytest.approx(1.89e-6, abs=1e-12)
    assert x["orders"] == pytest.approx([2.522, 2.010, 2.009], abs=2e-3)
    assert gates.axis_convergence(1.0 / np.array([100.0, 150.0, 200.0]), VAR, REF)["status"] == "below_resolution"
    assert gates.axis_convergence(1.0 / np.array([300.0, 600.0, 1200.0]), TIME, REF)["status"] == "below_resolution"
    three = gates.axis_convergence(1.0 / np.array([240.0, 480.0, 960.0]), X[:3], REF)
    assert three["status"] == "final_change_too_large"  # D-2: stopping at 961 fails the 5e-6 rule


def test_non_contracting_axis_is_not_converged(gates):
    values = np.array([[0.0], [1e-6], [3e-6]])
    assert gates.axis_convergence(np.array([0.02, 0.01, 0.005]), values, REF)["status"] == "not_contracting"


def test_reference_adds_each_axis_correction_to_the_base(gates):
    ref = gates.fd_reference(X[0], {"x": X[-1], "var": VAR[-1], "time": TIME[-1]})
    np.testing.assert_allclose(ref, [0.10759984, 0.04865818, 0.01949554], rtol=0, atol=1e-11)


def test_reference_verdict_requires_every_axis_and_the_domain(gates):
    ok = {"converged": True, "status": "converged"}
    assert gates.reference_verdict({"x": ok, "var": ok, "time": ok}, 0.0, REF)["converged"]
    bad = gates.reference_verdict({"x": {"converged": False, "status": "final_change_too_large"}, "var": ok, "time": ok}, 0.0, REF)
    assert not bad["converged"] and "x" in " ".join(bad["reasons"])
    assert not gates.reference_verdict({"x": ok, "var": ok, "time": ok}, 6e-6, REF)["converged"]


def test_level_selection_takes_the_coarse_side_of_the_first_passing_pair(gates):
    ref = level(0.1)
    calm = {name: level(0.1 + 1e-6) for name in SENSITIVITIES}
    levels = {"S0": level(0.1), "S1": level(0.1 + 4e-6), "S2": level(0.1 + 4.5e-6)}
    assert gates.select_level(levels, ref, {"S0": calm, "S1": None}, TH)["adopted"] == "S0"
    noisy_s0 = calm | {"chi_0.75": level(0.1 + 6e-6)}
    s1_calm = {name: level(0.1 + 4e-6) for name in SENSITIVITIES}
    assert gates.select_level(levels, ref, {"S0": noisy_s0, "S1": s1_calm}, TH)["adopted"] == "S1"
    assert gates.select_level(levels, ref, {"S0": noisy_s0, "S1": None}, TH)["status"] == "not_achieved_budget"
    apart = {"S0": level(0.1), "S1": level(0.1 + 6e-6), "S2": level(0.1 + 1.2e-5)}
    out = gates.select_level(apart, ref, {"S0": calm, "S1": s1_calm}, TH)
    assert (out["adopted"], out["status"]) == (None, "not_achieved")  # S2 is never adopted
    spotwise = {"S0": level(0.1), "S1": {q: np.array([0.1, 0.1, 0.1 + 6e-6]) for q in ("european", "american", "eep")}, "S2": level(0.1)}
    assert gates.select_level(spotwise, ref, {"S0": calm, "S1": None}, TH)["adopted"] is None  # one spot decides


def boundary_case(dx=0.0025):
    spec_z = np.linspace(math.log(2e-4), math.log(2.0), 160)
    fd_z = np.linspace(math.log(1e-5), math.log(8.0), 101)
    fd_edge = np.full((601, 101), -0.2)
    fd_edge[-1] = np.nan
    return dict(spectral_log_var=spec_z, spectral_boundary=np.full((101, 160), -0.2 + dx / 2),
                spectral_status=np.zeros((101, 160), np.int8), fd_log_var=fd_z, fd_primary=fd_edge,
                fd_check=fd_edge[::2].copy(), fd_dx=dx, fd_x_bounds=(-1.2, 1.2), thresholds=BOUNDARY)


def test_boundary_gate_pass_fail_mask_and_coverage(gates):
    case = boundary_case()
    ok = gates.boundary_gate(**case)
    assert ok["status"] == "pass" and ok["coverage"] == 1.0 and ok["max_deviation_cells"] == 0.0
    near = gates.boundary_gate(**(case | {"spectral_boundary": np.full((101, 160), -0.2 - 1.99 * 0.0025)}))
    far = gates.boundary_gate(**(case | {"spectral_boundary": np.full((101, 160), -0.2 - 2.01 * 0.0025)}))
    assert near["status"] == "pass" and far["status"] == "fail"
    edge = case["fd_primary"].copy()
    edge[:540] = -1.2 + 3 * 0.0025  # within 4 cells of the left x edge at every window time but t/T = .9
    masked = gates.boundary_gate(**(case | {"fd_primary": edge, "fd_check": edge[::2].copy()}))
    assert masked["status"] == "unsupported" and masked["coverage"] < 0.9


def test_boundary_gate_rejects_multiple_crossings_and_unconverged_fd(gates):
    case = boundary_case()
    status = case["spectral_status"].copy()
    status[50, 100] = 1  # multiple_crossings at t/T = .5, v inside [.01, .16]
    assert "multiple_crossings_in_window" in gates.boundary_gate(**(case | {"spectral_status": status}))["reasons"]
    shifted = case["fd_check"].copy()
    shifted[150, 60] -= 2 * 0.0025
    out = gates.boundary_gate(**(case | {"fd_check": shifted}))
    assert out["status"] == "fail" and out["fd_shift_cells"] == pytest.approx(2.0)


def test_bounds_check_reports_raw_violations(gates):
    spots = np.array([0.9, 1.0, 1.1])
    contract = {"domestic_rate": 0.05, "foreign_rate": 0.02, "expiry": 0.5}
    eu = np.array([0.1025, 0.0472, 0.0191])
    assert gates.bounds_check(eu, np.array([0.1076, 0.0487, 0.0195]), spots, contract, 2e-5)["pass"]
    bad = gates.bounds_check(eu, np.array([0.0999, 0.0487, 0.0195]), spots, contract, 2e-5)
    assert not bad["pass"] and bad["american_minus_payoff_min"] == pytest.approx(-1e-4)


def test_paper_match_uses_six_millionths_without_relaxation(gates):
    anchors = {"T0.5.american_n100": [0.107601, 0.048662, 0.019499], "T0.5.european": [0.102557, 0.047224, 0.019105],
               "T1.american_atm": 0.063668}
    values = {"T0.5.american_n100": [0.10760094, 0.04866224, 0.01949905],
              "T0.5.european": [0.10255734, 0.04722426, 0.01910466], "T1.american_atm": 0.06366789}
    assert gates.paper_match(values, anchors, 6e-6)["pass"]
    out = gates.paper_match(values | {"T1.american_atm": 0.063668 + 6.1e-6}, anchors, 6e-6)
    assert not out["pass"] and out["failed"] == ["T1.american_atm"] and out["status"] == "paper_mismatch"
    printed_only = gates.paper_match(values, anchors | {"T1.non_atm": "not_available"}, 6e-6)
    assert printed_only["pass"] and printed_only["not_available"] == ["T1.non_atm"]


def test_estimates_follow_the_design_formula(gates):
    measured = {"setup_seconds": 4.0, "solve_seconds": 2.0, "n_omega": 108, "n_var": 160, "n_time": 100, "scan_spacing": 0.0015625}
    job = {"n_omega": 120, "n_var": 240, "n_time": 400, "scan_spacing": math.pi / 2560}
    w, v, t, s = 120 / 108, 1.5, 4.0, 0.0015625 / (math.pi / 2560)
    out = gates.estimate_seconds("spectral", measured, job, factor=2.0)
    assert out["seconds"] == pytest.approx(2.0 * (4.0 * w * v**3 + 2.0 * t * w * v**2 * s))
    same = gates.estimate_seconds("spectral", measured, {k: measured[k] for k in job}, factor=2.0)
    assert same["seconds"] == pytest.approx(12.0)
    fd = gates.estimate_seconds("fd", {"setup_seconds": 1.4, "solve_seconds": 4.3, "nodes": 193819, "bandwidth": 101, "n_time": 150},
                                {"nodes": 193819, "bandwidth": 101, "n_time": 300}, factor=2.0)
    assert fd["seconds"] == pytest.approx(2.0 * (1.4 + 4.3 * 2.0))
    assert gates.estimate_seconds("spectral", None, job, factor=2.0)["status"] == "unmeasured"


def test_reproduced_requires_both_gates(gates):
    passed = {"0.5": {"price": True, "boundary": "pass"}, "1.0": {"price": True, "boundary": "pass"}}
    assert gates.reproduction_label({"pass": True}, passed) == "reproduced"
    partial = passed | {"0.5": {"price": True, "boundary": "unsupported"}}
    assert gates.reproduction_label({"pass": True}, partial) == "constrained"
    assert gates.reproduction_label({"pass": False}, passed) == "not_reproduced"


def test_deltas_use_central_differences(gates):
    s, b = np.array([0.9, 1.0, 1.1]), 1e-3
    np.testing.assert_allclose(gates.deltas(0.3 * (s + b) ** 2, 0.3 * (s - b) ** 2, b), 0.6 * s, rtol=0, atol=1e-12)
```

- [ ] **Step 2: runnerの失敗するテストを書く**

```python
"""DSINC runner: slot accounting, budgets, freeze checks, replay, export and figures."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from hullkit._dsinc_types import canonical_digest

RUN = Path(__file__).resolve().parents[2] / "research/DSINC/run.py"
PLOT = Path(__file__).resolve().parents[2] / "research/DSINC/plot.py"
BUDGET = {"job_wall_seconds": 180.0, "job_rss_bytes": 2**31, "total_seconds": 600.0}
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def run():
    return load(RUN, "dsinc_run_tests")


def fixture_job(job_id, **params):
    return {"job_id": job_id, "method": "fixture", "expiry": 0.5, "level": None, "variant": "fixture",
            "role": "fixture", "condition": None, "params": params}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_slots_are_accounted_under_a_fake_clock(run, tmp_path):
    clock = FakeClock()

    def launcher(job, root, timeout):
        clock.now += job["params"]["seconds"]
        if job["params"]["seconds"] > timeout:
            return {"status": "timeout", "reason": f"exceeded {timeout} s"}
        if job["params"].get("fail"):
            return {"status": "error", "reason": "boom"}
        return {"status": "ok", "prices": {"american": [1.0]}, "maxrss_bytes": job["params"].get("rss", 10)}

    roster = [fixture_job("ok", seconds=1.0), fixture_job("fails", seconds=1.0, fail=True),
              fixture_job("big", seconds=1.0, rss=3 * 2**30), fixture_job("slow", seconds=200.0), fixture_job("late", seconds=1.0)]
    records = run.execute_roster(roster, tmp_path / "root", BUDGET | {"total_seconds": 183.0}, launcher=launcher, clock=clock)
    assert [r["job_id"] for r in records] == ["ok", "fails", "big", "slow", "late"]
    assert [r["status"] for r in records] == ["ok", "error", "memory_exceeded", "timeout", "not_run_budget"]
    assert records[0]["prices"] == {"american": [1.0]} and all(r["prices"] is None for r in records[1:])
    assert records[2]["raw"]["maxrss_bytes"] == 3 * 2**30 and all(r["reason"] for r in records[1:])


def test_real_subprocess_timeout_and_thread_guard(run, tmp_path):
    records = run.execute_roster([fixture_job("sleepy", sleep=3.0), fixture_job("fine", value=1.0)], tmp_path / "root",
                                 BUDGET | {"job_wall_seconds": 1.0, "total_seconds": 30.0})
    assert [r["status"] for r in records] == ["timeout", "ok"] and records[1]["raw"]["maxrss_bytes"] > 0
    job = tmp_path / "job.json"
    job.write_text(json.dumps(fixture_job("x", value=1.0)))
    env = os.environ | dict.fromkeys(THREADS, "1") | {"OPENBLAS_NUM_THREADS": "4"}
    proc = subprocess.run([sys.executable, str(RUN), "solve-job", "--job", str(job), "--out", str(tmp_path / "out.json")],
                          env=env, capture_output=True, text=True)
    assert proc.returncode != 0 and "OPENBLAS_NUM_THREADS" in proc.stderr


def test_conditional_jobs_follow_the_condition_and_the_remaining_budget(run, tmp_path):
    roster = [fixture_job("first", value=1.0),
              fixture_job("skip", value=2.0) | {"condition": "S0_not_adopted:T0.5", "estimate_seconds": 1.0},
              fixture_job("take", value=3.0) | {"condition": "adopted:S0:T0.5", "estimate_seconds": 1.0},
              fixture_job("too_long", value=4.0) | {"condition": "adopted:S0:T0.5", "estimate_seconds": 1e6}]
    seen = []

    def should_run(job, records):
        seen.append([r["job_id"] for r in records])
        return job["condition"] == "adopted:S0:T0.5"

    records = run.execute_roster(roster, tmp_path / "root", BUDGET, should_run=should_run)
    assert [r["status"] for r in records] == ["ok", "not_run_condition", "ok", "not_run_budget"]
    assert seen == [["first"], ["first", "skip"], ["first", "skip", "take"]]


def test_conditions_read_the_level_selection(run):
    selections = {"0.5": {"adopted": "S0"}, "1.0": {"adopted": None}}
    assert run.condition_met("adopted:S0:T0.5", selections)
    assert not run.condition_met("S0_not_adopted:T0.5", selections)
    assert run.condition_met("S0_not_adopted:T1.0", selections)
    assert not run.condition_met("adopted:S1:T1.0", selections)
    with pytest.raises(ValueError):
        run.condition_met("adopted:S3:T0.5", selections)


def test_results_json_never_contains_nan(run, tmp_path):
    records = run.execute_roster([fixture_job("nan", nan=True)], tmp_path / "root", BUDGET)
    assert records[0]["status"] == "nonfinite" and records[0]["prices"] is None
    text = (tmp_path / "root/records.json").read_text()
    assert "NaN" not in text and json.loads(text)
    with pytest.raises(ValueError):
        run.write_json(tmp_path / "x.json", {"a": float("nan")})


def test_output_root_must_be_new(run, tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    (root / "old.json").write_text("{}")
    with pytest.raises(ValueError, match="exists"):
        run.execute_roster([], root, BUDGET)


def test_protocol_and_rosters_are_fixed(run):
    protocol = run.load_protocol()
    assert protocol["thresholds"]["paper_match"] == 6e-6 and protocol["thresholds"]["independent"] == 2e-5
    assert protocol["budget"]["job_wall_seconds"] == 180 and protocol["budget"]["main_seconds"] == 1800
    pilot = run.build_roster(protocol, "pilot")
    assert len([j for j in pilot if not j.get("optional")]) == 32 and len([j for j in pilot if j.get("optional")]) == 10
    main = run.build_roster(protocol, "main")
    always, conditional = [j for j in main if not j["condition"]], [j for j in main if j["condition"]]
    assert (len(always), len(conditional)) == (50, 38)
    assert all(len({j["job_id"] for j in r}) == len(r) for r in (pilot, main))
    s0 = next(j for j in main if j["job_id"] == "spectral-S0-base-T1.0")
    assert (s0["config"]["n_time"], s0["config"]["n_var"], len(s0["spots"])) == (200, 160, 147)
    run.check_job_in_roster(s0, main)
    with pytest.raises(ValueError, match="roster"):
        run.check_job_in_roster({"job_id": "spectral-S3-base-T0.5"}, main)
    with pytest.raises(ValueError, match="roster"):
        run.check_job_in_roster(s0 | {"config": s0["config"] | {"chi": 0.4}}, main)


def estimates(roster, seconds):
    return [{"job_id": j["job_id"], "condition": j["condition"], "status": "estimated", "seconds": seconds} for j in roster]


def passing_pilot(protocol):
    return {"all_pass": True, "protocol_digest": canonical_digest(protocol)}


def test_freeze_rejects_failed_pilots_and_unmeasured_or_large_estimates(run):
    protocol = run.load_protocol()
    roster = run.build_roster(protocol, "main")
    ok = passing_pilot(protocol)
    run.make_freeze_manifest(protocol, ok, estimates(roster, 1.0))
    with pytest.raises(ValueError, match="pilot"):
        run.make_freeze_manifest(protocol, ok | {"all_pass": False}, estimates(roster, 1.0))
    with pytest.raises(ValueError, match="protocol"):
        run.make_freeze_manifest(protocol, ok | {"protocol_digest": "0" * 64}, estimates(roster, 1.0))
    with pytest.raises(ValueError, match="roster"):
        run.make_freeze_manifest(protocol, ok, estimates(roster, 1.0)[1:])
    unmeasured = estimates(roster, 1.0)
    unmeasured[0] |= {"status": "unmeasured", "seconds": None}
    with pytest.raises(ValueError, match="unmeasured"):
        run.make_freeze_manifest(protocol, ok, unmeasured)
    slow = estimates(roster, 1.0)
    slow[-1]["seconds"] = 181.0  # a conditional job: the 180 s rule covers every job
    with pytest.raises(ValueError, match="180"):
        run.make_freeze_manifest(protocol, ok, slow)
    with pytest.raises(ValueError, match="1800"):
        run.make_freeze_manifest(protocol, ok, estimates(roster, 37.0))  # 50 always-run jobs x 37 s = 1850 s
    mixed = [e | {"seconds": 170.0 if e["condition"] else 30.0} for e in estimates(roster, 0.0)]
    run.make_freeze_manifest(protocol, ok, mixed)  # D-5: conditional jobs stay outside the 1800 s gate


def test_main_requires_a_matching_freeze(run, tmp_path, monkeypatch):
    protocol = run.load_protocol()
    roster = run.build_roster(protocol, "main")
    manifest = run.make_freeze_manifest(protocol, passing_pilot(protocol), estimates(roster, 1.0))
    path = tmp_path / "freeze.json"
    run.write_json(path, manifest)
    run.verify_freeze(path)
    run.write_json(path, manifest | {"thresholds": manifest["thresholds"] | {"independent": 3e-5}})
    with pytest.raises(ValueError, match="freeze"):
        run.verify_freeze(path)
    source = tmp_path / "source.py"
    source.write_text("x = 1\n")
    monkeypatch.setattr(run, "SOURCE_FILES", (str(source),))
    run.write_json(path, run.make_freeze_manifest(protocol, passing_pilot(protocol), estimates(roster, 1.0)))
    source.write_text("x = 2\n")
    with pytest.raises(ValueError, match="source"):
        run.verify_freeze(path)


def test_real_solver_jobs_run_in_subprocesses(run, tmp_path):
    spectral = {"job_id": "spectral-tiny", "method": "spectral", "expiry": 0.5, "level": "tiny", "variant": "base", "role": "ladder",
                "condition": None, "spots": [0.9, 1.0, 1.1],
                "config": {"n_time": 40, "n_var": 24, "log_var_bounds": [-5.298317366548036, -1.2039728043259361], "chi": 0.5,
                           "panels": [0, 2, 5, 10, 20, 40], "points_per_panel": 4}}
    fd = {"job_id": "fd-tiny", "method": "fd", "expiry": 0.5, "level": None, "variant": "tiny", "role": "reference", "condition": None,
          "spots": [0.9, 1.0, 1.1], "config": {"n_x": 41, "n_var": 11, "n_time": 10, "log_spot_bounds": [-1.2, 1.2],
                                              "log_var_bounds": [-11.512925464970229, 2.0794415416798357], "record_boundary": True}}
    records = run.execute_roster([spectral, fd], tmp_path / "root", BUDGET)
    assert [r["status"] for r in records] == ["ok", "ok"]
    for r in records:
        assert np.all(np.isfinite(r["prices"]["american"])) and (tmp_path / "root" / r["arrays"]["path"]).exists()
    with np.load(tmp_path / "root" / records[0]["arrays"]["path"]) as arrays:
        assert arrays["log_boundary"].shape == (41, 24) and arrays["boundary_status"].dtype == np.int8


def test_replay_recomputes_the_saved_verdicts(run, tmp_path):
    records = run.execute_roster([fixture_job("a", value=1.0), fixture_job("b", fail=True)], tmp_path / "root", BUDGET)
    results = run.write_results(tmp_path / "root", "fixture", records, run.load_protocol(), run.load_cases())
    assert run.replay(results)["match"]
    saved = json.loads(results.read_text())
    saved["records"][0]["status"] = "error"
    results.write_text(json.dumps(saved))
    assert not run.replay(results)["match"]


def test_export_respects_the_file_size_limit(run, tmp_path):
    records = run.execute_roster([fixture_job("a", value=1.0, array_bytes=3_000_000)], tmp_path / "root", BUDGET)
    results = run.write_results(tmp_path / "root", "fixture", records, run.load_protocol(), run.load_cases())
    with pytest.raises(ValueError, match="2000000"):
        run.export(results, tmp_path / "out", 2_000_000)


def test_plot_draws_three_figures_from_saved_results(tmp_path):
    plot = load(PLOT, "dsinc_plot_tests")
    results = plot.synthetic_results(tmp_path)  # writes a minimal results.json and arrays for the figure contract
    paths = plot.draw(results, tmp_path / "figures")
    assert sorted(p.name for p in paths) == ["exercise_boundary.png", "price_error_cost.png", "refinement_stability.png"]
    assert all(p.stat().st_size > 10_000 for p in paths)
```

- [ ] **Step 3: 失敗を確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_gates.py johnhull/hullkit/tests/test_dsinc_runner.py`
Expected: ERROR（`FileNotFoundError`: gates.py、run.py、plot.pyがない）

- [ ] **Step 4: `gates.py`を実装する**

- `order_from_levels`: (h₁^p−h₂^p)/(h₂^p−h₃^p)=d₁₂/d₂₃を、`brentq`でp∈[0.25, 8]について解く。比が正でないとき、根がないときはNone。
- `axis_convergence`: final_change=max\|v[−1]−v[−2]\|。
  - final_change>tolなら`final_change_too_large`。
  - final_change≤resolutionなら`below_resolution`（収束）。
  - それ以外は、\|最終差\|>resolutionの量ごとに、\|最終差\|<\|前の差\|（満たさなければ`not_contracting`）と、次数∈order_range（満たさなければ`order_out_of_range`）を確かめる。
- `select_level`: 量はeuropean/american/eepの3点で、各閾値は全spot・全量の最大値で判定する。
  - 候補の順はS0→S1で、相手は次の段。隣接差≤adjacent、|Sj−ref|≤independent、全感度≤sensitivityを満たす最初の候補を採用する。
  - 感度がNone（未実行）の候補しか残らなければ`not_achieved_budget`。どれも通らなければ`not_achieved`。
- `boundary_gate`:
  - N_spec=行数−1、N_fd=fd_primaryの行数−1。共通の時刻は、k·N_fdがN_specで割り切れ、t/Tが窓に入るk。
  - 対象は、窓に入るspectralの節点。FDの端をζ方向に線形補間し、bracketを[端, 端+dx]とする。
  - 端がNaNか、bracketやspectralの境界がx端から4セル以内なら`geometry_invalid`（maskする）。
  - 外れ=max(0, lo−x*, x*−hi)。
  - status=1が窓内にあるか、外れ>2dxか、根の残差の記録が1e-8を超えればfail。coverage<.9ならunsupported。
  - FDの収束: primaryの偶数stepとcheckを窓内のFD ζ節点で比べ、最大の差>1セル（+1e-9）ならfail。
- `bounds_check`: A−E、A−payoff、A−1、Eの上下界の、最大・最小の生の値と、許容に照らしたpassを返す。
- `estimate_seconds`: 設計§6の式に係数を掛け、factor倍する。
  - spectralでn_omega・n_var・n_time・scan_spacingがすべて同じなら、factor×(setup+solve)。
  - 異なれば、factor×[setup·w·v³ + solve·t·w·v²·s]。wはn_omegaの比、vはn_varの比、tはn_timeの比、sは走査点数の比（measuredのscan_spacing／jobのscan_spacing）。
  - fdは、factor×[setup·(nodes·bw²の比) + solve·(n_time·nodes·bwの比)]。
  - measuredがNoneなら`unmeasured`。
- `reproduction_label`: paper.passで、全満期がprice=Trueかつboundary="pass"ならreproduced。paper.passで、どれかの満期がprice=Trueならconstrained。それ以外はnot_reproduced。

- [ ] **Step 5: `run.py`と`plot.py`を実装する**

- `execute_roster`:
  - rootが存在して空でなければ、"exists"でValueErrorにする。
  - jobを順に処理し、残り予算（total_seconds − 経過）を見る。
    - 残りが0以下なら`not_run_budget`。
    - conditionがあるjobは、`should_run(job, records)`がFalseなら`not_run_condition`。Trueでも`estimate_seconds`が残りを超えれば`not_run_budget`（D-5）。
    - それ以外はtimeout=min(job_wall, 残り)で`launcher`（既定は`launch_subprocess`）を呼ぶ。
  - launcherの返り値はそのまま`raw`に残す。子が報告したmaxrss_bytesがjob_rss_bytesを超えれば`memory_exceeded`（pricesはNone）。
  - 価格が非finiteなら`nonfinite`。
  - recordは毎回`<root>/records.json`へ書き出す（途中で止まっても残す）。
- `launch_subprocess`: `[sys.executable, run.py, "solve-job", "--job", <root>/jobs/<id>.json, "--out", <root>/out/<id>.json]`を、thread変数を1にしたenvで、`subprocess.run(timeout=...)`で起動する。TimeoutExpiredならtimeout、終了codeが0でなければerror（stderrの末尾2,000文字を残す）。
- `solve_job`: thread変数4つが"1"でなければ、"1"でない変数名をすべてstderrに出して終了code 2で終わる。contractとmodelはprotocolから、満期・設定・spotsはjobから取る。
  - spectral: `american_put`。arrays（`log_boundary`・`boundary_status`・`log_variances`・`times`）を`<root>/arrays/<id>.npz`へ`savez_compressed`で保存する。
  - fd: `reference_put`。`contact_edge`があれば保存する。
  - heston_upstream: `run_heston_baseline`。
  - fixture: params（value / sleep / fail / nan / array_bytes）。
  - `PricingFailure`はstatus=`pricing_failure`とdetailsで返す。arraysのsha256をrecordに入れる。
  - 非finiteの価格はnullにしてstatus `nonfinite`で返す。子の出力JSONにもNaNを書かない。
- `evaluate`:
  - pilotでは次を出す。
    - paper_match（gate 7点と診断の列）。不一致は`paper_mismatch`。
    - T=.5のFD参照（D-3）、S0とrefの差、T=.5の境界gate（D-4）、crossing_lowerの感度（D-1）、感度の診断、Hestonの診断。
    - mainの全ジョブの見積もり（`estimates`）。
    - `protocol_digest`（`canonical_digest(protocol)`）と`all_pass`。
  - mainでは次を出す。
    - `selections`: 満期ごとのselect_level。
    - `independent_validated`: 満期ごとに`{"price": 採用段があり、その満期のbounds・独立gate・FD参照の収束がすべて通る, "boundary": boundary_gateのstatus}`。
    - `nonmonotone_effect`: scheme_nonmonotoneが記録された満期で、price・boundary・paper_matchのどれかが通らなければ`unsupported`、すべて通れば`confirmed`（設計§4）。
    - paper_match、Delta（診断）、`reproduction_label`、費用表。
    - `exports`: 書き出す配列の相対パス（採用段の境界と、FD primaryの接触端）。
  - fixtureでは、statusごとの件数と、全配列を`exports`に出す。
  - 未実行のjobはNoneとして扱う（mainの途中で`condition_met`のために呼ぶ）。
- `condition_met`: `adopted:<S>:T<expiry>`は採用段が<S>のときTrue、`S0_not_adopted:T<expiry>`はS0が採用されなかったときTrue。S0・S1以外の段や知らない形はValueError。
- `make_freeze_manifest`: 次を満たさなければValueErrorにする。
  - pilotの`all_pass`。
  - pilotの`protocol_digest`が現在のprotocolと一致する（pilotとmainは同じprotocol.jsonを使う）。
  - mainのrosterの全jobに見積もりがあり、unmeasuredがない。
  - 1件が180秒以下（条件付きも含む）。
  - condition=Noneのジョブの合計が1800秒以下（D-5）。
  - manifestには、protocol・cases・SOURCE_FILESのsha256、protocolの`thresholds`と`budget`の写し、mainのroster（各jobに`estimate_seconds`）、見積もり（式と係数）、pilotの要約のsha256、`manifest_sha256`（自分自身を除いた正規JSONのsha256）を入れる。
- `verify_freeze`: manifest_sha256、protocol・cases・sourceのsha256、rosterの再計算が一致しなければ、"freeze"または"source"を含むValueErrorにする。
- `write_results`: `<root>/results.json`（schema、phase、protocol・freezeのsha256、records、verdicts、arraysの索引、`exports`）を書き、そのパスを返す。
- `replay`: records・arraysを読み、`evaluate`を計算し直し、保存したverdictsと正規JSONで比べる。
- `export`: results.jsonと、`exports`に載った配列をtargetへ写し、`results/manifest.json`にsha256を書く。写す前にサイズを確かめ、どれかが`limit_bytes`を超えれば、その数値を含むValueErrorにする。
- CLIの引数:
  - `pilot --output DIR`
  - `freeze --pilot DIR --output FILE`（repoのfreeze_manifest.json）
  - `main --freeze FILE --output DIR`（freezeを検証してからrosterを実行し、`should_run`は`condition_met`と途中の`evaluate`で作る。終わったらmanifestをDIRへ写してresultsを書く）
  - `solve-job --job FILE --out FILE`
  - `replay --results FILE`
  - `export --results FILE --to DIR`
- `plot.py`: `draw(results_path, out_dir) -> list[Path]`、`synthetic_results(tmp) -> Path`（テスト用の最小のresults）、CLI `--results FILE --output DIR`。
  - Matplotlibは`Agg`で、ラベルは英語にする。
  - 3図: 価格誤差と費用（log-log、誤差の単位は価格/K）、行使境界（採用段とFDのbracket、maskした点、失敗の件数）、細分・減衰の安定性（感度ごとの差と5e-6の線）。
  - 保存した結果だけを読む。

- [ ] **Step 6: 通ることを確かめる**

Run: `cd $WT && $PY -m pytest -q johnhull/hullkit/tests/test_dsinc_gates.py johnhull/hullkit/tests/test_dsinc_runner.py`
Expected: `26 passed`（gates 13本、runner 13本）

Run: `cd $WT && $RUFF format johnhull/research/DSINC johnhull/hullkit/src/hullkit/_dsinc_*.py johnhull/hullkit/tests/test_dsinc_*.py && $RUFF check --fix johnhull/research/DSINC johnhull/hullkit/src/hullkit/_dsinc_*.py johnhull/hullkit/tests/test_dsinc_*.py`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git -C $WT add johnhull/research/DSINC/protocol.json johnhull/research/DSINC/gates.py johnhull/research/DSINC/run.py johnhull/research/DSINC/plot.py johnhull/hullkit/tests/test_dsinc_gates.py johnhull/hullkit/tests/test_dsinc_runner.py
git -C $WT commit -m "Add the DSINC protocol, decision gates and budgeted runner"
```

---

### Task 7: pilotとfreeze（ここで判断点）

**Files:**
- Create: `johnhull/research/DSINC/freeze_manifest.json`、`johnhull/research/DSINC/pilot_summary.json`（2,000,000 bytes以下）
- Modify: `johnhull/ROADMAP.md`

**Interfaces:**
- Consumes: Task 6の`run.py pilot` / `freeze`
- Produces: Task 8が読む`freeze_manifest.json`

- [ ] **Step 1: pilotを実行する**

```bash
RUN=$DATA/pilot-$(date -u +%Y%m%dT%H%M%SZ)
cd $WT && $PY johnhull/research/DSINC/run.py pilot --output $RUN
```

Expected（planning runに基づく。合計600秒以内）:
- `paper_match: pass`（7点、最大の差は約3.4e-7）
- 診断:
  - EEP列の差は≤4e-7。
  - S0の時間倍（`time_x2`）はN=200列と6桁で一致する。
  - 論文の格子のFDは、Table 4のFD列の粗い格子と≤5.1e-7、細かい格子と≤4.8e-7で一致する（印刷の丸め程度。spike_fdで(241,101,150)と(481,201,300)を実測）。
- `fd_reference T0.5: converged`
  - xは`converged`（次数≈2）、varとtimeは`below_resolution`、domainの差は0。
  - P_ref ≈ American [.1076000, .0486582, .0194955]。
- `s0_vs_reference T0.5`: ≤4.1e-6
- `boundary T0.5: pass`（最大の外れ≈1.03セル、FDの移動1セル、coverage 1.0）
- `crossing_lower T0.5`: ≤1e-8
- `budget`: mainの必須50本の見積もりの合計≤1800秒、1件≤180秒

- [ ] **Step 2: 判断する**

`$RUN/pilot_summary.json`の`all_pass`を確かめる。
- Falseの場合: freezeしない。止まった位置・原因・hashを`$RUN/stop.json`に残し、ユーザーに報告する。計画の改訂が必要で、閾値や予算は緩めない。
- Trueの場合: Step 3に進む。Hestonの任意10本は、予算内で走った分だけを準備結果として残す。

- [ ] **Step 3: freezeする**

```bash
cd $WT && $PY johnhull/research/DSINC/run.py freeze --pilot $RUN --output johnhull/research/DSINC/freeze_manifest.json
cp $RUN/pilot_summary.json johnhull/research/DSINC/pilot_summary.json
$PY johnhull/research/DSINC/run.py replay --results $RUN/results.json
```

Expected: freezeが成功し、replayは`{"match": true, ...}`。protocol.jsonはpilotから変えない（freezeがpilotの`protocol_digest`と照合する）。

- [ ] **Step 4: Commit**

ROADMAPの「現在地」に、pilotの結果（gate、費用、件数）とfreezeのsha256を書く。

```bash
git -C $WT add johnhull/research/DSINC/freeze_manifest.json johnhull/research/DSINC/pilot_summary.json johnhull/ROADMAP.md
git -C $WT commit -m "Freeze the DSINC main protocol from the passing pilot"
```

---

### Task 8: main、成果の書き出し、図、README、独立レビュー

**Files:**
- Create: `johnhull/research/DSINC/results/`（export）、`johnhull/research/DSINC/figures/{price_error_cost,exercise_boundary,refinement_stability}.png`、`johnhull/research/DSINC/REVIEW.md`
- Modify: `johnhull/research/DSINC/README.md`（結果）、`johnhull/MODEL_INDEX.md`（Verificationの列）、`johnhull/ROADMAP.md`

**Interfaces:**
- Consumes: `freeze_manifest.json`、Task 6のCLI

- [ ] **Step 1: mainを実行する**

```bash
MAIN=$DATA/main-$(date -u +%Y%m%dT%H%M%SZ)
cd $WT && $PY johnhull/research/DSINC/run.py main --freeze johnhull/research/DSINC/freeze_manifest.json --output $MAIN
```

Expected:
- 合計1800秒以内。全88本がrecordに残る（必須50本、条件付き38本のうち不要なものは`not_run_condition`）。
- 満期ごとに`adopted`（S0またはS1、あるいはnot_achieved*）、`bounds`、`boundary`が出る。
- `paper_match`と`reproduction_label`が出る。
- 途中で止まった場合も、records.jsonと止まった理由が残る。

- [ ] **Step 2: 再計算で照合し、書き出す**

```bash
cd $WT && $PY johnhull/research/DSINC/run.py replay --results $MAIN/results.json
$PY johnhull/research/DSINC/run.py export --results $MAIN/results.json --to johnhull/research/DSINC/results
du -sh $MAIN && du -b johnhull/research/DSINC/results/*
```

Expected: `"match": true`。run rootは50 MiB以下が目標で、超えた場合は実測値をREADMEに書く。exportの各ファイルは2,000,000 bytes以下。

- [ ] **Step 3: 図を描いて目で確かめる**

```bash
cd $WT && $PY johnhull/research/DSINC/plot.py --results $MAIN/results.json --output johnhull/research/DSINC/figures
```

Expected: PNGが3枚できる。Readで開き、軸・単位・maskの表示・失敗の件数が読めることを確かめる。

- [ ] **Step 4: READMEに結果を書く**

README.mdの「結果」に次を書く。
- paper_matchの表（7点と診断の列）。
- 6件の価格（spectralの採用段、reference、差、EEP）。
- 満期ごとの採用段と、各感度の差。
- 境界gate（coverage、最大の外れ、mask、多重交差）。
- 費用（cold setup、warm query、FDは1回の値）。
- 失敗の会計（元の件数）。
- `reproduction_label`。
- 未検証の範囲: 市場での妥当性、他のモデル、Deltaの精度認定、境界近傍のspotでの補間誤差。

- [ ] **Step 5: 全体を検証する**

```bash
cd $WT && $PY -m pytest -q johnhull/hullkit/tests johnhull/report/tests
$RUFF check johnhull/research/DSINC johnhull/hullkit/src/hullkit/_dsinc_*.py johnhull/hullkit/tests/test_dsinc_*.py
$RUFF format --check johnhull/research/DSINC johnhull/hullkit/src/hullkit/_dsinc_*.py johnhull/hullkit/tests/test_dsinc_*.py
git -C $WT diff --check main...HEAD
```

Expected: 0 failed、`All checks passed!`、format --checkの変更0件、空白の警告なし。失敗があれば、既存の失敗だと判断する前に、mainの同じコマンドの結果と比べる。

- [ ] **Step 6: 独立レビューを受ける**

branch全体を、新しいcontextの最も能力の高いモデルにレビューしてもらう。`superpowers:requesting-code-review`に従い、設計・計画・pilotとmainの要約を渡す。
- Critical/Importantの指摘は修正し、Step 5を再実行する。
- `REVIEW.md`に、判定、指摘、対応、レビュー対象のsha256を書く。

- [ ] **Step 7: 索引と現在地を確定してCommitする**

- MODEL_INDEXのDSINC 3行のVerificationを、「research/DSINC v1: <label>、paper_match <pass/fail>、採用段 <T=.5/T=1>」に更新する。
- ROADMAPの「現在地」と「完了までの計画」を、実測の件数で更新する。

```bash
git -C $WT add johnhull/research/DSINC johnhull/MODEL_INDEX.md johnhull/ROADMAP.md
git -C $WT commit -m "Record the DSINC main run, figures and independent review"
```

- [ ] **Step 8: 統合の方法を聞く**

`superpowers:finishing-a-development-branch`に従い、mainへのmerge・branchの保持・PRのどれにするかをユーザーに聞く。pushは承認されていない。
