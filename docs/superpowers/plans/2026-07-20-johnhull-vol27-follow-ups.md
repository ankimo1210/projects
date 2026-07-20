# JohnHull Vol.26/27 フォローアップ項目

**日付:** 2026-07-20
**対象:** `johnhull`（vol 26/27 マージ後の残債）
**起点:** `main`（`2026-07-20-johnhull-vol27-review-fixes.md` の6フェーズ完了後）
**位置づけ:** いずれもマージをブロックしないと判定した項目。着手時はこの順で
価値が高い。

## 1. Acceptance gate が「コミット済み配列から再計算」規約より弱い

vol 27 の 13 チェックのうち、まだ JSON の数値同士を比較しているものが残る。
`christoffersen_detects_clustering` と `pnl_explain_taylor_ordering` は
レビュー修正で配列再計算へ移したが、以下は未対応。

| Check | 現状 | 対応方針 |
|---|---|---|
| `fhs_coverage_improvement` | 保存済み `hs_violations`／`fhs_violations` フラグ配列を読む | `garch_returns` と `hs_var_forecast`／`fhs_var_forecast` はコミット済みなので、そこから違反系列を再計算できる（一致は実測確認済み）。各1行 |
| `gpd_parameter_recovery` | 配列を一切触らず JSON 同士を比較 | `gpd_losses` から MLE の一階条件を scipy-free で検査する |
| `kupiec_size_calibration` | 400本の reject flag しかコミットされていない | **構造的に再計算不可**。複製ごとの超過回数を artifact へ追加しない限り、z=0.0 が偶然か構成かを識別できない。artifact schema 変更を伴う |

`kupiec_size_calibration` は artifact 再生成が必要なので、他の巻の再生成と
まとめて実施するのが安い。

## 2. `mean_excess` の入力検証（レビュー修正の積み残し）

`hullkit.tail_risk.mean_excess` だけ Phase 3 のスコープから漏れており、
同じ「合格方向に無音で倒れる」欠陥が残っている。

```
mean_excess([1.0, nan, 3.0], [0.5]) -> array([1.5])   # NaN が黙って除外される
mean_excess(2-D losses, [0.5])      -> array([2.5])   # 2次元が黙って flatten される
```

`NaN > u` が False になるため、欠損が「閾値を超えなかった観測」として扱われ、
mean excess プロットが実際より低く出る。閾値選択の診断に使う関数なので、
GPD の閾値を過小に選ばせる方向に効く。`_validate_finite_1d`（Phase 3 で追加済み）
を通すだけで塞がる。

## 3. `limit_measure = np.abs(alloc_component_var)`

`johnhull/hullkit/src/hullkit/frontier_reference.py`（vol 27 capstone）。
現在のコミット済みデータは全成分が正なので**完全に no-op** だが、ヘッジ
ポジションで component VaR が負になると、**リスクを削減しているポジションが
満額の限度を消費する**。`pnl_explain.limit_utilization` 自体は abs していない
ので、修正対象は fixture builder 側のみ。artifact のバイト列が変わるため、
他の再生成とまとめる。

## 4. `figures.py` の重複ブロックと未消費 `tags`

`johnhull/report/report_builder/figures.py:242-254` の `FIGURES.extend(...)` は
`_FRONTIER_SPECS` 版と `tags` タプル以外同一。`tags` は `render.py:59` で
context へ渡るがテンプレート（`gallery/book/standalone.html.j2`）のいずれも
参照していない。既存70図すべてが同じ規約なので新規債務ではない。

**着手タイミング:** vol 28 で3つ目のほぼ同一ブロックが生じる時点。そこで
`tags` を実際に使う（ギャラリーのフィルタ等）か、フィールドごと落とすかを
決める。

## 5. ワークスペース root の pytest が壊れている（johnhull 外）

`/home/kazumasa/projects/conftest.py:22` が `import health` を行うが、
health はこの `.venv` に入っていないため、**root 経由の pytest が全プロジェクトで
collection error になる**。

```
ImportError while loading conftest '/home/kazumasa/projects/conftest.py'.
E   ModuleNotFoundError: No module named 'health'
```

health を main にマージした時点からの既存破損で、johnhull 起因ではない。
回避策は `--confcutdir=johnhull`（今回の検証で使用）。恒久対応は `uv sync`
（health をワークスペースメンバーとして .venv へ導入）だが、共有 venv を
変更するため未実施。

## 6. Greeks の境界契約が価格関数と非対称になった

レビュー修正で `call_price`／`put_price` は `T`／`sigma` の混在ベクトルを
要素別に扱えるようになったが、`call_delta`／`gamma`／`vega` 等は従来どおり
`d1 is undefined when sigma or T is zero` で拒否する。

これは**意図した既存契約の維持**（満期ゼロ・ボラゼロで Greeks は定義されない、
あるいはデルタ関数的になる）だが、価格だけが混在ベクトルを通るようになった
ぶん非対称が目立つ。Greeks 側を要素別にするなら、境界での値の定義
（`T=0` の delta を指示関数にするか NaN にするか）を先に決める必要がある。

## 7. vol 28 候補: FRTB IMA

vol 27 の設計時にスコープ外と決めた領域。liquidity horizon 別 ES 集約、
stressed ES scaling、NMRF、P&L attribution test、IMA/SA 比較。
`johnhull/ROADMAP.md` に vol 28 候補として記載済み。

## 8. テスト網羅の細目（各タスクレビューの Minor 積み残し）

いずれも実害は確認されていない。

- `basel_traffic_light` の yellow multiplier clamp が `n_obs != 250` で未テスト
  （docstring は「250日表・n≠250 では再導出しない」と明示済み）
- `risk_allocation` の tie テストが同一行の複製で stable-argsort を固定できない
  （和の恒等式は tie 不変であることが証明済みなので実害なし）
- k 式リテラルが `risk.py` と `risk_allocation.py` と `frontier_acceptance.py` に
  重複（`risk.py` は変更不可、acceptance 側は独立再計算のため意図的な重複）
- `risk_allocation` の退化 `sigma_p <= 0` 分岐が未テスト
- `pnl_explain` の delta-only「~linear」docstring が比率アサートされていない
