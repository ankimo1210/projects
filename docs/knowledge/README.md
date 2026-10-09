# 共通の知識・作業ノート

このリポジトリ全体で再利用する環境設定、手順、トラブル解決記録を置く。
プロジェクト固有の内容は各プロジェクトの README / `docs/`、
重要な判断理由は [`../decisions/`](../decisions/) を使う。

保存先の方針は [ADR 0003](../decisions/0003-keep-knowledge-in-repository.md) を参照。
ノートは必要なときに読み、秘密情報や勤務先・顧客の機密は保存しない。

- [WSL Ubuntu の仮想ディスク圧縮（2026-09-16）](2026-09-16-wsl-vhdx-compaction.md)
- [Windows のネットワーク状態を記録する（2026-09-27）](2026-09-27-network-monitor.md) — [詳細監視](network-monitor.ps1)・[1秒 ping](network-ping-monitor.ps1) の用途・実行・読み方
- [Windows PC の基準構成（2026-10-03）](2026-10-03-windows-pc-baseline.md) — 本体・モニター・周辺機器・主要ソフトウェア・WSL・メモリ帯域
- [Windows PC の性能測定（2026-10-03）](2026-10-03-windows-pc-performance.md) — CPU・メモリ・GPU・SSD・小ファイル・通信・Windows / WSL 呼び出しの実測、生データ、再測定手順
- [GPU の負荷と温度（2026-10-03）](2026-10-03-gpu-thermal.md) — 低・中・高負荷と冷却の6分間の推移、電力・ファン・制限フラグ、CPU温度の未取得事項
- [Codex 利用上限の API 料金相当額（2026-10-09）](2026-10-09-codex-usage-api-equivalent.md) — サブスクの実測ログによる30日換算、区間検証、推定の条件と再測定
