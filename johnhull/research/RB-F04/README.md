# RB-F04 — Heston と local volatility の動学比較

更新日: 2026-10-09。**包括pilot・独立pilotレビュー・条件固定・主実験・fresh再計算・両保管庫復元・3図を完了。最終レビューapproved・関連suite PASS。tracked release PASS・main統合/push済み。**

[固定protocol](protocol.json) / [主結果](reference.json) / [3図のnotebook](model_dynamics.ipynb) /
[pilotレビュー](PILOT_REVIEW.md) / [最終レビュー](REVIEW.md) / [検証記録](validation.json) /
[設計](../../docs/prep/design/RB-F04_DESIGN.md) /
[実施計画](../../docs/superpowers/plans/2026-10-09-heston-local-dynamics.md) /
[準備条件](prerequisites.json)。

## 結論と採否

**固定した実験では、月次Asianの価格差を識別できなかった。動学比較の教材として保持し、市場でのモデル順位や両モデルの同値性は主張しない。**

768内部steps、196,608 paired pathsのHeston価格は5.55084529、local価格は5.55451818。
local−Heston差は0.00367288、paired SEは0.00438743、samplingだけの約95%半幅は0.00859937。
固定した経験的識別閾値は0.01153142。差の絶対値がこれを超えなかったため、保存採否は difference_not_identified。
主実験後に閾値・seed・面を変更して差の検出を狙っていない。

二時点のjoint / conditional分布には点ごとの数値差が見える。
図の Asian decision はAsian価格だけの判定であり、二時点分布全体の同一性や差の同時検定ではない。
例えば S(0.5)∈[80,90) における P(S(1)>110) はHeston 4.2793%、local 5.8906%。
差 +1.6113 percentage points、paired ratio SE 0.1440 percentage points。
比の分母はそれぞれ25,074 / 25,006 pathsで、同じ経路集合を分母に強制しない。
区間はsamplingの点ごとの記述量で、格子bias・全bin同時coverageを保証しない。

## 固定契約と実装範囲

- 合成Heston: S0=100、r=.03、q=0、v0=.04、kappa=2、theta=.04、xi=.3、rho=−.7。Feller条件 .16>.09。
- 満期1年、Asian K100、算術平均の観測は i/12（i=1…12）。S0を平均へ含めず満期払。
- 内部stepsは192/384/768。内部全時点を平均に含めず、観測契約は固定する。
- 二時点は .5 / 1年。切点80/90/100/110/120に両側無限tailを含める。条件付きeventは S(1)>110。
- 固定パラメータのHestonから面を生成する実験。市場クオートへの較正は行っていない。
- CPU、torch-free、private。公開API・production依存・本編306節の台帳は変更しない。

| 部品 | 実装・検証 |
|---|---|
| _heston_local_surface.py | 安定CF、Riccati時間微分、密度/variance-weighted密度、Dupire局所分散、行ごとの支持域 |
| _model_dynamics.py | 共通normal driver、Heston full-truncation/log Euler、local log Euler、固定13観測、失敗/負分散数 |
| reference_methods.py | hullkitをimportしないown-CF Gil-Pelaez積分、calendar-time CN/Rannacher PDE |
| analytics.py | paired mean/SE、tail joint counts、モデル独自分母のconditional ratioとinfluence SE |
| pilot.py | Fourier次数/cutoff、面の時間/空間/翼/最小時刻、PDE空間/時間/域、粗細結合の包括検査 |
| build_reference.py | 承認済pilotと固定予算の検証、主3seed、原始配列checker/fresh replay、採否 |
| build_notebook.py | 保存成果だけから3図。金融計算・学習・ネットワークを実行しない |

## Pilotと主実験前の固定

pilotは8,192 paths / seed8117 / block2048。時間/空間を独立に倍増し、
baseline、time_refined、z_refined、joint_refined、z±4、z±6、最小時刻変更の7面を比較した。
Fourier次数と上限、PDEの空間・時間・領域を独立に変更した原始配列を保持する。

独立レビュー後、主実験前にjoint_refinedを選択した。
面は129 geom-times（1/4096…1）×161 z点（±5）、Fourier order1024、frequency_scale512、density_floor1e−10。
主paths65,536×3 seeds（9017/9029/9047）、block2048、steps192/384/768を固定。
review JSONの主設定・精度予算・選択面とprotocolを照合し、未承認の変更を開始前に拒否する。

比較は20 quotes（T=.25/.5/.75/1、K80/90/100/110/120）と、
8 holdouts（T=1/3,2/3、K85/95/105/115）。有限28価格の通過から全面一致を推論しない。
Fourier/独立CFの最大価格差は1.28e−13。選択面の独立PDE最大価格残差は0.00034396。
レビューでさらに細かくしたPDEでは約0.00036612となり、残差は単調減少しない。
格子/補間誤差の相殺を含み得るため、単一残差を連続時間の保証上界にしない。

## 主比較

各行は3独立seedの全196,608 pathsを集約。SEはlocal−Hestonのpaired payoffから計算する。

| 内部steps | Heston Asian | local Asian | local−Heston | paired SE |
|---:|---:|---:|---:|---:|
| 192 | 5.55194528 | 5.55694626 | +0.00500098 | 0.00441063 |
| 384 | 5.55139179 | 5.55535360 | +0.00396181 | 0.00439480 |
| 768 | 5.55084529 | 5.55451818 | +0.00367288 | 0.00438743 |

| Seed（768steps） | local−Heston | paired SE |
|---:|---:|---:|
| 9017 | +0.00172965 | 0.00757822 |
| 9029 | +0.00866154 | 0.00763076 |
| 9047 | +0.00062745 | 0.00758877 |

### 数値精度と誤差の種類

価格・誤差は通貨単位。step / surface項目は |paired refinement mean|＋1.96 refinement SE。
経験的な2水準変化で、厳密bias上界や全パラメータ域の保証ではない。

| 固定検査 | 実測 | 主実験前の上限 | 結果 |
|---|---:|---:|---|
| sampling_95_half_width | 0.00859936682 | 0.01 | PASS |
| heston_step_empirical_refinement | 0.00137384705 | 0.006 | PASS |
| local_step_empirical_refinement | 0.00120699961 | 0.003 | PASS |
| pilot_surface_empirical_refinement | 0.000351204903 | 0.0005 | PASS |
| pde_vanilla_residual | 0.000343960632 | 0.001 | PASS |
| fourier_vanilla_residual | 1.27897692e-13 | 1e-09 | PASS |

vanilla MC guardも各model×seed×quote/holdoutと集約でPASS。
許容値は6 MC SE＋経験的step allowance0.015＋選択面PDE残差。
6SEは実装診断であり、不偏性の証明や全価格面の信頼区間ではない。

Asianの経験的識別閾値はsampling半幅＋Heston step＋local step＋pilot surfaceの和。
vanilla PDE残差をAsian価格の誤差上界として足していない。
面/wing感度は別seedのpilotによる有限検査で、主経路全体や域外の真値を保証しない。

## 支持域・経路診断

Fourier支持判定は密度の符号/閾値、half-orderの相対安定性、端点CFの減衰を確認する。
未支持の密度/局所分散をclipせず、NaNとraw診断を保持する。
各行の連続支持域の端を定数延長してから時間補間し、訪問をflagsで記録する。
t=0はS0のv0だけを初期状態とする。最小正時刻より前のproxyも明示する。

選択面の20,769セルはすべて支持。z±6比較面では133セルが未支持で、NaNを残している。
主768stepsの失敗pathは両modelで0。
Hestonの負Euler variance状態は2,096、localのleft-wing使用は779 paths / 60,492 visits。
負状態を隠したり、wingを訪問した経路を除外したりしない。

## Asian差が小さいことの解釈

以下は定数r,q、平方可積分性、割引株価のmartingaleを仮定した計算である。
s<tなら E[S_t | F_s]=exp((r−q)(t−s)) S_s なので、

    E[S_s S_t] = exp((r−q)(t−s)) E[S_s²]。

従って、理論上すべての単一時点marginalが一致するmodelは、異なるjoint lawを持っていても、
固定重み算術平均の平均・分散が一致する。Asian call差は平均分布のそれ以外の形に依存する。
本実験の有限quote・補間・Euler近似を、この理論条件の厳密成立と同一視しない。
小さい価格差から「動学も同じ」または「ヘッジも同じ」とは結論できない。

## 成果・再計算

- reference.json / NPZ: 主3seed×3水準×両modelの全月次観測、failure理由・variance/status counts、
  面と支持診断、独立価格参照、pilot raw evidence、固定protocol/review snapshots、集計/採否。
- pilot.json / NPZ: 7面・Fourier/PDE収束・共通乱数の粗細経路・原始診断。
- 原始主archive 192,772,222 bytes / 1,393 arrays。pilot archive 28,967,239 bytes / 1,264 arrays。
  20MB超のNPZはGitへ入れず、既存C primary / F mirrorへ保存し、manifestを収録する。
- C/Fは別physical disk（0/1）と確認。各復元主NPZをpickle禁止で読み、数値checkerをそれぞれ実行してPASS。
- 主freshは同じ固定seedから面/経路/参照価格を再生成し、許容差rtol1e−9 / atol1e−10でPASS（115.27秒）。
  SHAはblob来歴・承認済文書の同一性に使用し、浮動小数点の数値正しさは許容差で検査する。
- artifact-only notebookは3PNG、error0/stderr0。図/軸/尾部/支持域/誤差内訳を目視確認した。
- 計算wall timeは記述的な実行費用であり、速度優位のbenchmarkではない。

repo rootから実行する。worktreeでは既存共有環境とそのcheckoutのPYTHONPATHを指定する。

    UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync --package hullkit python johnhull/research/RB-F04/build_reference.py --check --fresh
    UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync --package hullkit python johnhull/research/RB-F04/pilot.py --check --fresh
    UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv uv run --no-sync --package hullkit python johnhull/research/RB-F04/build_notebook.py --execute

archiveが無い場合はmanifestと接続済両保管庫を使って復元する。
--refreshは保存済主実験を上書きしない。新条件は別protocol / directory / reviewで扱う。

## 統合状態と次

独立最終レビューは [REVIEW.md](REVIEW.md) / [review.json](review.json) でapproved。
関連3suiteは7,316 passed / 6 skipped / 既存deprecation warnings2件（374.77秒）。
ruff / format、原始配列fresh・両復元、最新3図もPASS。tracked releaseはbranch/mainともPASS。c4430dfaをmainへfast-forward統合・pushし、mainでprimary保管庫復元と原始配列checkerを再確認した。

本編の追加artifact照合はworktreeでFAIL（158件）。基点main e803e00bでも同じ依存指紋69件がFAILし、
worktreeの追加89件はGit管理外のBook生成HTML欠如だけだった。既存本編source/証跡/台帳は変更していない。
この研究完了を本編306節の新しい全面再受入PASSとは扱わず、詳細はvalidation.jsonへ保持する。
F04の動的ヘッジ・barrier・別Heston域はこの固定比較の完了と区別し、後続研究として保持する。
研究順序の次はRB-F08 MLMC / RQMC CI。
