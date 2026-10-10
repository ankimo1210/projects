# 4fitの空ゲート・元validationの限定source確認

2026-10-10。**対象2fileの独立レビューapproved、未解決0。正式pilot/freeze/mainは未実行・未承認。**

## 修正

execution candidateの原4fitはnumeric gates=[]だった。従来のall(empty)=trueによって元checkpoint validationが未知でも空測定だけでqualifiedになり、逆にcompleted optimizer＋validation unknownをmeasured_precision_failureへ正しく写すと拒否された。

4fitのwithin_envelope/empty-gate measured_precision_failureだけにfit_validationを追加した。原fit ID・training N・prior validation N・原evidence SHA・first_failure_dateを束ね、元optimizer完了を要求する。completed/qualifiedのvalidation verdictはwithin_envelope、failed/unknownのverdictはunknown closureへ写す。validation_statusは元fixed-checkpoint検証の数値判定であり、checkerが実行を終えたかとは別である。元理由・unknown・分母・rawは消さない。

既存cap/構造拒否、empty readiness attempts、非空numeric gates、候補N/閾値/selectionとstrict金融v1は変更しない。Aはdetached metadata guardであり、金融rawやreviewerを認証する処理ではない。全欄を任意に製造できる環境への真正性は主張しない。実rawの再計算と値抽出はcheck_pilot側で別に確認する。

## 検証

- 追加15test cases。旧sourceの修正済REDは13 failed/3 passed（既存control1件を含む）、最終専用moduleは65 passed/1.20秒。
- 最初のREDにはstate controlのfirst_failure_date fixture誤り1件があった。原logを保持し、fixtureだけ修正したREDで本来の13反例を再確認した。
- Ruff/format2file PASS。独立reviewerも65 passed/1.20秒を確認した。同じ65を加算しない。
- 独立19mutationはsynthetic verification/reviewをresealしても全拒否。prior N欠落/0/bool、原fit/N/evidence/first_failure差、optimizer未完/source error、fake qualified等を含む。
- 全4fit同時unknownでも原121cases/51attemptsを保持し、execution readinessのみ閉鎖。financial qualificationはunknown。
- AST検査で元21関数不変、新helperと限定_pilot guardだけ追加。strict v1のSHAは5f63d5871cdf6871f83fb08bf8f403b556cf6730c40430c0fc391f5da29bda0fで不変。

## 固定sourceと証跡

| ファイル | SHA（由来のみ） |
|---|---|
| deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_execution.py | fad2c73a27b8314b9cdfa5db8505fb56c382b4eab79ce4224aa475b450223b3e |
| deep_hedge_price/tests/test_dynamic_hedging_execution.py | f1c9ea790144072e3be186acf72bd900b0e06145ffe054c13c3874cd5b4546ae |

[独立最終レビュー](empty-fit-evidence/task-5-empty-fit-independent-final-review-findings.md)・[原byte一覧](empty-fit-evidence/files.json)。

正式planの段階N選択/全費用・cap結合/controls・予算・domainと、check_pilotの実raw写像は別gate。全suiteは研究phase最終gateで一度実行する。
