# QuantCurve

預金・パー OIS・利付債から、監査可能な連続複利ゼロカーブを推定する Python 3.12 プロジェクトです。入力データを改変せず、全観測の判断理由、単純モデルとの比較、感度分析、固定受取 DV01 を出力します。

**今回の結果は研究用です。** 端数利払いの規約差、長期債券の系統的な価格差、単位推定の不確実性が残ります。モデルの選択根拠と数値は `reports/research_report.html`、制約は `MODEL_RISKS.md` を参照してください。

## 環境・実行方法

これは `feedback_round_01` の独立提出です。初回の数値推定、ノット、平滑化選択、Huber閾値、支払規約は維持しました。形式修正と割引関数による価格付けAPIの追加を数値精度の改善とは扱いません。改善ラウンドの測定結果は `reports/feedback_review.html` にあります。

実測環境は Python 3.12.11、NumPy 2.5.2、pandas 2.3.3、SciPy 1.18.1、Matplotlib 3.11.1、pytest 8.4.2、macOS arm64、BLAS 1スレッドです。承認済みPythonを `PYTHON_BIN` に指定します。このラウンドではパッケージの追加・更新・ネットワーク利用をしていません。`PYTHONPATH=src` で実行するためインストール不要です。

以下はこのプロジェクト直下で実行します。`PYTHON_BIN` と `RUNTIME_TMP` は実行者が指定します。このラウンドの一時出力は指定された `audit/` 内を使用しました。通常の独立実行では任意の書込み可能な一時ディレクトリを使用できます。

```bash
: "${PYTHON_BIN:?承認済み Python 3.12 の絶対パスを設定してください}"
: "${RUNTIME_TMP:?許可された一時ディレクトリの絶対パスを設定してください}"
source scripts/env.sh
PYTHONPATH=src "$PYTHON_BIN" -m pytest -q \
  -o "cache_dir=$TMPDIR/pytest-cache" --basetemp "$TMPDIR/pytest-run"
PYTHONPATH=src "$PYTHON_BIN" -m quantcurve.cli run \
  --market-data "$PWD/data/market_observations.csv" \
  --output-dir "$PWD/outputs" \
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

## データと監査

`data/market_observations.csv` は供給された可視 CSV の無変更コピーです。`data/provenance.json` の SHA-256 を供給マニフェストと照合しました。入力仕様とタスク仕様も `data/` に保存しています。初回の自分の提出物を比較元に使い、外部の正解・別候補の成果物は利用していません。

- 金利単位は PERCENT ÷100、明示 DECIMAL はそのまま、BPS ÷10,000。債券価格は額面100当たりの PRICE_POINTS。
- 誤ったラベルの金利は、同じ商品種類・同じ満期の他の2商品以上が安定し、100倍または1/100倍で整合する場合だけ推定補正します。ごく小さい・負の金利を大きさだけで補正しません。
- 1単位額面の債券価格の誤ラベルは、5年以内の他の3債券以上と近傍金利からの概算 PV の両方が25%以内で一致する場合だけ補正します。この推論は確定的な単位メタデータの代替ではありません。
- 全観測を監査 CSV に保存します。3暦日超の古い観測、不明な規約、回復不能な必須値を除外し、同一商品の有効な最新観測を優先します。
- 欠損価格は両側気配の中点でのみ回復します。逆転した気配は交換。低流動性・不完全な気配等は理由付きで精度を下げます。
- `weight` は `reliability × robust_weight / sigma²` です。異なるクォート単位の生の重みを直接比較しないでください。最終残差重みと補正前の精度も記録します。

## キャッシュフローとモデル

`maturity_years` を ACT/365F の権威ある時間とし、日付との差は監査します。OIS は2年以下の商品を年1回、それより長い商品は半年ごとの固定脚とします。最後の端数期間は実年数で按分し、債券は通常期間の定額利払と端数期間の按分利払、額面100の償還を持ちます。端数利払の細目は供給規約で未指定であり、なし・全額の代替も研究します。settlement_days=2 は検証し、提示された評価日起点の価格式に追加の割引シフトを入れません。

単純モデルは固定時定数2年の3係数 Nelson–Siegel、高度モデルは log(1+T) 上の自然3次スプラインです。両者とも同一の Huber 損失とスプレッド・流動性精度を使用し、非頑健な最小二乗もアブレーションとして報告します。高度モデルは曲率の二乗積分を罰則化します。8回以下の IRLS を初期化に使い、その後にデータのみ Huber・曲率のみ二乗損失の最適化を行います。Jacobian はキャッシュフローから解析的に計算します。

`D=exp(-Tz)` と `f=z+Tz'` を用い、負金利・負フォワード・1を超える割引係数を許容します。係数には±20%の安全境界を置き、到達すれば失敗を返します。最後のスプライン節点を超える区間は瞬間フォワードを一定に延長します。単純モデルの長端は Nelson–Siegel の漸近形です。

検証は満期バケット単位の決定的な分割です。両端は訓練に残し、近接満期の複数商品を同じ群で扱います。平滑化は外側のホールドアウトを使わず訓練内部で選びます。単位修正が分割前にテープ全体を参照するため、完全に未使用の時間外テストではありません。全検証観測をスコアに含めます。高度モデルは重み付き Huber 検証損失を5%超改善した場合だけ選択します。

## リスクの定義

固定受取 DV01 は `(PV[-1bp] - PV[+1bp])/2`。預金と OIS は元本1,000,000、債券は額面100です。観測された固定金利・クーポンを固定した PV の変化を測ります。

2/5/10/30年のキーはゼロ金利に対する線形ハット型バンプです。2年より前は2年キーが1、30年より先は30年キーが1。全時点でキーの和が1になり、個別キー DV01 の合計とパラレル DV01 の差は有限バンプの高次項だけです。半分の幅の中央差分を1bp単位に換算した値、解析的な一次感応度も出力します。市場クォートをバンプして再校正するリスクではありません。

## 成果物

| ファイル | 内容 |
|---|---|
| `outputs/curves/curve.csv` | 選択モデルの1/12–30年、721点、年率小数 |
| `outputs/curves/{baseline,advanced}_curve.csv` | 両候補の同一グリッド |
| `outputs/diagnostics/cleaning.csv` | 入力の全行、元値・正規化値・判断理由 |
| `outputs/diagnostics/repricing.csv` | 全データ再校正後の価格と残差 |
| `outputs/diagnostics/holdout_repricing.csv` | 検証データを使わず校正した予測 |
| `outputs/diagnostics/risk.csv` | 各採用商品の DV01・キー・有限差分照合 |
| `outputs/diagnostics/model_comparison.json` | 訓練・検証・全標本の指標と選択根拠 |
| `outputs/diagnostics/sensitivity.json` | 平滑化、閾値、10%除去8回、流動性、端数規約、両端 |
| `outputs/charts/` | 5枚の図 |
| `reports/research_report.html` | 自己完結の日本語研究報告 |
| `benchmark_summary.json` | 開始・終了・経過秒・テスト・修正回数・未解決事項 |

ラウンドの `audit/` には事前条件、全実験、分割ID、失敗を含む実行ログ、原本ハッシュ、図の点検結果を保存しています。これは研究履歴であり、提出CLIの依存物ではありません。`benchmark_summary.json` はこの改善ラウンドの実測値です。初回のサマリー・HTML・数値成果物は変更していません。

正確なトークン・クレジット・料金・割当消費量は取得できず、nullです。人工データの誤差は自作カーブに対する値であり、隠し採点の推定値ではありません。
