# 複素解析入門：実装・Opusレビュー・統合試読の計画

> **For agentic workers:** superpowers:subagent-driven-development と独立レビューを使用。ユーザーはこれまでと同じ実装→Opusレビュー→統合/試読を明示し、線形代数/ODE等への接続を維持する方針を確認した。既存承認の通常の編集判断で進め、再承認を求めない。

**Goal:** 複素数の平面の幾何から、正則性・境界積分・級数・留数と実積分の理由を理解できる10章を完成させる。
**Architecture:** 既存HTML readerへbook=complexを追加。inline SVG/native tables/MathML、pure JS＋操作UI、標準Python buildを継続する。
**Tech Stack:** HTML/CSS/MathML/SVG、Python標準、plain classic JS、Node built-in tests。新依存なし。
**Spec:** 以下の設計とユーザーの「数学の気持ち/なぜ役に立つ/コラム/図表」方針。対象読者は高校既習〜大学基礎、専門/院生の理論は必須にしない。

## 設計と前提

既存の数の拡張/回転、微積分Ⅰの極限・積分・級数、微積分Ⅱの偏微分/全微分を復習リンクで回収。確率・離散数学・既存ODE本の修了は前提にしない。Green/Stokesは既習扱いにしない。実2成分の極限・積分を複素数へまとめる意味を説明する。

| No | slug | 題名/内容 | 証明・図表・実験 |
|---|---|---|---|
| 01 | complex-plane | 平面の数で、変換を見る / 複素数・極形式・写像・領域/極限 | 掛算の回転/拡大、z²・1/z、開集合/領域、実行列との接続。既存numbers/rotationを復習 |
| 02 | complex-differentiation | 全方向で、同じ微分を持つ / 複素微分・正則性・CR | 複素微分⇒実全微分の特殊形、実全微分＋CR⇒複素微分（C¹は十分）。共役/|z|²、点と近傍。lab=complex-difference |
| 03 | complex-logarithm | 回ると、対数はどこへ行く / exp・sin/cos・Log・枝 | exp=eˣ(cos y+i sin y)を実C¹で正則と導出、周期と逆。主値LogはC∖(−∞,0]でArg∈(−π,π)、切断上未定義。lab=complex-log |
| 04 | complex-contours | 道に沿って、複素数を足す / 区分C¹曲線・向き・積分・ML・原始関数 | 定義∫f(γ)γ′dt、実2成分、向き/再param、primitive FTC、∮1/(z-a)=2πiと(z-a)^k。他点での大域Logなし |
| 05 | cauchy-theorem | 境界の足し算が、消える理由 / 三角形Goursat・凸領域・穴 | 4分割/入れ子/MLの証明、三角形差分で凸領域原始関数。曲線境界・有限円孔への拡張の条件を明示して借用、Green不使用 |
| 06 | cauchy-formula | 境界から、中の値を取り出す / 円板Cauchy公式・高階微分・評価 | 小円除去とMLで証明、可除を先取りしない。kernel差分一様評価でn階式、Cauchy評価/Liouville。Taylorに依存しない |
| 07 | complex-taylor | 微分できることが、級数を決める / Taylor・剰余・零点/一致定理 | kernel幾何展開、M R/(R-r)(r/R)^(N+1)、閉小円板で一様。項別微分の必要補題を自給、連結性/集積点の条件 |
| 08 | laurent-singularities | 穴の周りを、正負のべきで読む / Laurent・可除/極/真性 | annulusの外円−内円Cauchy→2幾何展開、閉部分annulusで一様。係数一意/積分半径不変、可除は展開の後 |
| 09 | complex-residues | 一周で残る、一つの係数 / 留数・有限特異点の定理 | a−1だけ残る、g,h正則かつh(a)=0,h′(a)≠0ならg/hの留数g(a)/h′(a)（g(a)=0なら可除で留数0）、高階極、穴の境界。輪郭上の極は不可。lab=complex-residue |
| 10 | complex-real-integrals | 実数の積分を、複素平面で解く / 半円輪郭・弧評価・実広義積分 | 1/(x²+a²)→π/a、1/(1+x⁴)→π/√2、左右tailと弧が消える根拠。ODE/Fourierへの任意の接続 |

各章25–45分、05/06/07/08/10は30–50分を目安。問い→定義の理由→短い証明→条件/反例→接続、任意コラム1、演習3（各ヒント2/解答）、振り返り3。主題の近くに正確な概念図2以上/比較表1を目安に配置。色以外の線種/記号、360幅/22px以上/固有title・desc/ARIA/data-visual、token色。表は短いth/式だけtable-math、長文をnowrapしない。NoJSでも本文/静的図表/解答を読む。

コラムは数学の意外なつながりか自作モデルを本文に接続する。実世界/歴史の固有事実は一次資料で確認。外部定理を証明済みと装わず、何を借りたか必要な仮定まで記す。

## 証明の境界・循環防止

1. 複素微分と正則を区別。CRは実全微分可能性と組で十分、偏微分が点にあるだけでは十分でない。|z|²は0で微分可能だがどの近傍でも正則でない。
2. exp/三角は実関数から定義して正則性を示す。一般複素冪級数の項別微分を03の前提にしない。Logの切断と偏角の主値を一貫させる。
3. 05で三角形Goursatと凸領域原始関数を示す。三角形縮小の共通点は座標Cauchy列/実完備性で説明。一般曲線境界への近似・有限個円孔の境界Cauchy拡張だけを、標準結果として未証明で借用する。
   借用版: 外側は単純・正向き区分C¹閉曲線、内側は有限個の互いに交わらない閉円板で外の内部に厳密に含まれる。fが全境界と間の閉領域を含む開近傍で正則なら、外周積分=各内周を反時計回りに積分した和。穴0も含む。境界の向きと内部/開近傍を明示。凸領域/穴なしの証明をこの一般版で置き換えない。
4. 06はf(ζ)/(ζ-z₀)の穴付き領域で借用境界定理→小円の誤差をMLで0へ。f差商の可除を先に使わない。高階公式は(a-h)^−pの有限差分を輪郭から距離δ>0で一様評価し、Taylorを先取りしない。Liouvilleは評価と直線上のFTC。FTAが任意コラムにある場合、閉円板上連続実関数の極値は借用事実と明記。
5. 07のTaylorはkernelの有限幾何和＋明示剰余から導く。一般冪級数の正則性を述べる場合は、r<ρで|aₙ|ρⁿの有界性→導関数の一様収束と線分積分補題を説明し、複素版を既習扱いしない。一致定理は領域/内部の集積点条件と局所零点の議論。
6. 08のLaurentはr<|z-a|<Rの円環、r<r′<|z-a|<R′<Rを使う（r=0可）。外円−内円の式に点zの小円を追加して06と同様に導出。閉部分円環で一様、係数の半径不変と一意性をMLで支える。可除/極/真性の分類はこの後。Picard/Casorati等は必須にしない。
7. 留数定理は有限個の孤立特異点、輪郭/間の領域で正則、境界上特異点なし、正向き。複雑な自己交差曲線の一般winding論は後回し。10では円弧上の具体的下界と実の左右tail収束を示す。Jordan補題/PVを未導入で使わない。

一次資料（2026-11-07閲覧）: MIT18.04 syllabusで学部基礎の範囲を確認。complexanalysis.orgの原著HTML教材 §6.3/§6.5でGoursat/境界変形と小円によるCauchy公式の条件を確認。本文は自作例/独自の日本語説明とする。
- https://ocw.mit.edu/courses/18-04-complex-variables-with-applications-spring-2018/pages/syllabus/
- https://complexanalysis.org/web/sec_cauchy-goursat.html
- https://complexanalysis.org/web/sec_cauchy-integral-formulas.html

## 実験の有限範囲と内部API

新assets/complex.jsはMathComplex/Node exports、assets/complex-experiments.jsはclassic script。具体的signature/controls/readoutsは担当者が早期にrootへ通知。3hostsは data-lab=complex-difference / complex-log / complex-residue、native controls/reset/status/NoJS。既存CSSを使用、外部fetch/moduleなし。
- difference: z²/共役/|z|²の有限差商。点x/y∈[−1.5,1.5]、h∈[.05,1]、角度[0,360]。有限hの値と微分極限を分け、原点の|z|²を正しく扱う。z²の誤差はh、共役の商はe^(−2iθ)、|z|²原点の商はh e^(−iθ)を独立オラクルにする。
- log: 半径[.5,2]、角度[−360,360]度。経路に沿う連続値log r+iθと主値Logを別表示。±180度は主値の切断上でundefined/null、±360は点z=rへ戻るが持ち上げ値は±2π違う。直交角のsin/cosは厳密0/±1に揃える。円全体の一価な連続Logとは呼ばない。
- residue: 円|z|=1、実pole a∈[−2,2]、向き±1、midpoint分割n=16..256（16刻み）。f=1/(z-a)、厳密積分は|a|<1で±2πi、|a|>1で0、|a|=1は輪郭に極で未定義。近傍を勝手にundefinedにするtol禁止。区間真中の数値和は観察で証明にしない。偶数nの数値値は独立式2πi/(1+aⁿ)（向き反転で負）をオラクル、境界は表示拒否。図は極/円/向きと正負を明示。

未定義は0/Infinity/NaNと混同せずnull＋説明、SVGを残す。一般的なUIエラー扱いとは分ける。入力型/範囲不正はAPIで拒否。UIで可能な特異境界は意図的な教育状態として扱う。

## 接続・担当・制約

- 既存線形代数・ODE・Fourier・統計の4入口/限定サーバmountを保持。複素解析01から線形変換、10の任意コラムからy′=λy/回転・振動と既存入口へ接続。これらの既存本の全面改稿/再buildは行わない。
- Scope: analytics/math_foundations、analytics/docs、analytics/READMEの入口。証拠は_data/math-foundations/complex-2026-11-07/の1root。
- 既存checkout/mainを継続（以前の承認設計と同じ方法を求めるユーザー指示）。既存51原稿/JS17/CSS/ユーザー変更を保持、branch/worktree切替・依存追加・commit/push/deployなし。
- author A: 新01〜04 HTMLのみ。author B: 新07〜10 HTMLのみ。mathUI: 新complex.js/complex-experiments.js/tests/complex.test.cjsのみ。root: 新05/06、catalog/build/template/portable test/QA/README/進捗統合。共有CSSはroot所有、必要なければ変更しない。
- 実装と独立数学/視覚レビューを分ける。既存win math/Opus maxへ設計/実装/最終差分レビューを依頼し、能動的に完了を確認。Opusの自分のLinuxブラウザ操作可、8765は維持。待つ間に独立の次工程を進める。
- 各図表data-visual必須、短い見出し保護、写像の入力ごと矢印、定量図の同縮尺、図/有限実験と一般証明を区別。

## Review Focus

1. CRの必要/十分、点と開近傍、0導関数と向き未定義、有限差商と極限の混同。
2. Log切断上の主値undefined、Arg選択域/±360の持上げ/expの非単射。
3. Cauchyの境界/内部/穴/正則な開近傍、三角形と借用一般版の区別、証明の循環。
4. Taylor/Laurentの収束領域と閉部分での一様、項別操作/高階微分を無条件に借りない、可除の先取り。
5. 留数のa−1・向き・極が輪郭上/外/内、実積分の弧/tailの正当化、数値求積を厳密値と混同しない。

## Tasks / progress

- [x] Task1: 現状/既存接続の監査、章構成・証明境界・有限3実験の設計。
- [x] Task2: 新10章を分担実装、図表/コラム/30演習・60ヒント/30解答/30振り返り。
- [x] Task3: 新3計算を独立オラクルのTDD（RED→GREEN）で実装、nativeUIと特異状態/キー/reset。
- [x] Task4: 新10ページ/3labのportable期待を先に追加してRED、catalog/build/入口/科目間移動を統合してGREEN。7科目61章/62ページ25実験。
- [x] Task5: 3担当の独立数学/視覚レビューとOpus段階レビュー、重要指摘修正/差分再確認。
- [x] Task6: 全62ページ×3幅×明暗=372状態、NoJS62/全25実験、183演習/366ヒント/183解答、全図表/表左右、既存4入口を検証。
- [x] Task7: 最終Opus固定原本レビュー、全体統合/内部試読、現在版hashと検証対応/サイズ/STATUS/README/完了記録を確定。

検証: Python既存20と意味あるportable期待、Node既存76＋新計算テスト、XML/固有ID/ARIA/静的図の正確性、同じ既存Chromium/Playwrightで実表示。グローバルQA成功後に局所図だけ変える場合、対象ページを3幅/明暗/NoJSで追試し、不変の他ページhashと合わせ現在版を検証したことを明記。WindowsHTTPとLinux描画/内部試読、Windows実機/実学生は区別する。

出力見積: 生成62×約230KiB≒14MiB、図表PNG/QA/レビューは同1root25MiB前後を目安。大きな配列や中間出力を保存せず、再試行は同名へ上書き、失敗は要約/原因/hashだけ残す。30GiBには遠く及ばない、最終duを記録。

独立カリキュラム監査：証明順序に重大循環なし。円弧の位置だけの一様近似で積分収束とは言わず、曲線境界の一般拡張は正確な借用定理として一括する。中点求積が境界a=1でπiを返しても、通常積分は未定義なのでAPIは求積前に拒否する。

## Opus設計レビューへの反映

2026-11-07。大きな循環なし。03でtanの定義・単調性と範囲・逆の連続性・逆差商によるarctan微分を自給し、Arg局所C1を根拠付ける。09のg/h公式はg,h正則、h(a)=0かつh′(a)≠0を明記（g(a)=0なら極ではなく可除で留数0）。01連結の相対開分離の定義と07開閉集合の伝播は本文で一致。04のMLは複素積分を単位複素数で回して実部を取る係数1の証明が本文にある。07は内容を維持し時間目安30–50分へ調整。独立レビューの3表の狭い文章列は対象tableだけ最小幅を局所設定し、全表一律/共通CSS変更や長文nowrapを避ける。

## 完了時の確認

2026-11-07。10章/23SVG/10表/3実験を統合。Python20/Node86、修正後の全62ページ372状態/13877checks失敗0、NoJS62/全25実験を確認。Opus全体レビューは重要欠陥0・軽微3件、修正後5原本差分も承認可。凸開集合の連結を上限論法で補い、原点除外平面の連結は未証明の借用と明記。矢印の所属・テーマに依らない凡例を修正した。19原本/62生成HTMLと検証のhashを照合。既存51原稿/17JS/CSS/serveは維持し、既存4接続のHTTP確認済み。残作業なし、後続科目/既存本の全面改稿は今回の範囲外。[完了記録](reviews/2026-11-07-complex-completion-response.md)。
