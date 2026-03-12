"""
╔══════════════════════════════════════════════════════════╗
║  DATA FETCHER                                           ║
║  Pulls OHLCV data from Binance (crypto) and             ║
║  Yahoo Finance (stocks/forex)                            ║
╚══════════════════════════════════════════════════════════╝

HOW IT WORKS:
─────────────
1. For CRYPTO  → We use CCXT library which talks to Binance API
   - Free, no API key needed for public data
   - Returns candles: [timestamp, open, high, low, close, volume]

2. For STOCKS/FOREX → We use yfinance (Yahoo Finance scraper)
   - Also free, no key needed
   - Some limitations on intraday data (max 60 days for 1m)

3. CoinGecko → Just for "trending coins" widget (fun extra)

The data comes back as a pandas DataFrame — basically a spreadsheet
in memory that looks like:

    timestamp     | open    | high    | low     | close   | volume
    ──────────────┼─────────┼─────────┼─────────┼─────────┼────────
    2024-01-01    | 42000   | 42500   | 41800   | 42300   | 1500
    2024-01-02    | 42300   | 43000   | 42100   | 42800   | 1800
"""

import pandas as pd
import ccxt
import yfinance as yf
import requests
from config import YFINANCE_TF_MAP


# ═══════════════════════════════════════
#  CRYPTO — via Binance (CCXT)
# ═══════════════════════════════════════
def fetch_crypto(symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
    """
    Fetch crypto OHLCV from Binance.

    Parameters
    ----------
    symbol : str     e.g. "BTC/USDT"
    timeframe : str  e.g. "1h", "4h", "1d"
    limit : int      how many candles to fetch (max ~1000)

    Returns
    -------
    DataFrame with columns: open, high, low, close, volume
    Index: datetime
    """
    try:
        # CCXT is a universal crypto exchange library
        # It speaks to 100+ exchanges with one API
        exchange = ccxt.binance({
            "enableRateLimit": True,  # be polite, don't spam
        })

        # fetch_ohlcv returns: [[timestamp, O, H, L, C, V], ...]
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df.astype(float)

    except Exception as e:
        print(f"[BINANCE ERROR] {symbol}: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════
#  STOCKS & FOREX — via Yahoo Finance
# ═══════════════════════════════════════
def fetch_yfinance(symbol: str, timeframe: str = "1d") -> pd.DataFrame:
    """
    Fetch stock/forex OHLCV from Yahoo Finance.

    YFinance needs (period, interval) pairs:
      - period = how far back ("3mo", "1y", "5y")
      - interval = candle size ("1h", "1d", "1wk")
    """
    try:
        period, interval = YFINANCE_TF_MAP.get(timeframe, ("1y", "1d"))
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval)

        # Normalise column names (Yahoo uses "Close", we want "close")
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        return df[keep].astype(float)

    except Exception as e:
        print(f"[YFINANCE ERROR] {symbol}: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════
#  COINGECKO — Trending coins
# ═══════════════════════════════════════
def fetch_trending() -> list[dict]:
    """Get trending coins from CoinGecko (free, no key)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/search/trending",
            timeout=10
        )
        coins = r.json().get("coins", [])
        return [
            {
                "name": c["item"]["name"],
                "symbol": c["item"]["symbol"],
                "rank": c["item"].get("market_cap_rank", "—"),
                "thumb": c["item"].get("thumb", ""),
            }
            for c in coins
        ]
    except Exception:
        return []


# ═══════════════════════════════════════
#  UNIVERSAL DISPATCHER
# ═══════════════════════════════════════
def fetch(symbol: str, market: str, timeframe: str = "1h",
          limit: int = 500) -> pd.DataFrame:
    """
    Smart router — picks the right data source based on market type.

    This is the ONLY function the rest of the app calls.
    It figures out whether to use Binance or Yahoo automatically.
    """
    if market.lower() == "crypto":
        return fetch_crypto(symbol, timeframe, limit)
    else:
        return fetch_yfinance(symbol, timeframe)