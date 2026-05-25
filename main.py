#!/usr/bin/env python3
"""
Daily News Digest
Sends two emails every morning:
  1. AI Frontier Digest  — top 5 AI news items
  2. Market Pulse        — macro/policy news + stock of the day
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from src.ai_news import fetch_ai_news
from src.market_news import fetch_market_news
from src.stock_screener import get_stock_of_the_day
from src.emailer import build_ai_email, build_market_email, send_email

RECIPIENT = os.environ.get("RECIPIENT_EMAIL", "lengyueshuang.luna@outlook.com")
GH_REPO = os.environ.get("GH_REPO", "your-username/daily-news-digest")


def main():
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    et = ZoneInfo("America/New_York")
    today = datetime.now(et)
    date_str = today.strftime("%A, %B %d, %Y")

    # ── Email 1: AI News ──────────────────────────────────────────────────────
    print("\n[1/2] AI Frontier Digest")
    print("Fetching AI RSS feeds...")
    ai_articles = fetch_ai_news(max_items=5)
    print(f"Found {len(ai_articles)} articles")

    ai_html = build_ai_email(date_str, ai_articles, GH_REPO)
    send_email(sender, password, RECIPIENT, f"🤖 AI Frontier Digest — {date_str}", ai_html)

    # ── Email 2: Market Pulse ─────────────────────────────────────────────────
    print("\n[2/2] Market Pulse")
    print("Fetching market RSS feeds...")
    market_articles = fetch_market_news(max_items=5)
    print(f"Found {len(market_articles)} articles")

    print("Running stock screener...")
    stock = get_stock_of_the_day()
    if stock:
        print(f"Stock pick: {stock['ticker']} (score={stock['score']:.2f})")
    else:
        print("No stock pick today")

    market_html = build_market_email(date_str, market_articles, stock, GH_REPO)
    send_email(sender, password, RECIPIENT, f"📈 Market Pulse — {date_str}", market_html)

    print("\nDone. Both emails sent.")


if __name__ == "__main__":
    # Allow a quick dry-run: python main.py --dry-run
    if "--dry-run" in sys.argv:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
        date_str = datetime.now(et).strftime("%A, %B %d, %Y")

        print("[dry-run] Fetching AI news...")
        ai_articles = fetch_ai_news(max_items=5)
        print(f"  {len(ai_articles)} articles")
        for a in ai_articles:
            print(f"  - [{a['source']}] {a['title'][:80]}")

        print("[dry-run] Fetching market news...")
        market_articles = fetch_market_news(max_items=5)
        print(f"  {len(market_articles)} articles")
        for a in market_articles:
            print(f"  - [{a['source']}] {a['title'][:80]}")

        print("[dry-run] Running stock screener...")
        stock = get_stock_of_the_day()
        if stock:
            print(f"  Pick: {stock['ticker']} — RSI {stock['rsi']:.1f}, "
                  f"vs MA200 {stock['vs_ma200']:+.1f}%, score {stock['score']:.2f}")
            print(f"  Signal: {stock['signal']}")
        else:
            print("  No pick today")

        # Write sample HTML to files for inspection
        ai_html = build_ai_email(date_str, ai_articles, GH_REPO)
        market_html = build_market_email(date_str, market_articles, stock, GH_REPO)
        with open("_preview_ai.html", "w") as f:
            f.write(ai_html)
        with open("_preview_market.html", "w") as f:
            f.write(market_html)
        print("\n[dry-run] HTML previews written to _preview_ai.html and _preview_market.html")
    else:
        main()
