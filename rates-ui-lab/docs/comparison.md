# Rates UI 比較

2026-09-06。元の OSS Dashboard と同じ色・書体・角丸を保ち、金利データに置換して確認した。

## 初回の判断

**数値を素早く確認するなら Template、直近の流れを合わせて見るなら Blocks が使いやすい。** 共通のカーブと表は維持し、カードとフィルターだけでも操作感を比較できた。

これは今回の実装を操作・観察した所感であり、ユーザーテストや定量的な効率評価ではない。

| 観点 | Template | Blocks |
|---|---|---|
| 情報密度 | KPI の値と前営業日比をコンパクトに確認できる | 同じ値に最大30観測日の Spark Chart が加わる |
| 比較日の操作 | 基準日・比較日をそれぞれ選択 | 同じ選択欄に前営業日/5/20観測日前のボタンが加わる |
| 見た目の差 | 余白が少なくチャートと表に早く到達する | KPI の推移が目に入り、ページは縦に長くなる |
| 狭い画面 | 日付欄・KPI・チャートを縦に並べる | 同様に縦並び。推移付きカードが4枚なのでスクロール量が増える |
| 共通条件 | 同じ基準日・比較日・データ・計算・カーブ・表 | 左と同じ。切替時も選択年限、凡例、表ソートを保持 |

## 画面

元画面は元の SaaS データ、金利2案は `jgb-demo.json` の同じ最終観測日を使用する。幅 1440 / 1280 / 390 px と light/dark の各条件で撮影した。

| 比較画像 | light 1440 | dark 1440 | light 390 |
|---|---|---|---|
| 元の Dashboard | [画像](screenshots/baseline-light-1440.png) | [画像](screenshots/baseline-dark-1440.png) | [画像](screenshots/baseline-light-390.png) |
| Template | [画像](screenshots/template-light-1440.png) | [画像](screenshots/template-dark-1440.png) | [画像](screenshots/template-light-390.png) |
| Blocks | [画像](screenshots/blocks-light-1440.png) | [画像](screenshots/blocks-dark-1440.png) | [画像](screenshots/blocks-light-390.png) |
| 21st.dev sample | [画像](screenshots/21st-overview-light-1440.png) | [画像](screenshots/21st-overview-dark-1440.png) | [画像](screenshots/21st-overview-light-390.png) |
| Massive data | [画像](screenshots/21st-massive-1m-light-1440.png) | — | [画像](screenshots/21st-massive-dark-390.png) |
| Prism Hero | [画像](screenshots/21st-prism-light-1440.png) | — | [画像](screenshots/21st-prism-light-390.png) |
| Meshyflix study | [画像](screenshots/meshy-desktop-1440.png) | — | [画像](screenshots/meshy-mobile-390.png) |

残りの画像も `screenshots/` に同じ命名規則で保存している。

## 使いたい部品・調整が必要な部分

- **採用候補:** KPI Card 1 / 14、ラベル付き Select、期間のボタングループ、Card と SparkChart。既存依存の範囲で組み込めた。
- **カーブ:** 元の LineChart へ年限の文字列を渡すだけでは実際の年限間隔を表せないため、既存 Recharts で数値軸の専用コンポーネントを作った。
- **比較色:** 元の SaaS 用の増減率・成功/失敗の色は金利の意味と異なる。%/bp と上昇/低下の表記に置き換えた。
- **フィルター:** Blocks 4 の期間ボタンは見た目の例なので、日付変更・選択状態・disabled・aria-pressed を追加した。
- **モバイル:** 当初、Flex の縮小によって日付欄が26pxまで狭まった。画像確認で検出し、640px未満では日付欄を全幅の縦並びに変更。横溢れだけでなく入力欄の最小幅もテストする。
- **表:** デスクトップは4列を一覧できる。390pxでは表内だけ横スクロールし、年限と利回りを先に確認できる。列数が増える RV 表には別途の密度調整が必要。
- **小さいカーブ:** 年限の実間隔を保つため短い年限の目盛りは重なり回避で一部省略される。観測点とツールチップ、表には7年限を保持する。

## 改造の範囲

元テンプレートの変更は7ファイル（package.json、lockfile、tsconfig、gitignore、RootLayout、desktop/mobile Sidebar）。このほか金利専用コンポーネント6本とルート、データ・計算・テストを追加した。Card と SparkChart は公式 Blocks から取り込んだ。

Stats Bento と Massive data までは追加の本番依存なしで実装した。Prism Hero では Three.js、React Three Fiber、Drei、Motion を追加した。全体の実行時間は目標管理の計測で約34分。UI案ごとの工数は未計測のため比較指標に使わない。

## 共通の比較課題

同じ JSON と以下の操作を使う。チャートエンジンを Recharts に揃え、主にシェル・ナビ・カード・フィルターの違いを比較する。

1. 2026-09-04 の 10Y、2s10s、5s30s を読み取る。
2. 比較日を5観測日前へ変更する。
3. 10Yを選び、表とカーブの対応を確認する。
4. 同じ選択状態で UI 案を切り替える。
5. 欠損と負金利のケース、390pxの画面、キーボード操作を確認する。

各実験で記録するものは、値の読みやすさ、操作の手数、スクロール量、必要な追加依存、修正量、使いたい部品と不満点。現段階の所感は実装の初見であり、ユーザーテストによる優劣評価ではない。

## 21st.dev sample の初見

Stats Bento の構成では、10Yを大きい主カード、2s10s / 5s30s / 30Yを補助カードにしたため、最初に読む値の順序が明確になった。Tremor Blocks は4指標を同格で比較しやすく、21st.dev sample は1つの主指標から入る用途に向く。

| 観点 | Tremor Blocks | 21st.dev Stats Bento study |
|---|---|---|
| 指標の階層 | 4指標を同じ大きさで横比較 | 10Yを大きく、スプレッドと30Yを補助に配置 |
| UI部品 | KPI / filter / chart / table が一式 | shell と card composition を選び、chart / table は手元で組む |
| チャート | 共通 Recharts | 共通 Recharts。追加ライブラリなし |
| 大量表示 | 60観測日・7年限の通常表 | 1万〜100万行、TypedArray、仮想スクロール |
| データ条件 | 固定 JSON と共通 view-model | Overview は同じ JSON / view-model、stress は決定的な実行時生成 |

21st.dev registry の source code は API key が必要なため取得していない。公開されている MIT の Stats Bento パターンを金利用に独自実装した比較であり、原コンポーネントの完全コピー比較ではない。

## Massive data の観察方法

100万行を選び、`Rows in memory`、`Worker generation`、`Typed payload`、`Initial DOM rows`を確認する。表の「50%地点へ移動」で約50万行目へ移動し、表示範囲が更新される。生成時間はブラウザと端末ごとに変わるため画面内の実測値を使い、固定の性能保証値にはしない。

## Prism Hero の初見

BEVEL UI の Prism Hero が持つ、背面の大きな文字を透明な立体で屈折させる構図を JGB の入口画面に翻案した。視線を集める効果は強い一方、数値比較の密度は Bento や Tremor の方が高い。分析画面そのものより、商品・シナリオ・レポートを選ぶランディング画面への適性が高い。

- デスクトップはポインターとスクロールでプリズムが回転し、10Y / 2s10s / 5s30s を最小限の補助情報として表示する。
- 390px では描画解像度と sampling を下げ、下部メタ情報を上部の小型カードへ移して CTA との重なりを避ける。
- 画面外では描画を停止し、OS の reduced motion 設定では静止表示にする。WebGL 初期化に失敗した場合は CSS の静止プリズムへ切り替える。
- 3Dコードは動的読込のため、Overview と Massive data の初期経路へ常時含めない。Prism を開いた時は Three.js 系の追加チャンクを読み込む。

## Meshyflix study の初見

黒・ライム色・半透明パネルの構成を、金利メッシュの検査画面へ応用した。60観測日×7年限の実際の合成値が面を決めるため、Prismの装飾的な立体と違い、ケース切替に応じて形状も変化する。数値の読み取りはKPIとCSV、形状の比較は立体と小型カーブで行う。

- Surface / Wireframe / Points と、ドラッグ回転・拡大縮小・リセット・任意の自動回転を試せる。
- 描画は操作時のみ。自動回転を有効にしたときだけ連続描画し、画面外・非表示タブでは停止する。OSの reduced motion では自動回転を無効にする。
- 4ケースで共通軸を使い、欠損セルは面を作らない。CSVには欠損を空欄として残す。
- デスクトップでは説明と3Dを左右に配置。390pxでは縦に並べ、ケースカードを2列、指標帯を2列へ折り返す。
- 100万行は Massive data へのリンクから引き続き比較できる。この3D画面が描画するのは最大420観測点で、100万頂点のGPU性能を検証する画面ではない。
