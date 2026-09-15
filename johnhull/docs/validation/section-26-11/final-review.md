# §26.11 M3a 独立コードレビュー

**Ready to merge: Yes.** M3aの要求整理・独立数値検証・台帳更新として、修正必須事項はない。§26.11全体の受入判定ではなく、状態は引き続き **gaps_found** とする。

- レビュー日：2026-09-15
- ブランチ：codex/johnhull-lookback-m3a
- 基準コミット／レビュー時HEAD：5e2f9ac7c7670426c68744e9f38774406edceacc
- 対象：新規ファイルを含むstage済み15ファイル。価格本体・notebook・描画ソースの変更なし。
- ファイル参照はリポジトリルートからの相対パスと行番号。

## 確認できた点

1. **原典と要求が一致する。** Hull 11e Global Editionの実PDFをpdftotextで物理・印刷pp.623–625まで確認した。4給付、今日までの極値、Example 26.2のcall 8.04／put 7.79、調整極値、連続観測の仮定と観測頻度の論点がL01–L06に対応する。現在のvol10の図は252分割のfloating callの経路図であり、教材を未完了とする評価も現物と一致する。
   - johnhull/docs/SECTION_26_11_REVIEW_2026-09-15.md:16
   - johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py:654

2. **オラクルは価格実装から独立している。** [MIT Lecture 7, Proposition 2（PDF p.3）](https://ocw.mit.edu/courses/15-070j-advanced-stochastic-processes-fall-2013/aca1518a09539a09ddd37428ab0d0268_MIT15_070JF13_Lec7.pdf)の終点・最大値の反射則を確認した。反射側の終点密度を指数傾斜して積分すると
   \[
   P\!\left(\sup_{t\le T}(\mu t+\sigma W_t)\ge y\right)
   =\Phi((\mu T-y)/s)+e^{2\mu y/\sigma^2}\Phi((-\mu T-y)/s),\quad s=\sigma\sqrt T
   \]
   となる。有限driftへの拡張を資料の転載とせず、自らの導出とする出典説明は正確。最小値には \(-X_t\)、価格積分には \(S_0e^{\pm y}\) と変数変換のJacobian \(s\) を用いる。4契約とも自分の給付期待値から価格を作り、本体の閉形式やfixed/floating parityを基準価格に流用していない。
   - johnhull/hullkit/tests/test_lookback_reference.py:59
   - johnhull/hullkit/tests/test_lookback_reference.py:88
   - johnhull/docs/SECTION_26_11_REVIEW_2026-09-15.md:61

3. **数値安定性と検証範囲の説明が適切。** 対数CDFと指数を結合し、積分幅を \(\sigma\sqrt T\) で規格化している。割引後の積分誤差見積りを通貨単位で検査し、QUADPACK見積りを厳密な誤差上限とは主張しない。128価格の最大絶対残差は \(4.064304448547773\times10^{-12}\)。ほぼ0の価格は絶対許容誤差で判定するという制約も明記している。
   - johnhull/hullkit/tests/test_lookback_reference.py:74
   - johnhull/hullkit/tests/test_lookback_reference.py:128
   - johnhull/docs/SECTION_26_11_REVIEW_2026-09-15.md:99

4. **負例が意図した誤りを検出する。** floating call／putにそれぞれ+0.25を加える2種類の改変では、対応するfixed put／callも+0.25となり、価格関係式は保たれる。その状態で4価格とも独立比較が失敗した。tracebackで失敗箇所が価格比較の131行目であることを確認しており、オラクル内の積分誤差assertによる偶発的な失敗ではない。この結果は、この共有バイアスの検出を裏付ける。
   - johnhull/hullkit/tests/test_lookback_reference.py:155
   - johnhull/hullkit/src/hullkit/exotics.py:270
   - johnhull/hullkit/src/hullkit/exotics.py:286

5. **台帳・履歴証跡・現在地の整合性が保たれる。** L01–L06の説明・図・描画はすべてpendingで、accepted数は2のまま。偽のaccepted変更とnumerical根拠の削除は既存checkerで拒否され、記録と同じエラーを再現した。既存受入節の台帳参照record全5件では95個のsource/artifact entryが開始コミットと不変で、唯一のsource hash変更は台帳件数テスト。親の保存検査はこのうち4件・90entryを対象にしており、数値の食い違いではない。M2bへの追記は、この件数更新と再検査を区別し、ブラウザ再実行を主張していない。
   - johnhull/docs/section_ledger.json:2132
   - johnhull/report/tests/test_section_ledger.py:573
   - johnhull/docs/validation/section-26-10/m2b-check.json:187
   - johnhull/docs/validation/section-26-11/m3a-check.json:49

## 指摘

- Critical：なし。
- Important：なし。
- Minor：未解決の指摘なし。

境界診断の各入力が追記され、12件すべて再現できる。\(|r-q|<10^{-8}\) の例外契約は保持されており、有限の参考価格を計算できることを実装完了と混同していない。

## レビュアー自身が実行した検証

作業ディレクトリは当該worktree、Pythonは /home/kazumasa/projects/.venv/bin/python。PYTHONDONTWRITEBYTECODE=1を指定し、pytest／ruffのcache書込みを無効にした。

~~~sh
PYTHONPATH=johnhull/hullkit/src:johnhull/report python -m pytest -q -p no:cacheprovider \
  johnhull/hullkit/tests/test_lookback_reference.py \
  johnhull/hullkit/tests/test_exotics.py \
  johnhull/hullkit/tests/test_exotics_puts.py \
  johnhull/hullkit/tests/test_hull_pins_exotics_ir.py -k lookback
~~~

**146 passed, 56 deselected（0.74秒）**。新規132件と既存の関連14件を含む。

さらに以下を実行した。

- 128価格を再計算し、保存表の全行・過去極値・行使価格・誤差・重複の有無を照合：完全一致。最大残差はsmall-positive-carry／new／fixed put／\(K=1.35S_0\)。
- Example 26.2の参考値：call 8.037120139607019、put 7.790219259890343。
- 2種類の価格改変の実際の+0.25変化と、4つの価格比較assertの失敗箇所を確認。
- 指数傾斜した反射密度の積分を80点で照合：最大確率残差 \(2.2453156695129477\times10^{-16}\)。
- 記録された12境界診断を各市場入力から再計算：参考値に一致し、本体はいずれも既存ValueError。
- ruff check --no-cache／ruff format --check --no-cache（新規テスト）：PASS。
- verify_section_ledger.pyの既定モード／--check-artifacts：PASS、306項目・accepted 2。最終統合記録追加後もartifactモードを確認。
- 最終M3a記録の14個のsource/artifact SHA-256、数値記録の4個のSHA-256、既存受入節のrecord群を照合：一致。
- 偽accepted／numerical根拠削除のメモリ上の台帳改変：記録と同じ拒否結果。
- git diff --check／git diff --cached --check：PASS。

全体pytestはレビュアーが重複実行していない。親が実行したfull-tests.logとfull-test-result.jsonを直接読み、exit code 0、**1681 passed／2 warnings／pytest計測74.32秒**を確認した。warningはtest_nbplotにおけるjapanize_matplotlib／setuptoolsのdistutils Version deprecation。統合記録の39 ledger tests、release契約、ruff／formatのPASSとも整合する。

## 判定と残る範囲

**M3aはマージ可能。** 要求整理と独立価格検証を追加し、検証結果を超えた受入表現はしていない。レビュー報告の保存と、その結果・hashを台帳／統合記録へ追記する最終メタデータ更新は親が行う。

次のM3bに残る本文、4給付・履歴・観測頻度の図、Book／portal確認、必要な既存節の再検証は、要求ノート122行目以降に明記済み。\(|r-q|<10^{-8}\)、\(T=0\)、\(\sigma=0\)、不正入力、全入力域の安定性や市場性能は今回の受入対象ではない。レビューのためのブラウザ／build再実行、価格コード編集、Git状態の変更は行っていない。
