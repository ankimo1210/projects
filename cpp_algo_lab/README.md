# cpp_algo_lab — C++ アルゴリズム実験室

## 概要

C++ を「アルゴリズムを素材に、測って理解する」ための学習ラボ。教科書の計算量表を眺めて終わりにせず、STL 形式のテンプレートとして自分で実装し、同じ計測ハーネスに 10 種のソートを通して、理論と実測のずれ（キャッシュ・分岐予測・アロケータ）まで含めて観察する。

Phase 1 の内容はソート 10 種（bubble / insertion / selection / shell / merge / quick / heap / counting / radix / bucket）の実装と **4 軸評価** — ①実測時間、②操作回数（比較・move・swap）、③入力分布別の挙動（5 分布）、④安定性の観測。全体設計と後続フェーズの計画はスペック [`../docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md`](../docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md) にある。

![time_vs_n](results/plots/time_vs_n.png)

## クイックスタート

`make` は**このディレクトリ（`cpp_algo_lab/`）で実行**する。また、ベンチマーク中は他の重い処理を走らせないこと — WSL2 ではホスト側のスケジューリングが計測のばらつきに直結する（ハーネス側でも中央値採用で緩和している）。

| コマンド | 内容 |
|---|---|
| `make test` | ASan/UBSan 付きで全 doctest をビルド・実行（デフォルトターゲット） |
| `make bench` | フル計測: 5 分布 × n=256〜1,048,576（二次族は 32,768 まで）→ `results/*.csv`。**数分かかる** |
| `make bench-quick` | 縮小スイープ（n≤4096・2 反復）。配線確認用 |
| `make trace` | n=256 の配列スナップショット列を採取 → `results/traces/trace_*.csv` |
| `make plot` | リポジトリルートの uv 環境（pandas/matplotlib）で 6 枚の PNG を `results/plots/` に生成 |
| `make clean` | `build/` を削除 |

## 構成

```
cpp_algo_lab/
├── Makefile              # test / bench / bench-quick / trace / plot / clean
├── common/
│   ├── lab/              # 計測基盤: Counted<T>・timer・datagen・stability・csv・table
│   └── tests/            # 計測基盤自体の doctest
├── sorting/
│   ├── include/sorting/  # 1 アルゴリズム = 1 ヘッダ（bubble.hpp … bucket.hpp、keys.hpp、all.hpp）
│   ├── tests/            # 全ソート × 全分布 + エッジケース + 安定性のテスト
│   └── bench/            # 計測・トレース実行体 bench_sorting.cpp
├── scripts/
│   └── plot_results.py   # results/*.csv → 6 図の PNG
├── results/              # 計測結果（CSV・図・トレース）— 再現性のためコミット対象
│   ├── plots/            # 6 枚の PNG
│   └── traces/           # アルゴリズム別スナップショット CSV
├── docs/                 # 学習ドキュメント（sorting.md が中心）
└── third_party/doctest/  # 同梱テストフレームワーク（外部依存なし）
```

## 学習ロードマップ

推奨する読み順は次のとおり。

1. **[`docs/sorting.md`](docs/sorting.md) を読む** — 各アルゴリズムの動き（手動トレース付き）・実装の要点・理論予想・実測の読み方を 1 本にまとめた中心ドキュメント。
2. **ヘッダを読む** — `sorting/include/sorting/` を bubble → insertion → selection → shell → merge → quick → heap → counting → radix → bucket の順で。この順は「隣接交換 → shift → 探索と交換の分離 → gap → 分割統治 2 種 → 暗黙の木 → 非比較 3 種」という概念の積み上げになっている。どれも 20〜75 行。
3. **`make bench && make plot` で図を再生成する** — 自分のマシンで数値がどう変わるか（キャッシュサイズや CPU が違えば bubble のジャンプ位置も変わる）を確かめる。
4. **`results/plots/` の 6 図を `docs/sorting.md` の「結果の読み方」と突き合わせる** — 各アルゴリズム節の予想が図のどこに現れているか、逸脱（quick × reversed、bubble の傾き 2.37 など）がなぜ起きるかを確認する。

## Phase 状況

| Phase | 内容 | 状態 |
|---|---|---|
| 1 | ソート 10 種 + 評価 4 軸（時間・操作回数・分布・安定性） | ✅ |
| 2 | 文字列検索 | ⬜ |
| 3 | CPU 並列化 | ⬜ |
| 4 | GPU | ⬜ |
| 5 | ドキュメント仕上げ | ⬜ |

## 依存

- **ビルド・テスト・計測**: g++ 13（C++20）と make のみ。doctest は `third_party/` に同梱しているため、C++ 側の外部依存はゼロ。
- **図の生成のみ**: リポジトリルートの uv workspace（pandas / matplotlib）。`make plot` が内部で `uv run --no-sync` を呼ぶ。
