# §26.15 M7a レビュー（2026-09-19）

状態は **gaps_found**。独立参照と BSK01–BSK06 を固定した段階で、公開 API、
本文の拡充、共有図、Book/portal の実画面確認は M7b に残る。
原典は Hull 11e Global Edition §26.15、印刷・PDF pp.628–629 を照合した。
この節に印刷された数値例はない。以下の市場はすべて synthetic である。

## 原典と現状

p.628 の rainbow は複数リスク資産への依存を指し、CBOT 債券先物の受渡選択権はその例である。
p.629 は European basket、相関 GBM の MC、厳密な最初の二モーメントを
対数正規分布に合わせる Black 近似を述べる。
既存 vol10 §4.5 はこの概説と式の再掲に留まり、重み・単位・給付の明示、
独立価格との比較、誤差と図が不足していた。

## 要求契約

| ID | 満たすべき契約 | M7a の根拠／M7b の残作業 |
|---|---|---|
| BSK01 | 欧州型 call/put の給付、basket/rainbow の違い、単位を説明する | 本レビューで定義。本文・給付図・両画面は未了 |
| BSK02 | 相関 GBM の厳密 M1/M2 と Black へのモーメント整合を分ける | 直接二重和と一資産解析アンカーを固定。公開 API・本文は未了 |
| BSK03 | 近似を独立条件付き積分・MC と比較し、標準誤差を示す | 72 価格を保存、54 確率的アンカー行で MC を検証。比較図は未了 |
| BSK04 | 相関が二次モーメント・価格へ及ぼす効果を、他条件固定で示す | baseline / negative-correlation / high-correlation の 18 行。共有図は未了 |
| BSK05 | 許容入力・除外領域・近似誤差・統計的に未確定な符号を明示する | 誤差、価格 floor、4SE 規則を保存。API 拒否契約・教材は未了 |
| BSK06 | 六小節・四共有図を Book/portal 両面に配置し実画面で確認する | M7b に残る。M7a は受入ではない |

給付は $B_T=\sum_i w_i S_i(T)$ に対する $(B_T-K)^+$ / $(K-B_T)^+$。
価格・行使価格・basket は共通通貨、$M_2$ は通貨の二乗、$w_i$ は非負の無次元保有量。
重みの和を 1 に制約しない。少なくとも一つの重みは正。期間は年、金利・配当利回りは
連続複利年率、ボラティリティは年率。一定パラメータのリスク中立相関 GBM を仮定する。

$F_i=w_iS_i\exp((r-q_i)T)$ と置くと
$M_1=\sum_iF_i$、
$M_2=\sum_{i,j}F_iF_j\exp(\rho_{ij}\sigma_i\sigma_jT)$ は厳密。
Black に入れる総分散 $\log(M_2/M_1^2)$ と価格は、一般の basket では近似である。
parity は $C-P=e^{-rT}(M_1-K)$。一資産および等ボラ・完全正相関の比例資産は厳密アンカーになる。

## 独立実装と再現

[scripts/build_basket_reference.py](../scripts/build_basket_reference.py) は hullkit の価格コードを import しない。
`moments_direct(...)` は直接二重和、
`conditional_two_asset(...)` は第 1 資産の Gaussian に条件付け第 2 資産を解析積分して
一重求積し、価格と QUADPACK 誤差推定値を返す。
$|\rho|=1$ は明示的に拒否し別の解析アンカーで検証する。
積分範囲は $\pm(12+\max(\sigma_1\sqrt T,|\rho\sigma_2\sqrt T|))$。
QUADPACK の値はこの有限区間内の誤差推定で、全誤差の保証ではない。
区間外は給付 $\le B_T+K$ と指数傾斜 Gaussian の tail を用い、別途上界を保存する。

`simulate(..., strikes=..., paths=..., seed=...)` は固有値分解で PSD 相関を扱い、
1 市場につき独立 pilot 20,000、評価 1,000,000 標本、chunk 50,000 を使用する。
pilot だけで一次モーメント control の係数を推定し、本計算は固定係数で不偏推定と
IID 標準誤差を計算する。put は同じ経路と対応する control から求め、
価格差は解析 parity、残差分散は call と等しい。
SE は評価標本の標準偏差を $\sqrt N$ で割る。時系列離散化誤差はない。

非退化二資産 6 市場 × 3 行使価格 × call/put = 36 行、
三資産 2 市場 × 同条件 = 12 行、解析アンカー 4 市場 × 同条件 = 24 行、計 72 行。
$K\in\{80,100,120\}$。二資産では相関 -0.65/0.35/0.9、短期 0.1 年、
長期 3 年・ボラ 65%、負金利 -1.5% を含む。
三資産は分散型と高ボラ・負金利型。解析アンカーは一資産、完全正相関、
完全負相関で一つだけ非零保有、全ボラ 0 の deterministic basket。

```sh
OPENBLAS_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python johnhull/scripts/build_basket_reference.py
OPENBLAS_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python johnhull/scripts/build_basket_reference.py --check
```

日時を含めず、同じ Python/NumPy/SciPy・BLAS 条件で JSON を byte 単位で再現した。
[prices.json](validation/section-26-15/prices.json) に市場入力・厳密モーメント・独立近似・
条件付き価格・MC/SE・seed・参照法・誤差・符号判定を保存し、
[numerical-check.json](validation/section-26-15/numerical-check.json) に集計と source/artifact hash を保存する。
数値記録の PASS は参照検証に限り、節の状態は gaps_found のままである。

## 実測値と限界

- MC と解析／条件付き参照の最大乖離は **2.404841 SE**（54 確率的アンカー行、4SE 閾値以内）。
- 最大 MC SE は **0.02088760** 通貨、4SE は **0.08355041** 通貨。
- 条件付き求積の最大誤差推定は **2.99e-10**、区間外の上界は **3.99e-31 未満** 通貨。
- 72 行全体で近似の最大絶対誤差は **6.41739463** 通貨。
- 参照価格 **0.5 以上の 63 行**では相対誤差が **−1.9361% ～ +66.8378%**。
  0.5 未満の 9 行の相対誤差は null とし、集計から除く。
- 参照が MC の場合は $|\text{近似}-\text{MC}|>4SE$ のみ符号を確定。
  条件付き参照は求積推定＋tail と 1e-10 floor の大きい方を用いる。
  解析参照も 1e-10 floor を使う。全 72 行中 26 行は符号未確定（厳密アンカーを含む）。

これは選んだ市場の経験的誤差で、全域の保証ではない。
高ボラ・長期・負相関では三次以上の分布形状が効き、最初の二モーメントの一致だけでは
高精度価格を保証できない。MC 参照は標本誤差を持つ。
非負 weights、正の spot/strike/expiry、非負 vol、有限かつ整合する配列、
対称・単位対角・PSD 相関が公開 API の領域である。
short basket、現金配当、時間変動パラメータ、リバランス、満期 0、
浮動小数点の全域安定性は今回の対象外。参照スクリプトは保存した有効市場用で、
公開 API の入力拒否実装を代替しない。

## 検証

TDD で moments の未実装 failure → 1 pass、conditional 未実装 3 failures → 4 passes、
MC 未実装 4 failures → 8 passes、生成と保存値テストの RED → 最終 11 passes。
独立解析 fixture は cash40 + ATM lognormal60、$r=q=0,\sigma=.2,T=1$ の
$C=P=60(2\Phi(.1)-1)=4.77934047324348$。
ruff、full-size byte 再生成、通常 ledger 検査は PASS。
追加の `--check-artifacts` は既存 M6b の生成済み Book/portal ファイルがこの新規 worktree に
存在しないため未達（M7 の参照ファイルにエラーなし）。これらの生成・統合検証は M7b に残る。
API・図・ブラウザーはこの段階では検証していない。
