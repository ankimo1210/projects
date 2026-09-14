# SECTION_AUDIT_2026-09-14 レビューフィードバック

棚卸しの方向性は妥当で、D1・D3・D5・D8 などには実装上の裏付けがある。ただし、**カバレッジ分類、acceptance の保証範囲、未実装の範囲に修正が必要**。この監査を実装計画の根拠にする前に、以下を反映することを勧める。

- レビュー日: 2026-09-14
- 対象: [SECTION_AUDIT_2026-09-14.md](SECTION_AUDIT_2026-09-14.md)、653 行
- コード: `cae1cd8410c56bcefe3548aba3c691e3c4531061`（監査記載の HEAD と一致）
- 監査文書 SHA-256: `38c75ca40edb9559452e1d4e6f94998448d4e723a4a25e130f54e1f65c9d73e3`
- 範囲: 文書全体のレビューと重要主張の抜き取り検証。全 306 節・全印刷値の再監査ではない。
- 以下の行番号はこのスナップショットに対応。ソースのパスは `/home/kazumasa/projects/` 基準。

## 1. 節カバレッジは表の訂正と分類規約の統一が必要

**対象: 監査 28–33、38–40、70–73、83、86–87、108、116 行。確信度: 高。**

vol 12 の内訳は \(2+4+8+1+19=34\) で、節数 35 と合わない。章表では Ch 1・8・16・35・36 が各 nb 1 なので、**70 行の nb を 4 → 5** とすると、現行の章表・要約・合計行と整合する。巻表の現状の列合計は code 104 / nb 56 / md 46 / absent 35 / qual 64。

さらに、後続巻の実装を数えるという 73 行の規約が一貫していない。

| 例 | 現在の分類 | 確認した根拠 | 修正案 |
|---|---|---|---|
| §3.4 | nb | `johnhull/hullkit/src/hullkit/weather.py:214–226` にヘッジ比率、`johnhull/hullkit/tests/test_weather.py:68–72` にテスト。監査 418 行も解決済みと認定 | 範囲を限定して code* にするか、節のノートへの配線を必須条件にする |
| §6.3、§28.1 | nb | 監査自身の 413、447 行が `compounded_rfr`、`girsanov_weights` を実装先として挙げる | 同じ規約で再判定 |
| §7.2 | absent | `johnhull/volumes/07_swaps/build_swaps_notebook.py:277–282` に OIS/SOFR・OIS 割引の説明 | FR-01 の「四半期 OIS 気配からの bootstrap 未対応」と、節への言及の有無を分ける |
| §36.4 | qual | 監査 CR-23 は Schwartz–Moon を未実装・blocked としている。GE p.806–807 には確率過程・MC・割引期待 CF の説明がある | パラメータ不足を「計算対象なし」に含めない |

「計算対象 242 節」「計算なし 81 節」は、分類統一後に再集計した値を採用する。上の抜き取り確認だけから新しい総数は断定できない。

**提案:** 節 ID、分類、実装シンボル、テスト、ノート、部分対応の範囲、判定理由を持つ節別台帳を添え、巻表・章表をそこから集計する。分類と「印刷値の再現可否」は別項目にする。

## 2. acceptance の二分法を改め、未検出の入力も追記する

**対象: 監査 46–48、134、377、384–386、403、407、490 行。確信度: 高。優先して修正。**

「vol 18–26 は保存値、vol 27–28 は配列から再計算」という要約は強すぎる。前者にも配列検査があり、後者にも保存済み結果への依存が残る。文書内の詳細表とも整合しない。

コミット済み JSON/NPZ を読み、**メモリ内だけ**で入力を変更して `evaluate_acceptance` を呼んだ結果:

| 変更 | 結果 | 判定箇所 |
|---|---|---|
| vol 20 の test 開始を train 終了と同じ位置にする | `purged_walk_forward` が FAIL | `johnhull/scripts/frontier_acceptance.py:261–268` |
| vol 22 の `variance_clock[1] = -1` | `variance_clock` が FAIL | 同 :609–614 |
| vol 27 の `gpd_losses` を全 0 にする | 14/14 PASS、判定辞書も不変 | 同 :1315–1341 は保存推定値を使用 |
| vol 28 の `cds_bootstrap_hazard` を全 0 にする | 17/17 PASS、判定辞書も不変 | 同 :1592–1606 |
| vol 28 の `cds_survival` を全 0 にする | 17/17 PASS、判定辞書も不変 | 同 :1565–1568 は保存 PV 列を使用 |

特に **BB-18 は CDS bootstrap の欠落を追記すべき**。`cds_bootstrap_round_trip` は保存済みの再価格スプレッドと市場スプレッドを比較するだけで、保存 hazard を使わない。標準気配を再価格する要件は vol 28 spec の 211 行にもある。hazard・tenor・割引・回収率から再価格し、hazard を変えたら失敗する検査を提案に加える。「保存値依存 6 件」の件数も見直す。

D6 の「これらを読む検査は常に PASS」も限定する必要がある。

- 元本フロア検査は coupon 誤差・元本配列も、測度検査は YoY 比率差も見る（同 :1077–1105）。リテラルを保ったまま対応配列を変えると両方 FAIL になる。
- ヘッジ固定配列の問題は維持してよい（同 :1118–1128）。
- 追加すべき直接的な自己照合は、`frontier_reference.py:1942` の `adjusted_clean_price = raw_clean_price + floor` と、:1975 の同じ式からその値を引く誤差。これを :1089–1094 の gate が検査している。

**要約の修正文案:**

> 配列検査と保存値への依存が巻ごとに混在する。vol 27–28 は再計算を拡充したが、原始入力からの独立検証は全面的ではない。形状・有限性検査、保存結果の再集計、原始入力からの再価格・再推定を区別して記録する。

上の結果は静的 acceptance の判定範囲を示す。fingerprint や再構築を含む release 全体をすり抜けると実証したものではない。

## 3. D11③は「完全版」という限定を落としている

**対象: 監査 139、489 行。確信度: 高（文書の比較）。**

巻別 VALIDATION 95 行は「full Hull–White (2003) knock-out treatment」、全体 VALIDATION 264–265 行も同じ限定をしている。さらに `docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md:49` は Black 型 knock-out を対象にし、:62–63 は forward measure の厳密な扱いを除外している。

`johnhull/hullkit/src/hullkit/cds.py:195–199` に Black 型 knock-out の実装説明があることだけで、元の文書が「逆」だとは言えない。「実際に欠けているのは knock-out しない版」という結論も、この根拠からは導けない。

**修正案:** 「Black 型 knock-out は実装済み。完全版との相違点・未対応範囲の説明を明確化する」とする。non-knock-out の追加は CR-13 の独立した拡張候補として扱う。完全版との金融理論上の同等性は本レビューでは判定していない。

D11② / CR-01 の「単調性だけ」も「合成パラメータの単調性・閉形式一致はあるが、Ex 24.8 の印刷値は未固定」に直す。`johnhull/hullkit/tests/test_credit.py:60–62` に閉形式一致の assert がある。

## 4. CR-09・CR-08 は既存 API と不足するシナリオを分ける

**対象: 監査 295–296 行。確信度: 高。**

`johnhull/hullkit/src/hullkit/credit_portfolio.py:507–529` の `expected_loss_curve` は任意の detachments・相関を受け取る。「標準点のみ」は誤りで、4%・8% でも既存 API が動く。

hazard 0.02、回収率 0.4、年率 r 0.03、満期 5 年、125 社、相関 0.2 のプローブでは、ポートフォリオ元本あたりの割引期待損失について、

\[
EL_{PV}(0,8\%)-EL_{PV}(0,4\%)
=0.01355080092105326
\]

となり、直接評価した 4–8% トランシェの protection × 0.04 との差は \(1.21\times10^{-17}\)。

**CR-09 の修正案:** 未対応を「標準気配から非標準点へ補間・較正する規約と、その再価格検証」に限定する。任意境界の評価 API を新規実装する必要はない。

CR-08 の「0 件」も、バイナリ CDS 本体がないように読める。`johnhull/hullkit/src/hullkit/cds.py:116–118` に `binary_cds_spread`、`johnhull/hullkit/tests/test_cds.py:39–42` に Table 25.5 の 205 bp 固定がある。「本体と基準例は実装済み、列挙した回収率感応度等の追加シナリオは未固定」と書き分ける。

## 5. D2 は完全な呼び出し条件と符号を残す

**対象: 監査 130 行。確信度: 高。**

期中評価で初回の利払期間を誤る指摘は妥当。ただし、`bonds = -1.1870` の再現には **`accrual_to_next=0.5`** が必要で、監査の再現条件にない。

`johnhull/hullkit/src/hullkit/swaps.py:36–74` に対し、監査記載の次回利率 0.02516 を使うと:

| 計算 | 受け固定価値（名目元本 100 と同じ単位） |
|---|---:|
| bonds、既定引数 | -0.436388946734 |
| fras、既定引数 | -0.436388946734 |
| bonds、accrual_to_next=0.5 | -1.186973879936 |
| 固定クーポンを全て半年分として直接評価 | -0.291999794242 |

「手計算 0.2918」は、受け固定の負符号と、次回利率の丸め前後を明記する。以下で記載入力からの結果を再現できる。

```python
import numpy as np
from hullkit.swaps import irs_value_bonds, irs_value_fras

times = np.array([0.2, 0.7, 1.2])
zeros = np.array([0.028, 0.032, 0.034])
curve = (times, zeros)
args = (100.0, 0.03, times, curve, 0.02516)
print(irs_value_bonds(*args))
print(irs_value_fras(*args))
print(irs_value_bonds(*args, accrual_to_next=0.5))
df = np.exp(-times * zeros)
direct = 1.5 * df.sum() + 100 * df[-1] - 100 * (1 + 0.02516 * 0.5) * df[0]
print(direct)
```

## 6. 再構築による改ざん検出には vol 21 の例外がある

**対象: 監査 48、342、367–373 行。確信度: 高。**

`johnhull/scripts/verify_frontier_artifacts.py:23–30` は vol 21 の speedup、対応する acceptance の observed、NPZ companion hash を比較時に正規化する。:33–46 では timing 配列を厳密比較から除外し、正値だけを検査する。

一時ディレクトリで同じ比較関数を実行し、speedup と observed を 2 倍、companion hash を変更しても正規化後の JSON が同じになることを確認した。`nested_mc_ms` を 2 倍にした NPZ も比較関数を通った。

**修正案:** 「vol 19–28 の再構築は原則として決定的成果物の差分を検出する。ただし vol 21 の計測値・関連フィールドは明示的に除外」と限定する。

BA-10 の「SHA はそもそも不要」も再考したい。決定的な数値配列の一致は、計測した実装の来歴を保証しない。`build_frontier_artifacts.py:526–527` が sources を無視して古い計測値を保存する問題には、計測時の source revision・環境を保持し、通常再生成の digest と区別する案が適切。SHA の削除は来歴を別途残すかを決めてから行う。

## 7. 実行順序と完了条件を具体化する

**対象: 監査 20–27、357、391、393、398、407、621、647–653 行。以下は改善提案。**

- **見積もり:** 647 行の「すべて S」は D6 の S–M、D8 の再生成＋照合 gate と合わない。D2 の API 判断、D4 の指標判断も先に必要。「確認済み欠陥を優先し、変更ごとに必要な判断と検証を置く」とする。
- **検証強化の順番:** 大型機能追加より前に、既存の PASS の根拠と出力の鮮度を修正する。BB-18 の hazard 再価格など、現在のチェック名・件数・許容値を保って判定を強化できる作業と、指標・閾値・検査集合を変える作業を分ける。生成物や fingerprint の更新は別途記録する。
- **now / decision:** BA-04 は decision、BB-04・BB-09・BB-18 は now、621 行ではまとめて判断事項になっている。また「vol 18–26」という行に vol 27/28 の ID が含まれる。技術的な実行可否と、API・仕様・release 契約の変更判断を別列にする。now は作業の承認を意味しない。
- **D5 / BB-02 の完了条件:** 「2 つの RMSE が異なること」では修正の正しさを検証できない。別の標本でも RMSE が偶然一致し得る。満期×αの全組合せ、固定した他条件、診断マスクの選択行、配列から再計算した RMSE の一致を検査する。26.2144 の単位も「価格 × \(10^4\) の bp」と明記する。
- **再現性:** scratch プローブ由来の数値には、完全な入力、seed、経路数・step 数、金利・利払・損失符号の規約、期待値、許容誤差と理由を添える。grep 不一致、静的確認、実行再現、印刷値照合を別々に記録し、✅ の根拠を追えるようにする。

推奨する最初の単位は、監査文書の上記訂正 → D1/D2 等の再現ケースと判定条件の確定 → acceptance・出力照合の補強 → 必要な成果物の再生成 → 未対応機能の追加。既定 seed の統一は、それ自体を欠陥修正の前提にしない。

## 検証記録と限界

- 監査全文、対象ソース・テスト・spec・VALIDATION の該当範囲を照合した。
- 巻表を機械集計し、GE PDF の §7.2 / §36.4 等を抜き取り確認した。
- D1・D2・CR-09 の軽い実行、vol 20/22/26/27/28 のメモリ内 acceptance 変更、vol 21 の一時ファイルでの比較を行った。
- 次の既存テストを実行し、**17 passed in 0.48s**。この成功は D2 の欠陥がないことを意味しない。

```bash
cd /home/kazumasa/projects
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  johnhull/hullkit/tests/test_rates.py johnhull/hullkit/tests/test_swaps.py
```

以下は bootstrap 検査の不足をファイル変更なしで再現する最小コード。projects root から `.venv/bin/python -B` で実行できる。

```python
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "johnhull/scripts")
from frontier_acceptance import evaluate_acceptance

ref = Path("johnhull/volumes/28_credit_desk/reference")
metrics = json.loads((ref / "metrics.json").read_text())["metrics"]
with np.load(ref / "credit_scenarios.npz", allow_pickle=False) as stored:
    arrays = {name: stored[name].copy() for name in stored.files}
before = evaluate_acceptance(28, metrics, arrays)
arrays["cds_bootstrap_hazard"][:] = 0.0
after = evaluate_acceptance(28, metrics, arrays)
print(before == after, after["passed"], len(after["checks"]))
# このスナップショットでは True True 17
```

全テスト、book build、artifact 再生成、release gate は実行していない。原監査・コード・成果物は変更しておらず、本フィードバックだけを追加した。ここで未確認とした主張は、実装着手前に対応する原典・入力条件を確認する必要がある。
