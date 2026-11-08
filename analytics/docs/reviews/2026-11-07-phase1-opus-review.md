# 実装レビュー：数学の見方（第1段階の20章）

**結論：** 定理の主張に誤りはなく、60組の演習・ヒント・解答もすべて合っています。基本定理を原始関数に頼らず証明する構成、Taylor の章が指数関数の性質を次章から借りて回収する構成も、循環していません。実験の数値表示と適用条件も概ね正確です（h = 0、|r| ≥ 1、飛びや極で根を主張しない点など）。ただし次の2点は修正が必要です。

- **積分の性質の抜け：** 基本定理以降の証明が、積分の章で扱っていない加法性・線形性に依存しています。
- **コラム：** ユーザーが求めた「面白い話・実世界の応用」に届いていません。

ほかに、前提の抜けが5か所、並べ替えで古くなった章の参照、手元のビルドに依存するテストがあります。

## 修正が必要な指摘

### P1-1 積分の加法性・線形性を証明しないまま使っている

- **対象：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\fundamental-theorem.html:4`
  - この行は「前提は積分の定義と加法性・大小関係」と書いています。
  - 同じファイルの :12・:18・:48 で使っています。
- **問題：** 積分の章にあるのは、上和・下和、可積分性の判定、連続関数の可積分性、x² の計算、反例だけです。加法性 ∫ₐᶜ = ∫ₐᵇ + ∫ᵇᶜ と線形性は、どこにも書かれていません。
  - 大小関係は、積分の章 :27 の L(P) ≤ I ≤ U(P) から導けます。
  - 加法性はそこからは導けません。
- **使っている箇所：**
  - **基本定理1の証明（:12）：** 加法性を使います。
  - **演習2の区間の分割（:48）：** 加法性を使います。
  - **p = 1 の判定：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\integration-methods.html:33` で加法性を使います。
  - **部分積分の証明（同 :21）：** 「両辺を積分」の段で線形性を使います。
  - **項別微分の補題：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\elementary-functions.html:18` が積分の差の評価に線形性を使います。
- **修正案：** 積分の章の「連続なら積分可能」の節の後に、「積分の基本性質」を1節置きます。
  - 加法性は、分割点に c を加えると上和・下和が左右に分かれることから、1段落で証明できます。
  - 線形性と単調性は、上和・下和の不等式から示せます。
  - 向きの約束 ∫ᵇₐ = −∫ₐᵇ もこの節へ移します。
  - 必読部（骨格）に入れない場合は、基本定理の章の冒頭に「証明は精密化に回す借用」と明記します。

### P1-2 コラムが「面白い話・実世界の応用」になっていない

- **対象：** 20本の内訳は次のとおりです。長さは216〜436字です。
  - 12本は「仮想」「架空」と明記した装置やモデルです（例：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\continuity.html:58`、`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\mean-value.html:60`）。
  - 出典付きの実例は `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\rotation.html:52` の W3C CSS の1本だけです。
  - 発見の背景（史実）を扱う本は0本です。
- **問題：** handoff の3分類（発見の背景・意外なつながり・実世界の応用）にも、ユーザーの「面白い話や実世界での応用例」にも届いていません。多くは「モデルの仮定は別に確かめよう」という同じ注意の繰り返しで、読んだ後に見方が変わりません。本文とのつながりは保たれており、この点は良い出来です。
- **修正案：** 各章の1本を、出典で確かめられる実話・実例に替えます。summary には型の札（背景・つながり・応用・破れ）と1行の要約を付け、折りたたまれていても開きたくなる入口にします。題材の例を挙げます。年と出典は私の知識によるもので、今回は確認していません。
  - **積分：** アルキメデスの放物線の求積。本文の 1/3 と直結します。
  - **級数：** オレーム（14世紀）の調和級数の発散。本文の倍々の組分けと同じ論法です。
  - **近似：** Heron が記した平方根の更新式は Newton 法と同じです。YBC 7289 の √2 の値は残っていますが計算法は不明で、史実と推測を分ける好例になります。
  - **数の拡張：** IEEE 754 は 1/0 = +∞ と NaN を導入し、代わりに体の法則の一部を手放しました。本文の「0 の逆数の代金」と直結します。
  - **集合と写像：** どのファイルも必ず短くする可逆圧縮は存在しません。単射と個数の比較だけで、読者自身が証明できます。
  - **不変量：** 15パズルの偶奇（Johnson & Story, 1879）。考案者をサム・ロイドとする伝承の訂正も添えられます。
  - **連続性：** ボルツァーノ（1817年）が当たり前に見える定理をなぜ証明したか。
  - **平均値の定理：** 区間の平均速度による速度取り締まり。導入国と方式は確認が必要です。
  - **Taylor：** 数学ライブラリの sin は、Taylor 多項式そのものではなく、引数の範囲を縮めた後の最良近似多項式で計算しています（fdlibm で確認できます）。

### P2-1 級数で定義した sin・cos と、角度の三角関数の同一性・π・周期が本文にない

- **対象：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\elementary-functions.html:47`
  - 両者の同一性は、任意のコラムにしか書かれていません。しかも弧長の定理を借りています。
  - 同じファイルの :3 と :42 が、この同一性を前提にしています。
- **問題：** 章の中に π も周期も出てきません。回転の章（rotation.html:9）は、三角関数を単位円上の角度で定義しています。このため本文だけでは、次の3点が成り立ちません。
  - 高校の (sin x)′ = cos x の借りを回収できません。
  - 回転の章の加法定理とつながりません。
  - 「定義の理由や主定理をコラムへ移さない」という方針に反します。
- **修正案：** 本文に1節を足します。
  1. cos 2 ≤ 1 − 2 + 2/3 = −1/3 < 0 を示します。第3項より後は減っていく交互の和なので、この評価が成り立ちます。
  2. 中間値の定理から最初の正の零点が存在するので、それを π/2 と定義します。
  3. 加法定理から sin(π/2) = 1 と周期 2π を導きます。
  4. 角度との同一性は、弧長または扇形の面積の定理を「借用」と明記したうえで、本文に置きます。

### P2-2 実数の完備性の出発点が章ごとに違い、相互の関係も不正確

- **対象：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\limits.html:43`：最小上界性を「完備性として借ります」とし、入れ子区間の性質と「同等な形」だと書いています。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\continuity.html:29`：入れ子区間の性質を「この章で出発点とする」としています。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\mean-value.html:16`：点列コンパクト性を借りています。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\integration.html:38`：一様連続性を借りています。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\series.html:34`：Cauchy の判定法を「完備性の別の形」として借りています。
- **問題：** 読者には公理がいくつもあるように見え、どれが公理でどれが定理か区別できません。また「同等」は不正確です。入れ子区間の性質から最小上界性を導くには、アルキメデス性も必要です。アルキメデス性を持たない順序体では、入れ子区間の性質が成り立っても最小上界性は成り立たない例があります。
- **修正案：**
  - 公理は、極限の章の最小上界性1つにします。
  - 連続性の章では、入れ子区間の性質を最小上界性から導きます。「左端の上限がすべての区間に入る」という3行で書けます。
  - 点列コンパクト性と Cauchy の判定法は、「二分法で証明できる定理（精密化）」と明記します。
  - limits.html:43 は「アルキメデス性と合わせると同値」に直します。

### P2-3 逆関数の微分公式を、証明も借用の明記もなしに使っている

- **対象：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\elementary-functions.html:34`（同じファイルの :54 の演習2も同様）
- **問題：** この公式は、微分の章にも平均値の定理の章にもありません。それにもかかわらず、次の2つの回収がこの一点に依存しています。
  - (log x)′ = 1/x
  - 積分法の章で借りた (xᵖ)′ = pxᵖ⁻¹
- **修正案：** 微分の章に短い定理を足します。
  - 狭義単調で連続な関数の逆関数は、中間値の定理から連続になります。
  - そのうえで差商の逆数を取れば、微分可能性が示せます。
  - 定理を足さない場合は、初等関数の章の冒頭に借用と明記します。

### P2-4 複素数の絶対値を、定義より前に使っている

- **対象：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\elementary-functions.html:40`（「|z| を使う先ほどの評価で絶対収束し」）
- **問題：** |z| の定義は数の拡張の章（numbers.html:37–40）になく、回転の章 `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\rotation.html:30` で初めて出てきます。回転の章は、目次では初等関数の章より後です。さらに次の性質は、どこにも示されていません。
  - |zw| = |z||w|
  - 複素数の三角不等式
  - 複素級数で「絶対収束すれば収束する」こと
- **修正案：**
  - 数の拡張の章に |z| = √(a² + b²)、|zw| = |z||w|、三角不等式を足します。
  - 初等関数の章の :40 に「実部と虚部の級数はそれぞれ |z|ⁿ/n! で抑えられ、実数の場合に帰着する」と添えます。

### P2-5 |r| < 1 なら rᴺ → 0 となることを証明していない

- **対象：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\series.html:12`
- **問題：** 同じ種類の事実を、証明なしに次の箇所でも使っています。
  - 区間幅 2/2ⁿ → 0：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\continuity.html:42`
  - 公比 1/2 以下の上界 → 0：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\taylor.html:27`、elementary-functions.html:11

  一方、`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\inequalities.html:39` で証明したベルヌーイの不等式は、どの章からも参照されていません。
- **修正案：** 級数の章か極限の章に補題を置きます。
  - 0 < |r| < 1 なら、1/|r| = 1 + t（t > 0）と書けます。
  - ベルヌーイの不等式 (1 + t)ᴺ ≥ 1 + Nt から、|r|ᴺ ≤ 1/(1 + Nt) < 1/(Nt) → 0 が出ます。
  - 入門で証明した不等式が、微積分で効く場面にもなります。

### P2-6 並べ替えで古くなった「前章」「次章」（既存3章の退行）

- **`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\continuity.html:31`**
  - 本文：「前章で証明したように x² = 2 を満たす有理数はありません」
  - 今の前章は極限の章で、この証明はありません。証明があるのは `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\numbers.html:30` です。
- **`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\rotation.html:3`（同じファイルの :30 も同様）**
  - 本文：「前章の複素数」「前章の分配法則」
  - 回転の章は「線形代数への橋」の第1章になったので、前のページは目次です。指しているのは数の拡張の章です。
- **numbers.html:32**
  - 本文：「次章で完備性…」
  - 数の拡張は入門の最終章で、次のページは科目選択です。
- **修正案：** どれも明示的なリンク（`numbers.html#numbers-gaps`、`limits.html#limits-completeness`）に置き換えます。

### P2-7 生成物のテストが、Git 管理外の既存教材のビルドに依存している

- **対象：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\tests\test_build.py:86-92`：すべてのローカルリンク先が存在すること（`is_file`）を確かめています。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\build.py:59`：既存4冊の `_build/html` へリンクしています。
  - 4冊のビルドは、すべて gitignore 済みで未追跡です。
- **再現：**
  - 手順：tokens.css だけを置いた作業領域を WORKSPACE に差し替えて build しました。
  - 結果：当時の21ページは生成されましたが、既存4冊へのリンクは4件とも切れました。この状態では test_build が失敗します。つまり、今の 2/2 成功は手元にビルドがあることに依存しています。
  - 補足：このテストはルートの testpaths にも Makefile にも入っておらず、`make test` では実行されません。
- **修正案：** 既存教材へのリンクは別扱いにします。パスの形式だけを検査し、未ビルドなら理由を表示して skip します。

### P3 軽微な指摘

- **極限の基本性質を、証明なしで使っている：** 極限の章が証明しているのは和と積だけです。次の4か所はそれ以外の性質を使っています。極限の章に枠を1つ足し、各1〜2行で証明すれば足ります。
  - 不等式が極限でも保たれること：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\mean-value.html:30`
  - xₙ → c なら f(xₙ) → f(c) となること：同じファイルの :17
  - 商の極限：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\approximation.html:29`
  - 極限の合成：`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\derivatives.html:46`
- **借用の宣言が使用より後にある：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\integration-methods.html:22` で (1 + x)³ᐟ² の微分を使っていますが、宣言は :29 です。宣言を章頭の :4 へ移します。
- **実験の表示：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\assets\calculus-experiments.js:52`：「各区間の最小値・最大値」は、本文の「最大の下界・最小の上界」と食い違います。「最大の下界・最小の上界（連続なら最小値・最大値）」に直します。
  - 同じファイルの :66：横軸のラベル n が、スライダーの N と合っていません。本文でも、Sₙ（1始まり、series.html:4）と S_N（0始まり、:9）を大文字と小文字だけで区別しています。幾何級数には別の文字（例：G_N）を使います。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\assets\experiments.js:179`（同じファイルの :197）：「R(α)R(β) = R(α + β) の数値」として表示している行列は、R(α + β) を直接計算したもので、積は計算していません。積も計算して並べるか、表示名を改めます。
- **文の誤りと未定義の用語：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\elementary-functions.html:28`：「加法性が普通のべきと一致させ」は文が壊れています。E(p/q)^q = eᵖ と、正の q 乗根がただ一つであることから一致を示す文にします。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\taylor.html:34`：「収束半径」が定義なしに使われています。
- **学習順序：**
  - 入門の最終章の「次へ」は科目選択に飛びます（`\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\build.py:99-102`）。STATUS の「通して読める」に合わせ、次の科目の第1章へ直接進めるようにします。
  - 回転の章の冒頭にも、前提となる章を書きます。

## 任意の改善案（5件）

1. **条件収束の並べ替えを具体例で示す：** 対象は `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\series.html:36` です。1 − 1/2 − 1/4 + 1/3 − 1/6 − 1/8 + … を3項ずつまとめると (1/2)(1 − 1/2 + 1/3 − …) になり、和が半分になります。対数を使わず、本文の部分和の議論だけで書けます。
2. **収束半径の謎を予告する：** 対象は `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\taylor.html:32` です。1/(1 + x²) は実数全体で滑らかなのに、級数は |x| < 1 でしか収束しません。原因は複素平面上の ±i です。今の例 1/(1 − x) は特異点が見えているので、驚きが弱くなっています。
3. **借用と回収の一覧ページを作る：** 完備性の各形、一様連続、弧長、逆関数の微分、実数べきについて、使った章と、証明した章（または未証明）を表にします。
4. **ヒント2が要点を渡しすぎている箇所を直す：**
   - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\approximation.html:51` の「M₂ = 6.6」は、演習の狙いそのものです。
   - continuity.html:68 の 2⁹・2¹⁰ も同様です。
   - どちらも、答えの一歩手前で止めます。
5. **n² + n + 41 の例を強める：** `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\observation.html:28` に、n = 0〜39 の40個がすべて素数で、最初の失敗は n = 40（41²）だと書きます。「40個確かめても証明にならない」が具体的に伝わります。

## 確認した範囲

- **読んだもの：**
  - 計画書・STATUS・README・catalog・build・template・テスト3本
  - 20章の全文（MathML を線形化して読みました）
  - math.js・calculus.js・2つの experiments.js・reader.js
- **手で確かめたもの：** 演習60組の計算をすべて検算しました（211/128、4(√2+1)/15、17/12、13/3、1/1280 など）。
- **実行したもの：** Python 2/2 と Node 15/15 を再実行し、どちらも成功しました。.pyc は書き出していません。
- **確認していないもの：** ブラウザでの表示（390px 幅、MathML の描画）。
- **並行作業：** レビュー中（14:03 以降）に、別セッションが次の作業をしています。
  - 線形代数への橋（vector-spaces・dimension・determinants と JS、テスト）を追加しています。
  - build・catalog・template・README・style・test_build を変更しています。
  - 対象の20章は 13:44 から変わっていないので、上の指摘はそのまま有効です。行番号は build.py が更新後、ほかは現時点のものです。
  - 追加された章はレビューしていません。
- **ファイルの変更：** リポジトリのファイルは変更していません。作業ファイルは scratchpad の `\\wsl.localhost\Ubuntu\tmp\claude-1000\-home-kazumasa-projects-analytics\53251b72-a10c-4aa7-ad4f-037d1a2d615e\scratchpad\linearize.py` と、同じフォルダの lin・fakews・out だけです。