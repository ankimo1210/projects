# 全306節の最終統合

更新2026-10-08。目的：全節受入と開発側の最新修正・P8・研究v1を合流し、検証後mainへ反映する。
現在：全306節の統合・独立レビュー修正・strict tracked release・main反映・root同期を完了。統合実装`a3a533cb`をmainと`codex/hull-final-integration`へpushし、remote実体を確認済み。

## 統合対象と完了条件

- main基点`b840f796`、集約開発`9dd53804`、受入`cef7cea1`（実装`5a2b72c9`）。
- P4最新review修正`00d8a651`、P8`ce801e48`、RB-F07/F05 v1、受入のBGM/business privateモデルを保持。
- 台帳306/306 accepted・全native artifacts・各受入便のread-only検査とreleaseを確認する。
- 影響する数値/画面証跡を実測から更新し、全プロジェクト対象suiteを1回、変更Pythonのruff/format、独立レビューを行う。
- 通常の`make hull-report`で受入済み補足教材も再生成し、未受入状態の生成物を配布しない。
- rootの未公開履歴と別プロジェクト変更、受入worktreeを保持し、検証済み統合branchだけをmainへpushする。

## 現時点の確認

- 開発基点：索引754 tests・既存33節のnative artifact検査PASS。受入基点：最終45節のread-only verify PASS。
- 競合はROADMAP/P4/P5/P7の進捗文書4件。計算コードは自動merge。最新開発修正と受入の記録を両方保持。
- fresh数値検査：Ch2–9 130、Ch10–15 389、Ch16–21 492、Ch22–25 245、Ch29–37 389 tests PASS。重複するtestsを合算しない。
- Ch2–25の画面と既存browser記録は再生成後も同一。P6_STATUSの更新も入力指紋に含まれるためCh2–9の数値記録を再検査・更新した。
- Ch36の脚注と共同最適化の差を説明へ反映。最終45節・9画像のfresh画面検査PASS。
- Ch1はノートブック・設定・入力・40画像の一致を確認し、受入済みBook HTMLを復元。31ローカル依存を確認し、不足PNG1点を復元。37値・40状態のverify PASS。
- 全体run：hullkit + report + deep_hedge_price、6,640 passed・索引2件FAIL・6 skipped。受入側でも欠けていたBGM/businessの索引を補い、両packageの索引764 tests PASS。計算・テストの904+74 sourceは不変で、導線/renderの16 testsもPASSし、重複を除いた検査は6,650 passed・6 skipped。[実測と再検査](validation/final-integration/full-suite.json)。初回runのexit 1と生ログも保存し、単一runがすべてPASSだったとは扱わない。
- 変更Python300ファイルruff/format PASS。整形4ファイルはAST不変。
- `make hull-report`で全補足教材を生成し、入口から全34章への実ブラウザクリック・見出し・接続案内・幅1280を確認。[導線記録](validation/final-integration/navigation-check.json)と[画面](validation/final-integration/navigation.png)。
- 既受入33行は開発基点9dd53804の最新P8/D1から完全保持。残273行はcef7cea1の要求・coverage・scope・assumptions・limitations・参照pathを保持し、768証跡参照のhashだけ更新。全306節`--check-artifacts` PASS。[照合](validation/final-integration/native-rebind.json)。

## 独立レビューと1回の修正

統合commit `ca3d71a3`を新しいreviewerが確認。Critical 0・Important 2・Minor 1。以下は完了したレビューの要約で、再レビューは行っていない。

| 指摘 | 修正・確認 |
|---|---|
| Important：full-suiteが必要とするログ2本がgitignoreで未追跡。新しいcheckoutでCh1のsuite照合が失敗する | full-run/index-repairの生ログと、今回必要なbuild/lint/format/navigationログを明示的に追跡。suiteの全参照ファイルが追跡対象で現物のhashと一致することを検査 |
| Important：受入済み補足34章への入口がない | homepageに章一覧とMathJaxの接続案内を追加。新テストのRED 1件を確認し、追加後16件PASS。実ブラウザで34章すべてへクリックして到達、固定header下の見出し・横幅・案内を確認し目視 |
| Minor：READMEの2コマンドが通常build全体と同等に読め、main未統合の記述も残る | 通常手順を`make hull-report`へ統一。部分生成コマンドの用途と本体のoffline/補足数式のonline条件を明記し、現在の統合記録を参照 |

reviewerは旧33行のP8/D1完全保持、残273行の受入意味保持、整形4ファイルのAST、source/artifact参照、unique 6,649/6、strict native 306 PASSも独立確認した。指摘修正後はprimaryが対象検査とreleaseを確認する。

全Book/全節画像/別幅/全306節の両保管庫再復元は承認済みfast-v1の範囲外として今回追加しない。§33.2/36.4の不足入力は未再現のまま明示する。この判断はprimaryも採用。mainの実際の反映状態とrootの同期を確認し、下段へ記録した。

## 判断と範囲

- Ruling: 衝突する進捗文書は最新の開発状態を基準に、受入の章別件数・参照を合わせる — 古い33/261/306の混在を避ける — 誤れば進捗/制限の表示がずれるため台帳と最終reviewで照合する。
- Ruling: 過去の受入記録は保持し、変更sourceを使う便の数値/登録と変更教材の画面だけ更新する — 承認済みfast-v1の依存範囲に従う — 全Book本文/別幅/両保管庫の保証は追加検証が必要。
- Ruling: 通常のportalビルドにも既存補足builderを接続する — 新しいcheckoutで全受入教材を再生成できるようにする — ビルドに5本の短い教材生成が加わる。
- Ruling: 複数便の証跡更新は全便の既存検査を通し、提案台帳の全306節gateを通してから一括反映する — 単一便registerは他便が古いと正しく拒否するため — 今後の複数便更新でも同じ一括照合が必要。検証器の拒否条件は変更しない。
- Ruling: Ch1のBookは入力が同じ受入済み実体を復元する — 既存キャッシュに新Ch1節が欠けていたため — 別の入力/実行環境で再生成した場合は出力と依存を再照合する必要がある。
- Ruling: 全体run後の索引漏れ2件は索引guardの再実行で閉じる — 修正はカタログ2行のみで計算・テストsourceが不変、全suite1回の方針に従う — 計算変更がある場合にはこの扱いを使えず再検証が必要。
- Ruling: 必須の検証ログはignore対象でも個別に追跡する — 新しいcheckoutでも保存結果を照合できるようにする — 将来の記録追加時もJSON参照と追跡対象の両方を確認する。
- Ruling: homepageに既存補足教材への一覧を設け、数学表示の接続条件を案内する — 通常生成と教材の入口をそろえる — 章の追加や配布先変更では導線テストの範囲も更新する。
- §33.2の原典strike/date/MC規約、§36.4の会計/ESO条件不足と未再現値を保持。caller条件の一致を原典価格の無条件再現としない。
- 公開API・production依存・旧Book本文・本編研究配列に新しい変更を加えない。

## 残り・反映結果

- 統合`ca3d71a3`・レビュー修正`a3a533cb`のstrict tracked releaseはPASS。後者をatomic・non-force pushし、origin/mainと統合branchの両方が同じ実装commitであることを確認。origin/mainは`b840f796`から`a3a533cb`へ進んだ。
- root mainへorigin/mainをmerge。元の未公開14コミットをすべて祖先として保持し、別プロジェクト24変更のstatusとmarket-research差分は不変。root HEADをremoteへpushしていない。
- rootで通常`make hull-report`を実行。Ch1の同一入力・40画像を照合して受入済みBook HTMLを復元し、31ローカル依存を確認してPNG1点を補った。全306節native artifacts・保存suite/導線の鮮度を確認。
- [配布・同期証跡](validation/final-integration/delivery-check.json)。公開した実装と同期の状態を固定し、この完了記録のcommitは別にmainへ反映する。
- 本編の残作業はなし。§33.2/36.4の不足入力・原典未再現、§36.5脚注との差は宣言した制限として保持。次の研究候補はRB-F05の離散バリア契約と独立参照の固定で、本編完了条件には含めない。
