# ニューラルネット実験室

[index.html](index.html) をブラウザで開き、**「学習と推論を観察」→「学習を開始」**で動かす。
入力 → 隠れ層 → 出力をつないだ図で、各ニューロンの反応地図が学習と一緒に変わる。
**「このPCで規模比較」**に切り替えると、GPUで計測した5規模の結果を比較できる。
HTMLはサーバー・追加パッケージ・外部通信なしで表示できる。
規模比較の再学習はPython/PyTorchでこのPCのGPUを使い、結果をHTMLに取り込む。
既存の [統合ポータル](../../report/README.md) の学習済みフレーム再生に対し、こちらは設定を変えて再学習できる。

## モデル・学習・推論を追う

1. 「学習を開始」を押し、隠れ層の地図と、出力の決定境界が変わるのを見る。
2. ニューロンを選び、前の層の値・重み・寄与の和・バイアス・活性化後の値を確認する。
3. 寄与の表で行を選ぶと、その接続が図で強調される。
4. 出力図の1点をクリック/タップで固定し、「この点の推論を追う」か「次の層へ」で順伝播を追う。
5. 「1 epoch」を押し、平均BCE・選んだ重みの勾配・Adamでの更新前後を確認する。

各地図は出力図と同じ元のx₁・x₂の範囲・向きを使い、実際の順伝播を計算している。
小さな十字も同じ1点の位置。入力は学習集合で推定した平均/標準偏差による標準化後の値、
隠れ層はtanh/ReLUの値、出力はクラス1の確率を示す。
入力・隠れ層の色は−1〜+1で飽和し、出力は0〜1を使う。各ニューロンの実値は地図の下に表示する。

「推論を追う」は重みを固定した順伝播の再生。入力から順に層を強調し、まだ進んでいない層の数値は伏せる。
学習を再開する、重みを更新する、点や設定を変更する、別タブに移ると再生を解除する。
出力図は矢印キーでも操作できる（Shiftで移動幅を拡大、Spaceで固定/解除）。
画面が狭い場合は図の枠内を横スクロールできる。

「1回の学習」の欄は**学習360点による実際の平均勾配＋L2項**を使った直前の更新。
選んだ1点の推論の値と、学習集合全体で求めた勾配を区別して表示する。
Adamは勾配の移動平均と二乗の移動平均を使うため、更新量は単純な `−lr × gradient` にはならない。
最新1回分の更新前/勾配/更新後だけをRAMに保持し、履歴ごとの重みコピーは保存しない。

## このPCでの規模比較

Fashion-MNIST（28×28の衣服画像、10分類）をRTX 5080で実際に学習した。
全モデルで固定の学習50,000／検証10,000／公式テスト10,000枚、batch512、8 epoch、
seed11/22/33、Adam lr=0.001・L2=0.0001・float32（TF32なし）を使用する。
平均と標準偏差は学習画像だけで求め、検証loss最小のepochの重みで最終テストを1回評価する。
隠れ層はReLU。幅と深さを同時に変えているため、規模だけの因果効果とは解釈しない。

2026-11-03の実測（± は3 seed間の標本標準偏差）：

| モデル | パラメータ | テスト正解率 | GPU学習・評価時間/実行 | 割当VRAMピーク |
|---|---:|---:|---:|---:|
| Linear | 7,850 | 83.97% ± 0.07pt | 0.78秒 | 277.6MiB |
| MLP 16×1 | 12,730 | 84.89% ± 0.26pt | 0.96秒 | 277.7MiB |
| MLP 128×2 | 118,282 | 87.40% ± 0.41pt | 1.12秒 | 279.8MiB |
| MLP 512×3 | 932,362 | 88.03% ± 0.11pt | 1.47秒 | 298.2MiB |
| MLP 2048×4 | 14,217,226 | 87.78% ± 0.17pt | 3.38秒 | 547.7MiB |

時間はwarmup後、全epochの学習・学習集合/検証集合の評価・RAMへのcheckpoint保存を含み、
画像読込・初期評価・最終テストは除く。VRAMは入力・学習・評価を含むPyTorch最大割当量で、
ドライバや他アプリを含むGPU全体の使用量ではない。

別にCPU4スレッドとGPUでデータ配置済みの更新時間も測定した。
線形モデルはCPU 0.295ms / GPU 0.796ms、最大モデルはCPU 119.120ms / GPU 3.453ms。
最大モデルのGPU/CPU速度比は約34.49倍。小さなモデルではGPU起動の固定費が大きい。

この設定では約93万パラメータで平均精度が最も高く、さらに大きくする利得は見られなかった。
8 epochと共通のハイパーパラメータに限った比較であり、より長い学習やモデル別の調整では結果が変わる。
最大モデルの割当ピークも約548MiBなので、このPCには大きいモデルや別の題材を試す余力がある。

画面では規模対精度、CPU/GPU時間、epoch/経過秒での検証曲線、各モデル・seedの損失と混同行列を確認できる。
全計測結果をJSONで保存できる。HTML内でGPU学習を開始する機能はなく、再計測は以下のCLIで行う。

```bash
# Run from the repository root in WSL. Uses the cached dataset; no download.
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  uv run --no-sync python -m nn_textbook.scale_experiment
python3 analytics/neural_net/playground/build.py \
  --import-comparison _data/analytics/neural_net/scale-comparison/latest.json
```

出力は単一の `_data/analytics/neural_net/scale-comparison/latest.json`。
`--import-comparison` は完了状態・全モデル/seed・行列/指標・時間・VRAM集計・表示metadataを検証してから
`benchmark-results.json` に最終snapshotを残す。入力4ファイルのSHA256、分割とコードのSHA256も含む。
画像の追加コピー・中間配列・学習済み重みは保存しない。
本計測のJSONは約0.86MB、単体HTMLは約0.32MB。

任意の試運転例：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
  uv run --no-sync python -m nn_textbook.scale_experiment \
  --models mlp-2048 --seeds 11 --epochs 1 --skip-step-timing
```

このコマンドも同じ作業JSONを置き換える。すでに取り込んだ最終snapshotとHTMLは明示的に取り込むまで維持される。

## 観察できること

- 三日月（初期設定）・同心円・XORの2値分類。
- 隠れ層0〜3層、各4/8/16ニューロン、tanh/ReLU、学習率、L2、ノイズ、seedの変更。
- 決定境界と予測確率、誤分類、選んだ位置での各ニューロンの反応・接続の重み。
- ニューロンごとの空間的な反応地図、1点の推論の再生、全入力の寄与の分解、実勾配とAdam更新。
- 全epochの学習・検証BCEと正解率、および学習済み線形モデルとの比較。
- 最終テストの正解率・BCE・混同行列。設定と計測履歴をJSONで保存。
- ライト／ダーク表示、狭い画面への対応、実際の学習エンジンのソース表示。

隠れ層を0にすると直線しか引けないこと、非線形の隠れ層を入れると境界が曲がることを試す。
点のばらつきを増やし、学習曲線と検証曲線の差も比較する。

## 学習と評価

合成600点をクラスごとにシャッフルし、学習360・検証120・テスト120へ分割する。
各集合のクラス比は1:1。標準化の平均と標準偏差は学習集合だけで推定する。
データ生成・分割・重みの初期化はseedで固定され、同じ設定で再現できる。

初期モデルは `2 → 8 → 8 → 1`（105パラメータ）。最後はsigmoid、損失は安定なBCE、
最適化はAdam。全学習360点による1回の更新を1 epochと数え、最大1,000 epoch。
最適化する目的関数は `mean(BCE) + L2 / 2 × sum(W²)`（バイアスは正則化しない）。
曲線には比較しやすいよう、更新後の同じ重みで計測した**L2項を含まないBCE**を表示する。

比較基準は、同じ学習集合で400 epoch、学習率0.03、L2なしで学習したロジスティック回帰。
学習予算を揃えたベンチマークではなく、直線で分ける場合の参照値として使う。
検証集合は学習曲線と設定選択に使い、テスト集合は「学習を終えてテストを評価」まで表示・評価しない。
最終テストは**その時点の重み**で評価し、その実行の追加学習を禁止する。
自動早期終了や最良checkpointの選択は行わない。

同じ固定テストを繰り返し見て設定を選ぶと、独立した最終評価にはならない。
この合成データでの正解率は現実の問題への性能を示さず、予測確率の校正も検証していない。

## コードと再生成

| ファイル | 役割 |
|---|---|
| `engine.js` | PRNG、合成データ、標準化、MLP、逆伝播、Adam、評価・履歴 |
| `app.js` | 学習操作、Canvas/SVG描画、テーマ、JSON保存 |
| `inspector.js` / `inspector.css` | ニューロン地図・接続・寄与・直前の更新を連動表示 |
| `comparison.html` / `comparison.js` / `comparison.css` | PCでのモデル規模比較、表・曲線・seed別の詳細 |
| `benchmark-results.json` | 実測結果・入力ハッシュ・条件の最終snapshot |
| `page.html` / `styles.css` | 編集用の画面とレイアウト |
| `build.py` | 共通デザイントークンと各ソースを埋め込み、`index.html` を生成 |
| `engine.test.cjs` | 数値勾配、再現性、学習、データ分離、評価状態、反応地図・寄与・更新の整合性 |
| `STATUS.md` | 完了条件、進捗、検証結果 |

GPU実験の本体は [`../src/nn_textbook/scale_experiment.py`](../src/nn_textbook/scale_experiment.py)。

リポジトリルート（WSL）から：

```bash
python3 analytics/neural_net/playground/build.py
python3 analytics/neural_net/playground/build.py --check
node --test analytics/neural_net/playground/engine.test.cjs
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  uv run --no-sync pytest analytics/neural_net/tests -q
```

配色は `docs/templates/claude-report/tokens.css` を全文埋め込む。
外部フォントは取得せず、そのトークンに指定されたローカルのフォールバック書体を使う。
生成HTMLも同梱し、編集後は必ず再生成する。

ブラウザなしで同じ学習を実行する例（Node.js）：

```javascript
const { Experiment } = require('./analytics/neural_net/playground/engine.js');
const run = new Experiment({ seed: 42 });
for (let epoch = 0; epoch < 350; epoch++) run.step();
console.log(run.history.at(-1)); // Training and validation metrics.
console.log(run.finalize());    // Final test; further training is rejected.
```

既存の類例：[TensorFlow Playground](https://playground.tensorflow.org/)。
本実験室はコードをコピーせず、教材用に独立して実装している。
