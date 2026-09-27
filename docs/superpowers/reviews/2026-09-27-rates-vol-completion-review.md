# レビュー: `rates-vol-completion` ブランチ（rates_volatility_model 完成計画の実装）

- レビュー日: 2026-09-27
- 対象: worktree `/home/kazumasa/rates-vol-completion-20260927`、ブランチ `rates-vol-completion`（`main..3492514f`、9 コミット）
- 計画: `/home/kazumasa/projects/docs/superpowers/plans/2026-09-27-rates-volatility-model-completion.md`
- 実装者: Sol

## 結論

**マージしてよい。** 計画の Task 1〜8 はすべて実装済みで、再検証でも通った。計画自体に 1 件バグがあり（下記「計画との差分 1」）、Sol はそれを見つけて正しく直している。マージ前に 1 行の修正（M1）を入れることを推奨する。M2 と L1 はマージ後でもよい。

## 再検証の結果（2026-09-27、レビュアーが実行）

| 項目 | コマンド / 方法 | 結果 |
|---|---|---|
| テスト | `PYTHONPATH=rates_volatility_model/src .venv/bin/python -m pytest rates_volatility_model/tests -q` | `63 passed in 10.94s`（計画の 61 + Sol が追加した 2） |
| lint | `ruff check` / `ruff format --check`（`src/`, `tests/`） | `All checks passed!` / `14 files already formatted` |
| 計画のコードとの一致 | `src/`・`tests/`・README・STATUS を、計画作成時に検証したファイルと diff | 違いは下記「計画との差分」の 2 件と、STATUS への実行記録の追記だけ |
| ノートブックのソース | 計画の書き換えスクリプト 3 本を適用した結果と、セル単位で比較 | 71 セル、cell id と並び順が一致。違いは 2 セル（`f3029894` の見出し、`dfe9c5f8` の no-root 案内）で、どちらも意図どおり |
| 保存出力 | nbformat で走査 | コードセル 35/35 実行済み、error 出力 0、PNG 11、kernelspec は `python3` |
| ルートの変更 | `git diff main...HEAD -- Makefile README.md pyproject.toml uv.lock` | 計画どおり。`uv.lock` は `rates-volatility-model` の追加だけ |
| 旧ファイルの削除 | diff stat | 計画の 11 ファイルが削除済み |
| xfail の扱い | `fe2cf426` に strict xfail があり、`dc8934af` で外れている | 計画どおり（TDD の赤→緑を履歴で確認できる） |

## 計画との差分（どちらも妥当）

1. **`sabr_alpha_from_atm_vol` を 3 次方程式の根で解くよう変更（計画のバグ修正）。** 計画は `brentq` で区間 [1e-8, 10] を探していた。Hagan の ATM 近似は α が大きいところで下に曲がるため、β=1, ρ=−0.9, ν=1 では区間の端点で符号が変わらず、Ch9 のスライダーが例外で止まる。Sol は x = α/F^{1−β} の 3 次式 c2·x³ + c1·x² + c0·x − σ_ATM = 0 の最小の正の実根を取る方式にし、根が無い設定では nan を返すようにした。ノートブック側でも案内文を出して描画をやめる。
   - 係数を ATM 公式から検算し、一致した（c0 = 1 + T(2−3ρ²)ν²/24、c1 = Tρβν/4、c2 = T(1−β)²/24）。
   - 720 通りのパラメータで検証した（σ_ATM ∈ {5, 20, 60}%、β ∈ {0, 0.5, 1}、ρ ∈ {−0.9…0.9}、ν ∈ {0…2}、T ∈ {0.1…30}）。結果は、709 通りが σ_ATM を 1e-9 以内で再現、11 通りが nan（到達不能）、不一致 0。
   - テスト 2 件と、ノートブック実行テストへの境界値呼び出しが追加されている。
2. **README と STATUS の追記。** SVI の g(k) 検査は k ∈ [−1.5, 1.5] のグリッド上でしか行っていないこと、保存出力が対話セルの初回描画を省いていること、既知の残件（M1）の 3 点。いずれも正確。

## 指摘

### M1（マージ前推奨・1 行）: Ch11 の override スマイルで市場点の横軸が % になっていない

セル `bf4cde9e` の `axes[0].scatter([F + bp/10000 for bp in STRIKE_OFFSETS_BP], ...)` だけ ×100 が抜けていて、曲線（`fine_k*100`）と市場点がずれて表示される。旧版からあるバグで、計画のレビュー（17 件）では見落としていた。Sol は STATUS の「既知の残件」に正しく記録している。修正は `[(F + bp/10000) * 100 for bp in STRIKE_OFFSETS_BP]` とするだけ。

### M2（マージ後で可）: 保存出力の作り方が再現できる形で残っていない

STATUS には「通常の `nbconvert --execute` は時間切れになるので、初回ウィジェット描画を抑えて保存出力を作り、ソースは元に戻した」とあるが、使ったコマンドが書かれていない。

レビュアー側では、同じブランチのノートブックを普通に実行して完走した（`nbconvert --execute`、セルごとのタイムアウト 120 秒、PYTHONPATH 指定）。所要 129 秒、error 0、出力 4.0 MB。ただし内訳は、G2++ の対話セル `7aaa0880` の後に約 120 秒の待ちが入るだけだった（セル自体は 0.37 秒で終わる）。つまり「時間切れ」はタイムアウトを短く設定したときの症状で、実行そのものは失敗しない。待ちの原因は未特定。

対応案: STATUS に保存出力の生成手順（コマンド全文）を書く。あわせて、`7aaa0880` の後の待ちが nbclient とウィジェットの組み合わせで起きる理由を調べる。

### L1（軽微）: ルート README のワークスペースメンバー一覧が未更新

`README.md` の「workspace メンバー（正は root `pyproject.toml`）」の列挙（約 100 行目）に `rates_volatility_model` が入っていない。計画が編集箇所として挙げ漏らしたもので、Sol の落ち度ではない。

## 残りの手順（未実施）

1. M1 を修正してコミット（任意で M2 の手順追記も）。
2. superpowers:finishing-a-development-branch でマージする。
3. main 側で `uv sync --all-packages --inexact` を実行し、続けて `uv run --no-sync pytest rates_volatility_model/tests -q` → 63 passed を確認する（STATUS の完成条件 1 はここで満たされる）。
4. main にある空の `rates_volatility_model/venv/`（git 管理外）を削除するか決める（本人の確認が必要）。
5. 計画ファイルと本レビューノートは main の作業ツリーで未コミットのまま。
