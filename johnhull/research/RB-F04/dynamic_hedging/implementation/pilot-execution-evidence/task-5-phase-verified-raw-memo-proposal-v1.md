# Phase内の教師検算再利用案

**読取設計のみ。再利用は未実装、短縮時間未確定。** 金融実行/source編集/新testsは0。v4の既知部分606.881時間は全段実行時の未承認外挿で、総時間保証や行政cap合計ではない。

## 最小案

completed teacher_grid / teacher_domain_selectionのbounded数値検算結果だけを同一phaseのprivate memoへ登録する。初回は元全N、保存driverからのSDE、11samples、16blocks、統計/covariance、全node/cacheを現在のapproxで検算する。原失敗値/statusと金融資格unknownを保持し、failed/capped/partial/unclosed/cache未成立は登録しない。原3138 jobs/121 cases/51 obligations/20 teachers/10 drivers/4N枝を変更しない。

run_pilot:4009とcheck_pilot_records:4420–4432にはinvocation単位の既存contextがある。fresh/resume/独立review/各restoreは新しい空memo。保存proofの読込やglobal/disk cacheは使わない。_dispatch、gate/selector/adapter/activationのprivate runtime経路へ渡し、locked arguments、worker input SHA、金融raw、portable artifact_contextへmemoを混ぜない。

calculate_teacher_candidate_gate→_raw_job_checkの縮約jobはproducer ID/source/input envelopeを落としている。外側で認証したproducer bindingの伝播が必要。同じ教師rawとdomain wrapperは別producerとして各々初回検算する。node単位共有は初期案の範囲外。

## Hitの認証

context nonce/root/role、locked plan、producer ID/op/status、元N/model/grid/seed、actual resolved arguments、parameters/surfaceの現content、source closure、原purpose/control、全node/driver物理由来を結合する。envelope/typed arguments/controlと全実bytesをhit前に再認証する。

元node・driverのmetadata/arrays/receipt、全pack roster、bank seed/calendar/chunks/prefixと実byte SHAを確認する。receipt自己申告、mtime/stat、保存SHAだけではhitを許可しない。金融float再構成のSHAを合否に使わない。既存physical_artifact_bindingはNPZ decodeも行うため、同じreceipt規則のprivate byte-only guardが必要。共有fileの重複読取は一回のguard内だけ省ける。

同producerのseal後改変は失効しsource defectとして拒否する。別producerは初回検算。同形配列で代替しない。返却結果の防御的複製でcaller改変によるproof汚染を防ぐ。既存immutable artifact契約を越える同時改変安全性は主張しない。

**activationの既存早期returnも要対応。** 現key(gate ID/raw/args)には外部物理byteがない。最小案ではgateの現行control/全roster/集計/qualificationを毎回確認し、教師検算だけmemoを使う。gate-result cacheを残すなら全消費dependencyのbyte認証が別途必要。教師memo追加だけで現在の早期returnを安全と扱わない。

## 費用・次工程

初回全検算は消費jobのinclusive実費へ一度だけ含め、毎hitのhash/read/copy費も実時計へ含める。副次イベントをinclusive費へ二重加算しない。phase側のverified-event/reuse-eventへsource/input/physical bindingを記録し、金融rawへ可変hit/timing項目を足さない。初回全N検算済と今回SDE未再実行を区別する。

限定TDDは初回→hit、raw/args/field/source/seed/physical bytes/自己整合receipt/control/status改変拒否、別producer非hit、fresh/resume/review/restore新検算、alias防止、資格/roster/approx不変、費用分離を確認する。今は未実施。

routine private fixとして実現可能だが、producer伝播・byte guard・activation接続の実装/限定review/新closure再結合は必要。教師以外のkernel、hash/I/O、fresh/restore、resume費用は未測定で全体ETAを保証できない。次工程は最小source案の限定実装と実測。新deps/public API、数学/原N/閾値変更、重い追加gateは不要。

## 固定根拠

既存closure81/dynamic0/canonical dc7631fe73a457cd995d109aa693be9401b266410b9f53aa4e2d51e59f56d39c、v4未承認補足、独立tamper/retentionメモ。今回3対象source SHAは前後不変。全81一致は既存独立auditを根拠とし、今回金融配列decodeは0。参照SHAと実費の範囲は同名decision/cost/manifestへ保存した。
