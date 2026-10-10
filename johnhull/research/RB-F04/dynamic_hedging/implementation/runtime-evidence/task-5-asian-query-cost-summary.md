# Asian query 部品コスト — 2026-10-10

## 結果

原 coarse/high 軸・12月次日・local t0専用spot5・16block の実 evaluate_asian を6,912回計測。元18状態の S/Q を元 bump_query_chunk（幅1,.5,2／diagnostic hS=.05,hQ=.01）で各grid/model13回再fitし、計936query・72groupを実行。同じ936queryのfit-onlyも別に測定した。RNG/MC/教師学習なし。事前cap300秒、実測envelope wall12.715秒／CPU12.700秒で終了。

| 格子・モデル | Asian成功平均 ms/query | fit＋Asian平均 ms/query | 同query fit-only平均 ms/query | 13query group中央値 ms |
|---|---:|---:|---:|---:|
| coarse / heston | 0.185 | 0.466 | 0.265 | 6.151 |
| coarse / local | 0.288 | 0.583 | 0.252 | 7.659 |
| high / heston | 0.210 | 0.511 | 0.278 | 6.757 |
| high / local | 0.714 | 0.953 | 0.259 | 12.846 |

表のAsianはfull original-axis fixed-box mode。historical global modeも結果JSONに別保存した。平均の差は独立に時間を測った参考差であり、厳密な処理内訳や正式時間の下限ではない。unknown早期終了は成功時間と分離。t0の5spot／各日／各queryのwall/CPU start-stop、中央値/p95、raw/status/16block/covarianceを保存。

## 入力と scope

- Asian格子は現 run_pilot.teacher_axes をそのまま取得：Heston coarse9×33、高13×65；local coarse9spot×5ell×33、高17spot×7ell×65；12dates、専用t0spot5。全16×3block曲線を保持。
- 原18個のS/Q・保存済モデルfit状態は selected-calls/refined/selected-calls.json。Heston最終日S80の未知状態はNaNを保ち、代替値で補わない。
- memoryは説明済fixture：月次post-fixing n、既往n−1個のfixing100＋最新/current S；t0はsum0。実際の過去市場経路を認証した入力ではない。全12日を埋める追加query fixtureも別ラベル。
- Asian meanは解析的な滑らかなproxy、16blockは決定論的offset。数学処理の形／計算量を測るためのdense fixtureであり、教材金融値・IID統計・教師precisionを認証しない。dense cache original_N=None。
- 同call cache/domainはroot scalar probeと一致：S65、Heston v33 [1e−5,.5]／local ell7 [.25,4]、原6selecteddates。実CF/PDE buildはH5.301秒／CPU5.297秒、local3.094秒／CPU3.093秒。金融precisionはunmeasured。
- full-domain refit原roots/residual/Ctheta/condition/unknown理由と全13raw claimを結果JSONに残した。ill_conditioned/no_rootを成功扱いしない。
- 元formal N、main/test seed streamは未開封・未生成・未変更。np.random.default_rng/normal/standard_normalは禁止して実行した。

## bump入力の相違

今回のdiagnosticは hS=.05,hQ=.01、正式producerは hS=.02,hQ=1e-4（いずれも幅1,.5,2）。同じfull-domain再fitアルゴリズムの部品コストを測ったものであり、正式bump入力での再現・金融bias・Greek精度を検証した測定ではない。特に大きなQ bumpのno_root/conditioning/support分布を正式入力へ転用しない。元の事前plan・script・rawは改変せず相違を保持し、不要な再計測はしない。

## 未測定と利用制限

正式教師生成・学習・precision/validity envelope、訪問する全パスのsupport分布、実際の限定patch、396evaluations/12fits、全serializer/savedcheck/CAS等は未測定。outer clockは最終結果JSONの書込／stdoutを除く。構築と別fit-onlyを含むphase totalを integrated group timingに混ぜない。温まったbasis・単一thread/OpenBLAS1でのsource-unit観測であり、正式実行時間・source-wide金融資格への読み替えは不可。金融qualificationはunknownのまま。予算には不足していた部品の参考実測として使い、正式wallは別途計測する。6,912/936件から正式Nへ換算するものは部品の参考推計であり、独立予算審査の対象とする。実測時間や金融qualificationへ読み替えない。

## 証跡と source固定

task-5-asian-query-cost-{plan.json,probe.py,probe.txt,results.json,summary.json,snapshot.json}。results.jsonは全6,912query timing、初回432raw、全72×13bump raw、原axesとdense入力SHA、raw status、入力SHAを含む。所有4sourceのSHAはfresh cap-cost-fix最終snapshotと一致、使用source全7件もbefore/after一致。source／Git／正本文書の変更なし。
