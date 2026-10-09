# Task5 prefreeze revision — private source checkpoint

2026-10-10。開発branchのみ。**固定評価領域、保存再計算、別execution契約と入口を実装。正式pilot・金融精度・freeze・主実験・研究受入・main統合は未完了。**

## 現在の範囲

| 部分 | 実装と確認 | scoped tests |
|---|---|---:|
| 固定Cartesian domain | 日付/modelごとの連続した元index範囲、同じC2 tensor operatorの価格・全Greeks・16 blocks。元全axes/arrays/NaN/Nを保存。支持外や必要node不明はunknown | 51 |
| 保存再計算 | domain geometry/bounds/sheetsを独立生成設定と照合し、原primitivesから価格・全blocksを再検算。legacy None互換、再生成RNG/solver呼出し0 | 101 |
| execution metadata | 別v1.1契約、元v1 candidate・121cases・51obligations・12fits・4×14候補・元閾値/費用/unknownを保持。Aのmetadata bindingを独立限定承認 | 50 |
| runner/API/CLI | strict v1入口を保持。execution入口とCLIで専用source providerを使い、raw閉鎖重み/全validation/元Nを再計算後にtest loaderへ。独立レビュー修正I1/I2、最終独立39tests/16probes・未解決0 | 39 |

両packageの索引/docstringは1,125 tests PASS。8変更Pythonのruff/check/format、著者source/docsのdiff-check PASS。これらは変更範囲の検査で、関連3suite・tracked releaseの最終gateではない。重複した著者/独立検査を合計に加えない。

## 承認境界と変更理由

- 旧strict v1の候補・閾値・sourceは変更していない。execution v1.1は研究を実行するmetadataの境界であり、精度合格や金融承認を意味しない。
- 元full call domainのroot一意性判定は維持する。Asianの固定domainに入るrootだけを先に選んで元非一意性を消さない。domain外・NaN・underresolved tailはunknown。exact-linear/settled branchは継続。
- 元N1024の予備測定、state15.Hのκ≈.808>.25、原36slots/121cases/51obligationsを保持。今回のsource検査はこれらの金融precisionを合格へ読み替えない。
- 実`run_fresh.py`はこのcheckpointで未実装。`execution_source_identity`は`reference_methods.py`・`run_fresh.py`を含む5入口の実在を明示確認し、欠落するとtest loaderの前に拒否する。placeholderでsource registryを通していない。
- 正常接続テストは合成source registryを供給し、実A metadata gateとraw closure checkerを置換せず確認した。金融試行・source実bytes・実freezeの証明ではない。

## レビュー・TDD・保存

元証跡と各失敗を[evidence対応表](prefreeze-source-evidence/files.json)で保持する。`.py`は`.py.txt`、baseline source/testsとdiffはtextとして保存し、元bytesを照合する。SHAはprovenanceのみ、金融比較は許容誤差/SE。

- B固定domain：著者RED/GREEN、rootの別解析price/Greek/16block probeを保存。
- replay：著者RED/GREEN、独立101tests/33反例、禁止RNG/teacher/solver検査を保存。
- A：著者RED/GREEN、classification矛盾F1の修正、独立50tests/57反例/6detachを保存。
- runner：元I1 source closure、追加I2 CLI providerの独立反例を保持。I1の3RED→合成fixtureのfailure_kind/weights binding不足1FAIL→3PASS、I2のCLI RED→1PASS、最終39PASSを区別する。最初のreview harness failureも元出力を保持する。

## 次の工程

1. 実fresh・premium/独立positions oracle、正式pilot orchestration/保存金融checkerを実装。
2. 121cases/51required attemptsの原N/grid/refinements/精度/cap/全費用を実測し、独立pilot review。selected oracleの精度を全cacheへ一般化しない。
3. 全12fits・NN validation/4baseline選択を閉じてからtest開封。正式396枠、元分母/全失敗/費用、Q/誤差/統計を保存。
4. fresh/両CAS、3artifact-only図、最終suite/レビュー/採否・main統合。

[候補revision](../PREFREEZE_REVISION.md)のレビュー前snapshotと[限定設計承認](../prefreeze-review/README.md)、[前source](TASK5_CONNECTORS.md)は歴史的証跡として保持する。
