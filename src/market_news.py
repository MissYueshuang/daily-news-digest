import requests
import feedparser
from datetime import datetime, timezone
from bs4 import BeautifulSoup

MARKET_FEEDS = [
    {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews", "weight": 3},
    {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "weight": 3},
    {"name": "CNBC Economy", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "weight": 3},
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "weight": 4},
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex", "weight": 2},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "weight": 2},
]

POLICY_KEYWORDS = [
    "federal reserve", "fed ", " fed ", "interest rate", "rate hike", "rate cut", "fomc",
    "powell", "inflation", "cpi", "pce", "core inflation", "monetary policy",
    "gdp", "unemployment", "jobs report", "nonfarm payroll", "retail sales",
    "consumer spending", "housing starts", "manufacturing",
    "tariff", "trade war", "trade deal", "trade policy", "sanctions",
    "debt ceiling", "treasury", "budget deficit", "fiscal policy", "stimulus",
    "s&p 500", "dow jones", "nasdaq", "market rally", "stock market",
    "recession", "economic growth", "earnings season",
    "china", "trade war", "geopolitical", "opec", "oil price", "energy",
    "sec", "regulation", "antitrust", "bank", "banking",
]


def _fetch_feed(url, timeout=12):
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception as e:
        print(f"  Warning: could not fetch {url}: {e}")
        return None


def _clean_html(raw):
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)
    return " ".join(text.split())


def _time_ago(dt):
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    diff = now - dt
    hours = int(diff.total_seconds() / 3600)
    if hours < 1:
        return "just now"
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _relevance_score(article):
    text = (article["title"] + " " + article["summary"]).lower()
    score = article["source_weight"]
    for kw in POLICY_KEYWORDS:
        if kw in text:
            score += 2
    if article["published"]:
        age_h = (datetime.now(timezone.utc) - article["published"]).total_seconds() / 3600
        if age_h < 6:
            score += 4
        elif age_h < 24:
            score += 2
    return score


def fetch_market_news(max_items=5):
    raw = []
    for feed_info in MARKET_FEEDS:
        print(f"  Fetching {feed_info['name']}...")
        feed = _fetch_feed(feed_info["url"])
        if not feed:
            continue
        for entry in feed.entries[:10]:
            try:
                title = entry.get("title", "").strip()
                # Quick keyword filter at title level
                title_lower = title.lower()
                if not any(kw in title_lower for kw in POLICY_KEYWORDS):
                    continue

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                summary_raw = getattr(entry, "summary", "") or ""
                summary = _clean_html(summary_raw)
                if len(summary) > 320:
                    summary = summary[:320].rsplit(" ", 1)[0] + "..."

                raw.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "source": feed_info["name"],
                    "source_weight": feed_info["weight"],
                    "published": published,
                    "time_ago": _time_ago(published),
                })
            except Exception:
                continue

    # Deduplicate
    seen = {}
    for a in raw:
        key = " ".join(a["title"].lower().split()[:6])
        if key not in seen or _relevance_score(a) > _relevance_score(seen[key]):
            seen[key] = a

    articles = list(seen.values())
    articles.sort(key=_relevance_score, reverse=True)
    return articles[:max_items]
