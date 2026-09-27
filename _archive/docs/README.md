# 過去の作業記録とスキル設計

2026-09-28 に、候補ごとの確認を経て _docs/ から移しました。文書の本文は変更せず、
当時の判断と作業状態を残しています。現在の仕様・進捗・実行手順として使う前に後継を確認してください。

| 群 | 元の場所・退避理由 | 現在の入口 | 実行可能性 |
|---|---|---|---|
| [作業ログ3件](worklogs/) | _docs/worklog_*。2026年6〜7月の一時的な引き継ぎ記録で、当時の進捗が現況と混ざらないよう退避 | [gto](../../gto/README.md)、[johnhull](../../johnhull/README.md)、不動産投資は[外部の re_invest_os](https://github.com/ankimo1210/re_invest_os) | 文書のみ。記載されたコマンド・外部サービス・作業状態は再確認が必要 |
| [hull-derivatives の設計・計画2件](skill-history/) | _docs/superpowers/plans/ と specs/。2026年5月のスキル作成時の記録で、現行の参照先と区別するため退避 | [リポジトリ内のスキル控え](../../agentic-setup/claude/skills/hull-derivatives/SKILL.md) と [johnhull](../../johnhull/README.md)。稼働中のスキルとの同期状態は別途確認 | 設計・手順の履歴。本文中のスキル内リンク例は当時の配置を表し、ここからの実行やリンク解決は保証しない |

## 内訳

- [GTO M1a のマージ作業ログ](worklogs/worklog_2026-06-11_gto_m1a_merge.md)：2026-06-11 の途中経過。
- [johnhull の作業ログ](worklogs/worklog_2026-06-11_johnhull.md)：2026-06-11 時点の構成と検証。
- [不動産投資の外部サービス調査](worklogs/worklog_2026-07-07_re_invest_os_external_services.md)：2026-07-07 時点の案。
- [hull-derivatives スキル設計](skill-history/2026-05-29-hull-derivatives-skill-design.md) と
  [実装計画](skill-history/2026-05-29-hull-derivatives-skill.md)：2026-05-29 の作成時記録。

再開するときは Git の移動履歴から元の配置を確認し、必要な内容だけを現在のプロジェクト文書へ反映します。
秘密情報や個人データは索引へ転記しません。[アーカイブ全体の入口](../README.md)に戻れます。
