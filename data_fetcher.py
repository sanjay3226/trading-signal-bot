import pandas as pd
import ccxt
import yfinance as yf
import requests


def fetch_crypto(symbol, timeframe="1h", limit=500):
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
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                return df.astype(float)
        except Exception:
            continue
    return fetch_crypto_yfinance(symbol, timeframe)


def fetch_crypto_yfinance(symbol, timeframe="1h"):
    try:
        base = symbol.split("/")[0]
        yf_symbol = base + "-USD"
        tf_map = {
            "1h": ("2y", "1h"),
            "4h": ("2y", "1d"),
            "1d": ("5y", "1d"),
            "1w": ("10y", "1wk"),
        }
        period, interval = tf_map.get(timeframe, ("2y", "1h"))
        tk = yf.Ticker(yf_symbol)
        df = tk.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        return df[keep].astype(float)
    except Exception:
        return pd.DataFrame()


def fetch_yfinance(symbol, timeframe="1d"):
    try:
        tf_map = {
            "1h": ("2y", "1h"),
            "4h": ("2y", "1d"),
            "1d": ("5y", "1d"),
            "1w": ("10y", "1wk"),
        }
        period, interval = tf_map.get(timeframe, ("1y", "1d"))
        df = None
        try:
            tk = yf.Ticker(symbol)
            df = tk.history(period=period, interval=interval)
        except Exception:
            pass
        if df is None or df.empty:
            try:
                df = yf.download(symbol, period=period, interval=interval, progress=False)
            except Exception:
                pass
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        if not keep or "close" not in keep:
            return pd.DataFrame()
        return df[keep].astype(float)
    except Exception:
        return pd.DataFrame()


def fetch_trending():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=10)
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


def fetch(symbol, market, timeframe="1h", limit=500):
    if market.lower() == "crypto":
        return fetch_crypto(symbol, timeframe, limit)
    else:
        return fetch_yfinance(symbol, timeframe)
