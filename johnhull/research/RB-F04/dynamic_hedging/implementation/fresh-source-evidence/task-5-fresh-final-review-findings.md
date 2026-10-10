# Fresh final snapshot 独立再レビュー

## 判定

**request_changes: Critical 0 / Important 2 / Minor 0。** 初回I1/I2は解消。新savedcheckerの費用/cap結合にI3/I4が残る。金融資格・正式pilot/mainは承認しない。

## 新指摘

### I3: 保存したrawのcapが固定job budgetへ結び付いていない

固定job receiptがeffective300秒でも、table/oracle/teacherのraw cap_secondsを150へ変えてraw provenance digestを更新すると全check_freshが通る。oracleのcap_evidenceをNoneにしても通る。_capは内部elapsed/overrunだけを照合し、Noneなら抜けるため、mandatory固定budgetを検査していない。

record.jobsの対応effective capとraw cap/deadline/区間を結合し、実job/子expenseが同じphase/parent jobに含まれることを検査すること。exact branchの例外は明示する。generic source errorをcapへ分類してはならない。

### I4: CPUの実測を失っても費用を受け入れる

phase costのclock.cpu_start/cpu_stopを削除しcpu_secondsをNaNにしても、再封印した全check_freshが通る。_clockはcpu_startがある場合のみCPU検査するため、実測が欠落しても拒否しない。

actual cost/expenseでは有限・非負CPU elapsedとstart/stopを必須にすること。wall-only cap receiptは別の明示検査モードへ分け、ゼロを捏造しない。

## 独立実証

- 専用56件PASS31.65s。author56と同じテストを再実行したもので112件とは数えない。
- 4Python Ruff/format --check PASS、前後SHA一致。
- 作者の既存source-unit-v2はtransitive pilot/main4source更新で正しく拒否した。旧raw/receiptsを再sealせず別原出力を保存。
- 両authorが45秒sourceを停止した間にcurrent fullregistryで別directoryのsynthetic metadata source-unitを生成。原N1024/13query/paired768+1536 inputs/rawをimmutable保存→実load→savedcheck→checked保存PASS。
- savedcheck時にはdefault_rng、CF/PDE、directMC、teacher_restartを禁止してPASS。金融unknown・前段生成未検証を保持。
- posttest main parent receiptを別に渡してもpretestplan SHAは不変。
- I3の4variantとI4の1variantがすべて誤受理される原反例をtask-5-fresh-final-review-live-probes.py/json/txtへ保存した。

## 原本と範囲

I1/I2初回reviewとI3/I4原counterexampleは変更しない。完全4SHA/実scoped stdout/元receiptはtask-5-fresh-final-review-findings.jsonと関連ファイル。正式pilot/main/fullpremium/金融precision/研究受入は未実行。source/tests/Git/docs変更なし。
