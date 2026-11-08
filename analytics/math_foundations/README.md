# 数学の見方

高校数学を一度学んだ読者が、「なぜその定義や定理が必要なのか」を再発見するためのHTML教科書。入門8章・微積分Ⅰ11章・線形代数への橋4章・線形代数10章・微分積分Ⅱ8章・確率の基礎10章・離散数学10章・複素解析入門10章・ベクトル解析10章・数値解析10章・最適化10章（計101章）の学習経路を用意しています。

| 科目 | 章数 | 主な内容 |
|---|---|---|
| 数学の言葉と証明 | 8 | 観察・論理・集合と写像・証明法・帰納法・不変量・不等式・数の拡張 |
| 微分積分Ⅰ | 11 | 極限から微分・積分・基本定理・級数・Taylor・初等関数まで |
| 線形代数への橋 | 4 | 回転・ベクトル空間の公理・次元・2次の行列式 |
| 線形代数 | 10 | 連立一次方程式・消去法・核/像・基底変換・直交化・最小二乗・固有値・対角化・二次形式・SVD |
| 微分積分Ⅱ | 8 | 多変数の極限・全微分・勾配・Hessianと極値・Lagrange法・二重積分・変数変換 |
| 確率の基礎 | 10 | 確率モデル・数え上げ・条件付き確率・独立・分布・密度・期待値・分散・同時分布・弱大数 |
| 離散数学 | 10 | 同値関係・順序・数え上げ・包除・合同・漸化式・グラフ・木・最短路・彩色 |
| 複素解析入門 | 10 | 複素微分・対数の分枝・経路積分・Cauchy・Taylor/Laurent・留数・実積分 |
| ベクトル解析 | 10 | 場・線積分・ポテンシャル・Green・div/curl・面積分・Gauss・Stokes |
| 数値解析 | 10 | 誤差・条件数・二分法・Newton・消去・補間・数値微分/積分・Euler・検算 |
| 最適化 | 10 | 問題と存在・凸性・最適性・勾配法・Newton・尺度・射影・Lagrange・KKT・双対性 |

操作できる実験は37個です。数・回転、微積分、多変数、確率、離散数学、複素解析に加え、ベクトル解析の仕事・傾斜面の流束・Stokesの面変更、数値解析の二分法/Newton・数値微分の丸め・Eulerの安定性、最適化の勾配反復・円板/箱への射影・KKTと双対gap、線形代数の解の分類・最小二乗・対称行列の固有方向を操作して確かめられます。

全101章に、定義や定理の近くで読める静的な概念図・比較表を置いています。静的203SVG・81表と実験の主要55SVG、計339対象について、読者が何を比較して何を発見できるかを全科目で個別に見直しました。正式な数学内容を101章・731節の主題とし、有用な動機表現だけを7章の副題へ整理しました。Opus承認、全102ページの統合検証と内部試読は [開発状況](../docs/STATUS.md) に記録しています。集合・写像、距離の違い、谷/山/峠、定理の条件、確率の重み、複素平面の変換・分枝・輪郭の向きを図表でもたどれます。

各章に問い、必要な定義、短い証明、仮定と反例、任意のコラム、演習・段階ヒント・解答を収めます。PythonやJupyterを読者の前提にせず、JavaScriptを無効にしても本文・静的図表・演習・解答は読めます。図の操作にはJavaScriptが必要です。

## 開く

リポジトリルートからWSL内で実行します。追加パッケージのインストールは不要です。

```bash
python3 analytics/math_foundations/build.py
```

生成された [site/index.html](site/index.html) をブラウザで開きます。CSS・JSは各ページに埋め込まれ、数式はブラウザ標準のMathMLで表示します。ネットワーク、サーバ、外部フォント、数式描画サービスは不要です。現在のChrome・Edge・FirefoxなどMathMLに対応するブラウザを使用してください。

102ページを同じフォルダに置けば、本文・図・演習は持ち運べます。既存教材へ進むリンクは、リポジトリ内のビルド済みHTMLを参照します。未ビルドの教材は入口に「準備中」と表示し、リンクは付けません。既存教材が未ビルドの場合は、リポジトリルートの `make books` で生成してください（既存教材の依存環境が必要です）。生成後にこの教科書も再生成するとリンクが有効になります。

狭い画面では「章を選ぶ」と「この章の目次」を開き、章や定義の節へ移動できます。長い数式は数式の枠内、横に長い表は表の枠内を左右にスクロールして読めます。表はキーボードでも操作できます。

## 原本と生成物

| 場所 | 役割 |
|---|---|
| `chapters/*.html` | 本文の原本。ノートブックのコードや実行結果を含めない |
| `catalog.json` | 科目・章・並び順の原本。入口と目次を同期 |
| `assets/math.js`、`assets/calculus.js`、`assets/linear.js`、`assets/multivariable.js`、`assets/multivariable-middle.js`、`assets/multivariable-integration.js`、`assets/probability.js`、`assets/discrete.js`、`assets/complex.js`、`assets/vector.js`、`assets/numerical.js`、`assets/optimization.js`、`assets/linear-core.js` | 図で使う数学の純粋関数。Nodeとブラウザで共用 |
| `assets/experiments.js`、`assets/calculus-experiments.js`、`assets/linear-experiments.js`、`assets/multivariable-experiments.js`、`assets/multivariable-middle-experiments.js`、`assets/multivariable-integration-experiments.js`、`assets/probability-experiments.js`、`assets/discrete-experiments.js`、`assets/complex-experiments.js`、`assets/vector-experiments.js`、`assets/numerical-experiments.js`、`assets/optimization-experiments.js`、`assets/linear-core-experiments.js` | 各章のスライダー・SVG・数値表示 |
| `assets/reader.js` | 表示テーマと、画面幅に応じた目次の開閉 |
| `tools/serve.py` | WSL共有パスで開けないときのローカル閲覧。入口から既存教材へ進むリンクも保つ |
| `tools/browser_qa.cjs` | 現行102ページ版の実ブラウザ表示・操作・JavaScript無効時の任意QA |
| `tools/figure_ink_qa.cjs` | 文字と線を別に描画して図中の重なり候補を検出。画像で裁定し、意図しない交差を防ぐ |
| `assets/style.css`、`template.html` | 共通の読み物レイアウトとナビゲーション |
| `build.py` | 共通カラートークンを含めた102ページの生成 |
| `site/` | 再生成可能な出力。Git管理しない |

本文の原本はHTML断片です。 数式中の比較記号 `<` も `&lt;` と書きます。ASCII英字が続くとHTMLタグとして解釈され、本文や解答が欠けるためです。現在の実験はブラウザ内で完結するため、配布ノートブックはまだありません。ノートブックは、今後Pythonによる発展実験が必要になった章で任意の付録として追加します。

## 図表を追加するとき

新しい節でも、定義域、量の比較、幾何、条件の違いを図や表で示せないか検討します。 立体図では投影の手系を確認し、Stokes実験では画面のy軸反転を含む行列式で境界矢印の回転方向を検査します。法線と座標軸のラベルも離して描きます。図は本文の近くへ置き、有限の例や模式図を一般の証明と混同しない説明を添えます。

既存の concept-figure / concept-grid / concept-table を使用し、SVGに固有のtitle・desc・ARIA参照、図表にcaptionを付けます。文字は基本22px以上、色は共通token、比較の縮尺差は明記します。長い式や説明は図外へ置き、320px・明暗・JavaScript無効でも読めることを実画面で確認します。 矢尻を付ける矢印はそれぞれ別のpathにし、複数のMをまとめて最後の矢印だけになることを避けます。

表は数学記号の大小文字を保持します。共通reportの見出し用uppercaseや小字をそのまま継承すると、ωやa(n)の意味が変わるため、concept-tableでは明示して打ち消しています。短い数式や見出しは table-math で一まとまりとして保ち、長い日本語の文全体は囲まず折り返せるようにします。最小幅を一律に固定せず、文章列が極端に細くなる表だけ最小幅を指定して折返し幅を確保します。表題は表示枠の幅に合わせて横スクロール中も読めるようにしています。横長の表はキーボードで全列へ進めるようにします。

## 検証

リポジトリルートから:

```bash
python3 -m unittest discover -s analytics/math_foundations/tests -p 'test_*.py'
node --test analytics/math_foundations/tests/*.test.cjs
```

数値テストは既知の回転、長さの保存、複素積、二分法・割線・求積・幾何級数の既知値、誤差、適用範囲、二変数の経路反例・線形近似の余りと誤差上限・数値表現の境界、勾配・曲率・制約上の接線変化率、上下和と中点和・極座標セルの面積、Bayesの分母0、同時確率表の実現可能域、二項PMF/CDFの正規化、密度の面積、弱大数の≥境界と固定seedを確認します。生成物のテストはHTMLのリンクとアンカー、ローカルで完結する構造、再生成時の一致を確認します。レイアウトと図の操作はブラウザでも確認します。


一般レベル集合の陰関数定理と一般の二重積分変数変換定理は、適用条件を示して未証明で借りています。明示曲線のLagrange条件、矩形の反復積分、円板へ極座標公式を拡張する除外誤差は本文で説明します。


確率の基礎では、確率をモデルの規則として導入し、観測した頻度との関係を弱大数の法則で説明します。有限離散の性質は直接証明し、一般の測度構成・絶対収束級数の並べ替え・一般の期待値と積分の性質は借用を明示します。弱大数の有限値iidの証明と、借用した性質の上での一般有限分散への拡張を区別します。中心極限定理・推定・検定は、その先の既存統計教材へ進む範囲です。

確率の実験は仮想モデルです。LLNの主図は二項分布から計算した逸脱確率とChebyshev上界、副図は固定seedの一本の経路です。疑似乱数は状態を更新してから値を作り、nを変えても同じ列の先頭を使います。≥の境界は、入力の最短十進表現を整数比として比較します。理論の確率、画面の丸め値、試行例の頻度を区別してください。

Windowsのアプリ内ブラウザでWSLの共有パスが正しく開けない場合は、ローカルHTTPで閲覧できます。リポジトリルートからWSL内で次を実行し、http://localhost:8765/index.html を開きます。

```bash
python3 analytics/math_foundations/tools/serve.py
```

このローカル配信は教材102ページと、入口から案内する既存4冊の生成済みHTML・静的資産だけを扱います。

## 任意の実ブラウザQA

既に導入済みの playwright-core と Chromium がある環境では、リポジトリルートから次を実行できます。このツールはパッケージやブラウザをインストールしません。二つのパスは手元の環境に合わせて指定してください。

```bash
node analytics/math_foundations/tools/browser_qa.cjs --self-test

MATH_QA_MODULE=/path/to/playwright-core \
MATH_QA_BROWSER=/path/to/chrome \
node analytics/math_foundations/tools/browser_qa.cjs
```

現行102ページを幅1280/390/320と明暗の612状態で確認し、全概念図/比較表の表示と文字・記号・NoJS/表の横スクロール、全37実験・前後移動・章内目次・画面幅切替・ヒントと解答・キー操作・JavaScript無効時の本文と目次も検証します。生成HTMLだけをローカルで配信し、終了時にサーバとブラウザを閉じます。通信・スクリプト・検証の失敗は非零終了にします。

結果のJSONと代表PNG、新しい概念図表の明暗切抜PNGは既定で _data/math-foundations/figure-messages-2026-11-08/ に保存し、--output で変更できます。生成HTMLのハッシュを記録するため、どの版を検証したか照合できます。図中文字の境界候補は実画像でも確認してください。Linuxヘッドレス描画は、Windows実機や実際の受講者による試読とは区別します。

[全体統合・内部試読の記録](../docs/reviews/2026-11-07-reader-integration-response.md)に、確認した範囲と限界をまとめています。

[確率の基礎の検証・レビュー記録](../docs/reviews/2026-11-07-probability-completion-response.md)と[確率10章の計画](../docs/2026-11-07-probability-foundations-plan.md)も参照できます。

シリーズ全体の [開発状況](../docs/STATUS.md) と [実装計画](../docs/2026-11-07-math-foundations-plan.md) を参照してください。

[図表充実版の検証・レビュー記録](../docs/reviews/2026-11-07-visuals-completion-response.md)に、全41章64節への追加、数学の検算、明暗/狭幅/NoJS、Opusレビューと最終確認をまとめています。

離散数学は、集合・証明・帰納法から進めます。微積分や確率の修了は前提にしません。漸化式の母関数は係数比較だけを扱う任意の寄り道です。整数の逆元、有限グラフの連結性、BFSとDijkstraの重み条件、貪欲彩色の上界と最小値の違いを、仮定と反例を添えて説明します。

[離散数学10章の実装・検証・Opusレビュー記録](../docs/reviews/2026-11-07-discrete-completion-response.md)と[離散数学計画](../docs/2026-11-07-discrete-mathematics-plan.md)も参照できます。

複素解析入門は、実の極限・積分・級数と偏微分/全微分を復習しながら読みます。Green/Stokesや既存ODE本は必修にしません。三角形Goursatと凸領域の原始関数は説明し、一般境界と有限円孔のCauchy定理だけ適用条件を示して借用します。主値Logの切断上、積分輪郭上の極は未定義であり、実験では0と区別します。既存の線形代数・常微分方程式・Fourier・統計への入口は維持しています。

凸な開集合の連結性は線分と上限の短い証明を添え、原点除外平面の連結性は本章で証明しない標準事実として区別します。[複素解析10章の実装・検証・Opusレビュー記録](../docs/reviews/2026-11-07-complex-completion-response.md)と[複素解析計画](../docs/2026-11-07-complex-analysis-plan.md)も参照できます。

ベクトル解析は三成分と外積から始め、向き/境界/正則性をそろえて局所と全体を結びます。矩形Green・箱Gauss・一枚patchのStokesは理由を導き、一般領域/曲面への拡張は条件を示して借用します。一般領域の三重積分の0拡張も明示します。

数値解析は問題の条件、算法の誤差、実行結果を区別します。丸めは自作十進モデルで説明し、実験のMath.exp最終桁や丸め尺度を厳密保証と呼びません。Newtonの停止/非収束、Eulerの有限時間収束と安定性を別々に扱います。既存線形代数/ODE本の修了は必須にしません。

[2科目の並行計画](../docs/2026-11-07-vector-numerical-plan.md)と[実装・レビュー・統合試読の記録](../docs/reviews/2026-11-07-vector-numerical-completion-response.md)を参照してください。

最適化は勾配・二次近似を必要な箇所だけ復習し、存在・必要条件・十分条件・反復の保証を分けます。有限n変数の微分法と一般LICQの必要性は条件を明記して借用し、凸KKT十分性と弱双対性は本文で証明します。一般の強双対性やNewton二次収束は必修にしません。実験は有限の軌道を描き、計算された微小残差を厳密な0と区別します。

[最適化10章の計画](../docs/2026-11-07-optimization-plan.md)と[実装・レビュー・統合試読の記録](../docs/reviews/2026-11-07-optimization-completion-response.md)を参照してください。

線形代数本編は橋4章の直後に読み進められます。実数の有限次元を基本に、一般の定理を使う範囲を明示し、2次行列のスペクトル/SVDと最良rank1誤差は直接説明します。入力と予測の一意性、零/重複固有値・特異値、回転と鏡映、計算残差と理論上の等式を区別します。

[線形代数本編計画](../docs/2026-11-07-linear-core-plan.md)、[全科目の図表メッセージ強化](../docs/2026-11-08-figure-message-quality-plan.md)、[正式な章立てと参照した公式目次](../docs/2026-11-08-textbook-titles-plan.md)を参照してください。全体612状態の最終QAは全科目の改修完了後に実施します。

[全科目の図表・正式章立ての完了記録](../docs/reviews/2026-11-08-textbook-quality-completion-response.md)に、最適化/線形代数追加と全101章の改修、Opus差分承認、最新102ページ版の検証範囲をまとめています。
