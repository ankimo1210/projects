"""Builder for notebook 00: B1 orientation and diagnostic."""

from nbkit import code, md

cells = [
    md(r"""
# 00. B1の地図 — 行列計算を「信頼できる研究道具」にする

> この4週間の目標は公式を増やすことではない。問題の構造に合う分解を選び、計算結果を疑う根拠を持つことである。

## 学習目標

- Week 1–4の依存関係と、各週の成果物を説明できる
- 統計的な当てはまりと数値的な信頼性を区別できる
- B1プロジェクトを再現可能な小さな研究として設計できる
- 事前診断で、復習すべき項目を自分で特定できる

## 前提知識

- Python、NumPy、配列の基本操作
- ベクトルと行列の積、微分の初歩
- 平均、分散、回帰を見たことがあること

証明経験や債券実務の知識は前提にしない。JGBに似せた合成データだけを使うため、外部データや認証情報も不要である。
"""),
    code("""
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260809
"""),
    md(r"""
## 1. 4週間の学習ループ

各週は「直感 → 導出 → 自作または薄い実装 → 破壊実験 → 金融応用 → 説明」の順で進む。

| 週 | 問い | 必須成果物 |
|---|---|---|
| Week 1 | 最小二乗は何を射影しているか | 残差直交性とrank欠損の診断 |
| Week 2 | 小さい残差なら答えは正しいか | solver比較と摂動実験 |
| Week 3 | 金利カーブの共通変動をどう圧縮するか | SVDによるPCAとrolling安定性 |
| Week 4 | 当てはまりと滑らかさをどう両立するか | 固定decayのNelson–Siegel fit |
| Project | どの曲線を採用すべきか | JGB-like価格とyieldを分けた評価レポート |

標準時間は週7–8時間である。図の「発展」は学習時間の上限ではなく、先へ進むための切り分けを表す。
"""),
    code("""
weeks = ["W1", "W2", "W3", "W4", "Project"]
core_hours = np.array([7.0, 7.5, 7.5, 8.0, 6.0])
extension_hours = np.array([2.0, 2.5, 3.0, 3.0, 4.0])

fig = go.Figure()
fig.add_bar(x=weeks, y=core_hours, name="Core")
fig.add_bar(x=weeks, y=extension_hours, name="Extension")
fig.update_layout(
    title="B1 study load by unit",
    xaxis_title="Unit",
    yaxis_title="Estimated hours",
    barmode="stack",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 2. 直感 — 何を「信頼できる」と呼ぶか

観測ベクトルを $y$、設計行列を $X$、係数を $\beta$ とする。最小二乗は

$$
\hat{\beta} \in \mathop{\arg\min}_{\beta}\lVert y-X\beta\rVert_2^2
$$

を解く。しかし、目的関数が小さいだけでは十分でない。少なくとも次の3軸を分けて記録する。

1. **近似誤差:** $\lVert y-X\hat{\beta}\rVert_2$
2. **数値感度:** 入力の小さな変化に対する $\hat{\beta}$ の変化
3. **研究妥当性:** 目的変数、重み、検証方法が問いに合っているか

同じ予測を返す係数が複数あるrank欠損問題では、近似誤差だけを見ても係数の意味は決まらない。逆に、条件数が大きくても予測対象によっては実用上十分な場合がある。診断値は合否判定器ではなく、追加検証を促す信号である。
"""),
    code("""
# Two coefficient vectors can produce the same fitted values.
design = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]])
beta_a = np.array([1.0, 0.0])
beta_b = np.array([-1.0, 1.0])

print("rank:", np.linalg.matrix_rank(design))
print("same fitted values:", np.allclose(design @ beta_a, design @ beta_b))
print("coefficient distance:", np.linalg.norm(beta_a - beta_b))
"""),
    md(r"""
## 3. B1を貫く導出 — 射影と分解

$\hat{y}=X\hat{\beta}$ が $\operatorname{col}(X)$ への直交射影なら、残差 $r=y-\hat{y}$ は列空間のすべての方向と直交する。

$$
X^\top r = 0
$$

任意の候補 $X\beta$ との差を $X(\beta-\hat{\beta})$ と書けば、これは列空間に属する。直交性から

$$
\begin{aligned}
\lVert y-X\beta\rVert_2^2
&=\lVert r+X(\hat{\beta}-\beta)\rVert_2^2\\
&=\lVert r\rVert_2^2+\lVert X(\hat{\beta}-\beta)\rVert_2^2
\end{aligned}
$$

となる。したがって $\hat{\beta}$ は残差平方和を最小にする。この幾何がWeek 1の土台であり、QRは直交基底、SVDは作用する方向と強さ、ridgeは不安定な方向への罰則として同じ絵に戻せる。
"""),
    md(r"""
## 4. 事前診断

次の5問を、資料を見ずに各10分で解く。正解数より、説明と数値チェックの両方ができるかを重視する。

1. QRで最小二乗を解く式を書き、明示的逆行列が不要な理由を述べる。
2. $\kappa_2(X^\top X)$ と $\kappa_2(X)$ の関係を説明する。
3. 中心化したデータ行列からSVDでPCAを構成する。
4. 第1主成分の符号が翌windowで反転したとき、それを構造変化と呼べるか答える。
5. rank欠損回帰で係数が一意でなくても、予測が一意になり得る理由を述べる。

目安として、0–2問なら4週を通読、3–4問なら演習中心、5問すべてを導出・実装・診断まで説明できるなら各章のExit Criteriaだけを受ける。
"""),
    code("""
diagnostic_scores = np.arange(6)
recommended_hours = np.array([36, 36, 32, 26, 18, 10])

fig = go.Figure(
    go.Scatter(
        x=diagnostic_scores,
        y=recommended_hours,
        mode="lines+markers",
        hovertemplate="Score=%{x}<br>Suggested core hours=%{y}<extra></extra>",
    )
)
fig.update_layout(
    title="Diagnostic score and suggested route",
    xaxis_title="Questions explained correctly",
    yaxis_title="Suggested core hours",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
## 5. 再現可能性の契約

Notebookの結果は、次を満たして初めて教材の主張として扱う。

- 乱数は `numpy.random.Generator` と固定seedから生成する
- 外部ダウンロードを必須にしない
- 入力の単位を明示する。yieldは小数、価格は額面100あたりを標準とする
- 学習・評価を分離し、LOO値を学習内RMSEと混同しない
- solver名、rank、条件数、残差、係数を一緒に保存する
- Notebookを上から順に再実行できる

合成JGB universeは学習用であり、市場価格、休日、決済、経過利息、入札慣行を完全には再現しない。プロジェクトの結論を実取引へ外挿しない。
"""),
    md(r"""
## 6. 失敗モード — きれいな図が監査を代替する

もっとも危険なのは、滑らかな曲線と小さいRMSEを見て終了することである。

- yieldへfitしたのに「価格誤差が小さい」と書く
- 学習データのRMSEでモデル選択する
- 条件数を表示せず、高次多項式の係数を解釈する
- PCAの符号反転を市場レジーム変化と誤認する
- 合成データで動いた規約をJGB実務の規約と呼ぶ

この教材では、図の下に「何を測ったか」「単位」「fitに使った情報」「未実装の市場慣行」を必ず書く。
"""),
    md(r"""
## 7. 段階別演習

### 基礎

1. 事前診断5問に答え、確信度を0–100で併記せよ。
2. 4週間のうち、自分の弱点に最も直結する破壊実験を1つ選べ。

### 標準

3. 「小さい残差」「小さい係数誤差」「小さい予測誤差」が一致しない例を文章で設計せよ。
4. Projectの評価表に、指標名、単位、学習内／学習外、望ましい方向の4列を作れ。

### 研究

5. JGB実データへ移行するときに必要なpoint-in-time情報と市場慣行を列挙し、合成教材との差分表を作れ。
6. モデル採用前に確認する停止条件を3つ定義せよ。
"""),
    md(r"""
## 8. Exit Criteria

- [ ] 射影、分解、正則化が同じ最小二乗問題をどう見ているか説明できる
- [ ] 当てはまり、数値安定性、研究妥当性の3軸を混同しない
- [ ] 事前診断から自分の学習ルートを決めた
- [ ] 合成JGB教材の限界を、少なくとも3点説明できる

すべて満たしたらWeek 1へ進む。チェックは自己申告で終えず、短い技術メモかコードで根拠を残す。
"""),
    md(r"""
## 9. 出典と次の読書

- [MIT OpenCourseWare 18.335J: Introduction to Numerical Methods](https://ocw.mit.edu/courses/18-335j-introduction-to-numerical-methods-spring-2019/) — conditioning、stability、数値線形代数の講義全体
- [MIT OpenCourseWare 18.065 Lecture 9: Four Ways to Solve Least Squares Problems](https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/resources/lecture-9-four-ways-to-solve-least-squares-problems/) — 最小二乗と分解
- [NumPy Linear Algebra Reference](https://numpy.org/doc/stable/reference/routines.linalg.html) — `lstsq`、QR、SVD、条件数の仕様
- [BIS Papers No. 25: Zero-coupon yield curves](https://www.bis.org/publ/bppdf/bispap25.htm) — 中央銀行によるzero-coupon curve推定の技術資料
- [財務省 Interest Rate Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm) — 公表JGB金利とconstant maturityの定義

次章では、この地図を最小二乗の射影へ具体化する。
"""),
]
