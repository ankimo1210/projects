# アーカイブ索引

2026-09-28確認。ここは退避済みの成果・旧構成を履歴として読む場所です。
現役の入口は [ルート README](../README.md)。新たな退避は
[整理計画](../docs/superpowers/plans/2026-09-27-workspace-cleanup.md) に沿って候補ごとに判断します。

## 退避済みの6群

| 群 | 退避理由・根拠 | 後継・現在の入口 | 実行可能性 |
|---|---|---|---|
| [capability_index/](capability_index/) | 旧横断索引。各プロジェクトの README / AGENTS / CLAUDE を入口にする構成へ変更（2026-05-21、`a7ec74a9`） | [ルート索引](../README.md)、各プロジェクトの文書 | 文書のみ。記載パスは退避時点の情報で、実行手順の正本ではない |
| [land_price_api_app/](land_price_api_app/README.md) | Streamlit PoC のデータ取得基盤を外部へ移管（2026-06-13、`b57432bd`） | [re_invest_os](https://github.com/ankimo1210/re_invest_os) の `packages/market-data` と `docs/data/market-data.md` | root uv workspace 非メンバー。旧 README 下段は当時の手順で、移管前データ参照も残る。ここでの起動は未検証 |
| [notebooks/](notebooks/) | 旧世代の不動産シミュと未完成の Streamlit 試作を保存（2026-05-21、`a7ec74a9`） | [現行の探索ノート](../notebooks/README.md)、製品開発は外部 re_invest_os | 下記参照。現在の配置・依存での再実行は未検証 |
| [restructure_prompts/](restructure_prompts/) | 旧ワークスペース再編プロンプトをルートから履歴資料へ移した（2026-05-21、`e4a807c9`） | [AGENTS.md](../AGENTS.md) と [今回の整理計画](../docs/superpowers/plans/2026-09-27-workspace-cleanup.md) | 文書のみ。当時の作業指示であり、今の構成にそのまま適用しない |
| [scratch/](scratch/README.md) | 2026年4月の単発比較ノート8件を、候補ごとの確認を経て作業場所から退避（2026-09-27） | [market-research](../market-research/README.md) は現役の市場研究入口。ノートの機能移植は未確定 | 出力付きノートをそのまま保管。移動後の再実行は未検証 |
| [docs/](docs/README.md) | 2026年6〜7月の一時作業ログ3件と、同年5月の旧スキル設計・計画2件を _docs から個別確認後に退避（2026-09-28） | [各対象の現行入口](docs/README.md) | 文書のみ。記録中の手順・配置は再確認が必要 |

### notebooks の内訳

- [old_real_estate_sim/](notebooks/old_real_estate_sim/): 旧ノート4件と生成スクリプト4件。
  現行の探索版は [real_estate_investment_sim.ipynb](../notebooks/real_estate/real_estate_investment_sim.ipynb)。
  旧スクリプトの出力先・依存を確認してから再実行する。
- [real_estate_app/](notebooks/real_estate_app/README_local_app.md): Streamlit 試作。
  旧 README の起動ディレクトリは移動前のもの。Python / Streamlit 等の環境と相対参照の確認が必要。
  外部 re_invest_os は製品開発の入口であり、この試作の全機能が移植済みという意味ではない。

追跡外の `tmp` 等はこの索引の対象外です。中身・所有者を確認するまでは、退避済みとみなしたり削除したりしません。

## 次に退避するときの記録テンプレート

候補ごとに次の内容を埋め、確認後にこの索引へ追加します。
個人データの中身・詳細な所在や秘密情報は書きません。

```text
名称 / 元のプロジェクト:
退避日 / 確認者:
退避理由:
後継の入口 / 重複を確認した機能:
後継にない機能 / 残す成果:
判断の根拠（コミット・比較結果）:
実行可能性（検証済み / 未検証 / 実行対象外）:
必要な環境・外部依存 / 旧パスの注意:
再開・復元方法:
参照リンクの更新箇所:
```
