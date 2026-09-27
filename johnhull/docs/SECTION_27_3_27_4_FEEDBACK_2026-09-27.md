# §27.3 M12・§27.4 M13 レビュー：指摘と確認

日付：2026-09-27。対象：`main` の `50ca22de..4d59efbc`（`5d906f31`・`44272e45`・`ff3ada12`・`4d59efbc`）。
納品した実装者とは別の立場から、原典照合・公開コード・検証スクリプト・ゲートを確認した。リポジトリのコードは変更していない。
要求と納品時の記録は [§27.3 REVIEW](SECTION_27_3_REVIEW_2026-09-27.md)・[§27.3 ACCEPTANCE](SECTION_27_3_ACCEPTANCE_2026-09-27.md)・
[§27.4 REVIEW](SECTION_27_4_REVIEW_2026-09-27.md)・[§27.4 ACCEPTANCE](SECTION_27_4_ACCEPTANCE_2026-09-27.md) にある。

## 判定の要約

受入を止める指摘はない。価格式・原典の数値・独立参照の中核に誤りはなかった。指摘は P3 の 2 件で、どちらも未対応のまま記録する。

## 確認したこと

| 項目 | 方法 | 結果 |
|---|---|---|
| §27.3 の原典照合 | GE 版 pp.649–650 の本文と IV01–IV06 を突合（式 27.4 の分子 $c_T+q(T)c+K[r(T)-q(T)]c_K$、瞬間値の $r(T),q(T)$、平滑化の脚注 19、単一時点は正しく複数時点は保証されないこと） | 一致 |
| `dupire_local_vol` | コードを読んで式 27.4 と照合。非正の蝶型密度・非正の分子を拒否し、クリップしない | 一致 |
| Example 27.1 | `hullkit` を使わない私の独立再計算（3 段、$p_u=0.5115$・$p_d=0.4860$・$p_{def}=0.0025$） | 10 節点と B の 119.54→116.18、D の 135.08→134.99、E の 106.78、初期値 107.4418504343806（印刷値 107.44）がすべて一致 |
| `convertible_bond_tree` | コードを読んで §27.4 の手順と照合。発行体コールは保有者価値を下げるときだけ行い、コール後も転換できる。利息は次の期に生存した場合だけ受け取る | 一致（満期の利息を権利判断の前に払う規約は §27.4 REVIEW に明記済み） |
| 独立参照と数値検査 | `build_local_volatility_reference.py`・`verify_local_volatility_numerics.py`・`build_convertible_bond_reference.py`・`verify_convertible_bond_numerics.py`・`verify_convertible_bond_notebook.py` を `--check` で実行 | PASS |
| テスト | hullkit+report：2786 passed・6 skipped。deep_hedge_price：206 passed | PASS |
| lint・release | 変更した Python に ruff、`verify_release.py --require-tracked` | PASS |

## 指摘

| ID | 重大度 | 指摘 | 状態 |
|---|---|---|---|
| F1 | P3 | 節ごとの notebook 検査は「§N 以外のセルが基点と同じ」ことを確かめる。そのため次の節が vol06 に入ると HEAD では再実行できない。`verify_local_volatility_notebook.py --check`（M12）は M13 の §10 追加後に FAIL し、M10 の `verify_alternative_models_notebook.py`・M11 の `verify_stochastic_volatility_notebook.py` も同じ理由で FAIL する。M12 で始まった問題ではない。既受入節の再検査は pytest とブラウザ検査が担っているので、受入の判断は変わらない。ただし受入ノートが挙げる検査スクリプトの一部は、その時点の証跡としてしか読めない | 未対応。次の節（M14）の前に、保持の検査を「自節の範囲と見出しの並び」に限るか、基点を直前の受入 commit に更新する規約にするかを決める |
| F2 | P3 | `dupire_local_vol` の docstring が「undiscounted-spot European call price」と「already discounted to today」を並べており、どちらの価格を入れるのか読み取りにくい。実装と独立参照は今日への割引済みのコール価格を前提にしている | 未対応（文言だけの修正） |
