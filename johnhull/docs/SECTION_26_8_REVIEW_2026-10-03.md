# §26.8 Chooser：原典照合とレビュー

日付2026-10-03、Hull 11e GE pp.619–620、main基点5013f2d4。

## 原典と実装の照合

標準的な同じstrike/満期のchooser、T1でのmax(c1,p1)、parity導出、T2call一枚と配当調整putを照合。
put枚数wとstrike H、選択境界とT1/T2の時点を区別した。
原典最後のcomplex chooserは本文で明記して範囲外とした。
原典には印刷数値例なし、以下は合成。

合成基準S=K=100、r5%、q2%、σ20%、T1=.5、T2=1：chooser=13.3442804480692。
選択境界H=98.5111939603063、put枚数w=0.990049833749168。
T1=.1/.5/.9/.999999の独立求積価格は10.483695744000126/13.344280448069238/15.168232237397923/15.55708234558728。
64ケースと図の全曲線で最大API差4.263256e-14通貨、複製差1.421085e-14、同次性差4.263256e-14、bounds逸脱2.842171e-14。
求積の誤差見積り最大4.867409e-11。低σ・負のr/q・T1/T2=.999999・両端点・zeroσ/満期を含む。
seed268、524288経路×4の条件付きMCは最大1.505955標準誤差で6SE以内。


## 検証と証跡

64独立求積・4MC、4保存改変/4実API変異、source欠落/参照改変拒否、notebook4改変を確認。
旧202セルを保存、213セルfresh検査。16表示状態/16画像、Book数式983・エラー0。
既受入24節のbrowser・runtime probe・個別pytest計1,868件・C:/F:両保管庫復元はPASS。23節再利用・1節再描画、追加保存505,902バイト。採用D1パスとSHA-256を固定。

## 実装者の判断

アプリworktreeはWindows側GitのUNC所有権拒否で作成できず、WSL Gitで専用worktreeを作成した。
共有Windows Gitのtrust設定を変えず、既存工程を維持する。誤りなら手動の管理/片付けの負担が残る。
初回baselineの1失敗はmain側namespace importを選んだ実行環境が原因で、worktree rootのPYTHONPATHとcwdを指定すると同じテストがPASSした。製品コードは変更していない。
歴史M24検査から新4.15だけを除く方針は計画どおり。旧202セルの保存をM25で検査。

## 独立最終レビュー

fresh-contextのgpt-6-astra（high）一名が、5013f2d4..721f14f4、原典、spec/plan、判断記録を読み取り専用でレビューした。Criticalなし、Important I1一件、Minor M1一件。効果による再判定でも同じ区分とした。再レビューは行わない。

### I1の修正と検証

object配列に含まれるNumPy complex scalarの虚部がfloat変換で捨てられ、誤った市場の価格を返す問題を修正した。変換前の配列とobject要素を検査し、複素数をValueErrorに統一する。有効な実数object配列のbroadcastは維持する。

complex64/complex128×全7入力と、0次元/mixed・虚部ゼロの4例、計18例の拒否テストは修正前にすべてFAIL、修正後にPASS。実数object配列の回帰例も含め、APIは45 passed。
修正後の数値/notebook記録を再生成し、16表示状態のbrowser検査を再実行した。実数の教材曲線と価格は不変で、既存HTMLの全traceを現行計算と比較した。旧24節のD1依存は変更されていないことを統合ゲートで照合する。
全suite・最終commit/releaseの結果は検証完了後に追記する。

### Deferred minors

- M1: 空batchとのbroadcastでK<0、σ<0、T1>T2等の不正設定が消え、空配列を返す。誤った価格は返さないためMinorとして保留。修正範囲には含めない。

### Rulings I made（判断順、誤りだった場合の費用）

1. 専用worktreeはWSL Gitで作成した。共有Windows trust設定を変更しないため。誤りなら手動管理/片付けの負担が残る。
2. M22の図と価格例の満期差は既存保留を維持する。未変更の受入済み教材のため。誤りなら読者が両者を同じ例と誤解する。
3. M23のNaN変異を拒否しない旧ゲートは維持する。chooserは有限出力を検査する。誤りなら旧モデルの非有限値回帰を見逃す。
4. M24の約32マイクロ秒の満期差での求積失敗は既存制限として維持する。誤りなら極端に近い満期のcompound価格を得られない。
5. 旧24モデル全体の数理を再導出せず、既受入と現行D1検査を根拠とする。誤りなら過去の数理上の欠陥が残る。
6. complex chooser/American/smile/確率的金利・変動率/離散配当は明記した範囲外を維持する。誤りなら仮定外での利用に不適切な価格を返す。
7. 独立求積の保証対象は固定64例と教材曲線とし、任意の極端な市場条件の一般保証はしない。誤りなら範囲外の参照価格が不正確になる。
8. 全画面再実行と全画像目視をレビュアーが行わない点は、実装者の16状態再実行・2画像目視と、レビュアーのコード/hash・2画像確認で補う。誤りなら他状態の配置問題が残る。
9. レビュアーの対象57件に加え、修正後に実装者が全suiteを再実行する。誤りなら独立レビューが対象外の相互作用を見逃す。

### 独立レビュアー報告（原文）

````markdown
## Strengths

- 原典 pp.619–620 と照合し、put の枚数 \(e^{-q(T_2-T_1)}\)、行使価格 \(Ke^{-(r-q)(T_2-T_1)}\)、\(T_1\) の選択と \(T_2\) の決済が正しく区別されています。
- 通常の市場入力、負の \(r/q\)、境界条件、近接満期について実装と独立参照が一致しています。独立参照は production API を使わず、選択境界と狭い vanilla 遷移を分割しています。
- 受入ゲートは数値の再計算、必要なハッシュ集合、旧24節の採用記録、両保管庫の実データを検査しています。旧202セルの本文・出力・Plotly の保存も確認されています。
- 対象57テスト、4種類の `--check`、台帳の `--check-artifacts` は独立実行で PASS。閲覧した1000px画像2枚に明らかな文字切れ・overflow はありません。

## Issues

### Critical

なし。

### Important — I1: object 配列内の NumPy 複素数を実数として価格化する

**場所:** `johnhull/hullkit/src/hullkit/chooser.py:24–26`

**再現:**

```python
chooser_price(
    100, np.array([np.complex128(100 + 3j)], dtype=object),
    .05, .2, .5, 1, .02,
)
```

**実結果:** `ComplexWarning` を出して虚部を捨て、`[13.34428045]` を返します。

`np.iscomplexobj` は object 配列内の要素を調べません。続く float 変換は NumPy complex scalar を拒否せず変換できます。既存テストの Python `complex` 要素では例外になるため、この差を捕捉できていません。

**影響:** 有限実数のみを受け付ける公開APIに非実数が入り、別の市場条件の価格として返されます。上流のデータ型や計算異常を見逃します。

**修正案:** float 変換前に object 配列内の複素数要素も拒否するか、複素数からの変換警告を捕捉して `ValueError` に統一してください。`np.complex64` / `np.complex128` を含む object 配列を回帰テストに追加してください。

### Minor — M1: 空配列との broadcast で不正な市場条件が消える

**場所:** `johnhull/hullkit/src/hullkit/chooser.py:32–37`

**再現:** `S=np.array([])` とし、通常の基準入力の `K=-1`、`sigma=-.2`、または `T1=2, T2=1` を指定します。

**実結果:** いずれも `ValueError` にならず `[]` を返します。broadcast 後に全配列が空になるため、領域検証を通過します。一方、NaN や infinity は broadcast 前に拒否されます。

**影響:** 空のバッチ処理において不正な設定が検出されず、入力検証の結果がバッチ件数で変わります。価格の誤返却はないため軽微です。

**修正案:** 各入力の単独の領域条件を broadcast 前に検査し、時点間の条件は `T1/T2` の組で検証してください。有効な空配列の返却は維持できます。

## Declined to judge

- **M22 の既存保留:** 経路図の `T1=.75/T2=1.75` と本文の価格例 `T1=1/T2=2` の対応説明。未変更の旧教材であり、今回修正対象には含めません。
- **M23 の既存保留:** 歴史数値ゲートが API の NaN 変異を拒否しない問題。今回の chooser ゲートは有限値を明示検査しており、旧ゲートの改修は範囲外です。
- **M24 の既存保留:** 約32マイクロ秒の満期差で compound API が数値積分に失敗する制限。未変更であり、今回再評価していません。
- **旧24節の金融モデル全体の再導出:** 現行依存・保存記録・成果物は検証しましたが、各モデルの全面的な数理レビューはしていません。
- **complex chooser、American、smile、確率的金利・変動率、離散配当等:** 承認済み範囲外です。
- **独立参照関数を任意の極端な市場条件で使用した場合の一般的精度保証:** 固定64ケースと教材曲線が対象です。固定積分区間 `[-12,12]` の万能な誤差保証までは評価していません。
- **全ブラウザ状態の新規実行・全画像の目視:** 読み取り専用のため証跡を再生成せず、検証コード、ハッシュ照合、保存画像2枚を確認しました。
- **全3738テストの再実行:** 実装者の報告と区別し、私が実行したのは以下の対象57件です。

## 実行した検証

- `python -m pytest -q` — chooser 関連8ファイル：**57 passed**
  - `test_chooser.py`
  - `test_chooser_reference.py`
  - `test_chooser_numerics.py`
  - `test_chooser_lesson.py`
  - `test_chooser_notebook.py`
  - `test_chooser_acceptance_record.py`
  - `test_chooser_ledger_update.py`
  - `test_chooser_registry.py`
- 次の各スクリプトの `--check`：**すべて PASS**
  - `build_chooser_reference.py`
  - `verify_chooser_numerics.py`
  - `verify_chooser_notebook.py`
  - `build_chooser_acceptance_record.py`
- `verify_section_ledger.py --check-artifacts`：**PASS、306節中25節 accepted**
- I1・M1 のメモリ上の再現コード。
- 最後の `git status --short` は空、HEAD は `721f14f409c209bbb25a6c532b09c6e21f513ad3e` ではなく、指定どおり **`721f14f409c209bbb25f2a1b34189dafa68b142d`** です。ファイルは変更していません。

## Assessment

**Ready to merge? With fixes.**

数理・教材・証跡の構成は良好ですが、I1 の非実数入力の拒否漏れは統合前に修正してください。M1 は軽微な保留として扱えます。
````
