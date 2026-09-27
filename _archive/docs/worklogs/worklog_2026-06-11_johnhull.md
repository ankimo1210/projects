# Worklog — johnhull (Hull 11e 学習ボリューム + hullkit)

Date: 2026-06-11
Scope: johnhull/ のみ（他プロジェクトの未コミット変更には触れていない）

## Status: 全コミット済み・全章カバー完了 / 直近はハードニング

johnhull の作業ツリーは clean（`git status` に johnhull/ のファイルは無し）。
Hull 11e 全37章を 12 volumes + レガシー2ノートブックでカバー済み。
2026-06-08 の「全14行 done」以降も、レビュー反映・ベクトル化・高次 Greeks 追加の
ハードニングを継続し、テストは 96 → **128** に増加。

## 構成（現状）

- `hullkit/`（uv workspace member）— 14 モジュール:
  bsm, trees, mc, nbplot, payoffs, hedging, rates, volatility, fd, swaps,
  risk, credit, exotics, ir_options
- `hullkit/tests/` — **128 tests collected**（17 test ファイル）
- `volumes/01..12` — 各巻に `.ipynb`（ウィジェット付き、末尾に全チェック合格 assert セル）
- レガシー: `notebooks/bsm_chapter15.ipynb`, `interest_rate_models/ir_models.ipynb`
- カバレッジ表は `johnhull/ROADMAP.md`（spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`）

巻 → Hull 章の対応:
| 巻 | ディレクトリ | 章 |
|---|---|---|
| 1 | 01_foundations | 13,14 |
| 2 | 02_options_basics | 10,11,12,17,18 |
| 3 | 03_greeks | 19 |
| 4 | 04_futures_forwards_rates | 2,3,4,5,6 |
| 5 | 05_vol_smile_estimation | 20,23 |
| 6 | 06_numerical_methods | 21,27 |
| 7 | 07_swaps | 7,34 |
| 8 | 08_risk_var | 22 |
| 9 | 09_credit_xva | 9,24,25 |
| 10 | 10_exotics_martingales | 26,28 |
| 11 | 11_ir_derivatives_market | 29,30 |
| 12 | 12_qualitative_summary | 1,8,16,35,36,37 |

## このバッチで入った変更（2026-06-08 以降、新しい順）

- `c269540` test(hullkit): fd American gamma の参照値修正
  （CRR N=400 bump は未収束 0.06627 → grid-stability + CRR N=6000 参照に書き換え）
- `d911cf5` feat(hullkit): `fd_vanilla(return_greeks=True)` がグリッドから delta/gamma を返す; vol06 demo
- `827ea07` feat(hullkit): 高次 Greeks `bsm.vanna` / `bsm.vomma`; vol05 vanna demo
- `d0626c2` feat(hullkit): package exports 整理 + `ewma_covariance`; vol05 がライブラリ関数を使用
- `be9716a` refactor(hullkit): bsm を numpy 配列でベクトル化; exotics の d1/d2 を bsm に集約
- `c54491f` fix(johnhull): 全ビルダーで決定的 cell id 付与（nbformat MissingIDFieldWarning 解消）
- `f8a3332` fix(johnhull): レガシー ir_models（重複 def・chart scale・RB band clamp）+ bsm cell-local rng
- `fc73179` fix(johnhull): vol09-12 レビュー反映（Merton d2 sqrt, real numeraire demo, GBM KO prob, vol-strip x軸, Schwartz mean）
- `1d89b26` fix(johnhull): vol05-08 レビュー反映（CV odd-N, LSM annotation, DV01 符号, ES demo, chart ylim）
- `fb06654` fix(johnhull): vol01-04 レビュー反映（arbitrage guard, FRA basis, hedge var shadow, theta 軸, citations）
- `560c885` / `59c1979` fix(hullkit): 退化入力に対する descriptive ValueError
  （rates/volatility/credit/risk, mc/trees/hedging/nbplot）
- `457dcab` fix(hullkit): `cap_black` が numpy spot-vol 配列を受理; wrapper の桁を固定
- `d08446a` fix(hullkit): barrier domain guard, Asian b=0 limit, lookback b=0 error
- `cdacb1c` fix(hullkit): LSM American が t=0 で intrinsic 下限を尊重

## 検証状況

- `uv run --project johnhull/hullkit pytest johnhull/hullkit/tests -q` → **128 passed**
  （本 worklog 作成時は `--co` で 128 tests collected を確認）
- 全12巻は headless 実行検証済み
  （`jupyter nbconvert --to notebook --execute`、末尾 assert セル合格）

## 成果物の見方

```bash
cd ~/projects
uv run jupyter lab        # ブラウザで volumes/<巻>/ の .ipynb を開く
```

- 静的な表・プロットは `.ipynb` に埋め込み済み → VS Code のノートブックビューア /
  JupyterLab でそのまま閲覧可。
- インタラクティブ・ウィジェット（スライダー）は live kernel が必要。

## 残（ユーザ確認のみ）

- live Jupyter でのウィジェット動作確認（`uv run jupyter lab`）。
  headless 検証は完了済み。slider/widget のコールバックは live セッションでのみ動く。

## 制約・注意

- johnhull/ 以外の未コミット変更（aisan_lbo_case/*, land_price_api_app/*,
  ルート .gitignore / CLAUDE.md, pokemon/ 等）は他セッションの作業。一切触れていない。
- Hull PDF は GE 版 — 節・図番号が US 版と異なるため、引用時はリポジトリ同梱 PDF で都度確認。
