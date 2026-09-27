# Monetization And Deployment Research

Date: 2026-04-30

## Current Product Assumptions

- Target user: individual real-estate investors.
- Beta scope: tens of invited users.
- Initial access model: unlisted URL, no user accounts.
- Initial monetization candidates: monthly subscription or advertising.
- Initial stack preference: keep Streamlit for beta, improve later.
- LLM usage today: `property_scraper.py` calls local Ollama at `127.0.0.1:11434` with `gemma3:12b`.

## Deployment Options

### Option A: CPU VPS For Streamlit, External LLM API

Best first beta option.

Use a normal CPU VPS or managed app platform for Streamlit and DuckDB, and use a hosted LLM API for extraction where regex cannot fill fields. This avoids GPU server cost and operational complexity during beta.

Recommended shape:
- 2-4 vCPU
- 4-8 GB RAM
- 50-100 GB disk
- persistent volume or server disk for DuckDB/data
- environment variables or provider secrets for API keys

Pros:
- fastest to launch
- lowest monthly cost
- enough for tens of beta users
- avoids running Ollama publicly

Cons:
- per-request LLM API cost
- data sent to LLM provider unless redacted or minimized

### Option B: CPU VPS For Streamlit, Separate GPU Worker For Ollama

Good if local/open-source LLM inference remains important.

Run Streamlit on a small VPS and send extraction jobs to a GPU worker. The GPU worker can be always-on or serverless. For beta traffic, serverless GPU is usually more cost-efficient than a 24/7 GPU VM.

Recommended shape:
- Streamlit app: 2-4 vCPU, 4-8 GB RAM
- Ollama worker for `gemma3:12b`: 16 GB VRAM minimum practical target, 24 GB VRAM preferred
- queue or simple internal HTTP endpoint for extraction requests

Pros:
- keeps LLM logic private and controllable
- can use current Ollama prompt/code with less rewriting

Cons:
- higher complexity
- cold starts if serverless
- GPU cost can dominate revenue early

### Option C: Single GPU Server Running Both App And Ollama

Technically simple but usually not cost-effective for a small beta.

Recommended only if you want the least architecture work and accept GPU cost. A 24 GB VRAM instance is comfortable for `gemma3:12b`; a 16 GB VRAM instance may work but leaves less room for context/KV cache.

Pros:
- simplest mental model
- app and Ollama communicate over localhost

Cons:
- expensive if always on
- scaling app and LLM independently is impossible
- public app uptime depends on GPU server stability

## Hosting Notes

- Streamlit Community Cloud is fast and free for prototypes, supports secrets, and deploys from GitHub, but it is not a good fit for private DuckDB data, URL-limited beta control, or local Ollama.
- Render/Railway/Fly/DigitalOcean can host the Streamlit app as a normal web service or VM. For this app, persistent storage matters because DuckDB and local data must survive deploys.
- DigitalOcean CPU Droplets are predictable for a first VPS. Their listed Basic plans range from small low-cost VMs up to 8 GB RAM and beyond.
- GPU hosting should be treated separately. RunPod and DigitalOcean GPU Droplets are candidates, but always-on GPU cost is much higher than CPU hosting.

## Ollama Sizing

Current code references:
- `land_price_api_app/property_scraper.py`
- `_OLLAMA_BASE_URL = "http://127.0.0.1:11434"`
- `_OLLAMA_MODEL = "gemma3:12b"`

Ollama's model page lists `gemma3:12b` at about 8.1 GB and `gemma3:27b` at about 17 GB. Model file size is not the full runtime memory requirement because context/KV cache also consumes memory.

Practical sizing:
- `gemma3:4b`: usable on cheaper CPU/GPU setups, lower extraction quality risk.
- `gemma3:12b`: target 16 GB VRAM minimum, 24 GB VRAM preferred for smoother concurrent use and longer prompts.
- CPU-only `gemma3:12b`: possible but likely slow for user-facing requests.

Beta recommendation:
- Do not make Ollama a hard dependency for the public beta.
- Keep regex extraction as primary.
- Add a provider abstraction: `LLM_PROVIDER=none|ollama|anthropic|openai`.
- For public beta, start with `none` or hosted API fallback.
- Reintroduce Ollama via a separate GPU worker only if extraction quality clearly needs it.

## Advertising Monetization

### Google AdSense

AdSense is the most direct path for display ads, but it requires a public site with enough original content and compliant traffic. It is less suitable for a private URL-only beta with tens of users.

Implementation paths:
- Auto ads: add one AdSense code snippet and let Google choose placements.
- Manual display units: place ad blocks in fixed locations.
- Page exclusions: avoid showing ads on sensitive or conversion-critical pages.

Important constraints:
- Do not click your own ads.
- Do not ask users to click ads.
- Do not place ads where they can be confused with navigation or app controls.
- A pure logged-in tool with thin public content may be harder to approve than a public content site.

### Sponsorships And Affiliate Revenue

For this product, direct sponsorship or affiliate links may be more realistic than display ads in the first phase.

Candidates:
- mortgage/loan comparison affiliates
- property management service referrals
- insurance / landlord insurance referrals
- real-estate education content sponsorship
- paid placement in educational articles, not inside analysis results

Rules of thumb:
- Keep ads separate from analytical recommendations.
- Clearly label sponsored links.
- Do not let sponsors influence valuation outputs.

### Hybrid Funnel

Recommended monetization path:
1. Beta: free, invite-only, collect usage and willingness-to-pay.
2. Public content pages: publish SEO-oriented area guides and investment explainers.
3. Ads: place AdSense on public content pages, not the core analysis workflow first.
4. Subscription: charge for saved analyses, report export, deeper area data, and batch comparison.

## Recommended 1-Month Path

Week 1:
- Add beta disclaimer and terms notice.
- Add `LLM_PROVIDER` switch and make Ollama optional.
- Add minimal access gate only if URL leakage becomes a concern.

Week 2:
- Package deploy target with `requirements.txt`, startup command, and production environment variables.
- Choose CPU hosting first.
- Keep DuckDB and `_data` on persistent storage.

Week 3:
- Add feedback form and lightweight usage logging.
- Add public landing/content pages if advertising will be tested later.
- Keep ad code out of core analysis UI during beta.

Week 4:
- Invite beta users.
- Measure: visits, URL analyses, failed extractions, report exports, repeat usage, and willingness-to-pay.
- Decide whether to prioritize subscription, public content + ads, or hybrid.

## Sources

- Streamlit Community Cloud deployment and secrets docs:
  - https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
  - https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
  - https://docs.streamlit.io/deploy/streamlit-community-cloud/status
- Ollama Gemma 3 model page:
  - https://www.ollama.com/library/gemma3
  - https://www.ollama.com/library/gemma3%3A12b
- Railway pricing:
  - https://docs.railway.com/pricing
- Fly.io pricing:
  - https://fly.io/docs/about/pricing/
- RunPod serverless pricing:
  - https://docs.runpod.io/serverless/pricing
- DigitalOcean Droplet and GPU pricing:
  - https://www.digitalocean.com/pricing/droplets
  - https://www.digitalocean.com/pricing/gpu-droplets
  - https://docs.digitalocean.com/products/droplets/details/pricing/
- Google AdSense:
  - https://support.google.com/adsense/answer/6242051
  - https://support.google.com/adsense/answer/9261805
  - https://support.google.com/adsense/answer/48182
