# EAGLE Playable Alpha — assisted terminal descent

日付: 2026-08-02

## 結論

EAGLE の最初の「遊べる形」は、着陸精度の未解決問題を隠さず、実 AGC / Luminary099、DSKY、P63→P66 の進行と ROD 操作を残した **ASSISTED DEMO** とする。専用シナリオだけで終端降下を補助し、既存の authentic / acceptance シナリオと合格基準は変更しない。

## 体験の範囲

- `make demo` で実 AGC を起動し、ブラウザの DSKY / ENGR から観察・操作できる。
- AGC の起動、パッドロード、TIG カウントダウン、P63、ENGINE ON、ATT HOLD、P66 は従来の実経路を使う。
- ENGINE ON 後、高度 500 m 以下では Terminal Assist が機体を水平化し、横速度を減衰させ、降下率を着陸可能な範囲へ収束させる。
- P66 では `ROD −1 / +1 ft/s` が Luminary と Assist の目標降下率の双方へ反映される。
- ENGR に常時 `ASSISTED DEMO`、補助の状態・目標降下率、接地時の 100 点スコアと速度・傾斜を表示する。

## 明示する妥協

Terminal Assist は AGC の誘導則ではなく、6-DoF 積分後の truth 速度・姿勢へ加えるゲーム用安全層である。補助による速度変化は PIPA にも戻してナビゲーションへ観測させるが、操縦結果を authentic landing の証拠には使わない。起動待ち約 5〜7 分は Alpha では残し、即時開始スナップショットと 3D 表示は次段階とする。

## Assist プロファイル

- 500 m から作動し、100 m までは 5.0 m/s の降下を目標とする。
- 100 m から接地まで、目標を 5.0 → 1.0 m/s に線形フレアする。
- 横速度は時定数 3.0 s、縦速度は時定数 1.0 s で指数収束する。
- ROD は 1 click = 0.3048 m/s。過剰入力でも降下率は 0.4〜8.0 m/s に制限する。
- 姿勢は機体 +X 軸を局所鉛直へ合わせ、角速度を止める。

## 着陸スコア

接地時の 3 軸を Apollo 判定の Hard 上限で線形採点する。

\[
S = \operatorname{round}\left(
40\max(0,1-v_v/6) +
35\max(0,1-v_h/3) +
25\max(0,1-\theta/20)
\right)
\]

ここで \(v_v\) は鉛直速度の絶対値 [m/s]、\(v_h\) は水平速度 [m/s]、\(\theta\) は傾斜角 [deg]。Touchdown の Nominal / Hard / Crash 判定自体は既存閾値を使う。

## Definition of Done

1. Assist を持たない既存シナリオの挙動が変わらない。
2. 専用シナリオの単体シミュレーションが Nominal touchdown まで到達する。
3. テレメトリと ENGR が demo / active / target / 接地値を表示する。
4. Rust tests、client tests/build、lint が通る。
5. 実 AGC の `make demo` を可能な範囲で通し、未実施部分は明記する。

## 実 AGC 検証結果

2026-08-02 に組み立て済み Luminary099 を使い、`make demo` と同じ引数で完走した。

- major mode: `00 → 63 → 66`
- ENGINE ON から接地: 91.8 s
- touchdown: Nominal
- 接地値: 縦 2.20 m/s、横 0.16 m/s、傾斜 0.0°
- score: 83 / 100
- alarm episodes: 0、接地前後 PROG lamp frames: 0 / 0
- sim pacing lost: 0 ms

この Nominal は assisted demo の結果であり、authentic acceptance の RED を上書きしない。
