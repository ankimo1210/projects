# data/

教材で使う小さなサンプルデータ。すべて `bayes_textbook.simulation.write_sample_csvs()`
で seed 固定により再生成できる(外部 API・ダウンロード依存なし)。

| ファイル | 内容 | 生成元 |
|---|---|---|
| `ab_test.csv` | A/B テストのバリアント別訪問数・コンバージョン数 | `make_ab_test_data(seed=8)` |
| `store_conversions.csv` | 店舗別の訪問数・CV 数・真の CVR(階層ベイズ用) | `make_store_conversions(seed=42)` |

再生成:

```bash
uv run python -c "from bayes_textbook.simulation import write_sample_csvs; write_sample_csvs()"
```
