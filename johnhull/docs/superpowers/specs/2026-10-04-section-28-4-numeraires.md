# M29 §28.4 Numeraire Choices

日付2026-10-04。M28 main受入後にP3を3/37から4/37へ進める。P3全37節を完了する目標を保持。原典pp.676–679、詳細12要件はdocs/prep/design/M29_NUMERAIRE_SOURCE_DESIGN_2026-10-04.md。元資料の印刷価格例はない。

## 仕様

式28.16–28.25と脚注5/6、money-market accountとQの確率割引、満期T債券とT-forward価格、futures Q平均とforward T平均、term fixing Tと支払T*、overnight realized T*、annuity測度とprojection V/OIS Aをすべて実装/説明/独立検証/図/配布画面へ接続する。合成市場を原典印刷値と称さない。

HW stateはQ zero-mean OU x、r=x+phi。既存hw_discount_bondが落としている-B*c(t)を条件付きintegralとQ towerの独立REDで確認して修正する。既存の公開signatureとstate定義を保持し、契約外のforward-centered stateへ定義を黙って変更しない。既存Jamshidian/ZCB optionとの整合と影響を検査する。

Gaussian state/integrated rateをexact covarianceで構成し、区間ごとのjoint moments/条件付きstate、sigma=0、負rate、PSD/correlation、同時刻、finite real/temporal型拒否を明示。追加計算はprivate module、依存追加なし。

同じ給付をQのpath discountとT-forwardのtilted Gaussianで解析/求積/非正規化直接MC照合。多時刻/状態、term payment measure、overnight rate、annuityのbond mixtureと2曲線を保持。定数金利とfutures=forwardの極限も検査。

## 工程

1. HW条件付きbond/towerの独立RED→GREEN、source参照とprivate joint Gaussian APIs/数値gate（型・単位・境界・実API変異・wrongmeasure/denominator controls）。
2. 6C六小節/4共有図へ12source要件を割当、旧246source/output/Plotly保持・fresh全文・消費結果hash/shape/statistics。
3. Book/portal4cards/件数/16states/MathJax/700px、共有CSSを再利用できる範囲で既存規約を守る。
4. 旧28D1/両保管庫、MTではなくNC01–NC06の5軸台帳29/277・P3 4/37、全suite/1freshreview/重要修正RED→GREEN/main統合push。残33節を継続。

詳細API/fixture interfaceと許容差は独立参照設計のpre-flightで確定し、計画へ記録する。未完原典/短期金利木/Bermudan/LMMを本節の簡易モデルで完了としない。
