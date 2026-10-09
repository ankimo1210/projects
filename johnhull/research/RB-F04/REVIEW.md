# RB-F04 最終独立レビュー

2026-10-09。判定: **approved — 固定合成実験と教材を受け入れる。Asian価格差は識別できず。**
RB-F04の評価範囲に未解決のblocking defectはない。正本の機械記録は [review.json](review.json)。
実装作者と別の f04_final_review が数式・契約・原始主配列・採否・実行済み3図を確認した。
本レビューの変更はこの2ファイルのみ。実装の編集・commit・pushは行っていない。

## 結論と適用範囲

固定したjoint_refined面、65,536 paths × 3 seeds（9017/9029/9047）、192/384/768内部stepsを評価した。
768stepsの全196,608 paired pathsでHeston Asianは5.550845294、localは5.554518176。
local−Hestonは **0.0036728814**、paired sampling SEは **0.0043874320**。
samplingだけの約95%半幅0.0085993668と、経験的refinementを含む固定識別閾値0.0115314184を確認した。
差の絶対値は閾値を超えず、再計算した判断は `difference_not_identified`、研究採否はtrueで一致した。

研究採否trueは、この条件の数値比較と未識別という結果を説明可能な教材として保持する意味である。
全面の価格一致、両モデルの動学的同値、全パラメータ域の頑健性、市場での優位性を認定しない。
二時点のjoint / conditional差は点ごとの記述量で、Asianの識別判定や全bin同時検定と区別する。
最新3図はすべて `Asian decision:` と対象を明示する。

## 数式・固定契約の確認

Dupireの式は

\[
\sigma_{\rm loc}^{2}(T,K)
=\frac{2\{C_T+qC+(r-q)KC_K\}}{K^2C_{KK}},
\qquad C_{KK}=e^{-rT}f_{\log(S_T/S_0)}(\log(K/S_0))/K
\]

と整合する。Riccati時間微分から得たvariance-weighted CFの逆変換を密度で割っている。
非零配当での独立数学検算も恒等式・独自CF積分と一致した。
PDEは暦時刻を用いたlog-price作用素、配当付きcall境界、CN/Rannacherで、
面の時間・空間・域、Fourier次数・上限の検査を分離する。

両モデルのdriftはr−q、stock shockは共通第1factor。
粗いBrownian増分は細かい増分の和で結合される。
Asianは満期1年・K100・正時点i/12の12観測だけを平均し、S0を除外して満期割引する。
内部stepを増やしても平均へ入れる観測日は変わらない。
モデル差のSEは各経路のlocal−Heston payoffからddof=1で計算する。

条件付き確率は各モデル自身の第1時点binを分母にする。
\(p_m=\sum_i A_{m,i}B_{m,i}/\sum_i A_{m,i}\)、
\(IF_{m,i}=A_{m,i}(B_{m,i}-p_m)/\bar A_m\) とし、
\(s(IF_L-IF_H)/\sqrt N\) がpaired SEである。
独立に4つの原始平均の共分散からdelta methodを計算し、全6binで一致した。
最低分母件数は支持条件であり、稀な成功事象のnormal区間の信頼性まで保証しない。

## 原始配列・checker・検証証跡

- 原始主NPZは **192,772,222 bytes / 1,393 arrays**。
  全seed・全水準のAsian、粗細差、joint全36セル、conditional全6bin、
  各model×seedと集約のvanilla/holdout guard、pilot面項目・閾値を独自式で
  **201組の数値照合（配列比較を含む）**。rtol1e−11 / atol1e−12で一致した。
- checker baseline PASS。Asian SE、joint件数、conditional分母/SE、decision、
  research_acceptance、元の1経路、経路削除、原始densityの **9種類の改変をすべて拒否**。
  保存された要約・フラグを信用せず、月次観測と原始診断から統計量・採否を再計算することを確認した。
- C/F由来の両復元コピーを別々に読み、容量・SHA・配列数とAsian差/paired SEを独立に確認。
  SHAは `26f18ffd5768e919b8ccca45f6a4e1e42fab3dea64c68e44ac803f9717573078`。
  hashはblob来歴の確認であり、数値正しさの代用ではない。
- rootの主fresh replayは **115.268秒、PASS**（rtol1e−9 / atol1e−10）。
  面・参照価格・固定seedの経路/statusを再生成し、開始/終了の金融ソースdigestも不変。
  両復元原始配列の完全checkerも各PASS。
  [validation.json](validation.json)を読み、現行金融ソースのdigestとの一致を確認した。
- 関連3suiteは **7,316 passed / 6 skipped / 2 deprecation warnings、exit0**。
  `hullkit/tests`・`report/tests`・`deep_hedge_price/tests`、pytest374.77秒。
  skipはr=qで定義されない既存lookback閉形式。warningはjapanize_matplotlib/distutils。
  rootの実行記録と完了ログを確認した。
- 最新notebookは **実行済み3PNG / error0 / stderr0**。
  notebook内PNGと抽出PNGのbyte一致を確認し、3図を独立に目視した。
  軸・月次契約・尾部・支持域・価格/percentage-point単位・誤差表・Asian採否の表示に問題はなかった。

金融/実験ソースのdigest、protocol・主JSON・notebookのSHAと図のdigestをreview.jsonに記録した。
pilot承認の元文書と主設定/予算の厳密照合も確認した。主結果を見て予算を緩めていない。

## 誤差・診断の読み方

| 固定精度目標（価格は通貨） | 実測 | 上限 |
|---|---:|---:|
| Asian sampling 95%半幅 | 0.0085993668 | 0.01 |
| Heston Asian step経験的変化 | 0.0013738470 | 0.006 |
| local Asian step経験的変化 | 0.0012069996 | 0.003 |
| pilot Asian面経験的変化 | 0.0003512049 | 0.0005 |
| PDE vanilla残差 | 0.0003439606 | 0.001 |
| Fourier vanilla残差 | 1.27898e−13 | 1e−9 |

vanilla MC guardを含む7検査はすべてPASS。
6MC SE＋固定step allowance0.015＋PDE残差は点ごとの実装診断で、全面一致の証明ではない。
Asian識別閾値にはAsianのsampling・各モデルstep・pilot面変化だけを加える。
vanilla PDE残差をAsian誤差上界として加えていない。
sampling SEはbiasを含まず、2水準の経験的変化は厳密bias boundではない。

選択面20,769セルはすべて支持。
主768stepsで経路失敗は両モデル0、Heston負Euler variance状態は2,096。
localのleft-wing延長は779 paths / 60,492 visitsを保持した。
比較用z±6面の未支持133セルはNaNのままで、定数支持端延長は明示した数値拡張である。
翼を訪れた経路や負分散状態を隠していない。最小時刻proxyも理論的な全spot初期面とは区別する。

定数r,qと平方可積分な割引stock martingaleの仮定下では、
\(E[S_sS_t]=e^{(r-q)(t-s)}E[S_s^2]\)。
真に単一時点marginalが同じなら固定算術平均の平均・分散も一致する。
Asian call差は平均分布の他の形に依存し、小さい差や未識別は自然である。
この理論と、有限quote・補間・Eulerの近似は区別する。

## 最終レビュー中の修正確認

1. **P2: 凍結後のtest fixture予算継承。**
   予算未設定を期待したfixtureが現行protocolの凍結予算を継承し、1testが失敗した。
   rootがfreezeを除去しnumerical_precision=Noneを明示した。
   当方の修正後単独実行は1 passed（0.44秒）、関連suiteもPASS。
2. **P3: 図3の実キー・観測表示。**
   coarse_steps/fine_stepsを実キーcoarse/fineへ修正し、
   「全内部stepを平均」のように読めるtitleを固定月次契約の表示へ変更。
   実図の192→384 / 384→768とregressionで確認した。
3. **P3: 採否表示の対象。**
   未保存reason fallbackを除き、固定検査・閾値・Asianに限定した説明を表示。
   全suptitleのAsian decision明示を再実行・独立目視で確認した。

修正はrootが表示・test fixtureに行い、凍結した金融計算・runner・protocolは変更していない。
本レビュー確定後のcommit・tracked release gate・main反映はrootの統合作業に属する。

## 本編artifact gateに関する適用範囲の補足

追加の本編artifact照合は **FAIL**（research158件、baseline main e803e00b69件）。
実測されたエラー集合を独立に比較し、共通69件は依存指紋、追加89件はすべて
Git管理外のBook生成HTML欠如、baselineだけのエラーは0件と確認した。
欠如は06_numerical.html / 10_exotics.html / 12_qualitative_summary.htmlの3ファイルに限られ、
非存在とgitignoreを確認した。エラー集合全体はbaselineと同一ではない。
詳細は [validation.json](validation.json) のcore_artifact_comparisonに保持する。

基点とのscoped tracked diffはMODEL_INDEX.md / ROADMAP.mdのみで、
既存本編source・証跡・台帳・__init__・Book入力は変更されていない。
F04の確認済みソースdigestも一致し、数値/fresh/両復元/関連7,316 testsのPASSは維持する。
本レビューのapprovedはF04の固定研究・教材に限定し、**本編306節の新しい全面再受入PASSを主張しない**。
本編を修正せず、tracked release gateはrootがcommit後に実行する。
