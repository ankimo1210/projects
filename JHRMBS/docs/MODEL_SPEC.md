# 期限前償還モデル仕様

## 1. 推定対象

JHF の回号 $j$、支払月 $t$ に対する公表任意期限前償還 CPR を

$$
y_{j,t}=SMM_{j,t}=1-(1-CPR_{j,t})^{1/12}
$$

へ変換し、$0\le y\le1$ の fractional response として扱う。長期延滞・その他解約は別列で保持し、
任意期限前償還 model の target に混ぜない。

## 2. 比較モデル

| model | 説明変数 | 目的 |
|---|---|---|
| `fixed_psj` | WALA と終端 CPR 6% | 市場標準の固定 baseline |
| `seasoning` | 60か月 seasoning ratio | 最小の推定 baseline |
| `rate` | seasoning + rate feature | 借換インセンティブ／金利 proxy の増分検証 |
| `full` | 上記 + lagged burnout + 月季節性 + vintage + 住宅着工 YoY + M3 YoY | 公開プールデータで可能な高度 baseline |

推定モデルは logit link の Bernoulli quasi-likelihood と L2 penalty を使う。

$$
E[y_{j,t}\mid x_{j,t}]=\Lambda(\beta_0+x_{j,t}'\beta),\qquad
\Lambda(z)=\frac{1}{1+e^{-z}}
$$

weight は予測直前のプール残高 `face_amount_jpy × factor_lag1`。平均1に正規化し、単一大型 pool が
目的関数を支配しないよう20で cap する。数値特徴量は train 内中央値補完・標準化し、変換値を
model artifact に保存する。乱数 seed は設定と run metadata に記録する。

## 3. 時点整合

- pool state は同じ回号の $t-1$ 支払月、外部系列は既定で $t-1$ 月を使用する。
- target 月の実績 Factor、CPR、将来改訂値を feature にしない。
- 発行時に前月値がない行（各回号の先頭行）だけ、JHF の発行時 WAC/WAM/WALA と Factor 1.0 を
  使う。それ以外の欠損 lag は補完せず null のまま残し、学習対象から除外する。
- 学習母集団は `series_type=monthly` の通常回号のみとする。他 series への予測は外挿として
  警告し、prediction metadata に `outside_training_population` を記録する。
- 将来予測では予定 Factor path は JHF 公表値、pool Factor は一段ずつ予測して burnout を更新する。
- 金利・macro は経路 model を持たず、直近既知値を固定する。CLI で mortgage / JGB rate を上書き
  した場合は metadata に残す。
- 金利特徴量は run 内で定義を統一する。既定は全期間 `WAC-JGB 10年`。`mortgage_rate` mode は
  `WAC-current mortgage rate` を使うが、`mortgage_rate_definition` で識別した**単一定義**の履歴が
  学習行の90%以上を覆う場合だけ学習する。proxy と住宅ローン金利差を同一係数へ自動混在させない。
  override は run の mode と一致するものだけ許可する。予測時の rate feature 平行シフト
  （`rate_feature_shift_pct`）は感応度診断であり、金利パスモデルではない。

## 4. Out-of-sample 評価

ランダム分割は使用せず、各 model を split ごとに再推定する。

1. `time`: 最新12支払月を holdout。
2. `vintage`: 最新2発行暦年を holdout。

保存指標:

- CPR percentage point の MAE / RMSE
- 前月残高加重 MAE / RMSE（主指標）
- 回号別 holdout 累積元本誤差 / opening balance
- holdout 観測窓内の truncated WAL 絶対誤差

truncated WAL は債券全期間 WAL ではなく、holdout 窓内に観測された元本のみの診断値である。
`oos_predictions` に行単位の target・prediction・weight・split を保存し、集計を再計算できる。

既定予測の `champion` は、推定可能な3モデルについて split 内の加重 RMSE 順位を平均し、最小の
モデルを選ぶ。同順位は平均加重 RMSE、worst split 加重 RMSE、model 名で決着する。これにより
単一 split の偶然の勝者や、説明変数が多いだけの model を自動採用しない。選定表は
`model_selection`、選定 rule と model 名は `run.json` に保存する。

## 5. Cashflow 接続

前月実績残高 $B_{t-1}$、連続する予定 Factor $SF_{t-1}, SF_t$、予測 SMM $s_t$ から

$$
B_t^{sched}=B_{t-1}\frac{SF_t}{SF_{t-1}},\quad
P_t^{sched}=B_{t-1}-B_t^{sched},\quad
P_t^{prep}=B_t^{sched}s_t,
$$

$$
B_t=B_t^{sched}(1-s_t),\qquad I_t=B_{t-1}\frac{coupon}{12}.
$$

clean-up call は契約を推測せず、明示シナリオ時だけ設定 threshold 到達後の指定 lag で残高を償還する。

既定の $s_t$ は任意期限前償還のみである。明示フラグ時のみ、長期延滞・その他解約の直近12か月
平均月率を生存確率積 $1-\prod_k(1-s_{k})$ で合成した total decrement を適用し、scenario 名に
`_totaldec` を付して区別する。

## 6. 選定・高度化基準

MVP では、pool 月次 fraction に自然、予測が $[0,1]$、係数監査が容易、依存追加が小さいため
fractional logit を採用した。次段階は同一 split・metrics・artifact interface で GAM、issue random
effects、gradient boosting を比較する。高度 model は weighted RMSE だけでなく、時系列／vintage
双方の安定性、cashflow/WAL 誤差、calibration、proxy 依存度を満たす場合だけ採用する。

competing-risk model への移行には、3種類の decrement の時点・母数・相互排他性を資料で再確認する。
借換費用・返済額差・PV差には個別 loan 条件または透明な仮定が必要であり、MVP では実装しない。
