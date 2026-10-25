# DSINC実装 — Opusレビュー記録

2026-10-25 JST。R0: REVISE（Critical0、Important4、Minor10）。**R1: APPROVE（Critical0、Important0、任意Minor5）。最終pilotの同一性照合が承認条件で、再実行で同一性を確認済み。**研究の採否はAmerican未再現・不採用で、main未実行。

## 対象と手順

WSL Claude Code 2.1.310、requested opus、modelUsage実測claude-opus-5-5。R0はfresh context/high、ツール/MCPなし、ファイル変更なし、セッション非永続。全自作ソース/テスト、設計/計画、pilot summaryを入力し、677.434秒。数学をコードから代数的に検査し、原論文との新たな照合やコード実行はしていない。

R0にはROADMAP/MODEL_INDEX、freeze本文、実画像、NPZ、上流原本を含めていない。これらの機械検査・目視・hash照合は作成者側の証拠であり、Opus独立検証とは記さない。全体7822PASS/6skipはR0送信時には実行中で、R1へ結果と制限を渡す。

## Importantへの対応

| ID | 指摘 | 是正と検算 |
|---|---|---|
| I1 | main replayがselection/採否/slots/costs/freezeを信用 | phase共通のderived reportを再計算、main freezeの検証、全recordの固定roster/settings/input hash照合を追加。採否・段・slot・費用の4改竄、設定改竄を拒否するテスト |
| I2 | poll間の短いRSS/wall超過がcompletedになる | 終了時ru_maxrssとwallも上限判定、valuesをnullにしraw証拠を保持。peak偽装と実timeout/memory fixtureで検査。R0受領前の自己検査で是正済み |
| I3 | hashしたworktreeとimportしたコードが別になり得る | types/spectral/americanのmodule.__file__.resolveをworktree期待値と照合してからhash。別checkoutのpath fixtureを拒否 |
| I4 | AMでEU/EEP誤差が相殺され得る | 隣接段/全個別感度を[EU,AM,EEP]/K stackの最大差へ変更。AM一定でもEU/EEPが反対に1e-5動く二つのfixtureを拒否 |

Importantの未実装時8テストはすべてREDを確認し、是正後GREEN。終了時資源/出力会計の自己検査もRED2→GREEN。許容差やroot選別を緩めず、数値作用素・EEP式・時間積分は変更していない。

## Minorへの対応

- 1: 元のrangeはPythonの半開区間を意図しており、包含区間に読み替えた指摘とは異なる。曖昧さを解消してstart/stop・half_openを明記し、全statusのencode/decode一致を検査。終端行をokにはしない。
- 2: scanに符号変化があっても端点がbracketを作らない失敗へendpoint_not_bracketedを追加。
- 3: FD境界比較は非finite spectral点が1点でもあれば不合格。coverage14/15でも成功にしないテスト。
- 4: IT相補性は構成的な診断と明記。SDE/BSM/CRR/細分/方程式欠損を精度検証に使う。
- 5: 出力予算超過でもresultsと未実行全slotを残す。例外だけで記録を失わない。
- 6: freezeにPython/NumPy/SciPy版とthread policyを追加。root/coverageの実効閾値もTHRESHOLDSへ接続。
- 7: 図の失敗凡例を一般化、価格を明示的にKで正規化。scanがない失敗とデータ未計算にも対応。
- 8: 事前費用式がS2を強く制約し得る点をRESULTSへ追記。式/予算は変更しない。
- 9: T1の最初のstepは独立追試でないこと、domain上端5点の別種の失敗、周波数解像度の概算を追記。既存scanの符号変化区間を保存し、原因未確定を保つ。
- 10: READMEの誤字を修正。

## 検証の制限

基点と現行のrelease scriptは同一で、両方ともworktreeに生成portal15 HTMLがないため同じFAIL。研究で本編の生成物を再生成しない。既存F04入力のignored symlinkによりfull hullkit/reportは7822PASS/6skip/2既存DeprecationWarning（467.50秒）。上の是正後の全体再検証は継続中。


## R1の最終確認

R1は新しい非永続context/medium、実モデルclaude-opus-5-5、200.513秒。R0の応答・是正表・R0からの全差分・現行runner/runner tests等を渡した。元packetから抽出したrun.pyのhashはR0 snapshotと一致し、差分の基点を検証した。

Important4点はすべて解消と判定され、新しい偽の成功経路は見つからなかった。R0 Minor1の半開区間の読み違いはレビュアー自身も訂正した。最終承認は同じ33jobのinput hash、EU/FD価格、失敗集合とNPZ配列の一致を条件とする。全文を再審査したfresh reviewはR0で、R1は是正差分の確認である。

残る任意Minor5点:
1. main replayのfreeze経路の無mockテスト。R1後に壊れたdigestの実ファイルをreplayへ渡すテストを追加してPASS（runner25件）。
2. replayのelapsed_seconds欠落は既定0になる。実測runは必ず値を保存し、charged wallも予算判定する。欠落を必須エラーにする是正は次版。
3. status圧縮が想定外patternならValueErrorがworker_errorになる。成功にはならないが、全配列保存のfallbackは未実装。
4. 予算超過時のDeltaはrecord内のraw数値として残り、raw_deltasへ改名していない。gateには使わない。
5. runtimeはPython/NumPy/SciPy版とthread policyを固定。policyの実効検査はworkerの環境変数assertであり、BLAS実装/版や他のhullkitモジュール全体のhashは固定していない。終了時wallの分岐単独fixtureも未追加。

追加依存/API変更/閾値緩和はなし。R1後の実行コードは変更しない。任意1のテストと文書だけを追加し、次版の変更と区別する。

## 入力・応答の固定値

| 回 | 入力SHA-256 | JSON応答SHA-256 |
|---|---|---|
| R0 | c49bc977a99af43e206822fa664e016d7a0c56b139e512f949077d819e0e04dd | 8278ce45fb8bce8bbae12adc388b18f1841a6b6bcd33c00e5e35a37be3572f2e |
| R1 | ac777d126e78ef5a5c79943022de398a2ccf51bcebf83111687174072ab925ef | 9cf62dabab21689751ed56162c11631c1afed0e57b1f5b2ecd7738dbaf78d0f8 |

## 承認条件の実測確認

最終pilot33jobは200.294秒、peak641,482,752 bytes、root failure11。全33input hash/価格、全32NPZ hash、失敗集合/ラベルが旧pilotとbit一致。main拒否も再確認した。R1の承認条件は達成。全2pilotは401.537秒で10分予算内。是正後関連1024PASS（32.73秒）、ruff/format12PASS。全体7822PASS/6skipは是正前epochとして区別した。[結果/検証記録](../../../research/DSINC/RESULTS.md)。
