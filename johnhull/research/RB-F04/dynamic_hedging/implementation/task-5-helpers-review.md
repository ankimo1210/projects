# Task5 statistics / protocol helper 独立レビュー

2026-10-09。凍結された disjoint 4 files の source checkpoint に限る。**statistics / protocol とも source proceed 承認**。Critical 0、Important 0、Minor 1。正式研究 freeze・pilot・study acceptance は承認していない。

## 判定

| Component | Spec | Code quality | Source proceed |
|---|---|---|---|
| statistics | approved | approved | 可 |
| protocol / expenses / artifacts | approved | approved with Minor M1 | 可 |

## 所見

### Minor M1 — includes_children の型を検査する

`deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py:579–611`（型検査なしのまま、611 行で inclusive 判定）。独立反例：親 wall/cpu=10、子 wall/cpu=4、親 `includes_children=-1` を受理し、子を excluded、charged_totals=10 とする。通常の bool receipt は正しく集計するが、不正な integer flag が費用除外を決められる。

最小修正：record 採用前に `includes_children` を bool に限定し、整数/null/string を明示的に拒否する。小さな拒否反例を追加する。source proceed を阻む金融欠陥ではない。

## 確認した契約

- 統計：同一 original seed/path の per-path d/r、baseline sampling uncertainty、seed 内 64 path blocks・保存 indices の無抽選 replay、Bonferroni .05/8 と全 3 init の IUT、strict `U_d+u_d<-.001` / `U_r+u_r<0`、missing envelope / 原始 nonfinite の unknown、個別 loss 上位 ceil(5% * original count) の ES を保持。finite subset は descriptive のみ。3 training seeds を path 分母へ乗算しない。
- protocol：固定 44 cells / 12 fits、用途別 local seed namespace、canonical source/receipt/frozen bindings、固定 width 全候補と失敗・重複・元分母・512 updates・300 秒 cap・test 非開封を検査。数値資格は caller checker が担う境界が docstring/report に明示される。
- expenses/artifacts：pending timing は None、failed reason を保持し、overrun を追加加算しない。inclusive 祖先で raw と charged を分ける。新規 immutable directory、object/pickle 拒否、header 込み 256 MiB expanded limit、load 時の bytes hash / dtype / shape / roster を確認。hash は金融精度の証明ではない。

## 検証と由来

canonical DESIGN §§8–13、Task5 split plan/root index、両 review-package.diff / review-source.json / report、4 source/tests を読んだ。実際の 4 SHA256 は manifest と一致する。実装者が報告した 41 statistics + 1 doc guard / 52 protocol と ruff/format GREEN は継承証拠であり、こちらで suite は再実行していない。

独立小 probe（3 seeds ×128 paths、64 path blocks、2 手指定 replay）：paired d bootstrap の手計算との差最大 `1.1102230246251565e-16`、within-seed per-path IID SE 差 0、individual ES95 差 0、original_count=384。M1 は上記 ledger の直接入力で再現した。性能・有限標本被覆・実 pilot 達成は主張しない。

## Caller integration に残る義務

- 実依存の transitive source closure、全 phase/attempt の required expense IDs、全 failure/weights/timing/raw primitives は caller が保存して検査する。
- 18 selected states/37 quotes・teacher の最小 qualified N/grid・accuracy/moment/Q gates は独立 saved numeric checker が全元分母から再計算する。receipt の checker 名/hash は真正性や金融精度の認証ではない。
- call/Asian support の交差を fit caller に渡し、未測定の reference/denominator/interpolation error を ok として資格化しない。shared teacher cluster covariance と deterministic error を同じ operator/F07 へ伝播する。
- 正式 pilot、費用審査、全 source/code/math/pilot review の後に研究 freeze、その後 main 12 fits と全 selection 終了前の test 非開封を caller が実際の実行境界で強制する。
- 保存 int16(2000,3,B) indices を全 method/G/init に共用し、全 original path・init と独立 reserved refinement envelope/Q/訓練完了を family 判定へ結合する。
- 256 MiB 以下 chunk の全 roster/CAS copies/load と金融 semantic 再計算、inclusive expense の実測範囲を caller が確認する。

## 承認範囲外

未完成 orchestrator、正式 pilot の accuracy/Q/moment 達成、全 12 fits/44 main cells、正式 freeze、最終受入、CAS 全復元。これらの未来の gate は今回の source defect を免除する理由にはしていない。caller-owned 数値 checker を helper 自身が実装していないことも、本境界の欠陥には数えない。

## SHA256

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py`: `d07d4d1524a005d5b9ebe765922748aadab2175ace98ff12c941c1a38e8497ce`
- `johnhull/hullkit/tests/test_dynamic_hedging_statistics.py`: `f5b433cbf55d24b687927fd72e982832500cfebc166cd8015f63f1ba43614f1d`
- `deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py`: `bbe326e8b1c31daf37a56e86a0464eb35cd8fed3e9dbf8e9f71291bf39f63700`
- `deep_hedge_price/tests/test_dynamic_hedging_protocol.py`: `1286179495e115ca435afe54be67af48caf034311556af7ab90f972da3f0aa36`
