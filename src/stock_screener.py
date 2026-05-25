import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Top 100 S&P 500 stocks by market cap — liquid, well-known names
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "BRK-B",
    "UNH", "LLY", "JPM", "V", "XOM", "MA", "AVGO", "PG", "JNJ", "HD", "COST",
    "MRK", "ABBV", "CVX", "KO", "WMT", "BAC", "CRM", "NFLX", "AMD",
    "TMO", "DIS", "CSCO", "ADBE", "ACN", "ABT", "TXN", "LIN", "MCD", "DHR",
    "NKE", "PM", "VZ", "NEE", "RTX", "HON", "LOW", "QCOM", "IBM",
    "INTC", "GE", "CAT", "UPS", "BA", "GS", "MS", "AMGN", "SBUX", "INTU",
    "PLD", "DE", "BLK", "SPGI", "NOW", "AXP", "SYK", "GILD", "MDLZ", "ADP",
    "MMC", "CB", "REGN", "TJX", "C", "WM", "ZTS", "ISRG", "ICE", "PNC",
    "USB", "BSX", "ELV", "AON", "VRTX", "MO", "HCA", "CI", "APD", "SO",
    "DUK", "CL", "SHW", "ETN", "NSC", "PGR", "ITW", "MCO", "EMR", "ECL",
    "PANW", "SNOW", "UBER", "ABNB", "COIN", "PLTR",
]

SECTOR_MAP = {
    "Technology": "Tech", "Health Care": "Healthcare", "Financials": "Finance",
    "Consumer Discretionary": "Consumer", "Communication Services": "Comm",
    "Industrials": "Industrial", "Consumer Staples": "Staples",
    "Energy": "Energy", "Utilities": "Utilities", "Real Estate": "Real Estate",
    "Materials": "Materials",
}


def _calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _buy_score(rsi, vs_ma50, vs_ma200, rel_vol, ret_5d):
    score = 0.0
    # RSI 30-48: sweet spot for oversold/recovering
    if 28 <= rsi <= 48:
        score += (50 - rsi) / 20 * 4  # max ~4.4 at RSI=28
    # Must be in long-term uptrend (above 200MA)
    if vs_ma200 > 0:
        score += 2
    # Below 50MA = pullback (opportunity), but not in freefall
    if -15 < vs_ma50 < 0:
        score += abs(vs_ma50) / 5  # bigger pullback = more points, capped
    # High relative volume = institutional activity
    if rel_vol > 1.5:
        score += min(rel_vol - 1, 2)  # cap at +2
    # Recent bounce (today +0.5%—+4%)
    if 0.5 <= ret_5d <= 8:
        score += 1
    return score


def _signal_text(rsi, vs_ma50, vs_ma200, rel_vol, ret_5d):
    parts = []
    if rsi <= 35:
        parts.append(f"RSI {rsi:.0f} — deeply oversold")
    elif rsi <= 45:
        parts.append(f"RSI {rsi:.0f} — oversold territory")
    else:
        parts.append(f"RSI {rsi:.0f} — cooling off")

    if vs_ma200 > 0:
        parts.append(f"long-term uptrend intact (+{vs_ma200:.1f}% above 200-day MA)")
    else:
        parts.append(f"{abs(vs_ma200):.1f}% below 200-day MA (caution)")

    if vs_ma50 < 0:
        parts.append(f"pulled back {abs(vs_ma50):.1f}% from 50-day MA — potential entry")

    if rel_vol > 1.5:
        parts.append(f"{rel_vol:.1f}x average volume suggests institutional interest")

    return ". ".join(parts) + "."


def get_stock_of_the_day():
    print("  Downloading batch data for watchlist...")
    try:
        data = yf.download(
            " ".join(WATCHLIST),
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"  yfinance download failed: {e}")
        return None

    if data.empty:
        print("  No data returned from yfinance")
        return None

    close_df = data["Close"]
    volume_df = data["Volume"]

    candidates = []
    for ticker in WATCHLIST:
        if ticker not in close_df.columns:
            continue
        close = close_df[ticker].dropna()
        volume = volume_df[ticker].dropna()

        if len(close) < 210:
            continue

        # Skip if most recent data is stale (older than 3 days — handles weekends/holidays)
        latest_date = close.index[-1]
        if hasattr(latest_date, 'tzinfo') and latest_date.tzinfo is None:
            latest_date = latest_date.tz_localize('UTC')
        if (datetime.now(timezone.utc) - latest_date).days > 3:
            continue

        try:
            rsi_series = _calc_rsi(close)
            rsi = float(rsi_series.iloc[-1])
            if np.isnan(rsi):
                continue

            ma50 = float(close.rolling(50).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1])
            price = float(close.iloc[-1])
            prev_price = float(close.iloc[-6]) if len(close) >= 6 else price

            vs_ma50 = (price - ma50) / ma50 * 100
            vs_ma200 = (price - ma200) / ma200 * 100
            ret_5d = (price - prev_price) / prev_price * 100

            avg_vol = float(volume.rolling(20).mean().iloc[-1])
            rel_vol = float(volume.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

            # Must be in long-term uptrend and not in extreme freefall
            if vs_ma200 < -20:
                continue
            # Filter out overbought
            if rsi > 65:
                continue

            score = _buy_score(rsi, vs_ma50, vs_ma200, rel_vol, ret_5d)

            candidates.append({
                "ticker": ticker,
                "price": price,
                "rsi": rsi,
                "vs_ma50": vs_ma50,
                "vs_ma200": vs_ma200,
                "rel_vol": rel_vol,
                "ret_5d": ret_5d,
                "score": score,
            })
        except Exception:
            continue

    if not candidates:
        print("  No candidates found after screening")
        return None

    candidates.sort(key=lambda x: x["score"], reverse=True)
    pick = candidates[0]
    ticker = pick["ticker"]

    # Fetch company info
    try:
        info = yf.Ticker(ticker).info
        pick["name"] = info.get("longName") or info.get("shortName") or ticker
        raw_sector = info.get("sector") or "N/A"
        pick["sector"] = SECTOR_MAP.get(raw_sector, raw_sector)
        pick["industry"] = info.get("industry") or ""
        pick["day_change_pct"] = info.get("regularMarketChangePercent") or 0.0
    except Exception:
        pick["name"] = ticker
        pick["sector"] = ""
        pick["industry"] = ""
        pick["day_change_pct"] = 0.0

    pick["signal"] = _signal_text(
        pick["rsi"], pick["vs_ma50"], pick["vs_ma200"], pick["rel_vol"], pick["ret_5d"]
    )
    pick["yahoo_url"] = f"https://finance.yahoo.com/quote/{ticker}"
    return pick
