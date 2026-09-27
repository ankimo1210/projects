# P8 再確認：未再確認の監査報告（R1–R4・R6・R11）と保存値依存 5 項目

- 日付：2026-09-27
- 対象：`main` の HEAD `7c4bb109`（`git -C /home/kazumasa/projects rev-parse --short HEAD`）。監査の記述は `cae1cd84` 時点。
- 位置づけ：製品・成果物に対する読み取り専用の調査。変更は準備文書のみ。
  再現スクリプトは git 管理外の `/home/kazumasa/projects/tmp/johnhull-prep/scratch/p8/` に置き、
  `/home/kazumasa/projects` から `uv run --no-sync --package hullkit python <script>`
  （deep_hedge_price のコードは `--package deep-hedge-price`）で実行した。
- 入力：`/home/kazumasa/projects/johnhull/docs/SECTION_AUDIT_2026-09-14.md`（§3 の R 表、§7、§11.2、§12）、
  `/home/kazumasa/projects/johnhull/docs/superpowers/plans/2026-09-27-research-backlog.md`（§5.1）、
  Hull GE 本文の抽出 `/home/kazumasa/projects/tmp/johnhull-prep/hull/sections/19.*.txt`。
- 制約：CPU のみ・1 回 5 分以内・学習なし・ネットワークなし。
- 記法：**事実**＝コードを読んだか実行して確かめたこと。**仮説**＝原因の候補で、まだ切り分けていないこと。**未確認**＝調べていないこと。

> §2–4 は中断前の調査記録を引き継ぎ、再開後に同じprobeを再実行して点推定の一致を確認した。
> R1の診断SEはantithetic pairを独立単位として補正した。§5–8も再開後に実行済み。
> 既定出力・受入判定は変更していない。

## 0. 要約

| ID | 再現 | 原因 | 既定出力の変化 | 影響する成果物・検査 | 判断が要るか | 前提になる作業 |
|---|---|---|---|---|---|---|
| R1 | 再現（原因は 2 つ。監査が挙げていない先読みの方が大きい） | 補償項の不一致（IV −0.005〜−0.008）と、分散の先読みで株価がマルチンゲールでないこと（$E[S_T]/S_0$=0.95–0.98、IV −0.045〜−0.055、スマイルの傾きが逆） | 変わる（vol 19 の rBergomi 教師 IV が約 +0.05） | vol 19 `surfaces.npz`・`metrics.json`・ノート出力・`VALIDATION.md`。acceptance の判定と改竄テストは変わらない見込み | 要る（§7 既定出力） | なし（着手可能）。RB-F06 の rough 版・RB-B19/B21・rough を使う RB-A02 の前提 |
| R2 | 再現（監査の数値と一致） | 対数空間の予測をそのまま exp（条件付き中央値寄り）。`log_har` に加え `regularized_linear`・`pca_ridge_challenger` も同じ（系列 4 モデルも同形だが未検証） | 変わる（Duan smearing で h1 QLIKE 3.54→1.41 など。PCA-ridge は h5 で EWMA に勝つ側へ） | vol 20 `forecast_paths.npz`・`metrics.json`・portal 図・ノート・`VALIDATION.md`・負の結果の文面。モデル追加なら acceptance の 10 モデル集合 | 要る（§7 既定出力。別モデル追加なら検査集合） | なし。R3 と同じ vol 20 再生成でまとめる。RB-A04/A05/A06・RB-B20・H23 の前提 |
| R3 | 再現 | `synthetic_hedge_capstone` の 1 つの `volatility` が経路・プレミアム・デルタを兼ね、パイプラインが予測ボラを渡すので真値≡予測。予測も walk-forward の 10 モデルとは別系列 | 経路用のボラを足すだけなら不変。vol 20 で予測誤差を入れると変わる | vol 20 `e2e_*`・`metrics.json` の `end_to_end`・acceptance `economic_comparison_controls`（戦略集合を固定）・改竄テスト・portal 図・ノート | 要る（戦略集合と評価設計、BA-01 と同時） | R2（補正後の予測を使うため）。RB-A04/A05/B17/B20・H23 の前提 |
| R4 | 再現 | Poisson の消費乱数数が強度で変わり、後続の正規乱数がずれる | stream を変えれば変わる | vol22 teacher・Greek・event差・NPZ/JSON/ノート | 既定出力変更は別判断 | RB-F05 の0DTE版より先 |
| R6 | 再現 | feeは同じno-fee終点への補償だけ。gross不変は式の構造 | fee-aware経路へ拡張すると変わる | vol24 AMM図・negative result・受入 | 新モデル/API/出力は別判断 | feeとLVRの意味を先に固定 |
| R11 | 全12値の丸め再現 | 成績表は利息・割引を除外、現行APIは資金繰り込み | 原典用計算を足すならその図だけ変わる | vol03 Table19.1/19.4、§19.2/19.4 | 公開API・既定出力変更は別判断 | 原典用と金融的規約の区別 |
| 保存値依存5項目 | 5件とも依存を確認 | 評価元の配列/終了状態/測定来歴が不足、または保存値だけで判定 | 再構築と検査追加が必要 | vol18×2、19、21、22 | 検査集合・出力変更は別判断 | §8の根拠保存設計 |

## 1. コード位置の移動（HEAD `7c4bb109` と監査時 `cae1cd84` の比較）

| ID | 監査の引用 | HEAD での位置 | 移動 |
|---|---|---|---|
| R1 | `johnhull/hullkit/src/hullkit/surrogate_data.py:319-324` | 同じ（`rbergomi_call_price` は :284、カーネルのループ :320-323、補償項 :324） | なし |
| R1 | `johnhull/hullkit/tests/test_surrogate_data.py:120` | 同じ（η=0 のテストだけ） | なし |
| R2 | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:880` | 同じ | なし |
| R3 | `deep_hedge_price/src/deep_hedge_price/hedge_capstone.py:91-98` | 同じ（:92 経路、:97 プレミアム、:98 デルタが同じ `volatility`） | なし |
| R4 | `johnhull/hullkit/src/hullkit/zero_dte.py:357-361` | :386-394（`rng.poisson` は :389） | +29 行 |
| R6 | `johnhull/hullkit/src/hullkit/amm.py:101-108,145-147` | 同じ | なし |
| R6 | `johnhull/hullkit/src/hullkit/frontier_reference.py:1290-1301` | :1369-1380（`fixed_result` と `result`） | +79 行 |
| R11 | `johnhull/hullkit/src/hullkit/hedging.py:3-8` | 同じ | なし |


## 2. R1：rBergomi 教師の補償項（vol 19）

**監査の報告：** カーネルは右端点リーマン和なのに、補償項は連続時間の $t^{2H}$。離散分散 / $t^{2H}$ = 0.533、12 step の $E[v_T]/\xi_0$ = 0.915–0.942。既存テストは η=0 だけ。

**実行したもの：** `/home/kazumasa/projects/tmp/johnhull-prep/scratch/p8/r1_rbergomi.py`
（`uv run --no-sync --package hullkit python tmp/johnhull-prep/scratch/p8/r1_rbergomi.py`、約 3 秒、結果は同じ場所の `r1_rbergomi.json`）。
再開後は `scratch/codex_integration/r1_antithetic_recheck.py` で元probeを読み込み、
SEだけを10万個のantithetic pair平均から計算して再実行した。元probe・元JSONは保持し、補正後JSONはwrapperと同じ場所に保存。
vol 19 の教師パラメータ（`deep_hedge_price/src/deep_hedge_price/frontier_reference.py:364-366`：ξ0=0.04、η=0.60、H=0.12、ρ=−0.60、12 step、S0=1、r=0、
K=exp(−0.02, 0, 0.02, 0.05)、T=0.25/0.75/1.25）で次を行った。

1. 離散カーネルの分散と $t^{2H}$ の比を解析的に計算した。
2. `rbergomi_call_price` を行単位で写した複製が、ライブラリと同じ推定値を返すことを確かめた（差 0.0）。
3. 200k パス（antithetic）で、現行方式と 3 通りの変種、厳密な参照を比べた。
   参照は Bayer–Friz–Gatheral の結合ガウス（Volterra 過程 $\tilde W$ と株価 BM の共分散を `hyp2f1` で組み、Cholesky で生成）で、
   分散は格子上で厳密、株価は左端点の Euler。格子は 12 step と 96 step。
4. コミット済みの `johnhull/volumes/19_inverse_surfaces/reference/surfaces.npz` の rBergomi 行が、現行ライブラリの出力と一致することを確かめた。

**結果（事実）：**

| 量 | T=0.25 | T=0.75 | T=1.25 |
|---|---:|---:|---:|
| 離散分散 / $t^{2H}$（12 step 目） | 0.5330 | 0.5330 | 0.5330 |
| $E[v_T]/\xi_0$ 解析値 | 0.9415 | 0.9246 | 0.9151 |
| 同 MC（現行） | 0.9416 | 0.9250 | 0.9147 |
| $E[S_T]/S_0$ 現行（pair単位SE） | **0.98191（0.0000407）** | **0.96514（0.0000757）** | **0.95318（0.0001042）** |
| $E[S_T]/S_0$ 分散を左端点にした版 | 1.00000 | 1.00005 | 1.00005 |
| ATM IV：現行 | 0.1476 | 0.1391 | 0.1354 |
| ATM IV：補償項だけ離散分散に直した版 | 0.1520 | 0.1444 | 0.1412 |
| ATM IV：分散だけ左端点にした版 | 0.1920 | 0.1896 | 0.1890 |
| ATM IV：両方直した版 | 0.1972 | 0.1963 | 0.1965 |
| ATM IV：厳密参照 12 step | 0.1977 | 0.1963 | 0.1958 |
| ATM IV：厳密参照 96 step | 0.1969 | 0.1951 | 0.1954 |
| コミット済み ATM IV（2,048 パス） | 0.1532 | 0.1428 | 0.1352 |
| コミット済み IV の MC 誤差（価格 SE / vega） | 0.0054 | 0.0053 | 0.0052 |

IV のスマイル（K の昇順）は、現行が T=0.25 で 0.1407 → 0.1560 と**右上がり**、厳密参照が 0.1997 → 0.1900 と右下がり（ρ<0 の rBergomi で期待される形）。
コミット済み配列も 0.139 → 0.157 と右上がり。コミット済み配列と現行ライブラリの出力は価格・IV とも差 0.0。

**判定：再現した。さらに監査が挙げていない、より大きい原因を確認した。**

- **原因 1（監査の指摘、確認）：** 補償項の不一致。`surrogate_data.py:324` は $\tfrac12\eta^2 t^{2H}$ を引くが、`:320-323` の離散カーネル和の分散は 12 step 目で $0.533\,t^{2H}$。
  そのため $E[v_T]/\xi_0$ は 0.915–0.942。ATM IV への影響は −0.005〜−0.008。
- **原因 2（新規、確認）：** 分散の時点ずれ（先読み）。`rough[:, index]` は当該 step の増分 `d_w[:, index]` を含む（:323）。
  それで作った `variance[:, index]`（区間の右端 $t_{i+1}$ の分散）が、同じ step の株価増分 `d_b[:, index]` に掛かる（:325-328）。
  `d_b` は `d_w` と ρ=−0.6 で相関するので $E[\sqrt{v_i}\,\Delta B_i] \ne 0$ となり、割引株価がマルチンゲールでなくなる。
  $E[S_T]/S_0$ は 0.95–0.98 で、pair単位SEの約445–460倍ずれる。ATM IV への影響は −0.045〜−0.055 で、原因 1 より大きい。スマイルの傾きの符号も逆になる。
- 両方を直した版と12 stepの結合ガウス参照の12価格は、独立seedのpair単位SEを合成した1.64SE以内で一致した。本fixtureの結果で、すべての条件で同じ精度になる保証ではない。
- 12 stepと96 stepの参照のATM IV差は約0.0004–0.0012。株価の時間離散化とMC変動を含み、差の全量をbiasと断定しない。修正の採用時には格子収束を別に検証する。
- コミット済みの教師 IV は、この独立参照より約 0.05 低い。これは教師自身が報告する MC 誤差（約 0.005）の約 10 倍で、`teacher_standard_error` は離散化の偏りを含まない。
- 先行probeのSEはantithetic経路を独立標本として数えていた。点推定は変わらないが、検定にはpair平均のSEを使う。保存済みteacherのSEはここでは変更せず、表示値と補正診断を区別する。
- 既存テスト（`johnhull/hullkit/tests/test_surrogate_data.py:120`、`deep_hedge_price/tests/test_surface_data.py:12-48`、`deep_hedge_price/tests/test_frontier_reference.py:14-20`）は η=0 か、形状・有限性・SE>0 しか見ないので、どちらの原因も検出しない。

**直し方の候補と影響：**

| 案 | 内容 | 既定出力 | 備考 |
|---|---|---|---|
| A | 分散を左端点（$v_0=\xi_0$、step i は $t_i$ の分散）にし、補償項を離散カーネル和の分散にする | 変わる | 変更は数行。上の「両方直した版」。12 step で厳密参照と一致 |
| B | 厳密な結合ガウス（Cholesky）を新しい scheme として足す | 変わる（既定を切り替えるなら） | 12–100 step なら数秒。正本の境界（`johnhull/CLAUDE.md` の表で exact rBergomi の重い実験は `rough_volatility`）との整理が要る |
| C | `scheme=` 引数を足し、既定は現行のまま（legacy） | 変わらない | 監査 §3 の「scheme 引数を足すなら now」。ただし vol 19 の教師は誤ったまま残るので、vol 19 で使う値を切り替えるには結局 A か B の判断が要る |

- 既定出力を変える場合（A・B、または C で vol 19 が新 scheme を使う場合）に更新が要るもの：
  - `johnhull/volumes/19_inverse_surfaces/reference/surfaces.npz` の `teacher_price[2]`・`teacher_implied_volatility[2]`・`teacher_standard_error[2]`、
    `metrics.json` の `array_fingerprint` と companion のハッシュ。再生成は `johnhull/scripts/build_frontier_artifacts.py --volume 19`（deep_hedge_price の builder。vol 19 自体は numpy/scipy だけで、torch は import されるが計算には使わない）。
  - `johnhull/volumes/19_inverse_surfaces/inverse_surfaces.ipynb` の出力と `VALIDATION.md`（どちらも `array_fingerprint` を表示している）。
  - vol 19 の acceptance は `numerical_teacher_ladder`（`johnhull/scripts/frontier_acceptance.py:216-238`、名前は :234）が形状・有限性・SE を見るだけなので判定は変わらない見込み。改竄テストに rBergomi 配列のケースはない。
  - portal 図と vol 19 ノートは rBergomi の IV を描いていない（制約曲面は Heston、`deep_hedge_price/src/deep_hedge_price/frontier_reference.py:179-185`）。
  - `surrogate_data.py` は vol 21 の SHA 契約の対象外（`johnhull/scripts/build_frontier_artifacts.py:568-571` は `frontier_reference.py` と `spx_vix.py` だけ）なので、vol 21 の再生成は要らない。
- 足すべきテスト：η>0 で $E[S_T]=S_0e^{rT}$（3–4 SE）、$E[v_t]=\xi_0$、小さい格子で厳密参照との一致。
- **判断が要る（監査 §7「既定の出力が変わる修正」）。** 監査は補償項だけを挙げていたので、判断材料に原因 2 を足す必要がある。
- 未確認：`deep_hedge_price/src/deep_hedge_price/surface_data.py:138,199` 経由で rBergomi を使う学習データの、コミット済み成果物の有無（テストは形状だけ）。

## 3. R2：Log-HAR の再変換バイアス（vol 20）

**監査の報告：** exp(E[log]) を平均の予測に使っている。train だけで smearing すると QLIKE が h1 3.545→1.414、h5 0.888→0.690、h21 0.163→0.141（EWMA は 1.316 / 0.458 / 0.053）。

**実行したもの：** `/home/kazumasa/projects/tmp/johnhull-prep/scratch/p8/r2_loghar_smearing.py`
（`uv run --no-sync --package deep-hedge-price python …`、numpy のみ、1 秒未満。結果は `r2_loghar_smearing.json`）。
コミット済みの `johnhull/volumes/20_surface_dynamics/reference/forecast_paths.npz` の特徴量・目的変数・fold 境界・fold ごとの scaler/PCA から、
対数空間で当てる 3 モデル（`log_har`、`regularized_linear`、`pca_ridge_challenger`）を fold ごとに ridge（1e-3、切片は罰則なし）で作り直した。
その上で train の残差だけから補正係数を求めた（Duan の smearing = mean(exp(残差))、対数正規の係数 = exp(½Var(残差))）。
EWMA・GARCH との差は、自前の moving-block bootstrap（block 8、2,000 回）で 95% 区間を付けた（参照実装の 160 回とは別物で、目安）。

**結果（事実）：**

- 作り直した予測は、3 モデル・3 ホライズンともコミット済みの予測と相対差 0.0 で一致した。
- QLIKE（テスト 84 行、3 fold）：

| モデル | h=1 | h=5 | h=21 |
|---|---:|---:|---:|
| `log_har`（コミット済み＝exp(E[log])） | 3.5446 | 0.8881 | 0.1631 |
| `log_har` ＋ Duan smearing（train のみ） | **1.4135** | **0.6896** | **0.1412** |
| `log_har` ＋ 対数正規係数 | 1.4685 | 0.6689 | 0.1434 |
| `regularized_linear` コミット済み → Duan | 2.5826 → 1.2187 | 1.6217 → 1.3001 | 0.2742 → 0.2473 |
| `pca_ridge_challenger` コミット済み → Duan | 2.4002 → 1.2033 | 0.5222 → **0.4101** | 0.1669 → 0.1463 |
| EWMA | 1.3156 | 0.4576 | 0.0531 |
| GARCH(1,1) | 1.2959 | 0.4075 | 0.0710 |
| harnet / tcn / lstm / transformer（コミット済み） | 4.34 / 3.27 / 3.51 / 3.14 | 0.54 / 0.56 / 0.59 / 0.54 | 0.087 / 0.079 / 0.090 / 0.089 |

- Duan の係数は h=1 で 3.07–3.45、h=5 で 1.19–1.26、h=21 で 1.03–1.05。テスト行の算術平均 / 幾何平均も 3.75 / 1.44 / 1.04 で、h=1 ほど偏りが大きい（1 日の二乗リターンの対数は歪みが強い）。
- EWMA との差（Log-HAR − EWMA、正は劣後）：h=1 はコミット済み +2.23 [+0.74, +5.00] → smearing 後 +0.10 [−0.10, +0.45]。
  h=21 は +0.110 [+0.003, +0.293] → +0.088 [−0.007, +0.256]。GARCH との差は h=21 で smearing 後も +0.070 [+0.016, +0.153]。

**判定：再現した（監査の数値と一致）。原因も確認した。** 範囲は監査の記述より広い。

- **原因（確認）：** 対数空間の予測をそのまま exp している（`deep_hedge_price/src/deep_hedge_price/frontier_reference.py:880-882`）。
  QLIKE は条件付き平均で最小になる損失なので、条件付き中央値に近い exp(E[log]) は系統的に低すぎて罰せられる。
- **範囲：** `log_har` だけでなく `regularized_linear`・`pca_ridge_challenger`（:881-882）も同じで、smearing で QLIKE が大きく下がることを確かめた。
  系列モデル 4 本（:904、`np.exp(target_mean + target_scale * normalized_prediction)`）も同じ形だが、補正には学習済みモデルの train 予測が要るので確かめていない（**仮説**）。
- **結論への影響：** 監査 §4.7 の負の結果「Log-HAR が h=1/21 で EWMA・GARCH に劣後（CI が 0 を含まない）」のうち、h=1 の劣後はほぼ再変換の偏りで説明できる。h=21 の GARCH への劣後は smearing 後も残る。
  acceptance の負の結果「PCA-ridge challenger が EWMA に勝てない」（h=5 の値で判定、`johnhull/scripts/frontier_acceptance.py:706`）は、smearing 後 0.4101 < 0.4576 で逆になる。

**直し方の候補と影響：**

| 案 | 内容 | acceptance | 備考 |
|---|---|---|---|
| A | 対数空間の全モデルに train のみの Duan smearing を掛ける（モデル名は変えない） | 判定は再計算で通る見込み（予測配列から QLIKE を再計算するため）。負の結果の文面が変わる | 既定出力が変わる。係数を fold ごとに配列で保存すれば、train 残差の保存と合わせて再計算の検査も足せる |
| B | 補正版を別モデルとして足す（例 `log_har_smeared`） | `horizon_model_ladders` が 10 モデルの集合を固定（`frontier_acceptance.py:473-495`）しているので、検査集合の変更になる | 監査 §7「acceptance の検査集合の変更」 |
| C | 分散水準で直接当てる、または QLIKE を最小化して当てる | A と同じ | 実装が大きい |
| D | 文書だけ直す | 変わらない | 負の結果の解釈を「再変換の偏りを含む」と書き換える |

- A・B・C で更新が要るもの：`johnhull/volumes/20_surface_dynamics/reference/forecast_paths.npz`（`walk_forward_h{1,5,21}_prediction_*`・`qlike_*`、互換配列 `walk_forward_prediction_har_ridge`・`walk_forward_prediction_challenger`・`walk_forward_qlike_*`）、
  `metrics.json`（全モデルの qlike・区間・regime 別・`paired_qlike_difference_model_minus_log_har` は Log-HAR 基準なので全行）、vol 20 のノート出力・`VALIDATION.md`、
  portal 図（`johnhull/report/report_builder/frontier_figures.py:54-61,210` が `har_ridge`・`pca_ridge` の予測を描く）。
  改竄テスト（`johnhull/report/tests/test_frontier_acceptance_tamper.py` の vol 20 ケース）は配列を倍率で壊すだけなので、そのまま通る見込み（未実行）。
- vol 20 の再生成（`build_frontier_artifacts.py --volume 20`）は系列モデル 4 本の CPU 学習（hidden 8・5 epoch、`torch.manual_seed` 固定）を含む。`make hull-artifacts-check` が毎回行っている規模だが、今回は実行していない。
- **判断が要る（監査 §7「既定の出力が変わる修正」の Log-HAR、B なら「acceptance の検査集合の変更」も）。** R3 と同じ vol 20 の再生成になるので、まとめて行うのが自然。

## 4. R3：予測からヘッジへの経路（vol 20）

**監査の報告：** パスもヘッジも予測ボラで作るので、予測誤差が P&L に入らない。モデル別・ホライズン別の経済指標もない。

**実行したもの：** `/home/kazumasa/projects/tmp/johnhull-prep/scratch/p8/r3_forecast_hedge.py`
（`uv run --no-sync --package deep-hedge-price python …`、数秒。学習なし。`walk_forward` は ridge のために import するだけ）。

1. `run_synthetic_surface_hedge_pipeline(seed=2020, n_paths=512, n_steps=12)`（vol 20 builder と同じ引数、`deep_hedge_price/src/deep_hedge_price/frontier_reference.py:1115-1119`）を実行し、コミット済みの `e2e_hedge_pnl` と比べた。
2. `synthetic_hedge_capstone` の `volatility` を 0.10–0.30 で動かした（同じ seed 2022）。
3. 経路のボラ（真値）とヘッジ・プレミアムのボラ（予測）を分けた delta 戦略を scratch で書き、両者が等しいときライブラリと一致することを確かめてから、予測誤差を入れた（20,000 パス）。

**結果（事実）：**

- 再構築した P&L はコミット済み配列と差 0.0。予測ボラは 0.20156（`metrics.json` と一致）。
- ボラを 1 つだけ動かすと、delta ヘッジの RMSE は 0.978 / 1.461 / 1.963 / 2.439 / 2.927（σ=0.10/0.15/0.2016/0.25/0.30）で、RMSE/σ は 9.74–9.78 とほぼ一定。
  平均 P&L は −0.11〜−0.15 で、取引コスト（0.05%）の分だけ。予測は実験全体の尺度を変えるだけで、予測の当たり外れは P&L に現れない。
- 経路とヘッジを分けた版は、両者が等しいときライブラリと差 0.0。予測を外すと：

| 真のボラ | 予測ボラ | 平均 P&L（SE） | ヘッジ RMSE | プレミアム − 公正価格 |
|---:|---:|---:|---:|---:|
| 0.20 | 0.15 | −2.095（0.015） | 2.982 | −1.987 |
| 0.20 | 0.20 | −0.107（0.014） | 1.936 | 0 |
| 0.20 | 0.25 | +1.875（0.014） | 2.768 | +1.982 |
| 0.15 | 0.20 | +1.883（0.011） | 2.457 | +1.987 |
| 0.25 | 0.20 | −2.088（0.018） | 3.304 | −1.982 |

  平均 P&L のずれはほぼ「予測ボラで受け取ったプレミアム − 真のボラでの公正価格」（vega × 誤差）で、RMSE も 1.94 から 2.8–3.3 へ増える。
- 予測の出どころ：パイプラインは別の 180 点の合成対数分散系列に HAR ridge を 1 本当てて、最後の 1 点の予測を使う（`deep_hedge_price/src/deep_hedge_price/surface_hedge_pipeline.py:59-72`）。
  walk-forward の 10 モデル（R2 の対象）の予測はヘッジにつながっていない。`metrics.json` の `end_to_end.strategy_metrics` は 4 戦略だけで、モデル・ホライズンの次元がない。

**判定：再現した。原因も確認した。**

- **原因（確認）：** `synthetic_hedge_capstone` は `volatility` 1 つで経路（`deep_hedge_price/src/deep_hedge_price/hedge_capstone.py:92`）、プレミアム（:97）、デルタ（:98）、2 本目のコール（:101-106）を作る。
  パイプラインはそこへ予測ボラを渡す（`surface_hedge_pipeline.py:73-79`）ので、真のボラ ≡ 予測ボラになる。
- 監査の「モデル別・ホライズン別の経済指標がない」も、コードと `metrics.json` で確認した。

**直し方の候補と影響：**

- 最小の変更は `synthetic_hedge_capstone` に経路用のボラ（例 `path_volatility`）を足し、既定では `volatility` と同じにすること。既定の出力は変わらない。
  ただし vol 20 で予測誤差を P&L に入れるには、パイプラインが真のボラ（例：`e2e_true_parameters[0]`=0.20、または実現分散）で経路を作る必要があり、そこで vol 20 の出力が変わる。
- モデル別・ホライズン別の経済指標（10 モデル × 3 ホライズンの予測を、それぞれヘッジと P&L に通す）を足す場合：
  - acceptance の `economic_comparison_controls` は `strategy_order == ["delta", "delta-gamma", "no hedge", "no-trade"]` を固定し（`johnhull/scripts/frontier_acceptance.py:645`）、戦略ごとの指標を配列から再計算する（:655-668）。戦略やモデルの次元を足すと検査の変更になる。
  - portal 図（`johnhull/report/report_builder/frontier_figures.py:55-75`）と vol 20 ノート（`johnhull/scripts/build_frontier_notebooks.py:513`）が `e2e_hedge_pnl` と `strategy_order` を読む。
  - 設計上の論点（未決）：真のボラを何にするか（合成の実現分散か、シナリオの真値か）、ヘッジ期間とホライズン（1/5/21 日）の対応、プレミアムを何のボラで取るか（公正価格か予測か）。
  - Phase-1 の深層ポリシー（BA-01）は同じ `e2e_*` の枠に入るので、同時に決めるのがよい。
- 更新が要るもの（出力を変える場合）：`johnhull/volumes/20_surface_dynamics/reference/forecast_paths.npz`（`e2e_*`）、`metrics.json`（`end_to_end`）、改竄テストの vol 20 の `e2e_hedge_pnl`・`e2e_hedge_turnover` ケース（新しい配列に合わせる）、portal 図、ノート、`VALIDATION.md`。
- **判断が要る（監査 §3 の「`strategy_order` 固定」、§7「vol 20 / 21 の評価設計」）。** R2 と同じ vol 20 の再生成なので、R2 → R3 の順にまとめて行うのが自然（R3 の経済指標は、補正後の予測を使うべきなので R2 が先）。

## 5. R4：Poisson生成と共通乱数のずれ

`zero_dte.py:386–394` は1本のRNGで正規・Poisson等を生成する。
同じseedでもPoisson強度が変わると内部の消費乱数数が変わり、次の正規標本が一致しない。
`r4_poisson_crn.json` の保存値照合に加え、再開後に `r4b_poisson_crn_seeds.py` を実行した。
元スクリプトの補助コード読み込みには `__file__` 未設定があったため、元を編集せず
`scratch/codex_integration/run_r4b.py` で実行名前空間だけ補った。

**機序の確認：** 強度0.0003と0.03では次の正規乱数が不一致、0.0003と0.0003000001では一致。
強度が違えば常にずれるわけではない。240分のevent行は最初のstep以外で正規列が一致せず、
eventが消える270分以降は一致する（先行JSON）。

40seed×3,000パスのevent効果（価格差）の比較：

| 時刻・方式 | 平均 | seed間SD | 各実行SEの平均 |
|---|---:|---:|---:|
| 0分・現行 | .1078 | .0140 | .0141 |
| 0分・stream分離 | .1111 | .0159 | .0162 |
| 0分・Poisson逆CDFの共通一様乱数 | .1071 | .0139 | .0141 |
| 240分・現行 | .1380 | .0189 | .0200 |
| 240分・stream分離 | .1390 | .0165 | .0163 |
| 240分・逆CDF | .1388 | .0155 | .0159 |

**判断：** CRNの結合が切れることは確認。周辺価格の偏りを示した結果ではない。
stream分離は正規列のずれを防ぐが、Poisson個数どうしの望ましい結合まで保証しない。
逆CDFも全条件で分散を小さくするとはいえない。既定乱数の変更はvol22の教師・bump Greek・図を変えるため、
本調査では実装せず、再生成時に全13時点のpaired SEとseed分布を残す設計とする。

## 6. R6：動的feeとgross LVR

`cpmm_reserves_at_price` はno-fee終点、`loss_versus_rebalancing` は
$L_{gross}=xp+y-2\sqrt{xyp}$、$L_{net}=L_{gross}-fee$。
`frontier_reference.py:1369–1380` の固定fee/動的fee比較は同じ初期在庫・外部価格を使う。
したがってgrossが変わらないのはこの計算の定義から従う。

独立式と関数を照合（`scratch/codex_integration/r6_r11_probe.py`）：
$x=100,y=10,000,p=120$ ではgross=91.0976997934、補償0/10/50に対して
net=91.0976997934/81.0976997934/41.0976997934。差は浮動小数点精度でゼロ。

**判断：** 現行の補償額分解は計算契約どおり。ただし「動的feeはgross LVRを減らせなかった」という
実験上の発見にはできない。取引閾値、裁定帯、feeで変わる在庫経路、順次の再均衡を含むモデルは別物。
それを作るなら参照モデルとAPIの設計を別途承認し、既存の1回の価格ジャンプ教材と区別する。

## 7. R11：ヘッジ成績の資金繰り規約

原典GE p.420（§19.2）はTable19.1の費用で利息・割引を無視すると明記。
p.425–426はTable19.4も同様に費用SD/BSM価格で計る。現行 `hedging.py` は債務にrで利息を付けt=0へ割り引く。
同じGBM経路に対し、独立な損益式「割引payoff−保有株数×割引株価増分の和」は現行APIと最大1.7e-13で一致した。
これと利息・割引なしの式を比較した。

- S=49,K=50,r=.05,σ=.2,μ=.13,T=20/52、BSM=2.4005273233。
- 各格子20万パス、seed=20260927+step数、1万パス×20batch。学習なし。
- スクリプト・JSON：`scratch/codex_integration/r6_r11_probe.py` と同名JSON。

| 間隔（週） | delta現行 | delta利息なし | 印刷 | stop現行 | stop利息なし | 印刷 |
|---|---:|---:|---:|---:|---:|---:|
| 5 | .41578 | .42034 | .42 | 1.02874 | .98008 | .98 |
| 4 | .37390 | .37979 | .38 | .97253 | .92662 | .93 |
| 2 | .26850 | .27994 | .28 | .86905 | .83348 | .83 |
| 1 | .19272 | .21125 | .21 | .82050 | .79356 | .79 |
| .5 | .13770 | .16452 | .16 | .79438 | .77150 | .77 |
| .25 | .09763 | .13419 | .13 | .78439 | .76392 | .76 |

全12値で小数2桁の印刷丸めと一致。batch間から見積もった指標のSEはdelta .00021–.00075、stop .00116–.00176。
**根因は規約差であり、現行の資金繰り計算の誤りではない。** 原典値再現用の独立計算と、資金繰り込みで
BSM価格へ収束する教材を併記するのが最小案。Table19.2/19.3の各行では利息を含むので、同章でも表ごとに規約を固定する。
MCの丸め一致は本seedの結果であり、すべてのseedに同じ2桁を強制するテストにはしない。

## 8. 保存値依存の5項目

`frontier_acceptance.py` を読み、参照JSON/NPZをメモリへ読み込んでJSONだけ変える診断を実行した。
`scratch/codex_integration/stored_dependency_probe.py/json`。対象4巻は未変更入力で全チェックPASS。
JSON改変でFAILになることと、原始入力から独立に結果を再現できることは別である。

| 項目 | 今の判定と診断 | 追加する根拠の案 |
|---|---|---|
| vol18 residual_baseline | 保存MAE .000611729 < .012620527。JSONを0<1に変えてもPASS | 同一test ID、教師、raw/residual予測、正規化単位。配列から両MAEを再計算 |
| vol18 hard_violation_rate | 保存率0と `violations_constrained` の和0を要求。率を1にするとFAIL | 各hard checkの入力・予測・mask・閾値・分母。違反件数配列自体も検査対象 |
| vol19 multi_start_calibration | `all_starts_successful` の真偽を直接使用。falseにするとFAIL | 各startの終了status、最適性、予算、残差。既存の初期値/最終値/RMSEだけでは終了理由を復元できない |
| vol21 timingフラグ | 正の時間配列と `timing_nondeterministic=True`。falseにするとFAIL | 生の繰返し計測、warmup、時計、threads、環境と測定時digest。時間比は既に配列から再計算。宣言フラグを数値から証明しようとしない |
| vol22 calendar_violations | 保存0に加え隣接満期のforward varianceを再計算。保存値1でFAIL | 保存calendar判定の対象slice、同一時刻/strike条件、価格・variance配列と閾値。隣接満期チェックだけで全calendar検査と呼ばない |

これらは未修正。vol26の旧3項目は第5便で解決済みなので残件へ戻さない。
修正時には保存JSONのみの改変、根拠配列の改変、整合的な複数値改変を分け、対象チェックのFAILを記録する。
学習・ベンチマーク再実行、全releaseゲート、ブラウザ検査は本調査では実行していない。
