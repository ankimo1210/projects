# P7 ロジック先行の実装状態

更新2026-10-06。目的：Ch35–37（台帳16項目）の本文計算をprivate moduleに実装し、本文例と独立参照を検証する。下調べは計算11・説明中心5（旧監査の定性6とは分類基準が異なる）。

- 完了条件：既存節メモの式/例を確認、計画を数行追記、private計算部品と本文/独立検証をそろえ、変更モジュールのtests/ruffを通す。入力不足は明示して次の節へ進む。
- 1節1コミット（P7 §xx.y）、codex/p7-logicへ節ごとpush。公開API・依存・台帳を変更しない。教材・画面・章受入・全suite・D1/保管庫は保留。
- 正式受入：P7 0/16、全体33/306。Ch1からの正式受入は別チャットの専用worktreeで進むため、この作業ではその台帳/教材を編集しない。
- 現在：計算7/11、入力不足0。次は§36.3のCAPMリスク価格。

## 節別の実装

対象検証は当該節完了時のモジュール累計で、合算しない。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 制限・未解決 | 状態・対象検証 |
|---|---|---|---|---|
| §35.4 | `_commodity_foundations.py` | Ex35.1 .034/20.4%、Ex35.2 17.729k、季節6値、Fig35.1/2の分岐/shift/価格、Fig35.3中間値とD/H/I行使。独立全経路とOU密度積分・jump MC | 計算完了。原典root1.48対1.501100501、年2最下11.10対11.094790584、I8.90対8.905209416は表示精度で不一致。複雑モデルの全面較正は範囲外。 | ロジック完了・6 passed・ruff check/format PASS |
| §35.5 | `_commodity_foundations.py` | 56°F/HDD9/CDD0、HDD820→1.2M/cap1.5M/upper850。独立日別台帳とcall spread/温度換算 | 計算完了。観測期間/stationはcaller入力、Celsius換算ではbase/tickも変える。市場仕様は原典時点。 | ロジック完了・8 passed・ruff check/format PASS |
| §35.6 | `_commodity_foundations.py` | 100M exposure→retained30M、loss50M→15M、30–40M layer10MとCAT principal10M。独立3領域台帳/call spread | 計算完了。原典reinsurerのlong/short文は不整合、protection買い手の受取とwriterの逆符号を固定。triggerはcaller入力。 | ロジック完了・10 passed・ruff check/format PASS |
| §35.7 | `_commodity_foundations.py` | d1 .2376/d2 .1676、250900/243400、mean697→180400/175100。独立密度積分/MCと支払割引 | 計算完了。非取引指数・系統リスク0の本文仮定に条件付き、trend原データはなく697を本文入力として使う。log-SDへ√年数を掛けない。 | ロジック完了・12 passed・ruff check/format PASS |
| §35.8 | `_commodity_foundations.py` | 本文にデータ/数値なし。合成a+bP+cT、独立共分散正規方程式とtrain/holdoutの単独/共同hedge | 計算完了。rank不足では一意な契約数が出ないため拒否。train推定をholdoutで固定し、Q pricing/完全hedgeを主張しない。 | ロジック完了・14 passed・ruff check/format PASS |
| §36.1 | `_real_options_foundations.py` | NPV−11.53M、call.545、要求call55.96%/put−70.4%。独立cash再投資/線形replication/root | 計算完了。P期待CFをrequired rateで割引、optionとbaseの割引率を同一視しない。比較企業betaの推定は本文データなし。 | ロジック完了・2 passed・ruff check/format PASS |
| §36.2 | `_real_options_foundations.py` | A4.5355/Q drift6%/E rent33.82/expected1.5015M/PV1.3586M。独立lognormal密度/前払CF | 計算完了。λはcaller仮定/推定、非取引資産から無裁定だけでは一意でない。annuityはt=2時点、optionと二重割引しない。 | ロジック完了・5 passed・ruff check/format PASS |

## 残りと検証

- 計算対象：§35.4–35.8、§36.1–36.5、§37.1。§36.4のSchwartz–Moon株価12.42は本文のモデル入力が不足するため、再現へ逆合わせしない。
- 説明中心5項目：§35.1–35.3、§37.2–37.3。教材・正式受入を保留。
- 商品のEuler三項木はCh32の分岐部品を共有するが、通常到達確率でfutures期待値へ較正する。割引state priceを商品futures較正に使わない。
