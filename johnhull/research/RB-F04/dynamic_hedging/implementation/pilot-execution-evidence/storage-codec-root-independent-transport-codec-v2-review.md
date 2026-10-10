# typed DAG transport v2 — 限定独立レビュー

**判定：保存transportとW2入口配線の範囲で承認。金融精度・正式pilot/main・phase受入・容量/RSS/実速度・予算は未承認。**

## 確認

- 作者の固定manifest f81560c1… と9項目の実byte/snapshot一致。helperは ac98536b…、root runnerは 9d007adb…。
- 元v1の自己整合反例（NPZ 194 B／展開NPY 80 B／uint8 shape 1 GiB／本文なし）は、そのままv2でprotocol reader **0回**で拒否。巨大配列allocationなし。v1 REDは independent-page-blob-header-RED-v1.md に保持。
- 独立small probe **3項目PASS**：元反例、実参照関数・Parameters ASTに基づく値/NaN/許容誤差とdigest由来照合、dict/list/array/Parameters各出現の独立性・書換え隔離、publish失敗時の非公開root保全。128 Bページでmetadata 20／array 11ページを横断。
- 限定pytest **17 passed / 0.96 s**：root malformedNPYをprotocol前拒否、真正旧PACK読取、unknown schema拒否、自己整合page roster/table未使用・参照範囲・receipt/symlink拒否。
- root guardはrunner 1956行、protocol readは1957行。完全なsource diffで旧teacher writer/legacy reader本体の変更なし。_teacher_storage.py はW1と同SHA 6a1ea6e5…。他runner 72関数、reference 23関数はAST不変；reference変更はhelperのsource必須登録だけ。

## 境界・費用

64 MiBはページの元ストリーム上限であり、完全な戻り値・DAG表・単一JSONL record・protocol root/wrapper JSONの全RAM上界ではない。配列のlogical値、元N・unknown/failed・16blocks・費用を削る方式ではない。SHAは保存由来の認証のみ。旧rawが読めても旧sourceのresume承認にはならない。W1/source/live/native/CAS/Gitは触れていない。

small probe 0.036258 s wall/CPU、限定pytest親1.235618 s wall・1.232099 s CPU。読み込み・shell・全レビュー・記録までの総費用は未測定。初回pytestはnamespace/conftest import環境で収集前停止（tool wall0.547566 s）；原logを保持し、W2 packageを明示importした同processで成功。source欠陥や金融失敗へ読み替えていない。

詳細は independent-transport-small-probe-v2-results.json、independent-transport-scoped-pytest-v2-results.json、independent-transport-source-scope-v2-results.json、判定は independent-transport-codec-v2-decision.json。
