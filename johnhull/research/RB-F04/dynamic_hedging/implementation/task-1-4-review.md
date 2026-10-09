# Task 1・4 独立 source review

2026-10-09。対象は base `d71b25f3` に対する凍結 package の追加6ファイル。Task 1/4 の承認可否を判定し、phase 受入とは区別する。reviewer は source/tests/Git を変更していない。

## 判定

| 対象 | 仕様適合 | 品質 | 統合へ進めるか |
|---|---|---|---|
| Task 1 core | PASS（この task の範囲） | blocking finding なし | 可 |
| Task 4 risk/policy | NEEDS FIX | Important 2件 | 修正後に再確認 |
| 合同 package | NEEDS FIX | Critical 0 / Important 2 / Minor 0 | 現状のまま不可 |

### Important T14-R1: local rank1 null 差が unknown になる

`johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py:149–154`。有限共分散を PSD と認める許容差はあるが、その後の quadratic を厳密 `>=0` で判定するため、rank1 の null 差が浮動小数点の微小負値になった場合 NaN を返す。DESIGN §8（251行）の「null方向 sd0、無取引」と不整合。

通常の `price_covariance("local",100,1,.6,10,1/12,base_variance=.04)`、old `[0,0]`、target `[-.6,1]`、width `.01` で再現。理論値は 0、計算 quadratic は `-2.1316282072803005e-15`、最小固有値 `-1.7763568394002505e-15`。band は `status=unknown`, holdings `[NaN,NaN]` を返した。CS=.3/.7/.9 でも再現する。原 N のうち一経路でもこの状態に当たれば全体集計を unknown にする原因となる。既存テストは .5 の正確に表現可能な fixture だけで、この問題を検出しない。

修正は diffusion loading／安定した PSD factor による二乗ノルム評価、又は明示・診断付きの roundoff qualification とする。raw 診断を保存し、ridge や実質的に不正な covariance の修復には広げない。CS=.6、月次 dt の null fixture を追加する。

### Important T14-R2: cap 超過でも completed のまま

`deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_policy.py:313–329`。requested updates を終えると completed になり、final diagnostics と thread restore 後の elapsed が cap を超えても `complete=True` を返す。DESIGN §10（282行）は cap 超過を completed family の一員として認証しない。関数 docstring 自身も cap に final diagnostics を含めている。

in-memory clock `[0,.1,.2,2]`、requested updates=1、cap=1 の小 fixture で `updates=1,status=completed,complete=True,elapsed_seconds=2,overrun_seconds=1` を再現。最終更新又は最終診断だけが上限を越えた実行を successful fit と扱う危険がある。overrun の記録だけでは complete/status の意味が整合しない。

elapsed 確定後、超過した completed を明示未完了に変更し、実更新数・last finite weights・overrun を保持する。最終更新／最終診断の超過を deterministic clock で確認する。

## 適合を確認した範囲

Task 1: old-v adapted log-stock、正 CIR quadratic と rationalized root、xi0 exact deterministic transition、calendar midpoint local、元 N と failure reasons、fixing-before-rebalance/S0除外、CF entitlement、initial/interim/terminal fee、一回の liquidation/claim payment は設計式と整合。固定 finite-grid の Gaussian coefficient と backward MGF recurrence も数式と実装が対応しており、continuous convergence や価格精度を認証していない。

Task 4: physical IFT、minimum-variance stock projection、Heston covariance の loading 展開、local multiplier/rank1、raw/legal constraint 保存、random baseline を含む paired d/r、元 N に unknown がある場合の集計 unknown は整合。NN は指定9features/9→32→32→2/±2/CPU float64、train-only scaler、local batch RNG、CPU RNG/thread restore、oldholding BPTT、全 fee と cash を実装。実 variance/G ID/future payoff は feature にない。public API/init/依存の変更は review package にない。

## 証拠と境界

最初の独立 probe 時点で6ファイルの現物 SHA256 は manifest と一致し、package の全追加行から復元したファイルも同じ digest だった。report 保存時には root の後続修正が始まって現物 digest が変化したため、この判定は以下の original frozen digest にのみ bind する。後続修正は本 report では未レビュー。報告済み scoped green は core29/risk21/policy9。今回はその suite を再実行していないため、新たに green を認証したとは扱わない。小数値 probe は `/tmp/dynamic_core_risk_probe.py` にだけ保存した。clock replacement は実行プロセス内だけであり reviewer による source 変更はない。

Task 5 の runner は、nonfinite dataset で fit が ValueError を返す場合も全 attempt/original N を保存する必要がある。これは caller の統合義務であり追加の Task4 blocker としない。quote root/support/state-scale/teacher ratio qualification、固定 claim/calendar/traded-call/market price、全12fits/selection/IDs も caller が契約を守る。索引3項目は review 時に存在した。文書/source/test の同時統合、post-format scoped 証拠、最終 whole-suite gate は別途必要。

Task2/3 全体、whole-suite、正式 pilot、freeze、main、NN優越、費用台帳、bootstrap/Bonferroni/IUT 判定は未判定。common fit/CF-PDE、実市場離散化とcall drift、local field boundedness、Greek moment/precision/empirical envelope は後続 Tasks5–7 の証拠で判断する。これらの未完了を今回の Task1/4 不合格理由にはしていない。

## 凍結 source digests

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_core.py`: `78ad0cc9e32628476da2023755cd688ea8363aee9be5f5655c204c6ab6fa5777`
- `johnhull/hullkit/tests/test_dynamic_hedging_core.py`: `3347d9def05ccff761527b0273d85c7d98b2712da9c45813bbe7a03999cfcb2b`
- `johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py`: `f2a1c533d8536fce5df3698f5413e430a61abf9fc5e469e55351f9af05c36242`
- `johnhull/hullkit/tests/test_dynamic_hedging_risk.py`: `7255a2b52b9974ea015c78fd45eb4193346c54f740f6a7d13b0de077a4c34bbd`
- `deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_policy.py`: `617910b429aefbe7c04b97e81dc75b15f419302eab5e3c838d33d8f26207651f`
- `deep_hedge_price/tests/test_dynamic_hedging_policy.py`: `41a165842e7d3f1386583d85f6f8c3927a2544404c3d53d710f2478ab3d0018f`

Package SHA256: `a22ead76073d740bc898ec8c406ff515d05deb66fb2738e261fba311cdd3b99b`。Manifest SHA256: `9b6b8c6c0f8c86fc33ef08a7bb2b4ee23e86426251ace0529c0b5c5e45803b22`。
