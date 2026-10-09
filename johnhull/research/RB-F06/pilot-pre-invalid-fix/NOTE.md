# 無効枠検査の修正前pilot

元30dataset/386solver callsは全finiteで、保存/fresh checker PASSと独立数値再評価を得た。
NaN/±Infを含む無効slotの保存検査・valid quote隠蔽のguardに仕様上の問題があり、金融sourceを修正した。
元成果を変更せず保持する。このsnapshotを新sourceの条件固定には使わずpilot/へ再実行する。
