# 参考文献と本ラボの対応

## ソート（Phase 1 / Phase 3–4 で使用）
- **Sorting with GPUs: A Survey** (arXiv:1709.02520) — GPUソートは radix / merge / sample / quick の4系統。Phase 4 の見取り図。
- **Onesweep** (Adinets & Merrill, NVIDIA 2022; 解説: AMD GPUOpen "Boosting GPU radix sort") — 現行SOTAのLSD radix。`thrust::sort`（整数キー）はこの系譜。Phase 4 で「自作bitonic vs 30年分の研究」を対比する基準線。
- **K. E. Batcher, Sorting Networks and their Applications (1968)** — bitonic sorting network。Phase 4 の自作カーネル題材。
- **IPS⁴o: In-place Parallel Super Scalar Samplesort** (Axtmann et al., ESA 2017 / ACM TOPC 2022, github.com/ips4o) — CPU並列ソートSOTA。同梱せず、Phase 3 の「現実の到達点」参照値。
- **Ciura, Best Increments for the Average Case of Shellsort (2001)** — shell.hpp の gap 列の出典。

## 文字列検索（Phase 2/4 で使用予定）
- **Kouzinopoulos & Margaritis, String Matching on a multicore GPU using CUDA** — naive/KMP/BMH/Quick-Search のCUDA比較（最大24×）。Phase 4 検索カーネルの答え合わせ先。
- **PFAC: Parallel Failureless Aho-Corasick**（Lin et al.; DNA最適化版 arXiv:1811.10498） — failure遷移を捨て1スレッド=1開始位置。本ラボのGPU naiveカーネルはこの思想の単一パターン版。
- **Efficient Parallel KMP for Multi-GPUs** (Springer) — KMPのfailure関数の逐次依存はGPU並列化の障害という教訓の出典。
- **GPUs for Pattern Matching** (arXiv:1412.7789) — サーベイ。

各文献の「何を縮小再現するか」は docs/sorting.md（Phase 2 以降は各モジュールのノート）の該当節から参照する。
