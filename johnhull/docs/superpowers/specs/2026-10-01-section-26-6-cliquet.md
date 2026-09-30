# M23 §26.6 Cliquet Options

承認範囲：P2の既存実装計画とユーザーの「go ahead」に従い、M22をmainへローカル統合し、次の§26.6を実装する。原典Hull 11e Global Edition p.618、準備資料docs/prep/sections/ch26.md。日付2026-10-01。既存の節受入手順の範囲で設計を具体化し、本人が承認済みの実装再開・継続を再確認で止めない。

## 契約と要求

固定した支払日0<t1<…<tnとt0=0を用いる。各期の行使価格は開始日の株価S(ti−1)、給付はcallがmax(S(ti)−S(ti−1),0)、putが逆の正部分、支払日は各ti。単位は原資産1単位当たりの通貨で、固定notionalに対する正のreturnの和とは異なる。定数r,q,σのGBM。

- CQ01：ratchet/strike-resetという名称、各期のstrike fixingと支払日を経路・cashflowで説明する。
- CQ02：最初の通常ATMオプションと後続のforward-startの和を実装し、各期の価値S0 exp(−q ti−1) c_unit(ti−ti−1)を足す。全給付をtnからまとめて割り引かない。
- CQ03：専用公開モジュールhullkit.cliquetのcliquet_call(S,r,sigma,payment_times,q=0)とcliquet_put（同シグネチャ）。固定1次元支払scheduleに対し市場入力をbroadcast。scalarはfloat、配列はndarray。S>0、σ≥0、全入力有限実数。scheduleは非空・正・厳密増加。n=1はATMvanilla、ゼロσは決定的給付。不整合shape・非実数・非有限・表現範囲外計算はValueError。
- CQ04：hullkit/CDFを使わない二増分密度求積60契約と、resetを含むGBM経路の各日割引MC（524288経路、call/put×2schedule）を独立参照にする。成分和、一次同次性、call-putの期待cashflow差を照合。固定strike・満期一括割引・固定notional returnへの誤変更をAPI変異で拒否する。
- CQ05：global cap/floor・範囲内での期末終了が単純和を崩すことを説明する。r=q=0の別の合成例で、期間給付の合計、全体floor/cap、各期cap、期末範囲終了を同じMC経路で比較する。r=0により支払日差の割引効果を除き、制約の非線形性を区別する。複雑型のpublic API、return cliquet、実市場smileは追加しない。
- CQ06：vol10 §4.13.1–4.13.6の11セル・4共有図、旧180セル保持、Book/portal×1440/1000pxの16状態・16画像・数式・trace・MC誤差棒・改変拒否、既受入22節のD1と両保管庫復元、台帳accepted23/unreviewed283を検証する。

## 構成と受入

callは既存forward_start_callを各期へ適用する。putはnormalized BSM putの同次性を利用する。既存pricingコード・hullkit.__init__・公開シグネチャを維持し、新しいproduction依存は追加しない。公開APIの追加はP2で欠けていた§26.6の実装として承認範囲に含まれる。

4図のキーはcliquet_reset、cliquet_components、cliquet_frequency、cliquet_limits。最初の3図は同じS=100,r=5%,q=3%,σ=20%を使い、契約図・成分図の支払日は0.5/1/1.5/2年。頻度図は満期2年でn=1/2/4/8/12/24。制約図は別市場r=q=0と明記する。原典に印刷数値例はない。全数値は合成。

M22のP3（経路図と価格例の時点差の本文明記不足）は既存の保留指摘として残す。今回の変更で旧セルを修正せず、M23の図ごとの前提は明記する。

作業は既存分離worktree /home/kazumasa/worktrees/m18、branch codex/m23-cliquet-options、基点main=14c94ac2。M22をローカル統合済み。mainの他プロジェクトの変更は保持する。Git/buildはWSL、共有venv /home/kazumasa/projects/.venv。M23のmain統合・pushは実装完了後の別選択を待つ。

参照・数値・notebook・browser・M23統合ゲート、全hullkit+report pytest、ruff、台帳通常/成果物検査、releaseとコミット後tracked検査を通す。実装は本人が継続承認したinline方式。executing-plansに従い最も能力の高い許可モデルで独立最終レビューを1本実施する。
