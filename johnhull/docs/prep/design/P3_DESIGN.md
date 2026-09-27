# P3：金利の章を受け入れる順序と独立参照

- 日付：2026-09-27。準備設計。Ch28–34の節受入・ツリー/LMM実装は未着手。
- 主線：P1→P2→P3。RB-F03は本編の該当要求へ組み込む。
- 完了条件：各節の原典要求、数値・契約・図・配布画面の証跡を揃えた受入。既存APIがあるだけでは完了にしない。
- 要求の詳細は [Ch28](../sections/ch28.md) から [Ch34](../sections/ch34.md) の草稿を参照。

## 1. 順序と境界

| 段階 | 本文で扱うもの | 検証の中心 |
|---|---|---|
| P3-1 Ch28 | numeraire・測度・martingale・応用 | 同じ契約の割引期待値を異なる測度で照合。PとQ、価格と予測を区別 |
| P3-2 Ch29 | bond option・cap/floor・欧州swaptionのBlack表現 | forward・annuity・fixing/paymentの単位、put-call parity、印刷値 |
| P3-3 Ch30 | convexity・timing・quanto | 無調整極限、相関の符号、1条件ずつ変更した独立小例 |
| P3-4 Ch31 | 短期金利・実測度と価格測度・affine | 条件付き平均/分散、解析ZCB、Euler等の時間刻み誤差 |
| P3-5 Ch32 | 曲線に合うモデル、HW三項木、一般化、較正 | 初期曲線→欧州価格→行使→較正の順。BKの本文説明も残す |
| P3-6 Ch33 | HJM、BGM/LMM、Bermudanへの応用 | drift・numeraire・caplet/swaption・行使方策の独立比較 |
| P3-7 Ch34 | 非標準swap | キャッシュフロー・複製・価格調整の契約ごとの確認 |

この順序は要求の依存関係を示す。節ごとの不足を見て小さな受入単位に分ける。
全機能を一括で追加する計画ではない。BK・時間依存volの原典にある説明を「研究拡張」として丸ごと除外しない。
その先の高機能な数値エンジン、2因子G2++との広い比較、多通貨多曲線は別の拡張範囲とする。

## 2. 既存資産を正しく使う

| 資産 | 再利用できること | 残る不足 |
|---|---|---|
| `hullkit.ir_options:bond_option_black`, `caplet_black`, `cap_black`, `swaption_black` | 規約を揃えた欧州価格・parity | 木・経路・早期行使の実装ではない |
| `hullkit.ir_options:bond_yield_convexity` | Ch30の局所convexity例 | 多通貨・担保・全smile調整の一般器ではない |
| `hullkit.hull_white:HullWhiteParams`, `HullWhiteSwaption` | 定数a/σ・契約fixture | 時間依存σや多曲線契約を既存仕様へ暗黙に足さない |
| `hullkit.hull_white:hw_discount_bond`, `hw_zcb_option`, `hw_jamshidian_swaption` | 解析的な欧州参照 | Bermudan・一般couponのJamshidian成立条件は別 |
| `hullkit.hull_white:hw_exact_transition`, `simulate_hw_paths`, `calibrate_hw1f` | OU状態の遷移・既存較正 | 状態の厳密遷移だけで積分金利の数値誤差まで消えない |
| ratesvolのHW1F/G2++ MC・HJM/LMM | 別実装での方式比較候補 | import依存を作らない。HW/G2++はEuler、ZCBは積分の離散化があるため厳密解扱いしない |

ratesvolの比較は数値fixtureと結果の照合で行う。同じ式・同じ補助関数を共有して「独立」と呼ばない。
比較側の版・scheme・時間刻み・SEを記録し、まず解析ZCBと欧州価格への収束を確認する。

## 3. 最初のHW木の仕様案

1. 単一通貨・単一割引曲線、定数a/σ、無信用・無取引費用。曲線は正の割引因子、補間法と年率単位を固定。
2. 原典の平均回帰による分岐変更を実装し、確率の和1・非負、条件付き一次/二次モーメントを確認する。
3. 各時点の状態価格の和で初期曲線を再現する。短期金利の単純な平行移動と状態価格調整の手順を図示する。
4. ZCB・ZCB option→単一行使payer/receiver swaption→複数行使へ進む。
5. 支払日と行使日を格子に入れ、支払直前/直後、行使時の経過利息、元本、call/put方向を固定する。
6. 時間格子・金利端点を別々に細かくし、価格と行使境界の安定性を記録する。誤差の相殺だけで合格にしない。

| 独立確認 | 判定案 |
|---|---|
| 曲線の再現 | 各満期の状態価格和と入力DF、数値解法の残差を保存 |
| 欧州の極限 | 1行使の木をJamshidian・ZCB optionと照合。契約が適用条件外なら低次元PDE等 |
| Bermudan | 価値≥対応する任意の単一行使欧州価格、行使日の追加で非減少、receiver/payerの方向を確認 |
| MC側 | 行使回帰のtrainと評価pathを分離。下界推定だけを厳密価格と呼ばない |
| dual上界 | 必要な場合は条件付き期待値・martingale条件・外側SEを検査。S001とP1の成果を再利用 |
| 較正 | 人工truthの価格生成と再較正、複数初期値、残差・識別性・失敗status。小残差だけでtruth回復を要求しない |

許容差・計算予算は独立参照の収束pilotから決め、受入試料を見る前に固定する。
短期・deep ITM/OTM・a→0・σ→0、負金利のHWと正値制約のBKも検討対象にする。

## 4. HJM/LMMと拡張の境界

- LMMではtenor・fixing後の凍結・共分散・spot/terminal測度のdrift・numeraireを契約に含める。
- 1期間capletをBlackと照合し、複数期間へ進む。predictor-corrector等のscheme差とMC SEを分ける。
- freeze-drift近似や単一caplet例を「完全なLMM」「Bermudan完成」と表示しない。
- Hull本文の範囲を受け入れた後に、normal/shifted lognormal、担保通貨、多曲線、2因子比較へ拡張する。
- RB-F07は市場quote感応度、RB-F06は識別性の見方を提供するが、P3受入を研究の成功に依存させない。

## 5. 成果物と着手条件

節別要求・契約fixture・独立計算表・tree/行使境界図・較正診断・Book/portalの表示記録を小分けに残す。
D1後の保管庫へ画像を保存し、Gitには要求・数値契約・manifestを置く。
公開API・依存追加は具体的な仕様で別承認。現時点では方式と順序を決める準備資料であり、実装承認・受入記録ではない。
