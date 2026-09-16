# Task 2 independent review

判定: **Needs changes**

対象: `5ab2c18b..98bd1cf7`。Task 2 brief、report、差分全体と必要な生成側・参照データ箇所を確認。ソース・コミットは変更していない。

## Findings

### [P2] 必須ソースハッシュの欠落を拒否する

- 箇所: `johnhull/hullkit/src/hullkit/_shout_lesson.py:35–41`
- `_load_data` は保存 JSON が列挙する `source_hashes` のみ検証し、必須パスの存在を検証しない。生成側 `SOURCE_PATHS` は6パスを各 family に保存する契約だが、項目が落ちたデータは正常として受理される。空の辞書でもチェックを通過する。
- 再現: 正常データとその6ソースを一時ディレクトリにコピーし、コピーした `_shout.py` にコメントを追加した。元の hash 一覧では `ValueError: stale shout lesson source: contract: hullkit/src/hullkit/_shout.py` を確認。同じソース状態で全6 family の hash 辞書から `_shout.py` 項目のみ削除すると `_load_data` は schema 1 を正常に返した。リポジトリのソースは変更していない。
- 影響: 不完全な生成物を介して変更済み pricing ソースに由来する古い数値が通常の図として表示され、要求されるソース鮮度保証が抜ける。
- 修正: loader 側で schema 1 の必須6パスを明示して各 family の包含を検証し、欠落を明確な `ValueError` とする。空辞書・単一パス欠落、およびソース変更とパス欠落を組み合わせた negative test を加える。生成スクリプトの実行や solver import に頼らないこと。

## 確認済みの適合点

- 4図の順序、trace の role/scenario/contract、メニューの可視性・title/meta 更新は共通インターフェースと整合。
- 原著 K50/shout60 の給付、10現金と K60 call の別レッグ、ATM50 恒等式、S_shout >= K の一致条件が表現されている。独立 frozen pins との比較がある。
- N3 は実ノードを使用し、負の現金レッグを保持。満期ノードは intrinsic のみで、非満期の各構成要素を独立参照と比較する sum-preserving negative control がある。
- 境界は実 CRR 層の分離線分とノードで描画し、独立 B と区別。正のキャリー tau=.5 の非包含、疎な59層、高ボラの粗い幅、全42例の残差が経験値であることを明記。同市場 ATM 残差を右側に選択している。
- 7市場の call 比較は独立21 pins に対応。r=q の lookback は trace を作らず、未対応と表示する。
- 図構築に solver 呼び出しはなく、私有モジュールの MODEL_INDEX 登録も妥当。

## 検証範囲

- 上記 freshness probe のみ追加実行。既に確立された354 tests は依頼どおり再実行していない。
- Task 1 数値実装の再レビューは対象外。実ブラウザでの配置・重なり・表示幅は Task 3/controller gate に残る。本レビューは layout 承認を意味しない。

最終判定: **Needs changes**（必須ソースハッシュ欠落の拒否を修正後、再確認）。

## Scoped re-review — round 1

対象差分: `98bd1cf7..4fcb8f9b`。最新判定: **Approved**。

- 元の P2 は解消。loader に明示された必須6パスは生成側 schema 1 の契約と一致し、各 family ごとに欠落を検査してからハッシュ照合を行う。図・メニュー契約の変更はない。
- 新しい36通りのテストは6 family × 6必須パスそれぞれの単独欠落を検証し、既存の値不一致テストも保持している。
- 独立の限定 probe を一時コピーで実施。ソース変更のみは stale として拒否、元の P2（ソース変更＋全 family から対応ハッシュ削除）は missing として拒否。空 hash 辞書・hash フィールド欠落も明確な ValueError で拒否された。4 probe すべて成功。
- 修正担当の43 targeted tests / ruff 成功報告を確認し、重複する354 tests は再実行していない。レビュー側はソース・コミットを変更していない。
- 新規指摘なし。ブラウザ配置確認は引き続き Task 3/controller gate の対象。

最終判定（round 1）: **Approved**。
