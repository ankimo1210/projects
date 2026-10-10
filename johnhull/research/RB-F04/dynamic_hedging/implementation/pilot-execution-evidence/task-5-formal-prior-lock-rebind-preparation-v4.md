# prior rebind v4: 同じrunner SHAの2重登録を正しく扱う

D-only。旧v3 script/manifest、独立268PASS/1FAIL、旧69raw/70fault/全実費・unknownは不変。

## 最小修復

v3はfiles以外のidentity全欄不変を要求したが、protocol_sourceにも同じrunner SHAがあるため、正当なe771→8f0df更新を拒否した。

v4はbefore/afterのprotocol_source[runner]==files[runner]を確認する。previousをdeepcopyし、files[runner]とprotocol_source[runner]の2箇所だけcorrectedのSHAへ置換して、**identity全key/valueをそのまま完全比較**する。protocol_source除外・field削除・別SHAの包括許可はしない。実identity5d/568は不変。

materializer-v4 SHA e800b93de39329d0076692f925f6c10fdf2c18ccfe9b43dea7aca2c045a1dca0。
monitor-v4はv3と同bytes SHA94ddf018…（behavior変更なし）。root approval builder-v3はmaterializer-v4とpending-example-v4へ更新しSHA d3173de6…。root launch builder-v3はmonitor-v4とguard-candidate-v4へ更新しSHA5a7e6e67…。各helperのreceipt名も新v3で旧receiptを上書きしない。

## RED / GREEN

RED-v4は独立元FAILと同じ実旧／現source closure JSONを結合し、元v3 predicateがFalseになる1件を保存。
GREEN-v4は同じ実JSONに2箇所だけの正規化で全identity一致を確認。別protocol SHA変更、runnerのfiles/protocol_source不一致、identity欄削除も拒否。pure metadata9項目／compile4。変更ASTはrebind_source_evidenceだけ。他の数学/budget/cap関数とmonitor全bytesは不変。

新helperをimport/起動せず、lock／金融/RNG/SDE/solver/Popen0。実helper検算はroot／独立rebind担当の許可範囲で行う。

## 承認状態

candidate_bindings-v4はv3との差がmaterializerSHAだけ。rows02da、recipe43eb、3138/121/51/4N/573122、原費用由来を保持。旧3cfのsource承認を新sourceへ偽装せず、新source/prior-binding独立decision・root approval・financial launchはpending/falseのまま。
