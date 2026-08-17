# SOURCES — 生スナップショットの manifest

`_data/sources/` は gitignore されている（統計の再配布を避けるため）。参照 TOML を
別 clone で再生成するには、下の URL から取り直したファイルがここに記録した
SHA-256 と一致することを確認する。

再生成と突合:

```bash
uv run python labor_ai_quadrant/tools/source_manifest.py --check   # 手元の生ファイルを突合
uv run python labor_ai_quadrant/tools/build_reference.py           # reference/*.toml を再生成
uv run --no-sync pytest labor_ai_quadrant/tests -q                 # 117 tests
```

**URL が同じでも中身は変わる。** e-Stat の `file-download?statInfId=` と日銀の
`co.zip` は更新のたびに同じ URL で別の中身を返す。だから URL ではなく checksum を
正本にしている。値が変わっていた場合は、参照 TOML を作り直して差分を見ること
（黙って新しい vintage を混ぜないため）。


| ファイル | バイト | SHA-256 | 取得日 | 出典 URL |
|---|---:|---|---|---|
| `boj_tankan_co.csv` | 1,924,048 | `c70005c8b836832a8509bbe4006e38b9fa3bebb6a06fc39ee58849945a2a6c82` | 2026-08-17 | https://www.stat-search.boj.or.jp/info/co.zip |
| `boj_tankan_code.html` | 37,700 | `0e21cda983609ca8d6f453fd4868283989f7c12c3d3f60cb8bd79f1ee579b5b9` | 2026-08-17 | https://www.stat-search.boj.or.jp/info/tankan_code.html |
| `estat_lfs_2_5_1_2025.json` | 488,335 | `2bffdf44711eae48a7ee01460dd60f3d8d0cdc0dd7fe9b5e8fb4a11295a4962e` | 2026-08-17 | e-Stat statsDataId=0003024266（労働力調査 表2-5-1 産業，職業別就業者数） |
| `estat_lfs_age_industry_2025.json` | 185,060 | `e5b8523a0d6ffb2f21641d9904b9145bb56f8de9d6b612614eed9dfe6476c6e0` | 2026-08-17 | e-Stat statsDataId=0003007108（労働力調査 年齢階級，産業別就業者数） |
| `ilo_wp140_scores.xlsx` | 2,598,951 | `c1940b87e7293b1eb95b530b6d3da7cd806b61d217c4bff1e69372b2cff5c90a` | 2026-08-17 | https://github.com/pgmyrek/2025_GenAI_scores_ISCO08 |
| `koyou_doukou_r7_zuhyo.xlsx` | 803,701 | `9619302298c0d59fbc0cd079ead19da917010d4bc08b8c8b0f6c39d6871e6d15` | 2026-08-17 | https://www.mhlw.go.jp/toukei/itiran/roudou/koyou/doukou/26-1/dl/zuhyo.xlsx |
| `mhlw_occupation_market_r8_06.xlsx` | 636,625 | `e9e641e69cb0dc546338f1fb8462113def9b3f4fde01f1e8886874d9bed6374e` | 2026-08-17 | https://www.e-stat.go.jp/stat-search/file-download?&statInfId=000040478179&fileKind=0 |
| `mkt_jissu.csv` | 20,803,425 | `162449609b9fa2a061c8fec671e57fd3eda2a42cd9a707accebcb1b25ae3df9b` | 2026-08-17 | https://www.e-stat.go.jp/stat-search/file-download?&statInfId=000032189776&fileKind=1 |
