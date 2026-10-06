# P4 追っかけレビュー記録（Claude）

P4（Ch10–21）のロジック先行実装を、Claude が後追いで確認した記録。正式受入の判定ではない。指摘は ID で追跡し、対応したら「状態」を更新する（このファイルは Claude が更新し、P4_STATUS.md とは分ける）。

- 確認対象：push 済みの `codex/p4-logic` を一時ディレクトリへ展開して実行（並行作業中の未追跡ファイルを含めない）。
- 再現コマンド：`cd <checkout>/johnhull/hullkit && PYTHONPATH=$PWD/src <repo>/.venv/bin/python -m pytest -q -p no:cacheprovider tests`（worktree の `uv run` は conftest の import で失敗し、ルート `.venv` の素の pytest は main の hullkit を読む）。
- 原典照合：`johnhull/options, futures and other derivatives 11th.pdf`（GE 版）の pdftotext 出力。数値はモジュールを使わず式から再計算した。
- 重大度：**中**＝有効な入力で誤った値を返す、または全 suite が落ちる。**低**＝境界ケースの誤り・検証の主張が実態より強い・検出力のないテスト。**nit**＝記述・許容幅など。

## 指摘一覧

| ID | 重大度 | 内容 | 場所 | 初出 | 状態（最終確認） |
|---|---|---|---|---|---|
| R-01 | 中 | P3 の docstring 修正 `e4bc9d7b` が未マージ。hullkit 全 suite が `test_docstrings` で3 failed | `codex/p3-logic` → `codex/p4-logic` | R1 | 解決（R3 `06bff3ca`、push 済み） |
| R-02 | 中 | 有効な入力で権利確定の判定を誤る（下記 R2-1） | `_employee_options.py:78` | R2 | 解決（R3 `3a75aed7`） |
| R-03 | 低 | 「ruff PASS」は `ruff check` だけ。`ruff format --check` は P4 新規の56ファイル全部が不合格（main 既存13は別件）。`make hull-release` は format を含む | P4 全ファイル | R1 | 解決（R4 `00d8a651`。P4 の79ファイル。main 既存13は別件） |
| R-04 | 低 | 節ごとの確認に hullkit 全 suite（約100秒）を入れていない。R-01 を見逃した原因 | P4_STATUS「検証」 | R1 | P4 では終了。P5 以降へ引き継ぎ（下記 R4） |
| R-05 | 低 | P4_STATUS にテスト実行コマンドがない | P4_STATUS | R1 | 解決（R4 `c89f749d`） |
| R-06 | 低 | ロジック進捗の分母がない（P3 は36/37、P4 は「52節」のみ） | P4_STATUS | R1 | 解決（Codex が計算対象95/95を明記） |
| R-07 | 低 | IV 二分法が絶対価格許容 1e-10 のため、小さいが正の価格で σ=0 や早期停止を返す（R2-2） | `_bsm_foundations.py:218,226` | R2 | 解決（R3 `e1acc40d`。深い ITM の早期停止も同根で修正） |
| R-08 | 低 | 二項 tail の strike 一致の丸め窓が狭く、節点と同値の strike を ITM に数える（R2-3） | `_binomial_foundations.py:173-177` | R2 | 解決（R3 `171a8227`） |
| R-09 | 低 | 配当付き木のテストに検出力がない（R2-4） | `test_option_properties_dividends.py` | R2 | 解決（R4 `a0e03774`） |
| R-10 | 低 | モジュールを呼ばない・恒等式のテストを「独立検証」と数えている（R2-5） | 複数 | R1 | 解決（R4 `cc36b2ff`・`c89f749d`・`ddf143d0`） |
| R-11 | 低 | Euler 積モーメントの式をどのテストも検証していない（R2-6） | `test_stochastic_foundations_stock.py:41-53` | R2 | 解決（R4 `2ea730b7`） |
| R-12 | 低 | §12.1「無配当の採算不能」の検証が配当の効果を分離していない（R2-7） | `test_option_strategies_notes.py:47-54` | R2 | 解決（R4 `2aaa64f4`） |
| R-13 | 低 | §13.8/13.10/13.11 の印刷値は既存 `trees` が計算しており、新モジュールの寄与は係数・5段方針列挙・終端和 | P4_STATUS | R2 | 解決（R4 `c89f749d`） |
| R-14 | nit | 許容幅が実誤差の5–170倍（R2-8）。誤りは隠していない | 複数 | R2 | 解決（R4 `3353c856`・`be443143`） |
| R-15 | nit | 記述の誤り：fBM 共分散を「equation 14.20」（14.20 は相関）、§11.3「本文11値」（列挙は12値） | `_stochastic_foundations.py:153`、P4_STATUS | R2 | 解決（R4 `c89f749d`） |
| R-16 | nit | `american_put_interval` が P≥max(K−S,0)・P≤K で絞らず、`no_dividend_bounds` と扱いが不揃い。C≤S も未検証 | `_option_properties.py:145-148` | R2 | 解決（R4 `a1e02606`） |
| R-17 | 低 | 絶対許容・厳密比較の同型バグ3件：先物 parity が正しい deep ITM call を拒否、早期行使の引き分けを「厳密に有利」と判定、経過時間＝満期を丸めで拒否 | `_futures_options.py:86`、`_index_currency.py:243,254`、`_greeks_hedging.py:365` | R4 | 解決（R4 `10f20d7c`・`36ae6523`・`64d1850f`） |
| R-18 | 低 | 値を変える変異が既存テストを全件通過：Ch17/18（金利・利回りの入替え、根の継続価値、先物満期）、Ch19 σ=0 の forward、Ch21（配当日直前の行使・割合配当のマスク・時刻許容・CN/hopscotch） | Ch17–21 のテスト | R4 | 解決（R4 `c0f8372c`・`0eca4540`・`387ac0b4`・`4155cea1`） |
| R-19 | 低 | 記述の誤り：Ex19.9 は88m/92mとも残存0.5年で一致（「同一規約で不一致」は誤り）、Table 20.3 K44 の58.8は丸めputと一致（tol .06 が隠していた）、§21.3 の S*/PV の数値 | P4_STATUS §19.13/§20.8/§21.3 | R4 | 解決（R4 `d76491a5`・`ddf143d0`） |
| R-20 | nit | contracts の `round()` が偶数丸め（−6.5→−6）。Hull は「最も近い整数」とだけ書き .5 の扱いは未定 | `_greeks_hedging.py:449` | R4 | 変更せず（原典が .5 を定めない） |
| R-21 | nit | P4_STATUS の §17.5（54）と §17.6（48）の件数が節順と逆。各節の完了時点の値なので改変しない | P4_STATUS | R4 | 記録のみ |

## R1 2026-10-05（Ch10、`010507a6`）

- 対象 56 tests PASS（PYTHONPATH 指定時）。`ruff check` PASS、`ruff format --check` は新規7中5ファイル不合格（R-03）。
- 原典照合：§10.1（115→1,000、120→15/株、102→−3）、§10.3（1,200）、§10.4（Ex10.1/10.2、満期3例、20%=6-for-5）、§10.6（4.25/0.25/25）、§10.7（4,240/3,520/5,040、put 下限は 10%×K、指数15%、日次時価、covered 0.5min(S,K)）すべて一致。
- 満期月の重複は「4限月」の記述から strict-after の読みに決まり、実装は妥当。丁度9か月は原典に記述なく、全額払い側の解釈を明記済み。
- 独立性：§10.2 の min 形は max 形の符号反転、§10.6 の Decimal 計算は同式の書き直しで、整合チェックとして扱う（R-10）。
- hullkit 全 suite：4,321 passed／6 skipped／3 failed。3件は P3 由来の docstring 漏れ（R-01）。P3 側は `e4bc9d7b` で修正・push 済み（4,266 passed／0 failed）。

## R2 2026-10-06（Ch11–16、`f70e5b21`）

- hullkit 全 suite：4,656 passed／6 skipped／3 failed（R-01 のみ）。P4 新6モジュールは docstring・MODEL_INDEX とも登録済み。
- 対象テスト件数は P4_STATUS と一致（Ch11 78・Ch12 50・Ch13 43・Ch14 36・Ch15 90・Ch16 26）。
- 原典の印刷値は全章で再現（下記「確認済み」）。数式の誤りは見つからず、指摘は境界ケースとテストの検出力に集中する。

### R2-1 権利確定の浮動小数比較（R-02）

`eligible = (time >= vesting)` で `time = i*dt` を許容誤差なしに比べる。確定日が節点に一致しても丸めで1期遅れる。行使倍率側は `np.isclose` を使っており不揃い。

- 例：`employee_option_tree(100, 40, .05, .3, .3, 3, vesting=.1, departure_probability=[0, 1, 0])` は `dt=0.09999999999999999` で 0.0 を返す。`vesting=.0999999` なら 60.1995（期待値：t=0.1 で確定済み・ITM で離職→即時行使）。
- T=1–10年・1–200期・確定0.5–5年のうち確定日が節点に一致する3,234通り中55通りで誤判定（例：T=1・98期・確定0.5年）。
- テストの全経路列挙（`test_employee_options_valuation.py:29`）と MC（同:98）が同じ `i*dt >= vesting` を複製しているため検出できない。
- 修正案：確定ステップを整数で決める（`ceil(vesting/dt − tol)`）か、`isclose` を含めて比較する。列挙側は独立に節点番号で判定する。

### R2-2 IV 二分法の絶対許容（R-07）

`price − lower <= 1e-10` で σ=0 を返し、収束判定も `abs(error) <= 1e-10`。docstring「決定論的下限でのみ σ=0」と食い違う。

- S=100・K=200・r=5%・T=0.1・σ=30% の BSM 価格 3.6e-13 → 0.0（既存 `hullkit.volatility.implied_vol` は 0.30）。
- K=150・σ=20% の価格 1.41e-10 → 0.195（早期停止）。
- 修正案：相対許容、または σ 幅での収束判定。既存 `volatility.implied_vol` の再利用も検討。

### R2-3 二項 tail の strike 一致（R-08）

丸め窓 `16*ulp(|threshold|)` は threshold の大きさに比例するが、`ln(S/K)/(2σ√dt)` の誤差は n と 1/(σ√dt) で増える。

- S=100・r=5%・σ=30%・T=1・n=9、K=49.65853037914092（節点値）→ `first_in_the_money_up_moves=1`（strict j>a なら2）、u2=0.998144（正しくは 0.981251、差はその節点の確率）。
- K=S·u^j·d^(n−j) で作った一致 strike は n<60 で1,829中103件を誤分類。価格は一致節点の payoff が0なので影響しない（誤差1e-13）。
- テスト（`test_binomial_foundations_tails.py`）は 100·e^0.2 型のみで、P4_STATUS §13.appendix「厳密j>a（strike一致含む）」は言い過ぎ。

### R2-4 配当付き木のテストの検出力（R-09）

`cash_dividend_tree` に、ありうる誤りを入れて既存テストを流した。

- 配当準備金の割引を外す（`_option_properties.py:246`）：13件中12件が通過。落ちるのは `test_call_early_exercise_only_at_ex_dates…` だけ。
- 配当日の行使比較から配当落ち後の側を外す（同:276 を `payoff(after+cash[i])` のみに）：Ch11 の78件すべて通過。
- 許容幅 0.012–0.015 に対し、実誤差は coarse−fine ≤0.0019、fine−PDE ≤0.0008、fine−閉形式 7e-5。
- 修正案：許容幅を実誤差の数倍まで縮め、配当日の前後で行使が分かれる put のケースを足す。

### R2-5 検証と数えているが検証していないテスト（R-10）

- モジュールを呼ばない：`test_option_properties_dividends.py:98`（両辺に同じ `funded_payments` を足した恒等式。§11.7「配当再投資の状態会計」）、`test_bsm_foundations_iv.py:60`（`15/100 == .15`。§15.11「15points=15%」）、`test_bsm_foundations_warrants.py:45`（`(50−45)*100000`。§15.10「Snapshot15.3」）。
- 恒等式・自己比較：`test_option_properties_parity.py:54-56`（購入と買戻しが打ち消し合う）、`test_bsm_foundations_hedge.py:28-29`、`test_employee_options_backdating.py:23`、`test_bsm_foundations_price.py:26`（`bsm.call_price` 同士）、`test_option_properties_factors.py:81`（`trees`/`fd` のみ呼ぶ）。
- §14.5 の「独立 Cholesky」は Hull の u, ρu+√(1−ρ²)v と代数的に同一で、実質の検証は MC 共分散だけ。§14.6 の forward 検証は `simulate_gbm_paths` の drift を再利用。
- 対応案：削除は不要。P4_STATUS の「独立」の語を外し、整合チェックとして記載する。

### R2-6 Euler 積モーメント（R-11）

`euler_stock_moments` の式自体は正しい（E[(1+μΔt+σ√Δt ε)²]=(1+μΔt)²+σ²Δt）。ただし二次モーメントから (μΔt)² を落とす変異でも両テストが通る。MC は Euler と厳密 GBM を区別できない（分散差 0.8SE）。n=1–2 の厳密な求積・列挙を足すと検証になる。

### R2-7 §12.1 無配当の採算不能（R-12）

σ=25% では q=1.5% でも call 221.15 > 予算 164.73 で不成立になり、配当の効果を切り分けていない。本文の主張は c ≥ S−Ke^{−rT}＝予算 から σ・満期によらず成り立つので、その不等式で直接確かめる。

### R2-8 許容幅（R-14）

`test_binomial_foundations_convergence.py:37`（.006、実誤差 8.7e-4）、`tails.py:46`（.003、2.4e-4）、`derivagem.py:33`（.01、6e-4）、`assets.py:45`（.02、4e-3）、Ch16 MC（6SE=価格の3%）、forward Euler MC（約10%）。いずれも厳密求積・列挙と重複しており、テスト群全体の判別力は保たれている。

### 確認済み（モジュールを使わず再計算）

- Ch11：7.116/4.677、下限 3.71/3.91/2.01/1.01、18.79/38.96、裁定利益 .79/1.79/1.04/3.04、32.26/31.02/1.02/29.73/0.27、Ex11.3 の 0.18/1.68/2.50、(11.1)–(11.11) の不等式の向き、`cash_dividend_tree` は独立 escrowed 木と 1e-14 で一致。
- Ch12：Ex12.1 の 835.27/164.73・σ 境界14.937164%・call 221.15/119.11/217.36/281.28・予算 86.07/259.18/451.19、Snapshot 12.1 の欧州 box 4.9338・米国 box 未丸め5.2668/丸め和5.26、§12.5 の誤差 0.020115→0.005323。
- Ch13：p=.5503・0.54478・p*=.6266・55.958%・0.9497・4.192654・5.089632、Figure 13.10 の 7.428402、DerivaGem 7.4284/7.6709/7.4710・欧州6.7569・BSM6.7601、Ex13.1–13.3 の 53.395/0.01888/2.8356（全節点）、CRR の Δt² 係数、付録 U1/U2。
- Ch14：Table 14.1 の全22セル（全精度累積で111.5353→111.54。セント丸め累積では 106.07 となり印刷 106.06 と合わないので実装の選択が正しい）、(14.12)・(14.16)・(14.17–19)、fBM の隣接増分相関 2^{2H−1}−1、二次変分の分散 2b⁴TΔt、(14A.10–11)。
- Ch15：Ex15.1–15.3、Snapshot 15.1、Table 15.1（Σu .095310・s .0121593・19.30%・SE3.05%）、Ex15.6（c4.7594/p0.8086）、Ex15.7（7.0402/5.8669/1.1734m/38.8266）、IV 0.2345129、VIX 800ドル、Ex15.9（c3.6712）、Black 近似、永久到達解、15A。
- Ch16：Ex16.1 6.3062、Ex16.2 の全15節点（根14.9692・通常 call 17.9828・行使確率 .43/.81/.335・継続価値 11.05/106.64/24.95）、MSU の E[S_T²/S0]、指数連動 strike 33/25.50、backdating の差8。

## R3 2026-10-06（修正、`171a8227`）

本人指示で R-01・R-02・R-07・R-08 を `codex/p4-logic` へ直接修正し push した。各修正は回帰テストが修正前に失敗することを確認してから実装した。

- R-01：`codex/p3-logic` をマージ（`06bff3ca`）。`test_docstrings` の3件が解消。
- R-02（`3a75aed7`）：権利確定の比較に行使倍率と同じ 8eps の相対許容を入れた。回帰テストは解析値 100−40e^{−0.005} と、確定日を節点の直前へずらした価格との一致（T=1・98期・0.5年、T=3・94期・1.5年、T=0.3・3期・0.1年）。
- R-07（`e1acc40d`）：σ=0 は厳密な決定論的下限の価格だけで返し、`price_tolerance` を時間価値（price−lower）に対する相対値にした。小さい OTM 価格（3.6e-13、1.4e-10）に加え、時間価値が 1e-7 程度の深い ITM（修正前は σ を最大 0.019 誤る）も回帰テストに入れた。時間価値が数 ulp しかない入力（価格57・時間価値2.8e-14）は倍精度で識別できず、誤差0.0003が残る。
- R-08（`171a8227`）：strike 一致の判定を、最寄り節点との log 距離 ≤ 64eps·max(1, |ln(K/S)|, n) に変えた。回帰テストは n<60 の全節点値 strike。σ 0.01–1.5・n≤1000・3通りの strike 構成と ±1e-7 のずらしで 2,260件の誤分類0を確認。
- hullkit 全 suite：5,037 passed／6 skipped／0 failed（`171a8227`）。変更ファイルの `ruff check` PASS。整形（R-03）は P4 全体の一括作業として触れていない。
- 参考：Ch18 の `_index_currency.carry_implied_vol` は当初から σ 側の収束判定で、Ch20 の smile もこちらを使うため R-07 の誤りは後続章に波及していなかった。
- 運用メモ：修正中、P4 セッションが同じ m29 で §21.1–21.4 をコミット・push した。私の未コミット変更を含めずにコミットされており衝突はなかったが、同一 worktree の同時作業は危険。次回の直接修正は P4 セッションの停止を確認してから行う。

## R4 2026-10-06（P4 完了後の全体レビューと修正、`00d8a651`）

Codex が Ch10–21 の計算95/95を完了して P5 へ移った後、Ch17–21 の新7モジュールを照合し、残りの指摘をまとめて修正した。作業は `claude/p4-review` worktree で行い、`codex/p4-logic` へ fast-forward で push した（`d9461273..00d8a651`、18コミット）。

- 原典照合：Ch17–21 の印刷値は全件再現（Ex17.1–17.2、Table 17.1/17.2、Ex18.5–18.7、§18.9、Ex19.1–19.10、Table 19.2/19.3、Ex20.1、Table 20.1–20.3、Ex20A.1、Ex21.1–21.8、Table 21.3–21.5）。数式の誤りはなし。
- バグ（R-17）：3件とも R-02/R-07 と同じ型。回帰テストが修正前に失敗することを確認してから修正した。
- テストの検出力（R-09・R-11・R-12・R-18）：実在しうる変異を入れ、強化後のテストで全件が落ちることを確認した。独立参照は GK 式、Fraction の CAPM、小さい木、Black、節点番号で揃える配当木、密行列の CN、節点ループの hopscotch、Gauss–Hermite。
- 記述（R-10・R-13・R-15・R-19）：恒等式・自己比較のテストは削除せず、P4_STATUS で「整合確認」「既存モジュール」と明記した。
- 整形（R-03）：P4 で追加・変更した79ファイルに `ruff format`。`ruff check`・`format --check` は P4 分で PASS（main 既存13ファイルのみ残る）。
- 検証：hullkit＋report のテスト一式 5,753 passed／6 skipped／0 failed（`00d8a651`、AGENTS.md の scoped コマンド相当）。修正前の基準は 5,728 passed。
- P5/P6 への影響：`codex/p5-logic`・`codex/p6-logic` は修正前の `d9461273` から分岐し、P4 のファイルに触れていない。`origin/codex/p4-logic` のマージは競合なしを確認済み。
- 引き継ぎ（R-04）：P5 以降も節ごとの確認に hullkit 全 suite（約100秒）を入れること、新規ファイルは `ruff format` まで通すことを推奨する。今回の同型バグ（浮動小数の時刻比較・絶対許容・引き分け判定）は P5/P6 でも確認対象にする。

