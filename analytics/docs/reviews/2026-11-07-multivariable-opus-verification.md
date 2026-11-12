## 多変数3章の修正後確認

**結論：前回の指摘はすべて解消しています。未解決の重要指摘はありません。**

- **重要1（解消）：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\partial-derivatives.html:25` は「y を固定すれば y² は定数なので、その x 微分は 0」になりました。
  - 同じ章の63行目の解答と79行目の振り返りとも合っています。
- **P2（解消）：** 次の3か所が同じ契約にそろいました。浮動小数点の比較では理論上の不等式が数 ulp 逆転しうること、非正規化数を拒否するのは大きな相対精度の損失を防ぐためであること、上向き丸めは保証しないことです。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\assets\multivariable.js:67-69` のコメント
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\tests\multivariable.test.cjs:131,201` のテスト名
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\docs\2026-11-07-multivariable-first-plan.md:148` の契約
  - 追加されたテスト（同じファイルの144行目）は、余りと上限の両方を既知値 19683/10000 と相対 16ε で照合しています。逆転する現在の挙動をテストで固定していない点も適切です。
- **P3（3件とも解消）：**
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\multivariable-limits.html:26` で、開円板と内点の両方に「正の半径」が入りました。
  - `\\wsl.localhost\Ubuntu\home\kazumasa\projects\analytics\math_foundations\chapters\total-derivative.html` の定数 C の添字は、全9か所が `<sub>A</sub>` と `<sub>B</sub>` に統一されました。
  - 負号の切れ：非正方形の図は left 82、目盛りの文字端 71 になりました。私の環境のヘッドレス Chromium で、経路実験の97状態すべてで文字が図の枠からはみ出さないことを確認しました。
- **任意改善3点（採用を確認）：**
  - 経路実験の現在点は橙の塗りつぶしになり、原点の点はその上に描かれます。白抜きの点は、線形近似実験の σ = 0（極限0）だけです。
  - 「h = k ≠ 0 で2本の曲線が重なる」という注記は数学的に正しいです。上限と余りの差は (h − k)²/2 なので、等号は h = k のときだけ成り立ちます。
  - 丸め誤差の注記も、両方の実験に入っています。
- **文言の任意修正（1点・凍結を止めるものではありません）：** 線形近似実験の注記は「初期状態の差0.03は…数値欄と第二図で確かめてください」となっています。しかし第二図に出るのは差の0.03ではなく、距離で割った比 0.03/√0.05 ≈ 0.134 です。「第二図では距離で割った比として」と添えると誤読を防げます。

### 実行した確認
- テストは Python 5/5、Node 36/36 で通りました。scratchpad で27ページ（2,522,880バイト）を生成しました。
- ヘッドレス Chromium で、経路実験97状態と線形近似実験243状態を操作しました。
  - NaN と、枠からはみ出す線・文字はありませんでした。
  - 出力の線が t = 0 をまたぐ箇所は0件で、リセットも正常です。
- 確認の開始時（15:15）と終了時（15:16）で、対象ファイルに変化はありません。ファイルは編集していません。

### 『未解決の重要指摘』：なし