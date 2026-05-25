# Daily News Digest

Sends two emails every morning at 9 AM ET via GitHub Actions:

| Email | Content |
|-------|---------|
| 🤖 **AI Frontier Digest** | Top 5 AI/ML news items with summaries and links |
| 📈 **Market Pulse** | US macro & policy news + Stock of the Day with technical analysis |

## Setup (5 minutes)

### 1. Fork or push this repo to GitHub

Create a new repo on GitHub and push this folder:

```bash
cd /path/to/this/folder
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/daily-news-digest.git
git push -u origin main
```

### 2. Create a Gmail App Password

1. Go to your Google Account → **Security** → **2-Step Verification** (must be enabled)
2. Scroll to **App passwords** → create one named "Daily News Bot"
3. Copy the 16-character password (shown once)

### 3. Add GitHub Secrets

In your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret name | Value |
|-------------|-------|
| `GMAIL_ADDRESS` | Your Gmail address (e.g. `yourname@gmail.com`) |
| `GMAIL_APP_PASSWORD` | The 16-char App Password from step 2 |
| `RECIPIENT_EMAIL` | `lengyueshuang.luna@outlook.com` |

### 4. Enable GitHub Actions

Go to **Actions** tab in your repo → click **"I understand my workflows, go ahead and enable them"** if prompted.

The workflow runs daily at 13:00 UTC (9 AM EDT). Use the **"Run workflow"** button to test it immediately.

---

## Test locally

```bash
pip install -r requirements.txt

# Dry run: fetches data and writes HTML previews (no email sent)
python main.py --dry-run

# Open previews in browser
open _preview_ai.html
open _preview_market.html

# Send real emails (requires env vars)
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python main.py
```

---

## How it works

```
main.py
├── src/ai_news.py        RSS feeds → score by recency + keywords → top 5
├── src/market_news.py    RSS feeds → filter by policy keywords → top 5
├── src/stock_screener.py yfinance batch download → RSI / MA / volume → pick 1
└── src/emailer.py        HTML email builder + Gmail SMTP sender
```

**AI news sources:** TechCrunch, VentureBeat, The Verge, MIT Tech Review, Wired, AI News

**Market news sources:** Reuters Business, CNBC Markets, CNBC Economy, Federal Reserve, Yahoo Finance

**Stock screener logic:** Scans ~100 major S&P 500 stocks for oversold RSI (30–48) + price above 200-day MA (long-term uptrend) + recent pullback + elevated volume → highest-scoring stock is the pick.

> ⚠️ Stock picks are for informational/educational purposes only. Not financial advice.

---

## Timezone note

GitHub Actions cron uses UTC. The workflow is set to `0 13 * * *` (1 PM UTC):
- **EDT (Mar–Nov):** arrives at 9 AM ET ✓
- **EST (Nov–Mar):** arrives at 8 AM ET (1 hour early)

To always get exactly 9 AM ET, change the cron to `0 14 * * *` in winter.
