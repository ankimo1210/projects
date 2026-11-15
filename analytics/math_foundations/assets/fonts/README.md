# Latin Modern Math

数学本文の字体を、TeXのComputer Modern系であるLatin Modern Mathに統一するための同梱フォント。バージョン1.959（2014-09-05）、作者B. Jackowski / P. Strzelczyk / P. Pianowski。

- 配布元：[CTAN lm-math](https://ctan.org/pkg/lm-math)
- 取得元：https://mirrors.ctan.org/fonts/lm-math.zip
- 原本：lm-math/opentype/latinmodern-math.otf（733,736 bytes）
- SHA-256：6075562b771f8b82f0c179e363389684f2dd09de30038269e2628e504bd7be0f
- ライセンス：同梱のGUST-FONT-LICENSE.txt、上流README-Latin-Modern-Math.txtを参照。

フォントの字形・MATHテーブルを含む元ファイルは無改変。生成時に元バイト列とライセンスを各HTMLのCSSへ埋め込む。利用者のフォントインストール・CDN・外部通信・追加JavaScriptは不要。フォントを持ち運べる分、生成HTMLは1ページにつき約0.93MiB増える。

MathMLのカッコは、生成処理で対応する部分だけをmrowにまとめる。通常のカッコには stretchy="false" を追加し、字体本来の幅と高さで表示する。行列・分数・根号・大型演算子を含むカッコは内容に応じて伸ばす。絶対値とノルムは同じ括弧範囲内に偶数本あるものだけ対応付け、条件付き確率などの単独の棒は対にしない。元の章HTMLは書き換えない。根拠：[MathML Coreのmrowと伸縮規則](https://www.w3.org/TR/mathml-core/#horizontally-group-sub-expressions-mrow)。

上流ライセンスとREADMEも原本のbyte列を保持するため、この2ファイルだけpre-commitの空白整形から除外する。

取得・検証日：2026-11-09。
