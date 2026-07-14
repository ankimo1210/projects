# cpp_algo_lab 設計書

- 日付: 2026-07-14
- 対象: `cpp_algo_lab/`（新規トップレベルプロジェクト、非Python独立プロジェクト）
- ステータス: 設計承認待ち

## 1. 目的

C++ を学ぶためのデモプログラムセット。題材は次の3テーマ：

1. **ソーティング** — アルゴリズム実装と評価（実測時間・操作回数・分布別挙動・安定性）
2. **文字列検索** — 同上（アルゴリズム間比較を含む）
3. **並列化** — 同じ問題を 逐次 → CPU並列 → GPU と段階的に速くする「ラダー」の実装比較

学習の比重は「モダンC++の書き方の習得」と「アルゴリズム評価」の半々。
理論計算量が実測で見えること（例: log-log 図で O(n²) は傾き2）を重視する。

## 2. スコープ

### 2.1 ソート（Phase 1）

- 自作10種: bubble / insertion / selection / merge / quick / heap / shell / counting / radix (LSD) / bucket
- 基準線: `std::sort` / `std::stable_sort`
- 評価4軸:
  1. 実測時間（wall-clock、N スイープ、中央値）
  2. 操作回数（比較・move/swap を計数）
  3. 入力分布別挙動（random / sorted / reversed / nearly_sorted / few_unique、固定シード mt19937）
  4. 正しさ（`std::is_sorted` + 順列検証）と安定性の自動判定（同キー要素の元順序保存チェック）
- O(n²) 系は N の上限を自動で抑える（ベンチ時間の暴走防止）

### 2.2 文字列検索（Phase 2）

- 自作4種: naive / KMP / Boyer-Moore-Horspool (BMH) / Rabin-Karp
- 基準線3種: `string_view::find` / `std::search` + `std::boyer_moore_searcher` / 同 `boyer_moore_horspool_searcher`（C++17 searcher の学習を兼ねる）
- 評価4軸:
  1. 実測時間 — テキスト長 n スイープ（線形性）+ **パターン長 m スイープ（4→1024）**。BMH の劣線形（スキップ）と KMP の O(n) 平坦の対比が見せ場
  2. 文字比較回数の計数 — BMH が n 未満になること、naive 最悪 O(nm) の爆発を数値確認。前処理（failure 関数 / スキップ表 / ローリングハッシュ）と照合本体を分離計測
  3. テキスト分布別 — 小アルファベット（DNA風4文字）/ ASCII乱文 / 自然文風 / 周期的テキスト（`aaa...ab` 型 = naive・RK の最悪、KMP の本領）
  4. 正しさ — 全出現位置を naive 参照と照合。重なりのある一致（`"aaaaaa"` 中の `"aaa"` は4箇所）、空パターン、パターン>テキスト等の境界ケース

### 2.3 並列化（Phase 3: CPU、Phase 4: GPU）

対比が主役：「ソート = 賢く並列化しないと速くならない」vs「検索 = 自明に並列（embarrassingly parallel）」。

- **ソートのラダー**: 逐次 merge sort → `std::thread` 分割統治（深さカットオフ） → OpenMP task → `std::execution::par`（TBB バックエンド） → CUDA bitonic 自作カーネル + `thrust::sort` 基準線
- **検索のラダー**: 逐次（Phase 2 最速の自作実装） → OpenMP チャンク分割（チャンク境界にパターン長-1 の重なりを持たせる正しさの教材付き） → CUDA naive カーネル（1スレッド=1開始位置）
- 計測:
  - CPU: スレッド数 1→20 のスケーリング曲線（20コア機）
  - GPU: **転送込み / 転送抜き** の両方を計測（正直な比較）
  - 結論の図 =「検索はほぼ線形スケール、ソートは頭打ち」の対比

### 2.4 非スコープ（YAGNI）

- 複数パターン同時照合（PFAC 本体の実装）— docs で文献紹介にとどめ、将来拡張とする
- SOTA 実装（IPS⁴o 等）の同梱 — 文献引用のみ（決定済み）
- GUI / Web レポート — 出力は CLI 表 + CSV + PNG まで

## 3. 環境前提（2026-07-14 実機確認済み）

| 項目 | 確認結果 |
|---|---|
| コンパイラ | g++ 13.3.0（C++20 OK）。cmake / clang++ は無し |
| CPU | 20 コア（WSL2） |
| OpenMP | `-fopenmp` でコンパイル・実行確認済み |
| 並列STL | libtbb.so.12 あり → `std::execution::par` + `-ltbb` 使用可 |
| CUDA | `/usr/local/cuda-12.9/bin/nvcc`（12.9）で `-arch=sm_120` のコンパイル・実行確認済み（RTX 5080）。`/usr/bin/nvcc` は 12.0 で sm_120 不可のため**使わない** |
| Python図化 | ルート uv workspace の matplotlib を利用（`uv run --no-sync`） |

## 4. アーキテクチャ

### 4.1 ディレクトリ構成

```
cpp_algo_lab/
├── README.md                  # 日本語: 学習ロードマップ + 実行方法
├── Makefile                   # build / test / bench / plot / gpu 系（GPU は分離）
├── third_party/doctest/       # doctest.h 単一ヘッダを vendor（唯一の外部依存）
├── common/                    # 共有基盤（ヘッダオンリ）
│   ├── counted.hpp            #   計数ラッパ型 Counted<T>
│   ├── timer.hpp              #   steady_clock ベース、中央値計測
│   ├── datagen.hpp            #   分布生成（固定シード mt19937）
│   ├── textgen.hpp            #   検索用テキスト/パターン生成
│   ├── csv.hpp                #   CSV 書き出し
│   └── table.hpp              #   CLI 整形表
├── sorting/
│   ├── include/sorting/       #   1アルゴリズム=1ヘッダ
│   ├── tests/                 #   doctest
│   └── bench/                 #   ベンチ実行体（CSV 出力）
├── search/
│   ├── include/search/
│   ├── tests/
│   └── bench/
├── parallel/
│   ├── cpu/                   #   std::thread / OpenMP / 並列STL 実装
│   ├── gpu/                   #   .cu（bitonic / thrust / 検索カーネル）
│   ├── tests/
│   └── bench/
├── scripts/plot_results.py    # matplotlib で results/*.csv → results/plots/*.png
├── results/                   # CSV + PNG をコミットする（deep_hedge_price と同方針）
└── docs/                      # 日本語学習ノート
    ├── sorting.md / search.md / parallel_cpu.md / parallel_gpu.md
    └── references.md          # 注釈付き文献リスト
```

### 4.2 インターフェース（決定: STL準拠テンプレート + 計数ラッパ型のハイブリッド）

- ソートは全て STL 準拠シグネチャ:
  `template <class RandomIt, class Compare = std::less<>> void merge_sort(RandomIt first, RandomIt last, Compare comp = {});`
- 計数は要素型で注入: 時間計測は素の `int`、回数計測は `Counted<int>`（比較・move・swap をオーバーロードして thread-local カウンタに加算）。**時間計測に計数オーバーヘッドが乗らない**
- 検索は `std::string_view` ベースで全出現位置を返す:
  `std::vector<std::size_t> kmp_search(std::string_view text, std::string_view pattern);`
  文字比較回数の計数は各実装の `*_search_counted`（統計構造体を返す）で分離
- 学べる C++ 機能: テンプレート、イテレータ、演算子オーバーロード、`string_view`、RAII、`<random>`、`<chrono>`、構造化束縛、C++17 searcher、`std::execution`、sanitizer
- コード内コメントは英語（ワークスペース規約）。日本語の解説は `docs/` のノートでコードと対応付ける

### 4.3 ビルド・テスト

- `make test` — doctest 全テストを `-fsanitize=address,undefined -g -O1` でビルド・実行（sanitizer 自体が学習項目）
- `make bench` — `-O2 -DNDEBUG` で計測ビルド、CSV を `results/` に出力
- `make plot` — `uv run --no-sync python scripts/plot_results.py`（リポジトリルートの uv 環境）
- `make gpu / gpu-test / gpu-bench` — `/usr/local/cuda-12.9/bin/nvcc -arch=sm_120` を明示。**CPU 側だけで全ターゲットが完結**し、GPU 系は分離（CUDA が無い環境でも Phase 1–3 はビルド可能）
- 共通フラグ: `-std=c++20 -Wall -Wextra -Wpedantic`（.cu は nvcc の対応に合わせ c++17/20 をプラン時に決定）

### 4.4 テスト方針

- ソート: 空 / 1要素 / 全同値 / 逆順 / 乱数×`std::sort` 照合 / カスタム Compare / 安定ソートの安定性 / counting・radix の前提（非負整数等）
- `Counted<T>`: 計数の自己検証（既知操作列で回数一致）
- 検索: naive 参照との全位置一致、重なり一致、境界ケース、OpenMP 版はチャンク境界をまたぐ一致の検出テスト
- 並列版: 逐次版と結果一致（複数サイズ×スレッド数）
- GPU: `make gpu-test` で bitonic の結果が `std::sort` と一致、検索カーネルが CPU 版と一致

## 5. 既存研究との対応（docs/references.md の骨子）

本ラボの実験は以下の文献の縮小再現・答え合わせとして位置付ける：

- **GPU 文字列検索**
  - Kouzinopoulos & Margaritis, *String Matching on a multicore GPU using CUDA* — naive/KMP/BMH/Quick-Search の CUDA 比較（最大24倍）。本ラボの GPU 検索と同一の題材
  - PFAC（Parallel Failureless Aho-Corasick）系 — failure 遷移を捨てて 1スレッド=1開始位置にする方が GPU では速い。本ラボの naive カーネルはその単一パターン版
  - 教訓（実測で確認する仮説として docs に先置き）: **「賢い逐次アルゴリズム（KMP）の逐次依存は GPU に不向き」**
- **GPU ソート**
  - *Sorting with GPUs: A Survey*（arXiv:1709.02520）— radix/merge/sample/quick の4系統整理
  - Onesweep（NVIDIA）— 現行 SOTA の LSD radix。`thrust::sort`（整数系は radix）の系譜
  - Batcher bitonic network（1968）— 教育の定番。自作カーネル題材
  - 解釈: 「自作 bitonic vs thrust radix」の性能差 = 研究30年分の差
- **CPU 並列ソート**
  - IPS⁴o（ESA 2017 / ACM TOPC 2022）— CPU 並列ソートの SOTA。同梱はせず「現実の到達点」として数値を紹介

## 6. フェーズ計画

| Phase | 内容 | 完了条件（各 Phase でリポジトリは green） |
|---|---|---|
| 1 | 足場 + `common/` + `sorting/` | make test 緑 / bench が CSV 出力 / plot が PNG 生成 |
| 2 | `search/` | 同上（検索の4軸が出る） |
| 3 | `parallel/cpu/` | スレッドスケーリング曲線の CSV/PNG |
| 4 | `parallel/gpu/` | sm_120 で gpu-test 緑 + 転送込み/抜きベンチ |
| 5 | docs 仕上げ | README ロードマップ + 各ノート + references 完成 |

ワークスペース統合: root `README.md` の索引に1行追加、root `Makefile` の
「Outside the workspace」ヘルプ行に `cpp_algo_lab` を追記（ビルドは巻き込まない）。

## 7. リスク・留意点

- **WSL2 の計測ばらつき** — 反復して中央値を採る。ベンチは他負荷の少ない状態で実行することを README に明記
- **O(n²) 系の暴走** — アルゴリズムごとに N 上限を設定
- **nvcc と C++ 標準** — .cu 側は nvcc 12.9 の対応状況を見て c++17/20 を決定（ホスト側は C++20 固定）
- **`/usr/bin/nvcc`（12.0）の誤用** — Makefile で CUDA_HOME を `/usr/local/cuda-12.9` に固定
- **OpenMP チャンク境界の off-by-one** — 専用テストで担保（設計済み）

## 8. 受け入れ基準

1. `make test` が sanitizer 付きで全緑（GPU 除く CPU 全テスト）
2. `make bench && make plot` で results/ に CSV・PNG が揃い、O(n²) vs O(n log n) の傾き差、BMH の劣線形、スレッドスケーリング、GPU 転送込み/抜きの各図が出る
3. `make gpu-test` が実機（RTX 5080 / sm_120）で緑
4. README と docs/ 一式（日本語）が揃い、references.md が実験と対応付いている
