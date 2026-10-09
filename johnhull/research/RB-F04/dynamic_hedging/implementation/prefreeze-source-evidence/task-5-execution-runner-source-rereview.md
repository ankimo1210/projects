# Task 5 execution runner independent rereview

## 判定

Critical 0 / **Important 1 (I2)** / Minor 0。CLI修正前のsnapshotは承認しない。

runner source: ee85c0f22b0fd709bd0f3573be38a0fbc0c08602584e5ce3fb4fe1fc28b95f7b
runner tests: fab67dae8c860bff362f99dd0843c160fb6a58dce1cb08343f6826f0e9cd262f
依存4files SHAは同名JSONに保存。

## I1の対応確認

execution_source_identityは専用5入口の実ファイル存在を確認してからtransitive registryを作る。
旧run_main/tinyのsource_identityは変更せず、common boundaryのproviderを入口ごとに選ぶ。
実run_fresh未実装は ValueError: required execution source missing: run_fresh として明示拒否し、
test loader呼出0。実mainが開ける状態とは判定しない。

## I2: execution-main CLIが旧providerのsourceを渡す

対象 run_reference.py:1162。entryとcandidateはphaseを選ぶが、source引数が常に
source_identity()[protocol_source] のままなので、専用execution_source_identityとの
照合を満たせない。

source providerだけを合成registryへ置き換え、実Aguard・raw fits・全validationを保持した
CLI probeは main.source_identity: saved keyset mismatch で拒否。test loader0回。
同じ合成sourceとclosureを直接APIへ渡した場合は正常に単体loaderへ到達する。

修正はCLIでphaseに応じたsource providerを選ぶこと。
未実装sourceの明示拒否、旧mainのsource providerは維持する。
独立反例原本は -cli.py/json/txt に保存。

## 独立14probes

実missing-source拒否、合成source providerのみを差し替えた実Aguard正常到達、
candidate N / frozen precision / source / rawfit N / weights / prior checkpoint digest /
rawloss truncation / baseline rescue / expense deletion / closure binding の10反例、
旧strict gateの拒否、loaderによる6入力mutationからsnapshotを保全する36 supplied-data評価を確認。

全12fit attempt・4×14 validation candidate の原2048lossを保持。
全baseline None、precision_selection unavailable、qualification unknownを維持する。
元rosterのstudy評価はmockであり、原32768経路の実金融評価はしていない。
金融RNG・teacher・solver・trainの呼出を禁止して実行した。

## 検証と境界

親の38tests PASS/Ruff結果は報告値。今回は追加14probesとCLI反例を独立実行した。
CLI修正の最終snapshotでscoped suiteを再実行する。
初回probeはevidence_sha256をinputsのdigestと誤認した。実契約は外部証跡SHAの形式と
inputs bindingを別に確認するため、正しい反例をinputs.closure変更へ訂正した。
失敗コード・原出力も保持した。金融証跡の実内容承認はしていない。

元I1 reviewと本I2原本を維持。ソース/Git/docs変更0。
正式pilot/freeze/main、金融精度、Q、refinement、expense実測、fresh実装は未承認。
