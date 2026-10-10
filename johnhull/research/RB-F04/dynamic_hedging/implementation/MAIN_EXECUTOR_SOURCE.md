# 主実験実行器のsource確認と残る接続

2026-10-10。正式pilot/freeze/main・研究受入は未実施。本書は既存の限定sourceレビューと、その後の接続修正の現在地を区別する。

## 固定済みの既存sourceレビュー

[原byteの一覧](main-source-evidence/files.json)と[canonical参照の独立判断](main-source-evidence/task-6-main-independent-final-review-canonical-decision.json)を保存した。レビュー済み旧3sourceは run_main=4956903e、check_main=ada38ad0、test=f2456468。現在の作業ファイルの承認とは扱わない。

- 旧保存reader/source単体を独立72件・反例24件で確認。固定配列と独立cash再計算の範囲であり、正式金融教師の生成ではない。
- 後続canonical-reference修正は独立14件PASS・自己整合の改変18件拒否。作者の専用80件PASSとは加算しない。
- [保管庫manifest](main-source-evidence/task-6-main-source-root-cas-manifest-v4.json)は635 entries / 199,151,285 bytes。C/Fから別々に原byte復元PASS。rootは金融semantic検査を再実行していない。
- 成功CAS検査の内側wall13.793699秒/CPU2.236475秒を記録。開始前のimport/作成費用と先行3失敗の費用は未測定のまま保持。MIME宣言とhelper呼出しの誤りは原script/logを残した。

## 現在の108件接続

実main DAGは774jobs（60本体＋714精度比較）。作者はempty_claim108件のdispatchと、元N4096・seed・state・5日付・cash・Q binding・失敗NaN・費用/時計・resumeを接続し、専用94件/Ruffを確認した。現在の固定3SHAは run_main=0b8fc24f、check_main=a988c164、test=6689e4da。独立レビュー中である。

独立実行ではHeston側のnative Q→empty保存再計算が動いた一方、local側のrun_q_jobがscalar APIのlocal_recordsへbroadcast配列を渡しTypeErrorになった。元のlocal Q54件の実行を妨げる依存sourceの欠陥なので、予算capや金融精度未達として閉じない。pilot source側の最小修正と両modelの再確認が必要。108件全体のsource接続を受理済みとはしない。

## 正式実験までに残る条件

pilotの選択adapter・全source固定と独立レビュー、実入力/111aliases、元件数/全774jobsの予算・費用・支持域・Q call精度の固定を行う。正式pilotの保存後照合とfreezeに続いて、12学習・baseline選択・主396枠/精度比較・fresh・全費用・両保管庫semantic復元・3図/教材・最終受入を行う。関連3suiteは章別部品検査と分け、最終phase gateで一度実施する。
