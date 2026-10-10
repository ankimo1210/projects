# source/prior rebind v3 限定独立レビュー

判定: **未承認**。stdlib による保存 JSON・AST・physical SHA の269件中268件は一致しましたが、実 materializer consumer に1件の拒否条件があります。helper、lock、monitor、金融処理は起動していません。

## 一致した範囲

- 旧全prior 3cf は旧 source 1cc/be のまま保持。元3,138 jobs・121 cases・51 obligations・4N・573,122 cap options・親相対順・各limit・履歴46件・外部費用10件を変更していません。
- 実effective rows 02da、旧 recipe e8fd を独立に再構成。新 recipe 43eb への差は source_identity だけです。18 bindings の差は予定の6項目だけでした。
- 現81 source の物理SHAは前後一致。旧sourceとの差は既受理の run_pilot 1キー修正のみ。cap生成・既存 validator・monitor 実行/停止処理のASTは不変です。

## 具体的な1件

materializer-v3 の rebind_source_evidence は files だけを比較から除き、残りを環境・import geometryとして完全一致させます。しかし protocol_source にも runner SHA が保存されており、e771→8f0df の同じ正当な更新が入っています。この実保存入力では条件がfalseになり、metadata materializationは拒否されます。金融 source の異常ではありません。

D-only最小修正は、files と protocol_source のbyte由来をgeometryから分け、protocol_sourceの元キー集合・他SHAの不変性とrunnerの新旧SHAがfilesに一致することを明示認証することです。元fcc35候補と本FAILは保持し、修正候補は新byte/SHAとして再結合してください。

旧70 partial・source error・全費用・unknownは保持します。本レビューはwhole金融精度、launch、main/phase acceptedを承認しません。詳細と実費は results-v3.json、machine-readable判断は decision-v3.json にあります。
