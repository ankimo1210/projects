# RB-F05 離散バリア — 微分教師とDML

更新2026-10-09。**private教師・独立PDE・OSS・学習器を実装し、固定数値pilotを完了。protocolは独立レビュー後にfreeze済み。主学習、計時、最終教材、研究受入は未完了。**

[設計§7](../../../docs/prep/design/RB-F05_DESIGN.md)／[追加調査](../../../docs/prep/design/RB-F05_DISCRETE_RESEARCH.md)／[実施計画](../../../docs/superpowers/plans/2026-10-09-discrete-barrier-dml.md)／[protocol](protocol.json)。
既存[digital v1](../README.md)の成果・本編306節・公開APIは変更しない。

## 契約と比較

配当なしGBM、K100/H120/r3%/sigma20%、rebate0のup-and-out call。
主監視集合は{0,T/12,...,T}（13時点）、接触S>=HでKO。区間内のbridge KOを追加しない。
S80–119/T.25–2、DeltaはK/H/r/sigma/T/mを固定したspot微分。
時点0の監視によりS=Hで価格がジャンプし、通常のDeltaは未定義。
左側価格を0へ強制せず、負Deltaを許容する。

| 方法 | 用途と限界 |
|---|---|
| 1回監視のCDF式・独立密度積分 | payoff K<ST<Hの検算。条件付き解析値はMC教師と区別 |
| Gaussian Markov逐次積分 | 監視日だけkill、strike分割GL、初回transitionのscoreでDelta |
| 独立log-PDE | Hより上を保持し、監視日にkill。Rannacher、空間/時間/領域/位相/bumpを別に診断 |
| raw LRM | actual IID paths、score=Z1/(S sigma sqrt(T/m)) |
| 最終増分conditioned LRM | 最終乱数を積分、初回scoreを保持。主学習のnoisy教師 |
| naive PW / 部分conditioned PW | 途中の監視境界寄与を落とすbiased負対照 |
| one-step survival | 生存確率の重みと条件付き状態の両方を微分。未支持pathを除外せず保存 |
| price-only / DML | 同じMC価格教師・初期重み・batch順・updates、spot Deltaだけを学習 |
| Hermite補間 | spot補間価格の同じ導関数をDeltaとし、logTで線形blend |

## 固定pilotの結果

S80/100/115/119 × T.25/1/2、m12。GL32/64/128/256、tail10/12、
独立PDEのspace/time/domain/phase、同じ価格のbump2幅とspline Deltaを比較した。

| 証拠 | 実測 |
|---|---|
| GL64→128/256 | 候補許容差 price1e-7／Delta1e-8を全12条件で満たす |
| finest PDEとGLの最大価格差 | 0.000155595887616 |
| finest PDEとGLの最大Delta差 | 0.0000311899153121 |
| PDE候補許容差 | price5e-4／Delta2e-4。pilot点で成立、領域全体の精度保証とは呼ばない |
| m12 raw/conditioned/OSSの価格・Delta | 72/72が6SE＋積分誤差以内、OSS未支持0 |
| m1/4/12/48の独立頻度診断 | 解析条件付き値をMCから除外し44/44が6SE＋積分誤差以内 |
| PW負対照 | naive/部分conditioned各11/12が6SE外。頻度診断は8/8・6/6 |
| raw pilot NPZ | 158,401,006 bytes、両保管庫から別々に復元PASS |

node-aligned phase0は価格最大0.0258／Delta0.00249の差を生じ、同じ精度のoracleには使わない。
6SE診断は不偏性の証明や多重検定の信頼区間ではない。
価格の打切り上界はpayoff cap×下側tail union probability、Deltaは初回scoreのCauchy–Schwarz上界。
GL次数・PDE格子の誤差を、この打切り上界へ含めない。
OSS proposalの経路件数は元契約の生存数ではなく、mean(survival_weight)を生存確率推定として扱う。
SE0・正payoff数・生存数・underflowを分けて記録する。

## 成果と再計算

- [pilot.json](pilot.json)：設定・全数値summary・乱数来歴・収束。保存PASSだけを検査根拠にしない。
- [pilot_manifest.json](pilot_manifest.json)：大きなraw normal/uniform/path samplesの保管庫参照。
- `pilot.npz`：ローカル成果。Gitへ格納せず、primary C／mirror Fの不変blobから復元する。
- `pilot.py`：固定pilotと通常checker。通常でも4つの独立streamのdrawを再生成し、全教師とsummaryを数値再計算する。
- `reference_methods.py`：金融教師をimportしない独立密度/PDE。
- `replay.py`：torch-free保存NN/補間再評価、OOD・価格bounds・KO/未定義を分けた提供処理。

CとFは2026-10-09に別physical disk（disk0/disk1）と確認した。
数学的に有効なOODは精度成立を確認したMarkov参照へfallback。
変更契約はunsupported、無効入力はinvalid、価格範囲を破る参照はoracle_failure/NaN。
価格boundsのPASSはGreek精度を保証しない。

## 次の工程

独立pilotレビューとprotocol freezeを完了。次は6fitsと独立主診断を一度実行する。
教師SE、参照誤差、NN近似誤差を分離。全3seed・強い補間対照・raw/safe・総費用を保持する。
学習を起動しないfresh check、artifact-only3図、独立レビューと採否、main反映で研究を閉じる。
0DTE・rough・動的ヘッジは後続の研究で、本研究の完了として数えない。
