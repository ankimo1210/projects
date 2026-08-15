# Portfolio Analyzer

複数口座のポジションを1つにまとめ、資産配分・集中度・通貨・セクター・感応度・PERを確認する
ローカル専用ダッシュボードです。個人データを外部サービスへ送らず、自己完結した HTML を生成します。

## 現在できること

- 口座別・資産クラス別・通貨別の配分
- 口座損益、逆算元本、元本比損益率と照合メモ
- 現金比率、外貨比率、最大ポジション、実効ポジション数
- 口座で絞り込める保有明細、取得価額、現地通貨損益
- 3つの仮定シナリオによる評価額インパクト
- ETF・バランスファンドを内部構成へ展開したセクター・発行体分解
- HHIの逆数による実効ポジション数・実効セクター数
- 市場βを使う単一要因・複合ショック感応度と商品別の寄与
- 実績・予想・提供会社基準に分離したPERと各カバー率
- 暫定投資方針の上限・下限チェック
- JSONの売買案を使った変更前後の配分・感応度・PER比較
- 確定値・推定値・残高調整の区別
- 数量×価格×為替、口座残高と明細合計の自動照合

> このアプリは分析補助であり、投資助言や売買推奨ではありません。価格・為替・分類は入力時点の
> スナップショットです。

## すぐに見る

```bash
cd /home/kazumasa/projects
uv run --package portfolio-analyzer python portfolio-analyzer/scripts/build_dashboard.py
```

記録済みのリバランス案も比較する場合:

```bash
uv run --package portfolio-analyzer python portfolio-analyzer/scripts/build_dashboard.py \
  --proposal portfolio-analyzer/data/rebalancing-proposal.private.json
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

### 口座損益

口座損益が入力されている場合、`逆算元本 = 評価額 - 口座損益`、
`元本比損益率 = 口座損益 / 逆算元本` を表示します。算術的に一致していても、
商品別明細を確認していない場合は照合メモに残します。

### セクター分解

ETFとハッピーエイジング40は、運用会社の公式資料の構成比で内部の広義セクターへ展開します。
「セクター分類率」は、セクターとして展開した評価額のうち、個別の広義分類を付けられた割合です。
「実効セクター数」は総資産比で計算したHHIの逆数です。発行体分解は公表された上位構成銘柄だけを
別軸で集計し、セクター金額には加算しません。

### ファクター感応度

各行は他の条件を固定した線形近似です。シナリオ $s$ の評価額変化は次で計算します。

$$
\Delta V_s = \sum_i V_i \sum_f \beta_{i,f} s_f
$$

$V_i$ は商品の評価額、$\beta_{i,f}$ は商品 $i$ のファクター $f$ への感応度、$s_f$ は仮定した変化率です。
市場βは2023-08-15〜2026-08-14の3年週次収益率を基本とし、国内株は1306、米国ETFはSPYを
市場代理として `quantkit` のyfinanceフォールバックで推定しました。低相関商品のβは不安定です。
金利は修正デュレーションの一次近似で、`+100bp = +0.01`とします。

`株式全体` と `日本株` / `海外株` は同時投入を禁止し、IT・エネルギーは市場変動への追加ショック
として扱います。複合シナリオは単純加算なので、予測、VaR、最大損失ではありません。

### PER

PERは実績、予想、提供会社基準を混ぜず、同じ区分内だけで評価額加重調和平均します。

$$
\mathrm{PER}_{portfolio} = \frac{\sum_i V_i}{\sum_i V_i / \mathrm{PER}_i}
$$

区分をまたぐ単一の「ポートフォリオPER」は表示しません。必ず「基準」「基準日」「鮮度」と
区分別カバー率を併読します。
債券、現金、REIT、PERを取得できないファンド部分は集計外です。

## データを更新する

実データは次の2ファイルに保存します。どちらも Git の対象外です。

| ファイル | 内容 | 公開用サンプル |
|---|---|---|
| `data/portfolio.private.json` | 口座・保有明細・評価額 | `data/portfolio.example.json` |
| `data/analysis_reference.private.json` | セクター・発行体、ファクター、PER、方針、出典 | `data/analysis_reference.example.json` |
| `data/rebalancing-proposal.private.json` | 売買数量と固定価格による比較案 | `data/rebalancing-proposal.example.json` |

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
  --reference /path/to/analysis-reference.json \
  --proposal /path/to/rebalancing-proposal.json
```

基本配分と簡易ストレスだけを生成する場合は `--no-analysis-reference` を付けます。

## リバランス案を記録する

[`docs/rebalancing-note-template.md`](docs/rebalancing-note-template.md) を使い、判断理由、
変更量、変更前後の感応度、税・手数料の未反映事項、実行前チェックを残します。実際の銘柄数・
残高を含むノートは `data/rebalancing-note.private.md` に保存してください。このファイルは
Git の対象外です。売買案JSONは発注せず、同一口座の円現金へ売買代金を自動振替した比較だけを作ります。

```bash
cp portfolio-analyzer/docs/rebalancing-note-template.md \
  portfolio-analyzer/data/rebalancing-note.private.md
```

## 検証

```bash
cd /home/kazumasa/projects
uv run --no-sync pytest portfolio-analyzer/tests
uv run --no-sync ruff check portfolio-analyzer
```

## データ上の注意

初期スナップショットにはスクリーンショットから転記・推定した情報があります。特に次は更新候補です。

- 海外口座の米国 ETF 3銘柄は、口座の証券評価額に一致するよう共通為替レートを逆算
- 海外口座は現金口座・基準通貨JPYで、円現金を明細確認済み
- 海外口座には、純資産と「証券 + 現金」の差額を残高調整として計上
- DC口座の評価額と口座損益は算術的に整合。商品別の元画面は未照合
- SMHの平均取得価額は非公開データへ入力済み。ただし日本の税務に必要な円換算取得原価・税区分は未確認
- ETF・ファンドのセクター構成は基準日時点の公表値で、現在の実時間構成ではない
- QQQのPERは2026年3月末値を「推定」、SMHは2026年7月末の公式値を「現行」として扱う
- 株式市場βは3年週次推定。為替感応度とJ-REITの金利デュレーションは暫定仮定
- 相関の変化、非線形性、流動性、税・手数料は未反映
- 6857などSMH以外の取得原価、配当、税・手数料、過去推移は未入力

## 構成

```text
portfolio-analyzer/
├── data/
│   ├── portfolio.example.json   # 架空サンプル（Git管理）
│   ├── portfolio.private.json   # 個人データ（Git対象外）
│   ├── analysis_reference.example.json
│   ├── analysis_reference.private.json
│   ├── rebalancing-proposal.example.json
│   ├── rebalancing-proposal.private.json
│   └── rebalancing-note.private.md
├── docs/
│   └── rebalancing-note-template.md
├── scripts/build_dashboard.py
├── src/portfolio_analyzer/core.py
├── tests/test_core.py
└── dist/                        # 生成物（Git対象外）
```
