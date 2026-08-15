# Portfolio Analyzer

複数口座のポジションを1つにまとめ、資産配分・集中度・通貨・セクター・感応度・PERを確認する
ローカル専用ダッシュボードです。個人データを外部サービスへ送らず、自己完結した HTML を生成します。

## 現在できること

- 口座別・資産クラス別・通貨別の配分
- 現金比率、外貨比率、最大ポジション、上位5ポジション集中度
- 口座で絞り込める保有明細
- 3つの仮定シナリオによる評価額インパクト
- ETF・バランスファンドを内部構成へ展開したセクター分解
- 株式、日本/海外株、IT、エネルギー、不動産、為替、金利の1ファクター感応度
- 保有商品別PER、PERカバー率、参考・混在基準PER
- 確定値・推定値・残高調整の区別
- 口座残高と明細合計の自動照合

> このアプリは分析補助であり、投資助言や売買推奨ではありません。価格・為替・分類は入力時点の
> スナップショットです。

## すぐに見る

```bash
cd /home/kazumasa/projects
uv run --package portfolio-analyzer python portfolio-analyzer/scripts/build_dashboard.py
```

生成後、次のファイルをブラウザで開きます。

```text
/home/kazumasa/projects/portfolio-analyzer/dist/portfolio-dashboard.html
```

ローカル HTTP で開く場合:

```bash
cd /home/kazumasa/projects/portfolio-analyzer/dist
python3 -m http.server 8765
```

その後 <http://localhost:8765/portfolio-dashboard.html> を開きます。

## 分析の読み方

### セクター分解

ETFとハッピーエイジング40は、運用会社の公式資料の構成比で内部の広義セクターへ展開します。
「セクター分類率」は、セクターとして展開した評価額のうち、個別の広義分類を付けられた割合です。

### 1ファクター感応度

各行は他の条件を固定した線形近似です。シナリオ $s$ の評価額変化は次で計算します。

$$
\Delta V_s = \sum_i V_i \sum_f \beta_{i,f} s_f
$$

$V_i$ は商品の評価額、$\beta_{i,f}$ は商品 $i$ のファクター $f$ への感応度、$s_f$ は仮定した変化率です。
金利は修正デュレーションの一次近似で、`+100bp = +0.01`とします。これは予測、VaR、最大損失ではありません。

### PER

「参考・混在基準PER」は、PERを取得できた実効株式部分の評価額加重調和平均です。

$$
\mathrm{PER}_{portfolio} = \frac{\sum_i V_i}{\sum_i V_i / \mathrm{PER}_i}
$$

会社予想PER、ETF提供会社のポートフォリオPER、古い参照値が混在するため、必ず「基準」「基準日」「鮮度」とカバー率を併読します。
債券、現金、REIT、PERを取得できないファンド部分は集計外です。

## データを更新する

実データは次の2ファイルに保存します。どちらも Git の対象外です。

| ファイル | 内容 | 公開用サンプル |
|---|---|---|
| `data/portfolio.private.json` | 口座・保有明細・評価額 | `data/portfolio.example.json` |
| `data/analysis_reference.private.json` | セクター構成、ファクター感応度、PER、出典 | `data/analysis_reference.example.json` |

各保有明細の `value_status` は次のいずれかです。

| 値 | 意味 |
|---|---|
| `exact` | 画面または正式な明細で評価額を確認済み |
| `estimated` | 数量・価格・口座合計などから推定 |
| `reconciliation` | 口座合計に合わせるための未分類差額 |

更新後はビルドを再実行します。別ファイルを使う場合:

```bash
uv run --package portfolio-analyzer python portfolio-analyzer/scripts/build_dashboard.py \
  --input /path/to/portfolio.json \
  --reference /path/to/analysis-reference.json
```

基本配分と簡易ストレスだけを生成する場合は `--no-analysis-reference` を付けます。

## 検証

```bash
cd /home/kazumasa/projects
uv run --no-sync pytest portfolio-analyzer/tests
uv run --no-sync ruff check portfolio-analyzer
```

## データ上の注意

初期スナップショットにはスクリーンショットから転記・推定した情報があります。特に次は更新候補です。

- 海外口座の米国 ETF 3銘柄は、口座の証券評価額に一致するよう共通為替レートを逆算
- 海外口座には、純資産と「証券 + 現金」の差額を残高調整として計上
- DC口座は画面内の損益表示同士に不一致があり、評価額だけを配分分析に使用
- ETF・ファンドのセクター構成は基準日時点の公表値で、現在の実時間構成ではない
- QQQとSMHのPER参照値は古いため、「要更新」として現行PERカバー率から除外
- 感応度は単一要因の線形近似。相関、ボラティリティ変化、凸性、流動性、税・手数料は未反映
- 取得原価・配当・税・手数料・過去推移は未入力

## 構成

```text
portfolio-analyzer/
├── data/
│   ├── portfolio.example.json   # 架空サンプル（Git管理）
│   ├── portfolio.private.json   # 個人データ（Git対象外）
│   ├── analysis_reference.example.json
│   └── analysis_reference.private.json
├── scripts/build_dashboard.py
├── src/portfolio_analyzer/core.py
├── tests/test_core.py
└── dist/                        # 生成物（Git対象外）
```
