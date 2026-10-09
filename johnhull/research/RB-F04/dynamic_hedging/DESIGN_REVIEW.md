# RB-F04 動的モデル横断ヘッジ：独立設計レビュー

2026-10-09。reviewer: /root/short_runner_review。対象 worktree: /home/kazumasa/worktrees/johnhull-research-roadmap。

## 結論

**残 Critical 0、Important 0。修正後の設計で実装へ進める。** 発見した Important 2 件は、canonical DESIGN.md と実装計画で解消を確認した。旧試作由来の SE、bootstrap サイズ、safe policy の 3 文言 Minor も修正済み。

これは数式・比較条件・実装契約のレビューである。正式 source、pilot の精度達成、主実験、NN の優越、所要時間、phase 受入を認証したものではない。新しい MC、乱数生成、訓練、checkpoint 選択は行っていない。

## 閉じた重要指摘

### 1. CM2 lognormal variance と old-v stock の二次モーメント発散

旧候補の v1=m exp(-w/2+sqrt(w)Zv)、w>0 について、2 回目の stock 更新を条件付き積分すると

$$
E[S_2^2\mid{\cal F}_1]=S_1^2\exp(2(r-q)\delta+\delta v_1).
$$

最初の stock normal を Zv=z に条件付けて積分した密度の対数は、定数を除き

$$
\delta m e^{-w/2+\sqrt w z}
+2\rho\sqrt{v_0\delta}\,z-\tfrac12z^2.
$$

z→∞ で指数項が優越するため E[S2²]=∞。後の月次 spot と無ヘッジ Asian payoff の二次モーメントも発散する。有限期待値を持つ GBM control の加減では、この母分散欠陥を解消できない。この結論は**草案にある組合せへの独立導出**であり、別の joint-stock scheme を持つ CM2 論文全体への主張ではない。

DESIGN §4.1 は旧方式を不採用とし、旧 LN sample SE を CI・必要 N 選定に使わない。有限 sample の witness は補足であり、発散の証明は上の tail 導出である。

代替の drift-implicit sqrt-CIR は、a=.02875、b=1、c=.15、d=1+bδ に対する正の二次方程式根で、負の u に rationalized 同値式を使う。stock の old-v 規約は adapted で、一 step の割引期待値を保存する。式は [Cozma & Reisinger §2, (2.7)–(2.9)](https://arxiv.org/pdf/1601.00919) と照合した。

固定 finite grid の第四モーメント証明も検算した。A=Σδv_i に対して

$$
A\le C_{N,\epsilon}+(1+\epsilon)c^2\delta^2
 \|L\|_F^2\|Z_v\|^2,\qquad
\|L\|_F^2=N(N-1)/2.
$$

exponential martingale と Cauchy–Schwarz により E exp((2p²-p)A)<∞ が十分。p=4、ε=.01 の Gaussian 条件は T1=.6363、T1.25=.99421875<1。C は N に依存するので、uniform dt bound と読み替えない。

さらに独立後退計算で p2/3/4 × T1/1.25 × 192/384/768/1536 per year の **24 rows 全数一致**を確認した。最小分母 1.0008165839716445、保存数値との差の最大値 1.33e-15。ρ を保持した別の Gaussian bound でも p4 の 8 grids 全てを確認した。

論文 §3 Proposition 3.4/§4 (4.3) から導く本パラメータの時間下限は 3.1111 年で 1.25 年を超えるが、step に関する定理は sufficiently-small の存在型である。**具体 grid の認証は独立の固定 grid 証明・24 rows 再計算による。** 価格 bias、Greek のモーメント、精度達成は別 gate である。[一次資料](https://arxiv.org/pdf/1601.00919)

### 2. 不確かな baseline MSE を CI 外の 5% 閾値にした旧判定

baseline squared loss が 1/3 を等確率、NN squared loss がそれぞれ .9/2.9 の例では、真の改善はちょうど 5%、paired d は全 path -.1 で SE0。しかし旧判定は sample baseline<2 の場合に「5%超」を支持する。N8192 の誤支持確率は厳密二項計算で **.4955924034**。3 init IUT と Bonferroni だけでは直らない。

修正後は d=LNN²−LB² と r=LNN²−.95LB² を別の paired score として、その各 CI・数値 envelope を判定に含める。Ud+ud<−.001 かつ Ur+ur<0 を全 3 init で要求する。8 family の α=.05/8 と family 内 3 init × 2 条件の IUT の論理は成立する。family 内の追加 Bonferroni 分割は不要。

ただし 64-path block bootstrap/2000 回の CI は名目・近似水準である。厳密な有限 N coverage、empirical numerical envelope による確率 bias 保証を宣言しない修正を確認した。3 test seeds、3 train init、64-path block を元 path 数の増加と数えない。

## その他の数学・契約チェック

| 対象 | 独立確認・結果 |
|---|---|
| Asian auxiliary control | 残る離散 fixing の GBM geometric log mean/variance は正しい。β1 固定、同じ ZS による CE(model−aux)+known aux mean は指定 discrete scheme に対して不偏。θ/S bump で aux path と known mean の両方を動かす。closed mean と独立 normal quadrature の差 6.88e-15。control に既知期待値が必要な点は [Han & Lai §2](https://mx.nthu.edu.tw/~chhan/gen_AAO_v.kan.final.pdf) と整合する。 |
| 同じ Asian scalar price の微分 | Heston VS=D(f−xfx)/12。local VS=D(f+fz−xfx)/12 で追加 fz が必要。Vell=DSfw/(12ell)。観測後 A,n 固定の片側時点、m0、x≤0、σ0 atom/kink を分離する設計を確認。 |
| market quote IFT | VQ=Vθ/Cθ、VS\|Q=VS\|θ−Vθ CS/Cθ。座標変換で相殺、stock bump は Q 固定で毎回再 fit。独立 Black の recalibration FD は hQ=.9064930365、hS=−.1426401580 と差 <1e-8。負の stock holding は数値失敗ではない。 |
| U1/Σ/band | Heston β=CS+Cvρξ/S、local β=CS。toy の βH=.516/βlocal=.6。local Σ は rank1、null=(-CS,1) の variance0。ridge で第二因子を作らない。band は局所リスク seminorm による規則であり global optimum の主張ではない。 |
| calendar/support | local 時刻を restart0 にしない。倍率固定 forecast、calendar PDE、spot-left/time-midpoint、t0 近傍 sheet、T*=1.25 までの field が必要。旧 T≤1 field・constant proxy は正式 field の精度証拠にしない。 |
| self-financing | 初回購入、前 cash の利息、実 CF 時刻、満期 claim 支払い、stock と未満期 call の売却、終端 fee を各一回計上。独立 cash/gain toy 差 7.11e-15。一般論文の満期 liquidation と数値例の fee0 は区別する。[Deep Hedging §2, (2.1)](https://arxiv.org/html/1802.03042v1) |

## 最終 scope と未実施 gate

canonical DESIGN と実装計画で、主は **月次 12 hedge 固定**、claim は S0 を除く 12 fixings、44 cells/12 fits と確認した。24/48 は selected Greek/band の取引頻度診断であり、異なる売買機会・費用を持つ policy の経済比較である。近接を同じ数値法の error gate にしない修正は妥当。主 NN の再訓練・全 44 cells の追加を暗示しない。

common p0 は、独立実装/reserved seed の Heston direct arithmetic-Asian pilot 65536 IID/1536 steps per year の推定を freeze する。主 MSE/CI はこの p0 と fixed training を条件にした比較で成立する。exact fair price、premium 不確実性を含む無条件のリスク主張とは呼ばない。

残る実装・pilot gate：

- actual local field の finite global variance bound/wing/support と T1.25 extension、t0 closure、各 G の actual Q に対する fit support、Cθ 一意性・比の SE/誤差を検証する。selected Heston-Q 18 states だけで全 G/path の fit を認証しない。
- continuous CF/PDE call と有限 step 市場は厳密な joint martingale simulator ではない。必須 Q/empty-claim/state-bin/call drift、同じ月次12 policy に対する SDE/teacher/grid refinement、独立 price/position oracle を維持する。18 selected の bias indicator を全域証明にしない。
- pilot 未達なら sourcefreeze 前 revision。元 raw failure、unknown、未達 candidate、研究費用を全 roster に残し、finite subset・safe/nearest/zero repair で受入しない。NN が基準を上回ることは研究完成条件ではない。
- N≤65536/highgrid、job≤10億 path-step、NPZ≤256MiB の分割は仕事量・保存上限であり、runtime 保証ではない。300s NN attempt cap と総研究費用を区別する。全 source/pilot/独立 review を主実験前に freeze する。

## 証拠・再実行

独立 script は /tmp のみ。shared .venv の Python、NumPy/SciPy による決定的計算で、両 script exit0/all assertions PASS。

- [数式・反例 probe source](/tmp/rbf04_dynamic_design_probes.py)、[出力](/tmp/rbf04-dynamic-design-probes.json)
- [24 moment 独立再計算 source](/tmp/rbf04_dynamic_moment_recheck.py)、[出力](/tmp/rbf04-dynamic-moment-recheck.json)
- [review input SHA/範囲](/tmp/rbf04-dynamic-design-review.json)。SHA は provenance、金融数値比較は許容誤差。

正式 source/test/Git、主 MC・訓練は変更・実行していない。実装後、正式 pilot/sourcefreeze、全原始保存値・phase の独立受入は別レビューが必要。

### Exact canonical binding

- /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F04/dynamic_hedging/DESIGN.md
  SHA256 provenance: 8fbef30a824aa0b4e4153ad0e559255a6fe77b102d8fde223adb25f6138248ce
- /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md
  SHA256 provenance: cf339d0baa55051cddddabfa7f2351cbb2e826153db288c1bf20507c0aaa7933

Canonical moment JSON and the independently recomputed /tmp input are numerically identical; SHA is used only for provenance.
