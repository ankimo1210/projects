# Task1–4 ソース実装チェックポイント

2026-10-09。**private sourceの実装・独立レビュー完了。開発branchのみ。正式pilot・研究受入・main統合は未実施。**

後続の[Task5 helperチェックポイント](TASK5_HELPERS.md)では統計/実験管理の2 private moduleを承認した。下表と1193件はTasks1–4時点の記録として保持する。最新の[Task5接続・予備測定](TASK5_CONNECTORS.md)でstudy/replay/runner/checkerのsourceを承認した。Task5全体・正式pilot・研究受入は未完了。

## 実装と確認

| Task | 内容 | 関係テスト | 独立レビュー |
|---|---|---:|---|
| 1 | 正CIR・calendar記録・自己資金cash／独立discounted gain | 29 | [初回レビュー](task-1-4-review.md)で承認。source不変をTask4再レビューで再確認 |
| 2 | 条件付きAsian・aux GBM・16 IID blocks／共通乱数教師 | 25 | [再レビュー](task-2-rereview.md)で承認 |
| 3 | CF／calendar PDE・同じC1価格面のGreeks・quote fit・独立参照 | 19 | [再レビュー](task-3-rereview.md)で承認 |
| 4 | quote IFT・rank1 band・観測9入力のTorch policy／BPTT | 22＋10 | [再レビュー](task-4-rereview.md)で承認 |

[変更範囲と索引/docstringの検査](source-checkpoint-tests.txt)：1193 passed（実測4.86秒）。[実行環境・11ファイルのruff/check/formatとソース指紋](source-checkpoint-run.json)を保存した。WTのhullkit/deep_hedge_priceを明示preloadしimport元を確認。これは関連3suiteの全実行ではない。数値は許容誤差／SEで比較し、SHAはレビュー対象・実行ソースの同定にだけ使う。

[照合記録](source-validation.json)はTasks1–4時点のソースと各再レビューを結ぶ。条件付きstatusとcall空間格子は後続で変更したため、現在の指紋は[Task5照合](connectors-source-validation.json)を参照。Task1の原レビューはTask4の原指摘も含むため、最新のTask4再レビューと組にして読む。元のレビュー対象・差分・RED/GREEN・費用ログを保持し、指摘を削除して履歴を成功扱いしない。

## 修正した重要指摘（5件）

- Task2：invalid pathのraw/CE/CV微分診断をNaN・unknownへ伝播。原始Nを変更しない。
- Task3：独立MCのxi=0極限に、非定常分散の厳密遷移を実装。旧vでのstock更新を保持。
- Task3：独立CF積分の未収束をunknownとし、全base/bumpの誤差・メッセージ・設定・原推定値を保存。
- Task4：rank1共分散の丸めによる微小負の二次形式にだけ、明示した演算誤差限界内の補正を適用。原値・限界・補正数を保存。ridgeは追加しない。
- Task4：最終診断・thread復元を含む訓練時間がcapを超えればincomplete。更新完了フラグ・重み・超過時間を保存。

## 実装上の判断と次のゲート

1. quote fitは各cubic pieceの全root／extremaを列挙し、scaled Brentで絞り込む。計画のNewton-bisection候補から変更した。精度・不一意判定はテスト済み、全gridの速度はpilotで測る。
2. Tasks1–4は共通索引で互いを参照するため、一つの整合したソースcommitにまとめる。各taskのRED/GREEN／独立レビューは別記録で残す。
3. 独立CFのadaptive quad誤差はcutoffやfinite bumpの誤差と別に扱う。convergedだけで参照値の精度を承認しない。
4. call cacheのsolver-okと研究上の適格性は別判定。Task5がAsian支持域との交差を明示し、有限の参照誤差・共分散・Ctheta誤差をIFTへ伝播させる。unmeasuredを0へ置換しない。
5. runnerで全raw status／原始分母／費用／attemptを保存してから、37 quotes、18 states、教師／position／P&Lの収束、tiny44cell、formal pilotの独立レビューを進める。主実験・CAS・3図・全suite・最終受入はTasks6–7。

設計承認は元commit d71b25f3に対する歴史的記録。今回のソース承認は上の指紋・差分・再レビューの範囲だけを示し、設計資料の過去のvalidationを最新コードの検証へ読み替えない。
