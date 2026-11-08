# 確率の基礎 実装計画

> **For agentic workers:** superpowers:subagent-driven-development を使い、分担実装と独立レビューを行う。

**Goal:** 高校の確率計算から大学基礎の確率変数・期待値・弱大数まで、定義の必要性と条件を説明できる自己完結HTML教材10章を追加する。
**Architecture:** 既存readerへprobability科目を追加。HTML断片、catalog、標準Python生成、独立UMD MathProbability、SVGの実験5個を使用する。
**Tech Stack:** Python標準ライブラリ、native MathML、Vanilla JS/SVG、Node test、既存Playwright/Chromium。
**Spec:** 本文の設計は以下。ユーザーの「今までと同じように実装・Opusレビュー・統合と試読まで」の依頼に基づく。既存31章とURLを維持し、公開・依存追加・commitはしない。

## 設計と章構成

確率は整合的なモデルの規則、頻度との関係は独立同分布等を仮定した定理とする。既存統計教材は応用先としてリンクし、その「長期頻度で定義」の表現を新冊の定義に流用しない。一般測度論、強大数・CLTの証明、推定・検定は対象外。CLTは式を出さず次教材への橋に留める。
各章: 動機、必要な定義、短い証明、条件と反例、任意コラム1、演習3(各ヒント2+完全解答)、振り返り3。問題は本文の道具で解けるもの。コラムの実例は一次資料を確認し、仮想数値を実測値と混同しない。

| # | slug | 内容・証明の核 | 実験 |
|---|---|---|---|
| 1 | probability-models | 標本空間/事象、有限の公理、補集合・加法・union bound、可算加法への橋。等確率は追加仮定 | — |
| 2 | counting-probability | 積の法則、順列/組合せ、二項係数と数え上げによる二項定理の証明、復元/非復元、二個の骰子。場合の数は重みを決めない | — |
| 3 | conditional-probability | P(B)>0、条件付け、乗法、全確率、Bayes、工場検査の基準率 | probability-bayes |
| 4 | independence | 積による定義、排反との違い、補集合、対独立≠相互独立、条件付けで壊れる独立 | probability-independence |
| 5 | random-variables | 写像と分布/PMF/CDF、Bernoulli/二項/幾何、正規化・パラメータ条件 | probability-binomial |
| 6 | probability-density | 密度・積分・CDF、一様/指数、点の確率0≠不可能、密度の値>1も可 | probability-density |
| 7 | expectation | 重み付き平均、g(X)、有限線形性(独立不要)、指示変数、絶対収束/絶対可積分、連続の平均 | — |
| 8 | variance | 二乗偏差、二乗平均−平均二乗、尺度変換、Markov/Chebyshevの証明 | — |
| 9 | joint-distributions | 同時表・周辺・条件付分布、変数の独立、共分散・和の分散(n変数、対ごとの無相関で十分)、無相関≠独立、有限の反復期待値 | — |
|10 | law-of-large-numbers | iid・有限分散の弱大数をChebyshevから証明、確率収束と各経路の違い、依存の反例 | probability-lln |

第1〜5章は微分・積分不要。ただし第1章の可算加法、第5章の幾何分布は極限・幾何級数を使い、既存章へリンクする。第6章と連続の期待値で既存積分章へ戻る。一般実数確率モデルの可測性/測度構成、絶対収束級数の一般の並べ替え、E[g(X)]の一般積分公式、一般可積分な変数の線形性・単調性、独立な積の期待値分解は未証明の借用を明示する。有限離散の主要性質は証明し、弱大数の自足証明は有限値iid、一般有限分散の形は借用の上の拡張と区別する。連続は本文で扱う非負区分連続の密度と通常/広義積分に限定。混合分布の全分類は扱わない。

## ファイルと担当

- root: catalog.json、build.py、template.html、tests/test_build.py、README類、STATUS、計画・review対応、browser QA統合。
- 担当A: chapters/probability-models.html、counting-probability.html、conditional-probability.html、independence.html。
- 担当B: chapters/random-variables.html、probability-density.html、expectation.html、variance.html、joint-distributions.html、law-of-large-numbers.html。
- 担当C: assets/probability.js、assets/probability-experiments.js、tests/probability.test.cjs。既存純粋関数APIに触れない。
- lab本文は <div class="lab" data-lab="..."></div> と外側noscript説明。数学はMathML。全色既存var token、--paperは存在しないので使用しない。
- 微積分Ⅱの末尾→確率第1章、確率第10章末尾→index.html#learning-map。出力41章+入口=42ページ、実験19、コラム41、演習123/ヒント246/解答123/振り返り123。

## 実験の契約

MathProbabilityはCommonJS/browser両対応、公開関数をObject.freeze。入力は有限数で域外をRangeError(Type違いTypeError)、既存数学namespaceは変更しない。
1. bayesState({prior,sensitivity,falsePositive}) : 各0..1。truePositive=prior*sensitivity、falsePositiveMass=(1-prior)*falsePositive、positive=和、posterior=前者/positive (positive=0はnull)。4セルの確率は非負・和1。UIはprior .01.. .99、sensitivity/falsePositive 0..1、初期 .01,.9,.05。未知の陽性なら「条件付け不可」と明示。
2. independenceState({a,b,joint}) : a,b∈[0,1]、joint∈[max(0,a+b-1),min(a,b)]。cells=[joint,a-joint,b-joint,1-a-b+joint]、product=a*b、difference=joint-product、conditional=joint/b (b=0はnull)。UIはa,b .1.. .9、jointは実現可能域を毎回更新、初期 .5,.5,.25。差の丸め表示と厳密独立の区別を注記。
3. binomialState({n,p}) : n整数1..200,p∈[0,1]、pmf長n+1、cdf、mean=n*p,variance=n*p*(1-p)。正規化は公式の二項分布、浮動小数差は許容。UI n1..40,p0..1、初期10,.5。第一図PMF、第二図は右連続CDFの水平段と塗点/白抜点。n>20は点を間引き半径5で狭幅の判読性を保つ。本文と成功数の記号Sを統一。p=0/1を分岐、端点でNaNを出さない。
4. densityState(b) : b∈[0,1]、density=2*b、probability=b*b (f=2x,0≤x≤1) 。UI b0..1 step.01 初期.5。2つの図(密度とCDF)、塗り面積と一点確率を区別。
5. llnState({n,p,epsilon,seed}) : n整数1..200,p∈[0,1],epsilon∈(0,1],seed整数0..4294967295。32bit LCG固定生成(1664525*s+1013904223 mod2^32), 状態を先に更新してからu=s/2^32、u<pを成功、prefixでtrajectory。返値mean,trajectory (n個),bound=min(1,p*(1-p)/(n*epsilon^2)), exactTail=binomialから|k/n-p|≥epsilonの和。理論境界の判定は整数/浮動小数誤差を考慮。UI n10..200 step10,p .1.. .9,epsilon .05.. .5 step.05、seed42固定、初期100,.5,.1。主図はn=1..200でのexactTailとboundの比較、選択nに点を置く。副図は固定seed42の一本の経路。有限疑似乱数の図は証明でない、境界は経路の帯保証ではないと明示。exactTailは格子の閾値の影響でnについて単調でない。≥は入力の最短十進表現を整数比として比較し、n100,p.5,epsilon.1のk40/60を含める。

各lab SVG viewBox幅480程度、文字26px以上を目安、title/desc/aria-labelledby、色+線種+文字で識別、ラベル付操作、reset、data-lab-initialized、.lab-readout、noscript。図と数値を再現可能にする。

## Review Focus

- prior=0/1や陽性確率0: 無定義を0と表示しない (数値test+UI操作)。
- joint実現可能域: 負のセルを描かない (上下端、a/b変更、reset)。
- 離散PMF p=0/1、n最大: 正規化・非負・既知値/整数端点 (Node)。
- 密度の高さと面積、一点と空集合: 本文/図/解答の整合 (試読+UI b0/1)。
- LLNの≥閾値と理論/実験: 独立の有限列挙と照合、seed prefix、p0/1、実ブラウザ。LLNを各経路の単調収束と誤読させない。

## 作業と検証の順序

- [x] 設計の独立事前チェックと契約確定 (独立scope check + Opus設計レビューを反映)
- [x] Python生成物の新科目・全章/実験・前後移動の期待を追加しREDを確認
- [x] A/B/Cを分担し純粋関数は意味あるテストを先に実行
- [x] 最初4章をOpus/max「win math」へ依頼、残りの実装/数値検算は並行
- [x] 全10章と5実験を統合、Python+Node+syntax+lint確認
- [x] Opus全冊レビュー、別担当による全問の独立再計算/通読、指摘対応・再確認
- [x] browser_qa.cjsを42ページ252状態/19実験へ拡張、実験の境界・reset・keyboard、全章NoJS/目次を実操作
- [x] Linuxの実スクリーンショットをrootが目視、Opusもブラウザで独立に代表画面を確認
- [x] 最終入力hashと検証対象を一致、STATUS/README/review対応の証拠と全体進捗表を更新

QA: python3 -m unittest discover -s analytics/math_foundations/tests -p 'test_*.py'; node --test analytics/math_foundations/tests/*.test.cjs; python3 analytics/math_foundations/build.py。変更Pythonをruff、全JS node --check。既存導入済みPlaywrightを指定してLinux Chromium。Windows/file:実機や人間の学習効果とは区別。

出力予算: 生成HTML42×約170KiB≒7MiB、QA JSON+代表PNG<15MiB、peak memoryブラウザ<1GiBを目安。QAは _data/math-foundations/probability-2026-11-07/ の1root、測定を記録。新規依存/大量シミュレーションなし。

## 完了時の確認

全10章・5実験を統合、Python20/20 (教材6/閲覧14)、Node65/65。最終browser QA6451 checks/失敗0、252状態/19実験/NoJS42ページ。Opus重要2点と任意4点を対応後に再確認し、重要なし・退行なし。新しいローカル閲覧helperと14テストも独立レビュー済み。詳細は reviews/2026-11-07-probability-completion-response.md。
