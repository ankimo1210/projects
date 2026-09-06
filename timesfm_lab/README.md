# timesfm_lab — TimesFM 3.0 の反証ベンチ

Google Research の時系列基盤モデル **TimesFM 3.0** をゼロショットで動かし、
意図的に強くした 5 つの古典ベースラインとローリング原点バックテストで
比較する。目的は「基盤モデルが速いか」ではなく、**どこまでが本物の
優位で、どこからが測り方の産物か**を切り分けること。

レポート（HTML / Artifact）: https://claude.ai/code/artifact/db4ac429-0c3f-4725-ba99-3eff5d0d741d
ディスク上の同内容: `reports/report.html`

## 結論（2026-09-06 実行、seed=0）

| 問い | 答え | 根拠 |
|---|---|---|
| 単体の古典手法に勝つか | **勝つ** | 5 手法すべてに勝率 71.5〜79.3%、全て p < 1e-40 |
| 窓ごと最良の選択に勝つか | **負ける** | オラクル MASE 0.899 対 1.065（p = 2.2e-4） |
| そのオラクルは到達可能か | **できない** | 実装可能な選択器は 1.275 止まり。的中率 32.5%（偶然 20%） |
| 勝ちは学習データの記憶か | **説明できない** | コーパス内/外で相対誤差に差なし（p = 1.00 / 0.54） |
| 不確実性は信用できるか | **できない** | 80% 区間の被覆が 7 系統すべてで名目割れ（平均 0.778） |

全体平均: TimesFM の MASE 1.029 / CRPS 0.831 に対し、最良の単体ベースライン
（Fourier + trend OLS）は 1.335 / 1.135。ただし **sMAPE では季節ナイーブが 1 位**
になる（32.0 対 39.3）— 指標の選択だけで結論が変わる。

## 学習データ汚染について（実測）

TimesFM 3.0 のモデルカードは学習源に `GiftEvalPretrain` を挙げている。その
中身を開いたところ、**Monash の `traffic_hourly` と `weather` が入っており、
値がバイト単位で一致した**（各 25 系列を `rtol=1e-4` で照合、全一致）。
コーパス側は末尾のテスト区間だけを削った完全なコピーで、traffic は 168 点
（7 日）、weather は 30 点短い。

そこで評価窓を「コーパス内 / コーパス外 / そもそも収録なし」に分類できる
（`src/timesfm_lab/contamination.py`）。**分けて比べても差は出なかった** ——
つまりこの 2 系統での優位は記憶では説明できない。残る交絡は「コーパス外の窓
＝より新しい窓」である点で、これを切るには学習カットオフ後の系列が要る。

残り 5 系統（electricity・ETTh1/h2・solar・河川流量）は GIFT-Eval のテスト側
にあるため GiftEvalPretrain から除外されている。fev-bench のタスク一覧にも
Monash の traffic / weather は無いので、モデルカードの「fev-bench と重なる
ものを除外」ではこの 2 つは落ちない。

## セットアップ

```bash
# ワークスペースルートから（uv はルートで実行する。member 内で叩くと .venv が増える）
uv sync --all-packages

cd timesfm_lab
./scripts/fetch_data.sh                              # 公開データ約 440MB を _data/ へ
uv run --no-sync python scripts/build_contamination_index.py   # GiftEvalPretrain 照合（約 230MB）
uv run --no-sync python scripts/run_bench.py         # 本走。RTX 5080 で約 158 秒
uv run --no-sync python scripts/build_report_data.py # 集計 JSON
uv run --no-sync python scripts/build_report.py      # HTML 2 種を生成
```

初回は HuggingFace から重み（約 800MB）を取りに行く。GPU が無いときは
`--device cpu`。

## テスト

```bash
uv run --no-sync pytest timesfm_lab/tests    # リポジトリルートから。46 tests
```

データ未取得だと `test_datasets.py` / `test_contamination.py` の実データ側は
skip される。ルートの `conftest.py` に `import timesfm_lab` があるのは、
ディレクトリ名とパッケージ名が同じメンバーが pytest 9 で namespace 化して
壊れるのを防ぐため（`AGENTS.md` 参照）。

## 設計上の判断

- **ベースラインは全部確率予測にした。** 季節ナイーブには経験残差ブート
  ストラップの区間を付けてある。基盤モデルの論文が省きがちな、確率予測と
  して本当に手強い相手を用意するため。実際これが較正では 1 位になった。
- **評価窓は重ねない。** 重なると誤差が系列相関して有意差が過大に出る。
- **MASE の分母は文脈側だけから作る。** 検証区間で正規化すると答えが分母
  に漏れる（`metrics.seasonal_scale_mae`）。
- **オラクルは手法ではない。** 窓ごとに 5 手法の最小を取る操作は、定義上
  どんな単体手法より良くなる。実装可能な選択器（直前の窓の勝者を引き継ぐ）
  と必ず並べて出す（`analysis.selector_table`）。
- **PIT は mid-PIT。** solar は 63% が厳密ゼロで、同点を全部ヒットに数えると
  10% 水準の較正が 0.70 という無意味な値になる。

## 既知の限界

- 単変量ゼロショットのみ。TimesFM 3.0 の目玉である多変量・共変量サポートも
  ファインチューニングも使っていない。
- ETS は季節周期 48 超で非季節にフォールバックする（solar の 150 窓が該当、
  レポートの表に明記）。AutoARIMA / TBATS / STL は入れていない。
- seed 1 本。系列サンプリングのばらつきは測っていないので、p 値は
  「この系列集合において」と読む。
- 金融時系列は含まない。公開ベンチマーク系列での性能である。

## ライセンス

コードは Apache-2.0 だが、**TimesFM 3.0 の重みは `timesfm-non-commercial-license-v1.0`**
で商用・本番利用は許諾されていない。商用の可能性を残すなら Apache-2.0 の
ままの 2.5 系（`google/timesfm-2.5-200m-pytorch`）を使うことになる。

## ファイル

| | |
|---|---|
| `src/timesfm_lab/datasets.py` | `.tsf` / ETT の読み込み、系列サンプリング、窓の切り出し |
| `src/timesfm_lab/baselines.py` | 5 ベースライン。点予測 + 分位点 |
| `src/timesfm_lab/metrics.py` | MASE / RMSSE / sMAPE / CRPS |
| `src/timesfm_lab/tfm.py` | TimesFM 3.0 のラッパ（公式ベンチと同じフラグ） |
| `src/timesfm_lab/bench.py` | バックテスト本体、地平線・較正の診断 |
| `src/timesfm_lab/contamination.py` | GiftEvalPretrain との照合と窓の分類 |
| `src/timesfm_lab/analysis.py` | オラクル / 選択器の分離、汚染検定 |
| `reports/results.parquet` | 生データ 6,468 行（1,078 窓 × 6 モデル） |
