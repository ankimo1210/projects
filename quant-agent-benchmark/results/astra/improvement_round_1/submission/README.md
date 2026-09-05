# QuantCurve

預金・パー OIS・利付債から、監査可能な連続複利ゼロカーブを推定する Python 3.12 プロジェクトです。入力データを改変せず、全観測の判断理由、単純モデルとの比較、感度分析、固定受取 DV01 を出力します。

**今回の結果は研究用です。** 端数利払いの規約差、長期債券の系統的な価格差、単位推定の不確実性が残ります。モデルの選択根拠と数値は `reports/research_report.html`、制約は `MODEL_RISKS.md` を参照してください。

## 環境とインストール

以下はプロジェクト直下で実行します。別の実行の仮想環境・キャッシュは使いません。標準の Python 3.12 実行ファイルが PATH に必要です。

```bash
mkdir -p tmp
source scripts/env.sh
python3.12 -m venv .venv
python -m pip install --no-cache-dir -r requirements.lock
python -m pip install --no-cache-dir --no-build-isolation --no-deps .
python -c 'import quantcurve; print(quantcurve.__file__)'
```

`requirements.lock` は今回インストールした全ライブラリの厳密な版です。主要な実行依存は NumPy、pandas、SciPy、Matplotlib、テストは pytest です。`outputs/diagnostics/run_metadata.json` と `logs/environment.json` に実際の版を保存します。ライブラリの取得時にだけパッケージ配布サービスを利用し、校正・テスト・研究処理にインターネット接続は必要ありません。

`scripts/env.sh` は一時ファイルと描画キャッシュを `tmp/` に向け、BLAS を1スレッドに固定します。数値結果と画像のバイト一致は、同じ Python・ライブラリ・OS・描画環境で検証しています。異なる CPU/BLAS/フォントでのバイト一致は保証しません。

## テスト

```bash
source scripts/env.sh
python -m pytest -q
```

供給された7テストは維持しています。追加テストは入力監査、欠損、重複、負金利、単位、不正フィールド、キャッシュフローの独立計算、解析 Jacobian、有限差分、キー集計、外れ値の影響、CLI の失敗応答、空の出力先2か所での全ファイル一致を検証します。

ベンチマーク実行時は `python scripts/run_tests.py` を使用し、開始前に実行回数を増やし、実際の成否・JUnit XML・標準出力を `logs/test_run_*` と `benchmark_summary.json` に保存しました。テスト内の小さな解析ケースと供給データの変形は検証用であり、研究データの代用品には使いません。

## 必須 CLI と再現例

```bash
source scripts/env.sh
PYTHONPATH=src python -m quantcurve.cli run \
  --market-data "$PWD/data/market_observations.csv" \
  --output-dir "$PWD/outputs" \
  --valuation-date 2026-01-15
```

インストール後は `quantcurve run` も同じ引数を受け付けます。別の仕様準拠 CSV は `--market-data` に指定します。時刻の基準日は `--valuation-date` に従い、商品数、観測 ID、金利形状、選択モデルは固定していません。

HTML をプロジェクトの所定位置へ複製する再現例です。

```bash
source scripts/env.sh
python scripts/run_example.py
```

CLI は出力先の `reports/research_report.html` を作ります。再現例はその自己完結 HTML をプロジェクト直下の `reports/research_report.html` にも保存します。両方とも画像を内包し、ローカルで開けます。

設定を変更する場合は `--config config/default.json` を追加します。平滑化は候補リストを訓練内部の3分割で比較して選びます。`smoothing` 単独は低水準の `fit_curve` で使う初期既定値であり、CLI の選択結果を上書きしません。

## データと監査

`data/market_observations.csv` は供給された可視 CSV の無変更コピーです。`data/provenance.json` の SHA-256 を供給マニフェストと照合しました。入力仕様とタスク仕様も `data/` に保存しています。外部の正解、過去の実行、別候補の成果物を利用していません。

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

`logs/` はテスト、環境、自己レビュー、HTML の実表示点検、最終のクリーン実行の記録です。`scripts/render_report.mjs` は任意の表示 QA 用で、Node 22+ とローカル Chromium が必要です。通常の Python CLI はこれらに依存しません。

## 隔離と計測

この実行の作業範囲は指定された Astra 出力先のみです。更新された実行指示に従い、新しいプロジェクト内仮想環境を使用しました。開始時刻は最初に記録した値を保持し、出力先の確認を待った時間も含みます。初回の依存インストールでは TMPDIR の転送が未設定で、標準一時ディレクトリを使用した点を `benchmark_summary.json` の integrity incident に記録しました。その後は一時・キャッシュ出力をこの実行内へ制限しています。

正確にこの実行へ帰属するトークン・クレジット・請求額・利用枠消費は取得できず、すべて `null` です。推定値は置いていません。
