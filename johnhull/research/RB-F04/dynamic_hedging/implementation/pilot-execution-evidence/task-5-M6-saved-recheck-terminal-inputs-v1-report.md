# M6 terminal saved-recheck 入力固定（2026-10-10）

## 結果

D-only の terminal input manifest を完成した。元の4class、N=1024、全2128node（108/156/520/1344）、原2driver/seed/global-ID、initial obligations、field、旧費用・cap履歴を保持する。新checkerの独立承認は未確定null、candidateはfalseのまま。

- Manifest: task-5-M6-saved-recheck-terminal-inputs-v1-manifest.json
- SHA256: e56e2b62b7584a48a0e489d679681b078cbcd545a264b85b0e745c80463b5d15
- 元M6 tree全13022ファイルを含む13155ファイル、5437727961物理bytes。
- 全2128 native nodeの既存root/pack bindingを原source recipeの由来と照合。全4339 physical receiptsのcanonical JSON、metadata SHA、NPZ container byte SHA、artifact origin SHAを確認した。
- 元生成source81の全bytesを旧固定snapshotから認証。identity=4e8f8b7bad48b9f6bf89b655cd115de835a9a486d89dd6d9ffafcad2b3cb64b0、dynamic importsは元空list。
- 独立M6 v2のinput26、evidence、terminal4class判定を再利用した。classes/shared SHA mapは既存saved-recheck interfaceの必須参照を満たし、各class directoryは全ファイル集合と一致する。
- old巨大checker artifactも物理bytesのSHA対象に含めた。NPZ member・金融配列は展開していない。NPY header／全金融内容の独立確認は既存M6 v2証跡を参照し、今回再実行していない。

## 状態の境界

Heston-coarseのみ元component completed。Heston-high、local-coarse、local-highは実RSS cap・unknown_unclosed_component、旧最終checker checkpoint欠落を保持した。生成済みraw-gridのexecuted状態と、旧component検査完了の有無を別々に記録した。

新bounded checkerの作業source identity d4a721c67c53a48bbabd7408c52d9ef5a5dfeb1770eaa2f242acaa625bf1c0dbはauthorから受領した別境界であり、このmanifestでは承認しない。rootが新sourceの独立承認・closureを固定し、別名prior budgetを作成してからsaved-only recheckを実行する。旧initial-descriptionのterminal=falseは準備当時の観測として書き換えていない。

全旧費用はhistory_cost_receiptsとして認証する。新検査費用に旧生成・旧失敗checker費用を足し直さない。金融qualification、formal pilot/main/phase、速度予測はunknown／未承認。

## 検証・実費

行政12case PASS。receiptのcanonical違反／metadata改変／opaque bytes改変／artifact由来変更／未知schema／入力欠落を拒否し、全入力集合・旧3cap・source approval nullを確認した。Ruff2・format2 PASS。金融array decode/RNG/solver/SDE replayは0回。

成功作成は親込みwall20.966851276秒、child CPU20.951124秒、kernel peak RSS120061952bytes。保存・再読・全byte hashing・metadata/binding検査・stdout/log生成を含む。費用receipt自体の最終write tailはunknown。

試行1は旧dynamic_importsが空listであることをint=0と誤指定して拒否された（0.103851803秒）。試行2は同じpack metadataの反復読取を止めるため、自分の行政producerだけをSIGTERMで終了した（79.010660905秒、exit -15）。原M6 capとは分類しない。両試行のsource/log/costを保持した。局所metadata cacheで同じ入力検査を維持して成功した。

行政検証/Ruff/log保存の親込みwall1.071899098秒。測定済み4工程のwall合計は約101.153263081秒、child CPU合計99.120682秒。事前の読取・script編集・最終report/manifest receiptの未測定tailはunknownで、0とも元金融費用とも扱わない。

## 範囲

変更はD内のproducer・manifest・検証・費用・reportのみ。production source、tests、docs、Git、CASは変更していない。元金融rawを生成・変更せず、新金融実行も行っていない。
