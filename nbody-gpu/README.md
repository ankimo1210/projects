# nbody-gpu

`nbody-gpu` は、GPU で加速した重力 N 体シミュレーションとリアルタイム 3D 可視化のプロジェクトです。力の計算は CuPy RawKernel によるカスタム CUDA C カーネル（Numba 不使用）、可視化は VisPy + PyQt6 で行います。Phase 0–2 が完了しています。

## 主な機能

- **直接法 O(N²) カーネル**（`nbody/forces.py`）— タイルベースの共有メモリ実装。現在の本番用デフォルト。
- **Barnes–Hut 法**（`nbody/forces_bh.py`）— 30-bit Morton コード + Z-order ソート、Karras (2012) 並列 radix tree による LBVH 構築、ボトムアップの質量・重心・BBox 伝播の上での木探索。正しく動作するが、この GPU では N が大きい場合にのみ直接法より有利。
- **Leapfrog 積分器**（kick–drift–kick、シンプレクティック）。
- **初期条件**: Plummer 球、二体円軌道。単位系は \(G=1\) の無次元（Plummer スケール \(a=1\)、全質量 \(M=1\)）。特異点回避のためソフトニング \(\varepsilon\) を \(r^2\) に加算。
- **リアルタイム 3D ビューア**（VisPy SceneCanvas + Markers）。エネルギー診断付き（O(N²) 計算のため N ≤ 8192 のときのみ既定で有効）。
- **ベンチマークスクリプト**（直接法 vs Barnes–Hut）。

RTX 5080 での実測（2026-05、詳細は `CLAUDE.md`）: 直接法は N=65,536 で 3.4 ms/step と N ≲ 10⁵ では Barnes–Hut を圧倒し、クロスオーバーは N ≥ 26 万程度の大規模側でのみ発生します。

## 動作要件

- **NVIDIA GPU + ドライバが必須**（CuPy が CUDA デバイスを要求。macOS 非対応）。
- CUDA 12.x（依存パッケージは `cupy-cuda12x>=14.0`）。Blackwell 世代（RTX 5080, sm_120 / CC 12.0）では RawKernel の JIT コンパイルに sm_120 対応の nvrtc（CUDA 12.8 系）が必要。
- Python 3.12 以上。
- GUI 表示環境（開発環境は WSL2 + WSLg で動作確認済み）。

## 技術スタック

| 層 | 技術 |
|---|---|
| 数値計算 | CuPy（RawKernel: カスタム CUDA C カーネル）、NumPy、SciPy |
| 可視化 | VisPy + PyQt6、imageio |
| 開発 | Python 3.12+ / uv workspace、pytest、ruff |

## セットアップと実行

本プロジェクトは `/home/kazumasa/projects` の uv workspace のメンバーです（ルート共有 `.venv`、初回のみ workspace ルートで同期）。

```bash
cd /home/kazumasa/projects && make install   # = uv sync --all-packages（初回のみ）
```

`nbody-gpu/` 以下からコマンドを実行します（workspace の `.venv` が自動検出されます）。

```bash
cd /home/kazumasa/projects/nbody-gpu

# 環境チェック（CUDA / CuPy RawKernel / VisPy）
uv run --no-sync python scripts/check_env.py

# インタラクティブデモ（Plummer 球の自己重力緩和、q キーで終了）
uv run --no-sync python scripts/run_demo.py
uv run --no-sync python scripts/run_demo.py -n 32768 --no-energy   # 大 N の例

# 直接法 vs Barnes–Hut ベンチマーク
uv run --no-sync python scripts/bench.py
```

`run_demo.py` の主なオプション: `-n/--n-particles`（既定 8192）、`--dt`（1e-3）、`--eps`（2e-2）、`--steps-per-frame`（4）、`--point-size`、`--no-energy`、`--seed`。

## プロジェクト構成

```text
src/nbody/
  forces.py             # CuPy RawKernel: タイルベース O(N²)（本番用）
  forces_bh.py          # LBVH 上の Barnes-Hut 探索
  integrator.py         # leapfrog (kick-drift-kick)
  initial_conditions.py # Plummer 球、二体円軌道
  simulation.py         # Simulation クラス（デバイス側状態を保持）
  octree/
    morton.py           # 30-bit Morton コード + Z-order ソート
    lbvh.py             # Karras 2012 並列 radix tree
    multipole.py        # 質量 / 重心 / BBox のボトムアップ伝播
src/viz/
  renderer.py           # VisPy SceneCanvas + Markers
  stars_visual.py       # 星のカスタム Visual
  app.py                # シミュレーション <-> 描画ループ
scripts/
  check_env.py          # CUDA / CuPy / VisPy 動作確認
  run_demo.py           # インタラクティブデモの入口
  bench.py              # 直接法 vs BH ベンチマーク
tests/                  # Kepler、エネルギー保存、Morton、LBVH、multipole、BH
```

## テスト

```bash
cd /home/kazumasa/projects/nbody-gpu
uv run --no-sync pytest          # 21 passed（GPU 必須）
```

workspace ルートからは `uv run --no-sync pytest nbody-gpu/tests -q` でも実行できます。テストは二体円軌道の Kepler 周期、エネルギー保存、Morton 順序、LBVH 構造、多重極伝播、直接法と Barnes–Hut の一致（差分テスト）を検証します。

アルゴリズム実装の進め方（参照実装 → 解析解での検証 → 性質テスト → 差分テスト → 最適化は最後）は `CLAUDE.md` の Algorithm Implementation Protocol を参照してください。
