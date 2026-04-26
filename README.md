# LinkedIn AI Post Studio

A local AI-powered tool for researching industry trends, drafting LinkedIn posts, and publishing them on schedule — all from a single browser tab.

Built on [Abacus.AI RouteLLM](https://abacus.ai/app/route-llm-apis) for text generation and the official LinkedIn API for publishing.

---

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Trend Fetching** | Aggregates fresh news from DuckDuckGo + 50+ RSS feeds across 7 domains |
| ✍️ **AI Drafting** | LLM writes LinkedIn posts in your chosen tone and length |
| #️⃣ **Hashtags** | Auto-generated, click to append |
| 🖼️ **Image Upload** | Drag & drop images → attached to LinkedIn post |
| 📅 **Scheduler** | Set a date/time per post; auto-publishes in the background |
| 📆 **Calendar** | Monthly view of scheduled, published, and failed posts |
| 🔎 **Custom Topics** | Search any topic → pick sources → draft a post |
| 📊 **Analytics** | Post impressions, clicks, likes, engagement rate (requires `r_member_social` scope) |
| 🧠 **Seen Cache** | Already-shown articles suppressed for 30 days |

---

## Domain Coverage

| Domain | Pills | Sources |
|--------|-------|---------|
| AI & Technology | 8 | TechCrunch, Verge, VentureBeat, MIT Tech Review, ArXiv CS.AI/LG |
| Chemistry & Computational Science | 5 | C&EN, RSC, Nature Chemistry, ChemRxiv, J. Chem. Inf. |
| Pharma & Life Sciences | 4 | FiercePharma, BioPharma Dive, STAT News, FDA, Nature Drug Discovery |
| Patents, IP & Legal | 3 | IPWatchdog, Patent Docs, Managing IP, Law360 IP |
| Cybersecurity | 5 | Krebs on Security, The Hacker News, BleepingComputer, Dark Reading, SecurityWeek, SANS ISC |
| Cloud — AWS · Azure · GCP | 6 | AWS News, Azure Updates, GCP Blog, The New Stack, Cloud Security Alliance |
| GRC | 4 | ISACA, IAPP, Risk.net, Compliance Week, NIST |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd linkedin_studio
pip install -r requirements.txt
```

### 2. Set up your `.env`

Copy `.env.example` to `.env` and fill in:

```env
# Required
ABACUS_API_KEY=your_abacus_key_here
LINKEDIN_TOKEN=AQV...
LINKEDIN_URN=urn:li:person:XXXXXXXX

# Optional — change the LLM model
ABACUS_BASE_URL=https://routellm.abacus.ai/v1
ABACUS_MODEL=route-llm
```

### 3. Run

```bash
python app.py
```

Open **http://localhost:5001** in your browser.

---

## Getting Your Keys

### Abacus.AI API Key
1. Go to [abacus.ai/app/route-llm-apis](https://abacus.ai/app/route-llm-apis)
2. Sign up for a ChatLLM subscription ($10/month — includes all LLMs)
3. Copy your API key

### LinkedIn Token & URN
1. Go to [linkedin.com/developers](https://www.linkedin.com/developers/)
2. Create an app (requires a company/brand page)
3. Add the **Share on LinkedIn** product
4. Go to **OAuth tools** → generate a token with these scopes:
   - `openid` `profile` `w_member_social` `email`
5. Copy the token and your member URN (`urn:li:person:XXXXXXXX`)

> **Token expiry:** LinkedIn tokens last 60 days. Regenerate at [developer.linkedin.com](https://www.linkedin.com/developers/tools/oauth/token-generator) when it expires.

---

## Project Structure

```
linkedin_studio/
├── app.py              # Flask backend — all routes and logic
├── templates/
│   └── index.html      # Single-page frontend (HTML + CSS + JS)
├── requirements.txt    # Python dependencies
├── .env                # Your secrets (never commit this)
├── .env.example        # Template for .env
├── schedule.json       # Auto-created: post schedule and history
└── seen_articles.json  # Auto-created: seen-articles cache
```

---

## Workflow

```
1. Select domain categories (AI, Pharma, Cybersecurity, Cloud, GRC…)
2. Set tone, post length, and number of topics
3. Click "Fetch trends" → review topic cards
4. Select topics to draft
5. Edit posts inline, attach images, set hashtags
6. Approve → publish immediately, or schedule for later
7. Calendar tab shows everything in one view
```

---

## .env Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `ABACUS_API_KEY` | ✅ | — | From abacus.ai |
| `ABACUS_BASE_URL` | No | `https://routellm.abacus.ai/v1` | Enterprise users change this |
| `ABACUS_MODEL` | No | `route-llm` | Or e.g. `claude-sonnet-4-6` |
| `LINKEDIN_TOKEN` | ✅ | — | Regenerate every 60 days |
| `LINKEDIN_URN` | ✅ | — | `urn:li:person:XXXXXXXX` |

---

## LinkedIn Scopes & Analytics

The app uses these OAuth scopes:

| Scope | Used for |
|-------|---------|
| `w_member_social` | Publishing posts, uploading images |
| `openid` + `profile` | Getting your member URN |

The **Analytics tab** requires `r_member_social`, which LinkedIn only grants to Marketing Developer Platform approved apps. For standard developer accounts it will return a 403 — this is a LinkedIn API restriction, not a bug.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ABACUS_API_KEY not set` | Add key to `.env` and restart |
| LinkedIn 401 | Token expired — regenerate at developer.linkedin.com |
| LinkedIn 422 Duplicate | Same post already published — safe to ignore |
| LinkedIn 403 on analytics | Need `r_member_social` scope — not available on standard accounts |
| DDG returns no results | DuckDuckGo rate limited — wait a minute and retry |
| RSS feed empty | Feed URL may have changed — check and update in `RSS_FEEDS` dict |
| Port 5001 in use | Change port in `app.py` last line: `app.run(port=5002, ...)` |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | Web server and routing |
| `requests` | HTTP calls to LLM API and LinkedIn |
| `python-dotenv` | Load `.env` file |
| `APScheduler` | Background auto-publishing |
| `ddgs` | DuckDuckGo web search |
| `pytrends` | Google Trends (optional) |

Install all: `pip install -r requirements.txt`

---

## License

MIT — for personal use. LinkedIn API usage is subject to [LinkedIn's API Terms of Service](https://legal.linkedin.com/api-terms-of-use).
