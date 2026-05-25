import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ── HTML building blocks ──────────────────────────────────────────────────────

_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);max-width:600px;width:100%;">
        {content}
        <tr><td style="background:#f8fafc;padding:16px;text-align:center;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;">
          Automated digest · Sent daily at 9 AM SGT · <a href="https://github.com/{gh_repo}" style="color:#94a3b8;">Source on GitHub</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _ai_header(date_str):
    return f"""<tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:28px 32px;text-align:center;">
  <div style="font-size:28px;margin-bottom:6px;">🤖</div>
  <h1 style="color:#f8fafc;font-size:22px;font-weight:700;margin:0;letter-spacing:-.3px;">AI Frontier Digest</h1>
  <p style="color:#94a3b8;font-size:13px;margin:6px 0 0;">{date_str}</p>
</td></tr>"""


def _market_header(date_str):
    return f"""<tr><td style="background:linear-gradient(135deg,#064e3b 0%,#065f46 100%);padding:28px 32px;text-align:center;">
  <div style="font-size:28px;margin-bottom:6px;">📈</div>
  <h1 style="color:#f0fdf4;font-size:22px;font-weight:700;margin:0;letter-spacing:-.3px;">Market Pulse</h1>
  <p style="color:#6ee7b7;font-size:13px;margin:6px 0 0;">{date_str}</p>
</td></tr>"""


def _ai_article(article, index, total):
    is_last = index == total - 1
    border = "" if is_last else "border-bottom:1px solid #e2e8f0;"
    tag_color = {"TechCrunch AI": "#f97316", "VentureBeat AI": "#8b5cf6",
                 "The Verge AI": "#ef4444", "MIT Tech Review": "#3b82f6",
                 "Wired AI": "#1d4ed8", "AI News": "#64748b"}.get(article["source"], "#64748b")
    time_str = f" · {article['time_ago']}" if article.get("time_ago") else ""
    summary = article.get("summary") or ""
    return f"""<tr><td style="padding:20px 32px;{border}">
  <div style="margin-bottom:6px;">
    <span style="background:{tag_color};color:#fff;font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:.5px;">{article['source']}</span>
    <span style="color:#94a3b8;font-size:12px;margin-left:6px;">{time_str.strip(' ·')}</span>
  </div>
  <h2 style="font-size:15px;font-weight:600;color:#0f172a;margin:0 0 8px;line-height:1.4;">
    <a href="{article['url']}" style="color:#0f172a;text-decoration:none;">{article['title']}</a>
  </h2>
  {f'<p style="font-size:13px;color:#475569;line-height:1.6;margin:0 0 10px;">{summary}</p>' if summary else ''}
  <a href="{article['url']}" style="color:#3b82f6;font-size:12px;font-weight:500;text-decoration:none;">Read article →</a>
</td></tr>"""


def _market_article(article, index, total):
    is_last = index == total - 1
    border = "" if is_last else "border-bottom:1px solid #dcfce7;"
    time_str = article.get("time_ago") or ""
    summary = article.get("summary") or ""
    return f"""<tr><td style="padding:14px 24px;{border}">
  <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;">
    {article['source']}{(' · ' + time_str) if time_str else ''}
  </div>
  <h3 style="font-size:14px;font-weight:600;color:#1e293b;margin:0 0 6px;line-height:1.4;">
    <a href="{article['url']}" style="color:#1e293b;text-decoration:none;">{article['title']}</a>
  </h3>
  {f'<p style="font-size:12px;color:#4b5563;line-height:1.5;margin:0 0 6px;">{summary}</p>' if summary else ''}
  <a href="{article['url']}" style="color:#059669;font-size:12px;font-weight:500;text-decoration:none;">Read more →</a>
</td></tr>"""


def _stock_card(stock):
    if not stock:
        return """<tr><td style="padding:16px 24px;color:#6b7280;font-size:13px;font-style:italic;">
          Stock screener unavailable — market may be closed or data source unreachable.
        </td></tr>"""

    ticker = stock["ticker"]
    price = stock["price"]
    day_chg = stock.get("day_change_pct") or 0.0
    chg_color = "#16a34a" if day_chg >= 0 else "#dc2626"
    chg_sign = "+" if day_chg >= 0 else ""
    rsi = stock["rsi"]
    vs_ma50 = stock["vs_ma50"]
    vs_ma200 = stock["vs_ma200"]
    rel_vol = stock["rel_vol"]
    signal = stock.get("signal") or ""
    name = stock.get("name") or ticker
    sector = stock.get("sector") or ""
    industry = stock.get("industry") or ""
    yahoo_url = stock.get("yahoo_url") or f"https://finance.yahoo.com/quote/{ticker}"

    # RSI color
    rsi_color = "#dc2626" if rsi < 35 else ("#f97316" if rsi < 45 else "#64748b")
    vs_ma50_color = "#16a34a" if vs_ma50 >= 0 else "#f97316"
    vs_ma200_color = "#16a34a" if vs_ma200 >= 0 else "#dc2626"

    sub = f"{sector}" + (f" · {industry}" if industry else "")

    return f"""<tr><td style="padding:20px 24px;">
  <div style="background:#eff6ff;border-radius:8px;padding:20px;border:1px solid #bfdbfe;">
    <div style="display:flex;align-items:baseline;margin-bottom:4px;">
      <span style="font-size:26px;font-weight:800;color:#1e293b;letter-spacing:-.5px;">{ticker}</span>
      <span style="font-size:14px;font-weight:600;color:{chg_color};margin-left:12px;">${price:.2f} {chg_sign}{day_chg:.1f}%</span>
    </div>
    <div style="font-size:13px;color:#64748b;margin-bottom:16px;">{name}{(' · ' + sub) if sub else ''}</div>

    <table cellpadding="0" cellspacing="0" width="100%" style="font-size:13px;margin-bottom:14px;">
      <tr>
        <td style="color:#6b7280;padding:4px 0;width:50%;">RSI (14-day)</td>
        <td style="font-weight:600;color:{rsi_color};padding:4px 0;">{rsi:.1f} {'(oversold)' if rsi < 40 else '(neutral)'}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">vs 50-day MA</td>
        <td style="font-weight:600;color:{vs_ma50_color};padding:4px 0;">{('+' if vs_ma50 >= 0 else '')}{vs_ma50:.1f}%</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">vs 200-day MA</td>
        <td style="font-weight:600;color:{vs_ma200_color};padding:4px 0;">{('+' if vs_ma200 >= 0 else '')}{vs_ma200:.1f}%</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Relative Volume</td>
        <td style="font-weight:600;color:#1e293b;padding:4px 0;">{rel_vol:.1f}x avg</td>
      </tr>
    </table>

    <div style="background:#dbeafe;border-radius:6px;padding:12px;margin-bottom:14px;font-size:13px;color:#1e40af;line-height:1.5;">
      <strong>Signal:</strong> {signal}
    </div>

    <div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">
      ⚠️ For informational purposes only. Not financial advice. Always do your own research.
    </div>

    <a href="{yahoo_url}" style="display:inline-block;background:#2563eb;color:#ffffff;font-size:13px;font-weight:600;padding:8px 18px;border-radius:6px;text-decoration:none;">
      View on Yahoo Finance →
    </a>
  </div>
</td></tr>"""


# ── Email builders ────────────────────────────────────────────────────────────

def build_ai_email(date_str, articles, gh_repo="your-username/daily-news-digest"):
    rows = _ai_header(date_str)

    if not articles:
        rows += """<tr><td style="padding:24px 32px;color:#64748b;font-style:italic;">
          No AI news articles could be retrieved today. RSS sources may be temporarily unavailable.
        </td></tr>"""
    else:
        for i, article in enumerate(articles):
            rows += _ai_article(article, i, len(articles))

    html = _BASE.format(subject=f"AI Frontier Digest — {date_str}", content=rows, gh_repo=gh_repo)
    return html


def build_market_email(date_str, articles, stock, gh_repo="your-username/daily-news-digest"):
    rows = _market_header(date_str)

    # Macro section header
    rows += """<tr><td style="padding:16px 24px 0;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#059669;">
        📊 Macro &amp; Policy
      </div>
      <div style="height:1px;background:#d1fae5;margin-top:6px;"></div>
    </td></tr>"""

    if not articles:
        rows += """<tr><td style="padding:16px 24px;color:#6b7280;font-style:italic;">
          No market news articles could be retrieved today.
        </td></tr>"""
    else:
        for i, article in enumerate(articles):
            rows += _market_article(article, i, len(articles))

    # Stock of the day section header
    rows += """<tr><td style="padding:16px 24px 0;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#1d4ed8;margin-top:8px;">
        ⭐ Stock of the Day
      </div>
      <div style="height:1px;background:#bfdbfe;margin-top:6px;"></div>
    </td></tr>"""

    rows += _stock_card(stock)

    html = _BASE.format(subject=f"Market Pulse — {date_str}", content=rows, gh_repo=gh_repo)
    return html


# ── Sender ────────────────────────────────────────────────────────────────────

def send_email(sender_addr, app_password, recipient, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_addr
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(sender_addr, app_password)
        server.sendmail(sender_addr, recipient, msg.as_string())
    print(f"  Sent: {subject}")
