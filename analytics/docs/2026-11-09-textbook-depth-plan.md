# 全100章の教科書充実 Implementation Plan
> For agentic workers: superpowers:subagent-driven-developmentを使う。ユーザーは見本と同じ基準・既存と同じ実装/Opus/統合/試読を明示承認済み。Routine decisionに追加承認は不要。

**Goal:** 残る100章を講義・例題・自力演習の深さまで改稿し、全章の独立試読・Opus max・統合検証を完了する。
**Architecture:** 既存HTML断片と章別exerciseCountを使用。執筆を並行準備し原本反映はcatalog順、rootが共有catalog/buildを単独管理。8章以内の固定bundleでレビューし、必要訂正を限定再確認する。
**Tech Stack:** 既存HTML/MathML/SVG、Python build/unittest、Node/Chromium QA。依存追加なし。
**Spec:** 2026-11-09-textbook-depth-spec.md。完成済み固有値章は品質基準。

## Global Constraints
Specの対象/保全/完成基準/レビュー/資源を継承する。現在のcodexブランチと未コミットの先行改稿を保持し、commit/pushしない。生成物は_dataの指定runのみ。UIと数学APIの広範な変更はしない。先行レビューを新稿の承認に流用せず、変わっていないものだけhash一致で継承する。

## Review Focus
- 定義前の記号と、方針を選ぶ理由/計算途中が抜けて初見問題へ使えない章。
- 量化・定義域・境界/反例・借用定理の条件を拡張中に落とすこと。
- 図表の見える根拠がcaptionの結論を支えない、縮尺/単位/手系/サンプルと一般論の混同。
- 新演習が本文再現のみになること、正解だけで方法や意味が分からない解答。
- 章別演習数・NoJS・長い式/表・狭幅/明暗/印刷CSS、前提と次章の接続の破綻。

## Task cycle（batch-01〜13）
Files: 各chapter原本・catalogの当該entry。作者の出力はrun/batch-NN/draft、rootが原本へ反映。
Interfaces: 完成草稿HTML＋metadata（exerciseCount正整数、省略時3/duration/保全/訂正）、独立review、固定bundleのsha、Opus required-open=0、対象QA/生成hash。
- [x] baselineを保存し、先行pilot/100章/共通codeの開始時hashを固定。
- [x] 各chapterの問い/定義/複数例題/比較/自力問題/図表を実装し、自己検算を記録。
- [x] 独立担当が作者意図を読む前に本文を読み、初見変形と数式/条件を照合。
- [x] catalog順に原本と演習数/時間を統合。既存Python23/Node111、変更章の6状態/NoJS/全details/図実画像とinkを確認。
- [ ] 8章以内の固定版をOpus maxへ依頼。レビュー中は次batchを準備。必要修正を限定再確認し、hashを接続。
- [ ] 必要指摘0と各QAの根拠がそろって初めて章を完了。工程表をSTATUSと会話に更新。

## Task final
- [ ] 全100章の完了ledgerと承認hash/生成hashの一致を確認。
- [x] 全102ページ612状態/37実験/全演習、全静的図表の表示、必要なink再検査、前後/横断接続の内部試読を完了。
- [ ] README/STATUS/完了記録、required hookとWindows HTTP、資源実測を照合。未検証を明記。

## 全100章の実行順
詳細な動的状態はSTATUSとrun/progress.jsonへ。以下は対象と順序の固定で、先行pilotは含まない。
| 順 | 内容 | slug | 開始時 |
|---:|---|---|---|
| 1 | 数学的な観察・予想と反例 | observation | 完了 |
| 2 | 命題・量化と必要十分条件 | logic | 完了 |
| 3 | 集合と写像 | sets-maps | 完了 |
| 4 | 直接証明・対偶・背理法 | proofs | 完了 |
| 5 | 数学的帰納法と再帰 | induction | 完了 |
| 6 | 不変量とユークリッドの互除法 | invariants | 完了 |
| 7 | 不等式と誤差評価 | inequalities | 完了 |
| 8 | 数の体系と複素数 | numbers | 完了 |
| 9 | 実数と数列・関数の極限 | limits | 完了 |
| 10 | 連続関数と中間値の定理 | continuity | 完了 |
| 11 | 微分係数・導関数と連鎖律 | derivatives | 完了 |
| 12 | 平均値の定理と関数の増減 | mean-value | 完了 |
| 13 | 一次・二次近似の誤差評価とニュートン法 | approximation | 完了 |
| 14 | リーマン積分と可積分性 | integration | 完了 |
| 15 | 微分積分学の基本定理 | fundamental-theorem | 完了 |
| 16 | 置換積分・部分積分と広義積分 | integration-methods | 完了 |
| 17 | 無限級数と収束 | series | 完了 |
| 18 | テイラーの定理とべき級数 | taylor | 完了 |
| 19 | べき級数と指数・対数・三角関数 | elementary-functions | 完了 |
| 20 | 平面の回転と行列・複素数 | rotation | 完了 |
| 21 | ベクトル空間と線形写像 | vector-spaces | 完了 |
| 22 | 基底・次元と次元定理 | dimension | 完了 |
| 23 | 2次の行列式と面積・可逆性 | determinants | 完了 |
| 24 | 連立一次方程式と行列表現 | linear-systems | 完了 |
| 25 | 基本行操作とガウスの消去法 | linear-elimination | 完了 |
| 26 | 連立一次方程式の一般解と核・像・階数 | linear-kernel-image | 完了 |
| 27 | 基底変換と相似変換 | linear-basis-change | 完了 |
| 28 | 内積・正規直交化とQR分解 | linear-orthogonality | 完了 |
| 29 | 直交射影と最小二乗法 | linear-least-squares | 完了 |
| 31 | 行列の対角化と累乗 | linear-diagonalization | 完了 |
| 32 | 実対称行列の直交対角化と二次形式 | linear-symmetric | 完了 |
| 33 | 特異値分解と低ランク近似 | linear-svd | 完了 |
| 34 | 多変数関数の極限と連続性 | multivariable-limits | 完了 |
| 35 | 偏微分と偏導関数 | partial-derivatives | 完了 |
| 36 | 全微分と連鎖律 | total-derivative | 完了 |
| 37 | 方向微分と勾配 | gradient | 完了 |
| 38 | ヘッセ行列と多変数関数の極値 | hessian-extrema | 完了 |
| 39 | 等式制約とラグランジュの未定乗数法 | lagrange | 完了 |
| 40 | 二重積分と累次積分 | double-integrals | 完了 |
| 41 | 重積分の変数変換とヤコビアン | change-of-variables | 完了 |
| 42 | 標本空間・事象と確率の公理 | probability-models | 完了 |
| 43 | 順列・組合せと確率 | counting-probability | 完了 |
| 44 | 条件付き確率とベイズの定理 | conditional-probability | 完了 |
| 45 | 事象の独立と相互独立 | independence | 完了 |
| 46 | 離散確率変数と確率分布 | random-variables | 完了 |
| 47 | 連続確率変数と確率密度関数 | probability-density | 完了 |
| 48 | 期待値とその線形性 | expectation | 完了 |
| 49 | 分散・標準偏差と確率不等式 | variance | 完了 |
| 50 | 同時分布・条件付き分布と共分散 | joint-distributions | 完了 |
| 51 | 確率収束と弱大数の法則 | law-of-large-numbers | 完了 |
| 52 | 二項関係・同値関係と同値類 | discrete-relations | 完了 |
| 53 | 半順序とハッセ図 | discrete-orders | 完了 |
| 54 | 全単射・二重計数と鳩ノ巣原理 | discrete-counting | 完了 |
| 55 | 包除原理 | inclusion-exclusion | 完了 |
| 56 | 整数の合同と剰余計算 | modular-arithmetic | 完了 |
| 57 | 漸化式と動的計画法 | recurrence-relations | 完了 |
| 58 | グラフ・次数と連結性 | discrete-graphs | 完了 |
| 59 | 木・全域木と幅優先探索 | discrete-trees | 完了 |
| 60 | 最短路とダイクストラ法 | shortest-paths | 完了 |
| 61 | グラフの彩色と二部グラフ | graph-coloring | 完了 |
| 62 | 複素平面と複素関数 | complex-plane | 完了 |
| 63 | 複素微分と正則関数 | complex-differentiation | 完了 |
| 64 | 複素指数関数と対数の分枝 | complex-logarithm | 完了 |
| 65 | 複素線積分と原始関数 | complex-contours | 完了 |
| 66 | コーシーの積分定理 | cauchy-theorem | 完了 |
| 67 | コーシーの積分公式 | cauchy-formula | 完了 |
| 68 | 正則関数のテイラー展開 | complex-taylor | 完了 |
| 69 | ローラン展開と孤立特異点 | laurent-singularities | 完了 |
| 70 | 留数と留数定理 | complex-residues | 完了 |
| 71 | 留数定理の実積分への応用 | complex-real-integrals | 完了 |
| 72 | ベクトル場と三次元のベクトル演算 | vector-fields | 完了 |
| 73 | 曲線のパラメータ表示と弧長 | vector-curves | 完了 |
| 74 | ベクトル場の線積分 | vector-line-integrals | 完了 |
| 75 | ポテンシャルと経路独立性 | vector-potentials | 完了 |
| 76 | グリーンの定理 | vector-green | 完了 |
| 77 | ベクトル場の発散と回転 | vector-div-curl | 完了 |
| 78 | 曲面のパラメータ表示と面積 | vector-surfaces | 完了 |
| 79 | 面積分と流束 | vector-flux | 完了 |
| 80 | 三重積分とガウスの発散定理 | vector-gauss | 完了 |
| 81 | ストークスの定理 | vector-stokes | 完了 |
| 82 | 数値誤差と浮動小数点数 | numerical-errors | 完了 |
| 83 | 条件数と前進誤差・後退誤差 | numerical-conditioning | 完了 |
| 84 | 二分法と誤差保証 | numerical-bisection | 完了 |
| 85 | 非線形方程式のニュートン法 | numerical-newton | 完了 |
| 86 | 連立一次方程式の消去法と残差 | numerical-linear-systems | 完了 |
| 87 | 多項式補間と補間誤差 | numerical-interpolation | 完了 |
| 88 | 数値微分と丸め誤差 | numerical-differentiation | 完了 |
| 89 | 数値積分と誤差評価 | numerical-quadrature | 完了 |
| 90 | オイラー法の収束性と安定性 | numerical-ode | 完了 |
| 91 | 残差・刻み比較・独立検算による検証 | numerical-reliability | 完了 |
| 92 | 最適化問題と最適解の存在 | optimization-problems | 完了 |
| 93 | 凸集合と凸関数 | optimization-convexity | 完了 |
| 94 | 制約なし最適化の必要条件と十分条件 | optimization-optimality | 完了 |
| 95 | 勾配法と下降補題 | optimization-gradient | 完了 |
| 96 | 最適化のニュートン法と直線探索 | optimization-newton | 完了 |
| 97 | 変数の尺度変換と前処理 | optimization-scaling | 完了 |
| 98 | 凸集合への射影と射影勾配法 | optimization-projections | 完了 |
| 99 | 等式制約付き最適化とラグランジュ関数 | optimization-lagrange | 完了 |
| 100 | 不等式制約とKKT条件 | optimization-kkt | 完了 |
| 101 | ラグランジュ双対性と最適値の評価 | optimization-duality | 完了 |

## 実装時の調整
演習込みの時間へ改めるため、共通buildの表示ラベルを「読む時間の目安」から「学習時間の目安」へ一語句変更する。catalogの時間表記は「90–140分」の形式を保ち、章内で演習込みと説明する。数学API・CSS・reader等の変更は不要。

## 現在の進捗
全100章の改稿・独立数学/試読・Opus max承認・統合・最終表示検証を完了。全102ページ612状態・37実験・NoJS全997演習/解答、Windows HTTP、全図画素検査、科目横断試読と同版のSHA照合が通過した。[完了記録](reviews/2026-11-09-textbook-depth-completion-response.md)とSTATUSを参照。完成後の追加依頼で、先行改訂・見本を含む本教材一式をGit公開対象とした。
