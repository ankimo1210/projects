# v55 固定 source 独立レビュー

2026-10-10。

## 判断

**限定 source transport と保存 native Q の integrity を承認する。**
v54で独立に見つけた2件の入力結合欠落は、元の保存データと元反例で拒否されることを確認した。
正式 pilot / main / 予算 / phase 完了と金融資格は承認しない。financial_qualification は unknown のまま。

## 固定 source

- johnhull/research/RB-F04/dynamic_hedging/run_pilot.py: 4e4765f4bc7ae1cc0a7020fa3bb1fab1ad4eabec4e89fca511589cd5a799b829
- johnhull/research/RB-F04/dynamic_hedging/check_pilot.py: 14d6f877d8e0e6a9d4f8db0fbe741f7552767b64138952d7572605e9ec3c3486
- deep_hedge_price/tests/test_dynamic_hedging_pilot.py: feceea05f0769b7f78140da395637dac0e1282f329d1f1ff101e1fd90eb51dc8

独立 snapshot は task-5-pilot-v55-independent-source-snapshot/。
3 SHA の実値を作者archiveと照合し、検査後も同じ値であることを確認した。
run_pilot は v54 から byte 不変。変更は check_q_record、check_resolved_job_arguments、check_capped_job_raw の3関数。
v54既存test/helper107定義はAST不変で、原131専用testを削っていない。

## 独立検査

| 検査 | 結果 |
|---|---|
| 固定 source で metadata/control/purpose/7 bridge を再検査 | 37 passed /153 deselected、pytest1.82秒、親 subprocess3.815159672秒 |
| 元 v54 の保存 Q→empty claim 4件を再使用 | Heston/local×正常/失敗、N32、正常mask32・失敗mask31、原failure保持 |
| positive native原入力結合・保存normal SDE再計算・独立cash式 | 4件すべてPASS、unknown保持 |
| 元F1: variance変更＋parameters削除 | 両モデル拒否 |
| 元F2: explicit spotは原値のままraw parameters.spotを101へ変更、元worker引数hashを保持 | 両モデル拒否（raw入力parametersの出所不一致） |
| 27必須フィールド削除、null、13raw入力差し替え、自己整合chunk8対保存7、capped入口の入力欠落 | 元F1/F2と合わせ105反例すべて拒否 |
| native Qの実時計cap入口 | 両モデルN32、数値draw0、元mask32本が未実行、必須入力欠落は拒否 |

元データは task-5-pilot-v54-independent-native-raw-{Heston/local}-{False/True}/。
v55検査では新RNGも新金融pathも生成していない。cap入口ではdefault_rngを**乱数を初期化しないNoDraw sentinel**へ置換し、実時計で最初のdraw前にcapした。
capの数値計算は0件であり、実行済み金融データの資格は付かない。run_pilotの全formal envelope/予算承認とは区別する。
cashは exp(-rΔt)Q_t-Q_0 を独立に計算し、rtol/atol1e-12で比較した。
SHAは原入力の出所・固定source・保存証跡の追跡用であり、数値正確性の判定には使わない。

## v54指摘の解決

native判定のkind/quoted_calls/chunks/parameters/call_cacheが残る場合は、必須入力と配列の欠落を拒否する。
actual Q wrapperは常にnative原入力を必須とし、parameters削除でlegacy統計fixtureへ切り替えられない。
Hestonのparametersとlocalのparameters/fieldはnullや無効型を拒否する。
native saved-normal SDE再計算は条件付きでなく必須となった。
原worker引数の parameters/surface/spot/state/model/seed/N/state_id/call_cache/bin_edges/date/rate/chunk_geometryをrawへ明示的に結合する。
capped Qも同じ check_q_record 境界を通り、capを理由に必須入力や保存再計算を省略しない。

## 残る範囲

- 作者190 PASS・Ruff/formatは作者証跡。独立37 PASSへ加算しない。
- N32と解析toy call cacheの source arithmetic を、原N4096や4Nの価格・Greeks精度へ広げない。
- rootによるmain empty N4096×4再実行は既存作者probeの再実行であり、本レビューの独立承認に加えない。
- 元121cases/51obligationsの金融closure、原仕事/bytes/rates・事前budget・A cap_options・inclusive expense/historyは別の未完了作業。
- 元v53/v54失敗、v54未測定費用、元指摘の原証跡は保存した。source編集・Git操作・全suite・formal financeなし。

## 証跡・測定

- task-5-pilot-v55-independent-tests.{py,log,json}
- task-5-pilot-v55-independent-native-saved.{py,log}、-results.json、-parent.json
- task-5-pilot-v55-independent-native-cap-raw-{Heston/local}/
- 固定snapshotとv54との差分、decision/manifest

saved source probeは内側0.161715063秒、親subprocess1.69100259秒。価格誤差・正式金融原Nの費用はunknown。
