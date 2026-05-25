import requests
import feedparser
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

AI_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "weight": 3},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "weight": 3},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "weight": 2},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "weight": 3},
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss", "weight": 2},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "weight": 2},
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/", "weight": 1},
]

PRIORITY_KEYWORDS = [
    "breakthrough", "launch", "launches", "announce", "announces", "release", "releases",
    "new model", "gpt-5", "gpt 5", "claude 4", "gemini 3", "llama 4", "mistral",
    "openai", "anthropic", "google deepmind", "meta ai", "apple intelligence",
    "agi", "superintelligence", "reasoning", "multimodal", "agent",
]

BOOST_KEYWORDS = [
    "gpt", "llm", "language model", "ai model", "foundation model", "generative ai",
    "machine learning", "deep learning", "neural network", "chatgpt", "claude",
    "nvidia", "chip", "training", "inference", "benchmark", "paper", "research",
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
    # Collapse whitespace
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


def _score(article):
    title = article["title"].lower()
    score = article["source_weight"]
    for kw in PRIORITY_KEYWORDS:
        if kw in title:
            score += 3
    for kw in BOOST_KEYWORDS:
        if kw in title:
            score += 1
    # Recency bonus: articles within last 24h get +5
    if article["published"]:
        age_h = (datetime.now(timezone.utc) - article["published"]).total_seconds() / 3600
        if age_h < 6:
            score += 5
        elif age_h < 24:
            score += 3
        elif age_h < 48:
            score += 1
    return score


def fetch_ai_news(max_items=5):
    raw = []
    for feed_info in AI_FEEDS:
        print(f"  Fetching {feed_info['name']}...")
        feed = _fetch_feed(feed_info["url"])
        if not feed:
            continue
        for entry in feed.entries[:8]:
            try:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                summary_raw = getattr(entry, "summary", "") or ""
                summary = _clean_html(summary_raw)
                if len(summary) > 320:
                    summary = summary[:320].rsplit(" ", 1)[0] + "..."

                raw.append({
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "source": feed_info["name"],
                    "source_weight": feed_info["weight"],
                    "published": published,
                    "time_ago": _time_ago(published),
                })
            except Exception:
                continue

    # Deduplicate by first-6-words title key
    seen = {}
    for a in raw:
        key = " ".join(a["title"].lower().split()[:6])
        if key not in seen or _score(a) > _score(seen[key]):
            seen[key] = a

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    articles = [a for a in seen.values() if a["published"] and a["published"] >= cutoff]
    articles.sort(key=_score, reverse=True)
    return articles[:max_items]
