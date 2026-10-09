# Task5 helpers targeted 再レビュー

2026-10-09。**M1 resolved。statistics / protocol とも spec・quality / source proceed 承認。未解決所見なし。** 正式 pilot・研究 freeze・study acceptance は未承認。

## 範囲と修正

初回 `task-5-helpers-review.md/.json` は変更せず継承する。今回の対象は `task-5-protocol-fix.diff` / `task-5-protocol-fix-source.json` / 最新 protocol report と M1 の修正だけ。

protocol source の 583–584 行が `includes_children` を bool に限定し、truthy numeric/string を record 採用前に ValueError で拒否する。その他の source 変更は docstring の契約明示のみ。tests は -1 と文字列 false の拒否反例追加。初回の Critical/Important 0 を継承し、新たな所見なし。

## 独立 targeted probe

- 不正 flag `-1`, `"false"`, `None`, `0`, `1`, `0.5`：すべて includes_children を理由とする ValueError。元 M1 反例も解消。
- 正常 False：親10 + 子4 を両方 charged、total wall/cpu=14。
- 正常 True：親10 のみ charged、子を excluded、total wall/cpu=10。両場合 raw total=14、raw records はそのまま保持。
- False の親と pending/None の子：charged total は None、子 unknown/raw を保持。

実装者の RED→GREEN54 / ruff check / format PASS は報告として継承。full/scoped suite は再実行しなかった。

## 指紋・継承境界

統計 source/tests は初回 SHA と一致し、不変。protocol source/tests は修正 manifest と一致する。今回の4 SHA：

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py`: `d07d4d1524a005d5b9ebe765922748aadab2175ace98ff12c941c1a38e8497ce`
- `johnhull/hullkit/tests/test_dynamic_hedging_statistics.py`: `f5b433cbf55d24b687927fd72e982832500cfebc166cd8015f63f1ba43614f1d`
- `deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py`: `5f63d5871cdf6871f83fb08bf8f403b556cf6730c40430c0fc391f5da29bda0f`
- `deep_hedge_price/tests/test_dynamic_hedging_protocol.py`: `54f55ded625e8fcd107fdf0ea6d1948a7d76d1548e208047c7d6d201c560a67c`

初回レビューの保存 bytes SHA（今回書換えなし）：

- `task-5-helpers-review.md`: `2bde39b037b99dea6b57e7dbe70f0cc5023208d1bd96513b1f80fc4d298595d0`
- `task-5-helpers-review.json`: `708cb01c07d39a61f737d9fcdf5106e8c70e09cb61a2740ee2750cdd6f4c2f99`

## Integration 義務

初回レビューに記した caller の数値 checker、source transitive closure、原始分母・全 failure/費用、call/Asian support 交差、未測定 error の資格化禁止、shared teacher covariance/error propagation、正式 pilot→freeze→selection→test 境界、共用 bootstrap indices/CAS semantic 再計算は継続する。今回の helper source approval でそれらの実装や実験達成を認証していない。
