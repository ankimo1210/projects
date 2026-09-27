# D1-preflight 実証記録

更新日: 2026-09-28
判定: **PASS**。M15 の前提とした D1 の小群実証を完了。受入済み14節の
台帳・証跡は変更していない。[方針](../../EVIDENCE_POLICY.md)と
[進捗](../../../ROADMAP.md)を参照。

## §27.3 の比較

| 経路 | ブラウザー・節テスト | 新規画像 | 保存・復元 |
|---|---|---:|---|
| [全再描画](section-27-3/d1pf-27.3-20260927T220449Z-redraw.json) | 16状態と14テスト PASS | 16枚・413,577 bytes | C: / F: の各コピーから復元・ハッシュ一致 |
| [基準再利用](section-27-3/d1pf-27.3-20260927T220502Z-reuse.json) | 同じ16状態と14テスト PASS | 0枚 | 上記の画像へ直接参照し、両コピーから復元・ハッシュ一致 |

両経路の[ブラウザー結果](section-27-3/d1pf-27.3-20260927T220449Z-redraw.browser.json)と
[再利用時の結果](section-27-3/d1pf-27.3-20260927T220502Z-reuse.browser.json)は
PASS。16枚は受入時と M14 再検査時の画像にもバイト一致した。
基準再利用記録は全再描画記録を直接参照し、連鎖は作らない。
両記録の schema 2 検査と、C: / F: の実体検査は PASS。

[負の対照](section-27-3/negative-controls.json)16件も PASS。
対象と無関係な節の追加は再利用可。本文・値・データ・共有 CSS / JS・
描画環境・normalizer の変更、未宣言の依存、欠損・破損した blob は
再利用を拒否した。負の対照は一時 overlay と保管庫の一時コピーで実施した。

## 既存 gate

- johnhull 全体の pytest: **2,978 passed、6 skipped**。
- 台帳: source 検査と `--check-artifacts` がともに PASS
  （306節中14節受入）。
- release 契約と §27.3 の独立した数値検証: PASS。
- [§27.4 の別小群](../ARTIFACT_STORE_PILOT.md)4画像も、同じ保存器で
  2コピーから復元し、出典と入力ハッシュを検証済み。

専用 worktree での Book 初回ビルドは `myst-nb` の CSS が静的ファイルへ
配置される前に HTML が生成され、CSS URL の `?v=8cd3d715` が欠けた。
この状態では既存 M14 の artifact ハッシュ検査は FAIL する。
CSS 配置後に `jupyter-book build johnhull/book/ --all` で全ページを再ビルドすると
同じ版識別子を含む HTML となり、`--check-artifacts` が PASS した。
単発の初回ビルドだけを D1 の品質ゲートの結果として扱わない。

M15 以降の新しい再検査画像は [保存器](../../../scripts/evidence_store.py)で
不変 blob として2コピーへ保存し、Git には参照・指紋・検証要約を残す。
公開クローンに保管庫の実体は付属しないため、完全監査には両コピーへの
アクセスまたは検証済みの復元が必要。既存の受入画像は Git に残す。
