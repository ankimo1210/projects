# OpenAI と Anthropic API の検証と引き継ぎ

更新日: 2026-11-01（JST）

両社の API 利用・検索付き調査・機能比較スモークテストを実行済み。
スモークテストは OpenAI が全項目 PASS、Anthropic は JSON 形式のみ PASS。
クレジット残高・利用額の API 取得は未完了。
ユーザーは残高を API 経由で確認したい。今後の残高確認ではコンピューターユーズを使わない。

## 確認済み

- OpenAI `gpt-6-luna`、Anthropic `claude-haiku-5-5` とも、認証・短い文章生成は HTTP 200。
- 同じ質問で検索付きの全国 CPI 調査を実行。最新は 2026年9月分（10月23日公表）、前年同月比は総合 +2.1%、生鮮食品を除く総合 +2.1%、生鮮食品及びエネルギーを除く総合 +2.4%。両社の主要数値は統計局の原文と一致した。
- Anthropic は初回、思考用トークンの消費で回答が出力上限に達した。同じ質問・上限で `thinking: {"type": "disabled"}` のみを追加し、検索付き回答が `end_turn` で完了した。簡単な調査では検索回数と出力上限を制限する。

## 機能比較スモークテスト

2026-11-01 15:49 JST に、同じ架空の円建て債券3本・プロンプト・JSON Schema で実行した。
金利 +25 bp、信用スプレッド +40 bp に対し、Python の `calculate_pnl` が
固定 DV01 の線形損益を計算する。正解は金利 -3,325,000 円、スプレッド -1,280,000 円、
合計 **-4,605,000 円**。最大損失銘柄は `CORP_5Y`（-2,180,000 円）。

| API / model | JSON | Tool Calling | 計算・日本語説明 | HTTP回数 | HTTP合計秒 | 入力 / 出力token |
|---|---|---|---|---:|---:|---:|
| OpenAI / gpt-6-luna | PASS | PASS | PASS | 2 | 5.457 | 2087 / 385 |
| Anthropic / claude-haiku-5-5 | PASS | FAIL | FAIL | 1 | 2.829 | 2218 / 148 |

- OpenAI は自動選択でツールを呼び、実行した Python 関数の結果を返送すると、正しい損益と整合する日本語説明を返した。
- Anthropic はツールを使わず、合計損益 -6 円、空の銘柄・リスク配列、空の日本語説明を返した。HTTP は 200、`end_turn` であり、スキーマ適合のみ PASS。今回のツール往復は未検証で、機能の非対応と断定しない。
- 実 API は計3回、再試行なし。両社とも思考を無効にし、Web検索・ブラウザー操作・コンピューターユーズ・残高照会は行っていない。公式単価を確認していないため料金概算は算出せず、トークン使用量を保存した。
- ローカル15テスト、lint・format・秘密情報チェックは成功。レビュー指摘の修正後、保存済みレスポンスをオフラインで再評価して結論が変わらないことも確認した。日本語の自動判定は限定した句形・数値の照合で、未知の表現は手動確認が必要な FAIL とする。

実行コマンド（WSL、リポジトリのルートから。今回はキーを非表示の標準入力で渡した）:

```bash
uv run --no-sync python api-smoke/smoke.py --keys-stdin
```

通常の再実行は、両キーを安全に環境変数へ設定し `--keys-stdin` を省略する。
[コード・手順](../../api-smoke/README.md) と
[比較レポート](../../_data/api-smoke/20261101T064936389141Z/summary.md) を参照。
同じ出力フォルダーの `results.json` は実リクエスト・レスポンス・使用量とコード／プロンプトのハッシュ、
`validation.json` は修正後の検証結果を保持する。実行データは合計 60,395 bytes（`du -sh`: 68 KiB）、
Git 管理外のローカル保存。キーは記録せず、今回のコード・メモも未コミット。

## 残高を API へ直接問い合わせた結果

| 提供元 | GET エンドポイント | 実測結果 |
|---|---|---|
| OpenAI | `/v1/dashboard/billing/credit_grants` | 403。ブラウザー用セッションキーが必要で、通常の API キーでは不可と応答 |
| OpenAI | `/v1/organization/costs` | 403。`api.usage.read` が不足 |
| Anthropic | `/v1/organizations/me` | 200。返却項目は `id`、`type`、`name` のみで、残高なし |
| Anthropic | `/v1/organizations/analytics/cost` | 401。Admin API key または organization-scoped API key が必要と応答 |

利用額を返す Costs API とクレジット残高は別の情報。確認した公開仕様では残高照会 API を特定できておらず、管理用キーを用意しても残高取得まで可能とは確認できていない。

参考として、同日に管理画面で読んだ値は OpenAI $61.00（期限 2026-11-17）、Anthropic の付与分 $99.95 / $100.00（期限 2026-11-20、UTC 表示）と購入分 $3.83。これらは **API 取得値ではない**。現在値として再利用しない。

## 次に進める条件

- スモークテストの修正案は、計算をツールへ委ねる責務をプロンプトで明確化し、同じ修正版を両社で比較すること。まだ追加実行していない。自動選択の成功を、強制ツール呼出しで代用しない。
- 残高を返す公式 API と必要な認証方式を確認する。利用額の取得で代用して残高確認済みと報告しない。
- キー本体・ブラウザーの認証情報は保存していない。引き継ぎ先では安全な認証情報の設定を確認する。チャットに提示されたキーの再発行は推奨済みだが、実施は未確認。

## 参照

- [OpenAI Costs API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs)
- [Anthropic Usage and Cost Analytics API](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api)
- [総務省統計局 全国 CPI](https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html)
