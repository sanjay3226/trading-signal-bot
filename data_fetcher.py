"""
DATA FETCHER — Uses exchanges that work from US/cloud servers
"""

import pandas as pd
import ccxt
import yfinance as yf
import requests


# ═══════════════════════════════════════
#  CRYPTO — Try multiple exchanges
# ═══════════════════════════════════════
def fetch_crypto(symbol: str, timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
    """
    Try multiple exchanges in order until one works.
    Binance blocks US IPs, so we try alternatives.
    """

    # List of exchanges to try (in order)
    exchanges = [
        ("bybit", ccxt.bybit({"enableRateLimit": True})),
        ("okx", ccxt.okx({"enableRateLimit": True})),
        ("kucoin", ccxt.kucoin({"enableRateLimit": True})),
        ("binance", ccxt.binance({"enableRateLimit": True})),
    ]

    for name, exchange in exchanges:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if ohlcv and len(ohlcv) > 10:
                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                print(f"[OK] {symbol} fetched from {name}")
                return df.astype(float)
        except Exception as e:
            print(f"[SKIP] {name} failed for {symbol}: {e}")
            continue

    # Last resort: try yfinance for crypto
    return fetch_crypto_yfinance(symbol, timeframe)


def fetch_crypto_yfinance(symbol: str, timeframe: str = "1h") -> pd.DataFrame:
    """
    Fallback: fetch crypto from Yahoo Finance.
    Yahoo uses different symbol format: BTC-USD instead of BTC/USDT
    """
    try:
        # Convert BTC/USDT → BTC-USD
        base = symbol.split("/")[0]
        yf_symbol = f"{base}-USD"

        tf_map = {
       "1h":  ("2y", "1h"),
       "4h":  ("2y", "1d"),
       "1d":  ("5y", "1d"),
       "1w":  ("10y", "1wk"),
   }

        period, interval = tf_map.get(timeframe, ("2y", "1h"))
        tk = yf.Ticker(yf_symbol)
        df = tk.history(period=period, interval=interval)

        if df.empty:
            return pd.DataFrame()

        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        print(f"[OK] {symbol} fetched from Yahoo Finance as {yf_symbol}")
        return df[keep].astype(float)

    except Exception as e:
        print(f"[FAIL] Yahoo Finance failed for {symbol}: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════
#  STOCKS & FOREX — Yahoo Finance
# ═══════════════════════════════════════
def fetch_yfinance(symbol: str, timeframe: str = "1d") -> pd.DataFrame:
    try:
         tf_map = {
       "1h":  ("2y", "1h"),
       "4h":  ("2y", "1d"),
       "1d":  ("5y", "1d"),
       "1w":  ("10y", "1wk"),
   }
        period, interval = tf_map.get(timeframe, ("1y", "1d"))
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, interval=interval)

        if df.empty:
            return pd.DataFrame()

        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        return df[keep].astype(float)

    except Exception as e:
        print(f"[YFINANCE ERROR] {symbol}: {e}")
        return pd.DataFrame()


# ═══════════════════════════════════════
#  COINGECKO — Trending coins
# ═══════════════════════════════════════
def fetch_trending() -> list:
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
    if market.lower() == "crypto":
        return fetch_crypto(symbol, timeframe, limit)
    else:
        return fetch_yfinance(symbol, timeframe)

