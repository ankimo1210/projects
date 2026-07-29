# genequest

Genequest の健康リスク・体質一覧と各項目の詳細を、個人利用のためローカルに
保存するプロジェクトです。

## データ

`data/` には次のスナップショットを保存します。

| ファイル | 内容 |
|---|---|
| `health_risks.csv` | 表計算向けのフラットデータ。疾患名、リスク、遺伝子型要約、詳細本文を含む |
| `health_risks.json` | セクション、表、関連リンク、構造化マーカーを保持したデータ |
| `health_risks.md` | 遺伝子型表を含む、人が読みやすいMarkdown版 |
| `genotypes.csv` | 疾患 × SNPマーカー単位の本人遺伝子型、効果、頻度、研究情報 |
| `genotype_verification.json` | Genequest現在表示との全件照合結果 |
| `manifest.json` | 取得日時、件数、カテゴリ別件数、ファイルハッシュ |
| `traits.csv` | 体質254項目の結果、カテゴリ、信頼性、遺伝子型要約 |
| `traits.json` | 体質の詳細本文、表、リンク、PGS、構造化マーカー |
| `traits.md` | 体質結果とマーカーを確認しやすいMarkdown版 |
| `trait_genotypes.csv` | 体質 × SNPマーカー単位の本人遺伝子型と対応タイプ |
| `traits_verification.json` | 体質一覧・カテゴリ・詳細ページの全件照合結果 |
| `traits_manifest.json` | 体質スナップショットの件数とファイルハッシュ |
| `ancestor.csv` | 母系ハプログループ、サブグループ、起源・分布の要約 |
| `ancestor.json` | 祖先解析5ページの本文・画像URL・構造化した移動経路と分布 |
| `ancestor.md` | 祖先解析結果と解釈を確認しやすいMarkdown版 |
| `ancestor_journey.csv` | Genequestに表示された母系祖先の移動経路 |
| `ancestor_regions.csv` | 本人のハプログループに対応する国内地域別ランキング |
| `ancestor_haplogroups.csv` | Genequestが掲載する23ハプログループ |
| `ancestor_verification.json` | 本人のグループ・サブグループと各ページの照合結果 |
| `ancestor_manifest.json` | 祖先解析スナップショットの件数とファイルハッシュ |

取得元:

- <https://genequest.jp/healthrisk/risknumber/>
- 各項目の Genequest 詳細ページ
- <https://genequest.jp/traits/>
- <https://genequest.jp/traits/risknumber/>
- 各体質項目の Genequest 詳細ページ
- <https://genequest.jp/ancestor/>
- <https://genequest.jp/ancestor/group/>
- Genequestのハプログループ一覧、本人のグループ公開ページ、解析方法ページ

## データ構造

個人値を含む実データはGit管理外とし、構造だけを以下に記録します。

```text
data/
├── health_risks.json         # HealthRisk[]（健康リスク1項目につき1レコード）
│   └── markers[]             # SNPごとの本人遺伝子型・効果・研究情報
├── traits.json               # Trait[]（体質1項目につき1レコード）
│   └── markers[]             # SNPごとの本人遺伝子型・効果・研究情報
├── ancestor.json             # 祖先解析全体を表す単一オブジェクト
│   ├── result                # ハプログループとサブグループ
│   ├── journey[]             # 母系祖先の移動経路
│   ├── regional_rankings[]   # 国内地域別分布
│   └── haplogroup_catalog[]  # Genequest掲載グループ
├── *_verification.json       # 表示元との照合結果・欠損・不一致
└── *_manifest.json           # 件数、取得日時、取得元、SHA-256
```

健康リスクと体質のJSONは、概ね次のフィールド群で構成します。

| フィールド群 | 主な内容 |
|---|---|
| 識別 | `id`、`index`、項目名、カテゴリ |
| 結果 | リスク値・リスク表現、または体質結果・PGSスコア |
| エビデンス | `reliability`、`asian_evidence`、研究集団、文献 |
| 遺伝子型 | `markers[].snp`、`genotype`、`effect`、頻度、選択肢 |
| 詳細 | 説明本文、セクション、表、関連リンク |
| 由来・検証 | 取得元URL、取得日時、遺伝子型取得状態、照合結果 |

CSVはJSONを確認・集計しやすくした派生形式です。`health_risks.csv`と
`traits.csv`が項目単位、`genotypes.csv`と`trait_genotypes.csv`が
1項目対複数SNPのマーカー単位です。祖先解析も結果、移動経路、地域分布、
ハプログループ一覧に分けています。

## プライバシー

このデータには個人の遺伝・健康リスク情報が含まれます。`data/` の生成物は
`.gitignore` 対象であり、Gitへコミットしません。外部共有やクラウド同期を行う前に、
保存先と共有範囲を必ず確認してください。

## 検証

リポジトリルートから次を実行します。

```bash
python3 genequest/scripts/validate_snapshot.py
python3 genequest/scripts/validate_traits_snapshot.py
python3 genequest/scripts/validate_ancestor_snapshot.py
```

検証では、JSON/CSV/manifestの件数一致、IDの一意性、必須項目、詳細本文、
本人遺伝子型とSNP・効果表の対応、PGS/データなしの扱い、SHA-256ハッシュを
確認します。

体質スナップショットでは、254項目すべてのGenequest表示元、詳細URL、
項目名、信頼性、アジア系集団での研究有無、結果、選択済みマーカー行を照合します。
PGSの2項目は個別SNPを持たない方式として、データなしの項目は欠損として区別します。

## 分析レポート

`report/traits_analysis.html` は、カテゴリ別件数、信頼性、アジア系研究の有無、
PGS、複数項目で共有されるSNP、注目結果、欠損をまとめたローカルHTMLレポートです。
`report/ancestor_analysis.html` は、本人のグループ・サブグループ、母系祖先の
移動経路、国内分布、解析範囲と不確実性をまとめたローカルHTMLレポートです。
レポートも個人の遺伝情報を含むため、`data/` と同様にGitへコミットしません。

## 注意

保存内容は取得時点の統計的な遺伝子解析結果であり、疾患の診断ではありません。
診断、治療、服薬、検査については医療機関へ相談してください。
祖先解析はミトコンドリアDNAによる母系1系統の分類であり、父系、常染色体由来の
祖先構成、民族比率、国籍を示すものではありません。
