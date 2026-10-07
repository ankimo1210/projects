# 後続章の軽量受入（fast-v1）

2026-10-07。「受け入れどんどん進めよう」と、前の便の条件緩和承認に従い、
Ch10以後も[前の軽量方針](FAST_ACCEPTANCE.md)と同じ必須条件で進める。
この方針自体と各便のrecipeを固定し、後の章を追加しても以前の証跡を編集しない。

- 原典の節・全要求、単位、符号、時点、モデル前提、印刷精度を維持する。
  数値・記号式の部分は原典値と別方法で検証し、混在する制度・経済的理由は説明も確認する。
  説明のみの要求に計算実装のverifiedを付けない。任意の数値化を省く場合も理由を残す。
- 補足教材を章順のHTMLへ生成する。全節/全要求の文章・数式・表・リンク・幅1280を自動検査し、
  各章1節だけ撮影して目視する。図の関係を式・受払・表で説明できる場合は追加図を省く。
- 対象計算、検査器、台帳を一括実行する。全suite、全Book build/巡回、別幅、全節目視、
  二重保管庫復元は省略する。未実施の確認をPASSへ混ぜない。
- PDF、下調べ、recipe、教材、使うローカル計算依存、試験、検査器、配布物のSHAを記録する。
  recipeには当該基点の計算範囲を保存し、更新される全体進捗文書を過去証跡の依存にしない。
- 重要な再現可能な指摘を解決し、独立レビューとfreshな統合確認後に登録する。
  古い受入判定を保つ。件数をassertする台帳試験は、各便の現在の件数でfresh実行するが、
  [台帳ガイド](SECTION_LEDGER_GUIDE.md)に従い、過去の計算sourceへpinしない。
  過去のmetadata gateはその時点の件数の履歴で、現在値は最新便の台帳検査を根拠とする。

既存Book本文の改訂、現在の市場・税務・規制、章末問題、入力のない較正価格、
main統合/remote push/公開は別工程。受入対象は指定した補足教材と計算範囲である。

## Ch10–15の実行

repo root、既存環境、当該checkoutのPYTHONPATHを使う。新規依存なし。

```bash
python johnhull/scripts/fast_acceptance_options.py build
python johnhull/scripts/fast_acceptance_options.py test
node johnhull/scripts/verify_fast_acceptance_options_browser.cjs
python johnhull/scripts/fast_acceptance_options.py check
python johnhull/scripts/fast_acceptance_options.py register
python johnhull/scripts/verify_section_ledger.py --write-summary
python -m pytest -q johnhull/report/tests/test_section_ledger.py
python johnhull/scripts/verify_section_ledger.py --check-artifacts
```

登録・commit後の再確認は`verify`を使う。`check`は生成時の日時を含む記録を作り直す。

```bash
python johnhull/scripts/fast_acceptance_options.py verify
python johnhull/scripts/verify_section_ledger.py --check-artifacts
```

後続の便は別recipeを`--profile`で指定し、ブラウザ検査器にはその生成configを渡す。
同じ章の教材を後で改訂する場合は、改訂した章の証跡を再検査する。
