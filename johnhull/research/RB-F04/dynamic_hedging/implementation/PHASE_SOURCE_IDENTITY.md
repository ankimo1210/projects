# 正式実験のsource照合 — 限定source確認

2026-10-10。**source照合機能の限定承認。正式pilot・freeze・主実験・金融精度・研究受入は未完了。**

## 変更

`execution_source_identity` が研究側の10入口（reference_methods、run_fresh、check_fresh、run_pilot、check_pilot、run_main、check_main、run_reference、check_initial_quotes、check_selected_calls）と、private学習・検証module `deep_hedge_price._dynamic_hedging_closure` の存在を必須とする。欠けた入口を外部ライブラリとして処理しない。

研究側のbare importを同じディレクトリのcanonical moduleへ結び、関数内importを含む依存を再帰登録する。通常の外部ライブラリはそのまま環境versionへ記録する。同名のbare aliasが別checkoutから読み込まれていた場合は拒否する。

既存37quote保存検査の固定helperをstatic importへ変更した。一時的な検索pathはfinallyで復元し、cached aliasが他checkoutならhelperを呼ぶ前に拒否する。保存したCF/PDE数値を検算する算術は変更しない。

この変更はコードの所在と依存を照合する境界である。runtime monkeypatch、import後に同じpathで変更されたコードのメモリ内容、optimizer/RNG履歴や金融精度を認証するものではない。正式計画と実行は安定sourceの新規processを使い、各jobのsource/input bindingを照合する。

## 実在checkoutでの確認

10入口・closureを含む80ファイルを登録し、取得後の原ファイルdigestが観測中に変わっていないこと、未解決dynamic importが0であることを確認した。独立probeでも同じ境界を確認した。

このinventoryには別作者が開発中のpilot/fresh/main helperが含まれる。今回commitするのはroot-owned照合機能と証拠であり、80ファイル全部の実装・独立受入が完了したとは扱わない。inventoryのSHAは観測時点の由来であって正式freezeではない。

## 検証・修正経過

| 検査 | 結果・範囲 |
|---|---|
| 最初のcounterexamples | 5 RED：bare依存、loaded alias、全入口欠落の拒否 |
| 最初のscoped検査 | 45 PASS、29.55秒。後続の独立反例でclosure欠落が判明 |
| 独立closure反例 | missing closureを許したP1を修正。原counterexampleとrequest changesを保持 |
| 修正後 | 46 PASS、28.11秒。closureを事前必須検査しexplicit入口へ追加 |
| 実在inventoryからの追加修正 | 固定quote helperの動的読み込みが未解決扱いで残るためstatic importへ変更。追加2 REDを保持 |
| 最終scoped検査 | **48 PASS、29.01秒**。実保存37quotes、dynamic loader禁止、検索path復元・foreign alias拒否を含む |
| 最終独立検査 | **14 PASS、34 deselected、3.61秒**。著者48件へ足し合わせない |
| 変更Python2ファイル | Ruff check / format、diff whitespace PASS |
| 最終独立レビュー | 未解決0、宣言したsource境界のみ承認 |

一時的なdeep fixtureのloaded package隔離不足による最初のREDも区別して保持する。参照するmoduleのpathは一致しても、それだけで金融arrayの意味や実実験の完成を証明しない。

## sourceと原証拠

| 対象 | SHA-256（由来の照合用途） |
|---|---|
| 最終 `run_reference.py` | `f86f59a142492f31dc7348e65539555d4eeed4d02b226234021078d28751d9e2` |
| 最終runner tests | `e9da348cf6251411b02817b32c21a39941b0c06c298517304d5330f6f0eda8b3` |

[原証拠一覧](phase-source-evidence/files.json)。RED・途中/最終GREEN、原反例と修正後probe、独立レビュー、未解決importあり/修正後の実在inventoryを原byteで保持する。Python・log原証拠は末尾 `.txt` を付ける。数値の検算にSHAを使わない。

## 次の条件

正式pilotの全121case/51obligationと事前budget・cap scope・原入力・共通sourceを固定し、実jobと保存checkerを実行する。cap依存の未実行と後続独立jobを区別して全記録を残す。freshの保存算術・main全396件の実行器を独立確認し、その後に正式freeze/main/fresh、両CAS復元、3図、artifact-only notebook、全関連suite、最終独立受入・main統合を行う。
