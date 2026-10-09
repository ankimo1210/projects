# 計時に使ったsource

`measure-loading-2026-10-09.py.txt` は100回のwarm-cache NPZ読み込みと34モデルdecodeを測った版。
自己digestを計測記録に残し、format修正前に同じbytesを保管した。
測定対象は計時配列追加後・load配列追加前のbundleで、そのSHA/bytesを`loading.input_npz`に記録する。
後の検査・費用集計コードと、実際に計ったコードを区別する。

2026-10-09の本計時プロセスが読み込んだ`benchmark.py`を、`.py.txt`として保持する。
実行中にmeasurement registryの検査を補強したため、計時版と現行検査版を区別する。
このファイルは履歴資料で、通常の実行入口ではない。

- ファイル：`benchmark-2026-10-09.py.txt`（20,490 bytes）
- SHA-256：`cfbddf68f85901c6a9b8f65fd32a870273abf3155340605969768e07d34dc3c0`
- 保持の方法：修正前に取得したsource全文から保存し、同じプロセスが継続稼働している間に照合した。
- 金融teacher/hedge、`_quote_risk.py`、CPU学習moduleは`b5fc6e85`以降不変であることをGit差分で確認した。

生成時の`record.sources`を現行sourceのSHAへ置き換えない。
fit、計時、検査・教材のphaseを分け、事後照合した情報は事後照合と記録する。
SHAは出典と保存物の同一性を示す。価格・Greekの正しさは独立数値照合で検査する。
