# re_invest_os 外部サービス調査メモ

調査日: 2026-07-07

## 要約

今の `re_invest_os` の外部サービス構成は、プロトタイプとしては妥当。ただしローンチ時は、`vercel.app` / `fly.dev` をユーザーに見せる状態、Supabase Free の停止リスク、監視なし、Auth メールが独自ドメインでない状態が弱い。

ローンチ前の優先対応は次の通り。

1. Web を独自ドメイン化する。
2. 商用公開するなら Vercel Pro に上げる。
3. Supabase を Pro 化し、停止リスクとバックアップ面を改善する。
4. Supabase Auth の custom SMTP を設定する。
5. Anthropic の spend limit とアプリ側の日次 rate limit を確認する。
6. Sentry を Web/API に入れる。
7. 市場データを本番で重視するなら Fly volume + DuckDB lake 構成を本番へ反映する。

## 現在のプロトタイプ状態

| 領域 | 現状 |
| --- | --- |
| Web | Vercel: `https://re-invest-os-web.vercel.app` |
| API | Fly.io: `https://reio-api.fly.dev` |
| API 経路 | Vercel proxy `https://re-invest-os-web.vercel.app/api/backend/health` は復旧確認済み |
| DB/Auth | Supabase project ref: `tguzdmsllxqmkvmzcozv` |
| LLM | Fly secrets に `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `RATE_LIMIT_LLM_PER_DAY` あり |
| 不動産データ | Fly secrets に `REINFOLIB_API_KEY` あり |
| Fly Machine | region `nrt`, shared CPU 1, memory 1024 MB, auto-stop 有効 |
| Fly volume | 本番には volume なし |
| local `fly.toml` | `/lake` mount、`MARKET_DATA_SOURCE=local`、memory 2048 MB を想定 |

注意点: ローカルの `fly.toml` は 2GB memory + `/lake` volume 前提だが、現在の Fly 本番 Machine は 1GB + volume なし。市場データ lake 構成は、まだ本番反映されていない可能性が高い。

## ローンチ / 本番の理想状態

| 領域 | 理想状態 |
| --- | --- |
| Web | `app.<domain>` などの独自ドメイン。ブランド上、`vercel.app` は本番で見せない。 |
| Vercel | 商用利用なら Pro。Hobby は個人・非商用向け。 |
| API | ユーザーには直接見せず、Vercel の backend proxy 経由にする。必要な場合だけ `api.<domain>` を設定。 |
| Supabase | Pro 以上。RLS、SSL enforcement、MFA、複数 owner、backups を確認。 |
| Auth メール | Supabase 標準ではなく、Resend / AWS SES などの custom SMTP。送信元は独自ドメイン。 |
| Anthropic | 組織側 spend limit + アプリ側 rate limit。通常は Haiku、重要処理だけ Sonnet を検討。 |
| 市場データ | API fallback だけでなく cache / DuckDB lake を安定化。volume 作成、データ投入、deploy 設定を揃える。 |
| 監視 | Sentry for Web/API。PostHog は利用分析・ファネル・session replay 用。 |
| 決済 | 課金するなら Stripe Checkout。日本向けカード決済の基本料率は公式価格を確認。 |
| DNS | Cloudflare または Vercel Domains。Web は proxied/DNS 設定を整理し、検証用やメール用 record は DNS-only を使い分ける。 |

## 優先度

### P0: 本番前に必須

- 独自ドメインを設定し、`vercel.app` をユーザー-facing から外す。
- Supabase を Pro 化し、Free project pause による停止リスクを消す。
- Supabase Auth の custom SMTP を設定する。
- Anthropic spend limit と `RATE_LIMIT_LLM_PER_DAY` を確認する。
- Sentry を Web/API に入れる。

### P1: ローンチ品質

- Fly の実デプロイ状態を local `fly.toml` と揃える。
- 市場データを local DuckDB 前提にするなら、Fly volume `market_lake` を作成し、データ投入と 2GB memory deploy を行う。
- API custom domain は必須ではない。Vercel proxy 経由で隠せるなら後回しでよい。
- PostHog を入れて、オンボーディング、検索、レポート生成、課金導線のイベントを見る。

### P2: 成長後

- Supabase PITR、network restrictions、read replicas を検討する。
- Sentry / PostHog の paid plan を必要量に応じて上げる。
- Cloudflare WAF / rate limiting を必要に応じて足す。

## 公式情報メモ

- Vercel pricing: https://vercel.com/pricing
- Vercel fair use guidelines: https://vercel.com/docs/limits/fair-use-guidelines
- Vercel domains: https://vercel.com/docs/domains
- Supabase production checklist: https://supabase.com/docs/guides/deployment/going-into-prod
- Supabase backups: https://supabase.com/docs/guides/platform/backups
- Supabase custom SMTP: https://supabase.com/docs/guides/auth/auth-smtp
- Fly.io pricing: https://fly.io/docs/about/pricing/
- Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic rate limits: https://platform.claude.com/docs/en/api/rate-limits
- Stripe Japan pricing: https://stripe.com/jp/pricing
- Stripe Checkout: https://docs.stripe.com/payments/checkout
- Sentry pricing: https://sentry.io/pricing/
- PostHog pricing: https://posthog.com/pricing
- Cloudflare DNS proxy status: https://developers.cloudflare.com/dns/proxy-status/
- Resend pricing: https://resend.com/pricing
- AWS SES pricing: https://aws.amazon.com/ses/pricing/
