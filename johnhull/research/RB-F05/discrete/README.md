# RB-F05 離散バリア — 微分教師とDML

更新2026-10-09。**離散バリアv1の数値pilot・主6fits・精度/費用比較・教材・独立レビューを完了。main統合済み。**
既存digital v1と区別し、0DTE・rough・動的ヘッジは後続とする。

[独立レビュー](REVIEW.md)／[主結果](reference.json)／[3図のnotebook](discrete_barrier_dml.ipynb)／[protocol](protocol.json)／[実施計画](../../../docs/superpowers/plans/2026-10-09-discrete-barrier-dml.md)／[追加調査](../../../docs/prep/design/RB-F05_DISCRETE_RESEARCH.md)。

## 結論

**DMLは全3seedでprice-only NNを改善した。教材として保持し、標準高速器へは採用しない。**
固定2入力問題では、強いHermite補間がDMLより価格約64–77倍、Delta約99–117倍高精度で、準備費用も小さい。
DMLの推論時間が短いことだけを採用理由にしない。固定GBMの結果を実市場・較正・ヘッジ改善へ外挿しない。

| Seed | price-only価格RMSE | DML価格RMSE | price-only Delta RMSE | DML Delta RMSE |
|---|---:|---:|---:|---:|
| 11 | 0.0554403 | 0.0231837 | 0.0173016 | 0.00569780 |
| 29 | 0.0580777 | 0.0279957 | 0.0205833 | 0.00608412 |
| 47 | 0.0656552 | 0.0266067 | 0.0213356 | 0.00671777 |
| Hermite | — | 0.000363767 | — | 0.0000576622 |

DML/price-onlyのRMSE比は価格0.405–0.482、Delta0.296–0.329。表はraw推論で、fallbackの参照値を混ぜない。
safeテスト結果・routeは別に保存する。負Deltaを許容し、出力価格をclipして見かけの精度を上げない。

## 固定契約と学習

配当なしGBM、K100/H120/r3%/sigma20%、rebate0のup-and-out call。
監視集合は{0,T/12,...,T}（13時点）、接触S>=HでKO。区間内のbridge KOを追加しない。
S80–119/T.25–2、DeltaはK/H/r/sigma/T/mを固定したspot微分。
時点0監視のためS=Hでは価格がジャンプし、通常のDeltaは未定義。
S=119.999の参照価格はT.25/1/2で1.30909/0.548898/0.331388、S=120では0/NaN、S>120では0/0。
S<Hの価格を0へ接続しない。変更契約はunsupported、数学的無効入力はinvalid。

train512・validation128、1入力4096 IID paths、test25 spots×8 maturities。
主教師は実際のMC経路から得た最終増分条件付きpayoffと初回transitionのLRM。
price-onlyとDMLは同じ価格ラベル・初期重み・batch順を使う。
2→32→32→1 tanh、内部S/logT、CPU float64、train-only尺度。
seed11/29/47、512 updates、batch128、Adam .003、fit cap120秒。全6fits完了、失敗0。
共通CPU scalar Adam初期化は単独導入ごとに1回の費用とし、fit capには含めない。
保存weightのNumPy価格・Delta再生と最終lossを許容差で確認し、検査では学習しない。
主生成commitは35fe9280。source SHAは来歴で、数値のPASS条件には使わない。

## 教師・独立数値検証

| 方法 | 用途と限界 |
|---|---|
| m1 CDF式・独立密度積分 | payoff K<ST<Hの検算。解析条件付き値はMCと区別 |
| Gaussian Markov積分 | 監視時点だけkill、strike分割GL、初回score Delta。同じTのtransitionをcall内で共有 |
| 独立log-PDE | Hより上を監視間は保持。Rannacher、空間/時間/領域/位相/bumpを個別診断 |
| raw / conditioned LRM | 実IID paths。初回score=Z1/(S sigma sqrt(T/m)) |
| naive / 部分conditioned PW | 途中の監視境界寄与を落とすbiased負対照 |
| one-step survival | 条件付き状態と生存確率の重みを両方微分。未支持pathを除外しない |
| Hermite | 65 spot×33 logT格子、spot価格の同じ導関数をDeltaとしlogTで線形blend |

pilotは主実験前に独立レビューしprotocolをfreezeした。GL128/256、tail12、
独立PDE4800 space×256 steps/monitor、half-width1.5、barrier phase=.5を主条件とする。

| 証拠 | 実測 |
|---|---|
| pilot PDE/GL最大差 | price1.55596e-4、Delta3.11899e-5 |
| 主PDE200点8満期/GL最大差 | price1.53798e-4、Delta3.11899e-5 |
| 固定照合許容差 | GL price1e-7/Delta1e-8、独立PDE price5e-4/Delta2e-4 |
| 主65,536 paths診断 | 価格・Delta116/116が6SE＋積分誤差以内 |
| train/validationラベル診断 | 1024/1024、256/256が同条件内。SE0なし |
| PW負対照の識別 | naive19/20、部分conditioned17/18が6SE外 |
| OSS未支持・underflow | 全20主診断点で0 |
| raw pilot NPZ | 158,401,006 bytes、両保管庫から別々に復元PASS |

6SE診断は不偏性の証明・全域の上界・信頼区間ではない。
PDEの位相0は価格最大0.0258/Delta0.00249のaliasingを示し、同精度のoracleには使わない。
固定m12の格子収束とm1/4/12/48の監視頻度比較は別の問い。
価格打切り上界はpayoff cap×下側tail union probability、Deltaは初回scoreのCauchy–Schwarz上界。
GL次数/PDE格子誤差を打切り上界に含めない。
OSS proposal件数を元契約の生存数と解釈せず、mean(survival_weight)を使う。

## 計時・費用

全8方式×raw/safe×batch1/32をwarmup3後20反復。32測定の返却価格・Delta・routeを保存し独立replayで照合。
oracleは全方式で同じGL128/256＋tail12のchecked batch参照。固定設定・importをtimer前に準備し、入力結果のmemoはしない。

| raw価格＋Delta | DML 3seed中央値 | Hermite中央値 | checked GL中央値 |
|---|---:|---:|---:|
| 1入力 | 14.1–15.4 µs | 27.1 µs | 7,839 µs |
| 32入力のwhole batch | 28.3–28.8 µs | 40.7 µs | 11,993 µs |

単独NNの測定準備費は教師＋共通初期化＋fit elapsed＋exportで、DML約2.15–2.20秒。
setup/trainingはelapsedの内訳で、二重加算しない。Hermite格子生成/構築は約0.170秒。
loadは**計時配列を追加する前の主fit bundle（287,346 bytes）**を3warmup後100回全decodeした値。
中央値5.847ms/p95 6.197msで、最終332,089 bytesのarchiveを測った値ではない。
各単独NN/Hermiteへこの1回のwarm loadを課す条件付きscenarioである。
cold IO・process start・import・最小standalone packagingなどは未計測と記録し、0費用に置かない。

測定境界内の対oracle回収はraw単発でDML276–282 calls、Hermite23 calls。
32入力batchではDML181–185 calls、Hermite15 calls。
N queriesにはceil(N/32)のwhole/padded callsを課す。p95成分の和は総費用のp95実測やCIではない。
safe32はOOD2点・H接触・KOを含む。Hの通常Deltaが未定義なので、
全方式のlatencyを残し、price＋ordinary Deltaの成功速度/費用回収比較はunsupportedとする。
safe1と域内safeテストの数値は別に保持する。価格boundsの通過はGreek精度を保証しない。

## 成果と再計算

- reference.json/npz：入力、ラベル/SE/seed/count、独立参照、全重み、raw/safe予測、計時出力、100 load samples、会計。
- pilot.json：設定・収束・全教師summary。通常checkerも4streamのdrawを再生成し、教師/summaryを再計算。
- pilot_manifest.json：大きなraw normal/uniform/path samplesの保管庫参照。Gitにraw pilot NPZを格納しない。
- C primary / F mirrorは2026-10-09にdisk0 / disk1の別physical diskと確認した。
- discrete_barrier_dml.ipynb：artifact-onlyで3図、error0。学習・ネットワーク・GPU検出・raw pilot NPZの読込みなし。
- REVIEW.md：教師/runner、200点の独立PDE、保存NN、32計時/費用、境界と採否の独立記録。

repo rootから実行する。作業worktreeでは該当checkoutのhullkit/deep_hedge_price/srcをPYTHONPATHへ指定する。

    uv run --no-sync --package hullkit python johnhull/research/RB-F05/discrete/build_reference.py --check --fresh
    uv run --no-sync --package hullkit python johnhull/research/RB-F05/discrete/finalize.py --check
    uv run --no-sync --package hullkit python johnhull/research/RB-F05/discrete/build_notebook.py

refreshは主fit用build_referenceと計時用finalizeに分離。上の通常検査では再学習・再計時しない。
主recordのpaired採否とbenchmark/costsの検査は別のgateで、保存PASSフラグを証拠としない。
公開API、依存、本編台帳、既存教材の契約を変更していない。

## 統合状態

関連3suiteは2026-10-09に7,104 passed／6 skipped（366.24秒）、既存deprecation warnings2件。独立最終レビュー・fresh再計算・計時/会計checkを完了。09b8c1afをmainへfast-forward統合。mainでrelease gate、pilotのprimary保管庫復元、主保存重み/32計時・会計checkを確認した。研究の次はRB-F04。
