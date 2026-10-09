# Task 5 execution runner independent source review

## 判定

**Important I1: 既定の source closure が execution 契約の必須ファイル2件を欠く。修正前の実入口は受入不可。**
Critical 0 / Important 1 / Minor 0（現段階）。

runner source: d0c056223db903589fe06eda6ce2996628cc6615874acb4cf1792a7f47ce4214
runner tests: ff35642d4e1b87a24eb4bf2517d096d15d60ed333f70e4f1d87353933c8b12a4

## I1

対象: run_reference.py:88 の source_identity default entrypoints。

実 source_identity()[protocol_source] は新 _dynamic_hedging_execution.py を含むが、
execution_candidate の required_source_files にある次の2件を含まない。

- johnhull/research/RB-F04/dynamic_hedging/reference_methods.py
- johnhull/research/RB-F04/dynamic_hedging/run_fresh.py

実 A の execution_fixture() を使い、source を現在の実 registry に置き換え、
fixture の検証 receipt を reseal した上で、未置換の freeze_execution を呼ぶと
ValueError: missing source dependency で拒否される。
run_execution_main も supplied source を同じ既定 registry と照合するので、
caller がファイル2件を独自に足すだけでは整合を満たせない。

修正: execution で必要な2入口を実 runner registry の roots に加え、
A の実 gate と全 raw fit / validation closure を結合する bounded fixture test を追加する。
これは synthetic metadata の境界検証であり、実金融 freeze の承認ではない。

## 証跡と境界

同名 .py / .json / .txt に再現コード、source4files SHA、未加工出力を保存した。
probe の金融 RNG・solver・main test loader 呼出は0。
親の scoped35 GREEN は報告値。今回の初回 probe は上の実 gate 不整合を検出する限定実行。
旧 gate の隔離・snapshot・domain 経路の追加確認は修正後 rereview で行う。

全 suite / 正式 pilot / freeze / main / 金融 precision / Q / refinement / expense / fresh は認証しない。
