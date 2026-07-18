# 参考文献と本ラボの対応

## ソート（Phase 1 / Phase 3–4 で使用）
- **Sorting with GPUs: A Survey** (arXiv:1709.02520) — GPU ソートを radix / merge / sample / quick の系統で整理する見取り図。[`parallel_gpu.md`](parallel_gpu.md) では、教育用 network を実用 GPU sort の全体像と混同しないために使う。
- **Onesweep** (Adinets & Merrill, NVIDIA 2022; 解説: AMD GPUOpen "Boosting GPU radix sort") — 現代的な LSD radix の memory traffic 削減例。整数 `thrust::sort` の内部方式を本ラボは同定していないため、特定系譜だとは断定せず、最適化済み library と自作 bitonic の距離を読む背景に限定する。
- **K. E. Batcher, Sorting Networks and their Applications (1968)** — [`sort.cuh`](../parallel/gpu/include/gpu/sort.cuh) の bitonic compare-exchange 段の原典。$O(n\log^2 n)$ の段数と padding は [`parallel_gpu.md`](parallel_gpu.md) §4 で縮小再現する。
- **IPS⁴o: In-place Parallel Super Scalar Samplesort** (Axtmann et al., ESA 2017 / ACM TOPC 2022, github.com/ips4o) — CPU並列ソートSOTA。同梱せず、Phase 3 の自作 merge / parallel STL の先にある「現実の到達点」参照値。
- **Ciura, Best Increments for the Average Case of Shellsort (2001)** — shell.hpp の gap 列の出典。

## 文字列検索（Phase 2 で使用・Phase 4 で GPU 化）
- **Knuth, Morris & Pratt, Fast Pattern Matching in Strings (SIAM J. Comput., 1977)** — kmp.hpp の failure（prefix）関数と走査 ≤2n 保証の出典。docs/search.md §3.2 が縮小再現。
- **Boyer & Moore, A Fast String Searching Algorithm (CACM, 1977)** — 劣線形スキップの原典（bad-character + good-suffix の 2 表）。std_bm 基準線が対応し、小アルファベットでの good-suffix の効きは search.md §5.2 ④。
- **Horspool, Practical Fast Searching in Strings (Software: Practice & Experience, 1980)** — bad-character 単独への簡略化。bmh.hpp の直接の出典で、シフトの σ 飽和則は search.md §5.3。
- **Karp & Rabin, Efficient Randomized Pattern-Matching Algorithms (IBM J. Res. Dev., 1987)** — rabin_karp.hpp のローリングハッシュ照合。衝突と検証の必然性は search.md §6。

## 並列化（Phase 3 で使用）

- **Amdahl, Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities (AFIPS, 1967)** — 並列化できない部分が speedup の上限を決める法則。`parallel_cpu.md` §5.4 では観測 speedup から「実効逐次率」を逆算する。ただし runtime・メモリ・scheduler の overhead も含む尺度であり、コード上の逐次部分そのものとは解釈しない。

以下の GPU 文献は、Phase 2 の逐次実装（`search.md` §7）を [`search.cuh`](../parallel/gpu/include/gpu/search.cuh) と [`parallel_gpu.md`](parallel_gpu.md) §6 へ接続する答え合わせ先:

- **Kouzinopoulos & Margaritis, String Matching on a multicore GPU using CUDA** — naive/KMP/BMH/Quick-Search の CUDA 比較。本ラボの 1 start / thread と CPU 基準線の設計を比較する先であり、hardware・計測境界の異なる speedup 値は直接移植しない。
- **PFAC: Parallel Failureless Aho-Corasick**（Lin et al.; DNA最適化版 arXiv:1811.10498） — failure 遷移を捨て 1 thread = 1 開始位置へ寄せる発想。本ラボの GPU naive は単一 pattern で独立性だけを縮小再現し、PFAC そのものとは呼ばない。
- **Efficient Parallel KMP for Multi-GPUs** (Springer) — KMPのfailure関数の逐次依存はGPU並列化の障害という教訓の出典。
- **GPUs for Pattern Matching** (arXiv:1412.7789) — サーベイ。

各文献の「何を縮小再現するか」は `sorting.md`、`search.md`、`parallel_cpu.md`、`parallel_gpu.md` の該当節から参照する。GPU の実測値は `results/gpu_*.csv`、図は `results/plots/gpu_*.png` が再現可能な一次成果物である。
