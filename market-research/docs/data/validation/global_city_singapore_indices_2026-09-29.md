# シンガポール非土地付き住宅：地域別価格・賃料指数

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

更新: 2026-09-29。対象: 2004年第1四半期〜2026年第2四半期、90四半期×3地域。

## 結果

[URAの地域別価格指数](https://data.gov.sg/datasets/d_f65e490a8ad430f60a9a3d9df2bff2a0/view)と[SingStat掲載のURA賃料指数](https://data.gov.sg/datasets/d_56b0c7f6538be69f24956634d88d82e8/view)を政府公開APIから取得。どちらも非土地付き民間住宅のCore Central Region（CCR）、Rest of Central Region（RCR）、Outside Central Region（OCR）を対象に、四半期と地域を一致させた。両指数を2015Q1=100に換算し、

\[
\text{相対的な価格／賃料指数}_t
= 100\frac{P_t/P_{2015Q1}}{R_t/R_{2015Q1}}
\]

を計算した。100超は基準期以降に価格指数が賃料指数より速く上がったことを意味する。

| 地域 | 2015Q1→2026Q2 価格指数 | 同・賃料指数 | 2026Q2 相対価格／賃料指数 |
|---|---:|---:|---:|
| CCR | +22.9% | +38.1% | 89.0 |
| RCR | +57.0% | +51.8% | 103.4 |
| OCR | +65.5% | +49.3% | 110.9 |

つまり、2015年初から2026年半ばにかけてCCRでは賃料の伸びが価格を上回り、OCRでは価格の伸びが賃料を上回った。**この指数は表面利回りでもNOI利回りでもない。** 実際の売買価格と同じ物件の家賃を対応させておらず、絶対利回りの水準や将来収益は計算できない。指数は名目で、通貨・インフレ調整もしていない。

## データ品質・定義

- 価格APIは縦型270行、賃料APIは横型3行を読取。3地域×90四半期の270セルが一対一に一致し、欠損・重複はない。価格・賃料の原本と加工CSVのSHA-256を保存した。
- [SingStatの注記](https://data.gov.sg/datasets/d_56b0c7f6538be69f24956634d88d82e8/view)では、賃料指数は2015Q1以降、物件の築年・面積等を調整する層別ヘドニック法で計算される。2015年以前を同一方法の連続系列と断定しない。上表の変化率は2015Q1を起点にした。
- 価格と家賃は非土地付き住宅・同じ地域区分だが、取引と契約の標本や物件構成が完全に同じとは限らない。個別の一棟賃貸住宅のNOI、運営費、空室、取得時Cap Rateは両原本にない。
- [data.gov.sgのAPI](https://guide.data.gov.sg/developer-guide/api-overview)は試験利用ならキー不要。原本のライセンスは両データセットのページでOpen Data Licenceと表示される。APIの本番利用条件・制限は運用前に再確認する。

## 再現

- コード: `scripts/analysis/global_city_singapore_indices.py`。`.venv/bin/python scripts/analysis/global_city_singapore_indices.py` で保存原本から再生成。初回のみ `--download`。
- 原本と取得URL・ハッシュ: `data/market/raw/global_city_pilot/singapore_indices_20260929/` の `price.json`、`rent.json`、`manifest.json`。
- 加工: `data/market/processed/global_city_pilot/singapore_indices_20260929/locality_price_rent_indices.csv`、`quality.json`。CSVのSHA-256: `7407b6ff2b905b34b265aacf87cddbb17645ffd04c462617e0dc49741c986005`。
- worktree内の `data` はシンボリックリンク。WindowsからCSVを開く場合は `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os\data\market\processed\global_city_pilot\singapore_indices_20260929\locality_price_rent_indices.csv`。
