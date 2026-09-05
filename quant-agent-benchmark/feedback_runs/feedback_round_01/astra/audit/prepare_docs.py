from pathlib import Path
import json
R=Path(__file__).resolve().parent.parent
p=R/'submission/README.md'
s=p.read_text()
start=s.index('## 環境とインストール');end=s.index('## データと監査')
s=s[:start]+'''## 環境・実行方法

これは `feedback_round_01` の独立提出です。初回の数値推定、ノット、平滑化選択、Huber閾値、支払規約は維持しました。形式修正と割引関数による価格付けAPIの追加を数値精度の改善とは扱いません。改善ラウンドの測定結果は `reports/feedback_review.html` にあります。

実測環境は Python 3.12.11、NumPy 2.5.2、pandas 2.3.3、SciPy 1.18.1、Matplotlib 3.11.1、pytest 8.4.2、macOS arm64、BLAS 1スレッドです。承認済みPythonを `PYTHON_BIN` に指定します。このラウンドではパッケージの追加・更新・ネットワーク利用をしていません。`PYTHONPATH=src` で実行するためインストール不要です。

以下はこのプロジェクト直下で実行します。`PYTHON_BIN` と `RUNTIME_TMP` は実行者が指定します。このラウンドの一時出力は指定された `audit/` 内を使用しました。通常の独立実行では任意の書込み可能な一時ディレクトリを使用できます。

```bash
: "${PYTHON_BIN:?承認済み Python 3.12 の絶対パスを設定してください}"
: "${RUNTIME_TMP:?許可された一時ディレクトリの絶対パスを設定してください}"
source scripts/env.sh
PYTHONPATH=src "$PYTHON_BIN" -m pytest -q \\
  -o "cache_dir=$TMPDIR/pytest-cache" --basetemp "$TMPDIR/pytest-run"
PYTHONPATH=src "$PYTHON_BIN" -m quantcurve.cli run \\
  --market-data "$PWD/data/market_observations.csv" \\
  --output-dir "$PWD/outputs" \\
  --valuation-date 2026-01-15
PYTHONPATH=src "$PYTHON_BIN" scripts/run_example.py
```

`--market-data`、`--output-dir` は任意の絶対パスに変更できます。CLIは新しい出力先でも動き、以前の成果物を読みません。`run_example.py` は公開CSVでCLIと同じ処理を行い、自己完結HTMLを `reports/research_report.html` にも保存します。`audit/` や初回ディレクトリに実行時依存しません。

別のオフライン環境でパッケージとしてインストールする場合のコマンドです。このラウンドでは実行しておらず、共有の承認環境では実行しないでください。`WHEELHOUSE` は必要な依存物を含むローカル配布先です。

```bash
: "${WHEELHOUSE:?ローカル wheel 配布ディレクトリを設定してください}"
"$PYTHON_BIN" -m pip install --no-index --find-links "$WHEELHOUSE" -r requirements.lock
"$PYTHON_BIN" -m pip install --no-index --find-links "$WHEELHOUSE" .
```

`requirements.lock` は直接使用した数値・描画・テスト依存物の実測版です。推移依存や別OSの完全な環境再構築まで保証するものではありません。実際の版はCLIの `run_metadata.json` とラウンド監査の `environment.json` に記録します。

供給テストを維持し、単位、キャッシュフロー、負金利、解析Jacobian、リスク差分、CLI失敗応答、別データ、2つの空の出力先での全ファイルの一致を検証します。新しいAPIは `PricingEngine(frame).quote_from_discount(D)` です。`D` は指定時点と同じ形状の正の有限な割引因子を返します。

設定を変更する場合は `--config config/default.json` を追加します。CLIの平滑化は訓練内部の3分割で候補から選びます。比較JSONの `selected_model` が選択結果で、旧キー `model_selected` も互換性のため残しています。感度JSONは名前付き実験ごとに `conditions`、`numerical_results`、`interpretation` を持ちます。改善率は `(前−後)/前`、比較元0ならnullです。

''' + s[end:]
s=s.replace('外部の正解、過去の実行、別候補の成果物を利用していません。','初回の自分の提出物を比較元に使い、外部の正解・別候補の成果物は利用していません。')
s=s[:s.index('`logs/` はテスト')]+'''ラウンドの `audit/` には事前条件、全実験、分割ID、失敗を含む実行ログ、原本ハッシュ、図の点検結果を保存しています。これは研究履歴であり、提出CLIの依存物ではありません。`benchmark_summary.json` はこの改善ラウンドの実測値です。初回のサマリー・HTML・数値成果物は変更していません。

正確なトークン・クレジット・料金・割当消費量は取得できず、nullです。人工データの誤差は自作カーブに対する値であり、隠し採点の推定値ではありません。
'''
p.write_text(s)
(R/'submission/requirements.lock').write_text('numpy==2.5.2\npandas==2.3.3\nscipy==1.18.1\nmatplotlib==3.11.1\npytest==8.4.2\n')
p=R/'submission/MODEL_RISKS.md'
s=p.read_text()
s+='''\n## 改善ラウンドで確認した範囲\n\n数値設定を維持しました。自作20条件の平均長期ゼロRMSEは5.8356bp、平均長期フォワードRMSEは41.6469bpで、長期の山や低流動性条件の精度に弱さが残ります。平滑化を弱めた実験は長期平均ゼロRMSEを3.9156bpに減らしましたが、公開S2の短期OIS誤差を2.0274bpから9.1071bpへ悪化させ、不採用です。最終版で確認できた数値改善はありません。\n\n支払規約は独立価格式と照合しましたが、按分、端数利息なし、全額利息のどれが実際の生成規約かは確定していません。独立式との一致は隠し真値との一致を意味しません。OISの全脚頻度と期間途中の頻度変更という解釈差も監査し、観測属性を用いる既存の全脚頻度を維持します。\n\n複数の数値要因は合成していません。一要因の結果からノット・罰則・ロバスト重みの相互作用は推定しません。公開の単位補正は分割前に全テープを参照します。自作の人工条件は事前に固定しましたが、採用判断に使用した研究集合であり、別の確認用集合や時系列外検証ではありません。元のCLIのハイパーパラメータ選択まで含めた人工データ全条件の比較は未検証です。\n'''
p.write_text(s)
print('Prepared independent source-run instructions and round-specific limitations; no environment installation performed.')
