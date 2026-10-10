# 主実験の依存cap入口 — 限定source確認

2026-10-10。**入口の限定source承認。正式pilot/freeze/main・金融精度・研究受入は未完了。**

## 変更と境界

run_execution_main は、実source・raw選択・元12fitの事前gateを通った後、execution_status=unexecuted_dependency_cap のケースだけ run_main.dependency_cap_evaluation へ渡す。元Nは frozen selection と一致を要求し、dataset/riskを読まず政策を実行しない。親capのraw・receipt・事前budget・費用・source/inputを照合する責務は実helperと保存checkerにある。

helper例外はsink前に伝播する。正常ケース、36回のsink、保存例外、旧strict v1は保持する。旧strict v1にこの別execution経路を開放しない。成功したゼロ損失・no-hedge・直前holdingで未実行を埋めない。

## 検証

| 検査 | 結果 |
|---|---|
| TDD | 追加3 RED → 全runner **51 PASS、32.54秒** |
| 独立限定レビュー | **approved・未解決0**、6 PASS、4.08秒 |
| root変更Python2ファイル | Ruff check / format・diff whitespace PASS |
| 実helperとの合同unit | main側の actual parent cap/helper で18ケース×2集合×11政策の396枠、元N32768を保持 |

runner側3件はstub helperの入口検査であり、親金融arrayの正しさを証明しない。合同unitもsource registryは合成fixtureで、reserved RNG/政策は開封していない。396枠の保存能力と正式396件の金融実行を区別する。main作者のrisk chunk修正・producer/checker全体は別途独立レビューを要する。

RED原logの末尾には、証跡読取補助スクリプトのsubstring例外も含まれる。pytestの3件のREDとは区別し、原logを編集しない。最終51件は成功したpytest実測である。

## 証拠と次の条件

[原証拠一覧](dependency-cap-evidence/files.json)に固定source SHAと原RED/GREEN・独立レビューを保存。数値一致をSHAで判定しない。

正式pilot全121case/51obligation、元N・seed・全費用・cap scopeの固定と独立レビュー、正式金融main/saved-check/fresh、両CAS復元、3図/notebook/全関連suite・最終受入を残す。
