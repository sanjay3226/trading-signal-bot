"""
╔══════════════════════════════════════════════════════════╗
║  CONFIG — All settings, watchlists, indicator params    ║
╚══════════════════════════════════════════════════════════╝

HOW THIS WORKS:
───────────────
Every indicator has a "w" (weight) value. When we aggregate
all 30 indicators, each one "votes" BUY or SELL with a signal
strength from -1.0 (strong sell) to +1.0 (strong buy).

The WEIGHT controls how much that vote matters:
  - EMA 50/200 golden cross (w=2.5) matters more than
  - Donchian channel position (w=1.0)

This is like a jury — some jurors (indicators) are more
experienced, so their opinion counts more.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────── Alert Credentials (optional) ───────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ─────────── Watchlists ───────────
CRYPTO_ASSETS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "NEAR/USDT",
    "ARB/USDT", "OP/USDT", "FIL/USDT", "APT/USDT", "INJ/USDT",
]

FOREX_ASSETS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
    "NZDUSD=X", "USDCHF=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
]

STOCK_ASSETS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
    "JPM", "V", "JNJ", "WMT", "NFLX", "AMD", "DIS", "BA",
]

# ─────────── Multi-Timeframe Map ───────────
# For each primary TF, which higher TFs to also check
# This is the KEY new feature — we confirm signals across
# multiple timeframes for much higher accuracy
MTF_MAP = {
    "1h":  ["4h", "1d"],
    "4h":  ["1d", "1w"],
    "1d":  ["1w"],
    "1w":  [],
}

# ─────────── YFinance TF → (period, interval) ───────────
YFINANCE_TF_MAP = {
    "1m":  ("7d", "1m"),
    "5m":  ("60d", "5m"),
    "15m": ("60d", "15m"),
    "1h":  ("2y", "1h"),
    "4h":  ("2y", "1d"),     # YF doesn't have 4h; fall back to 1d
    "1d":  ("5y", "1d"),
    "1w":  ("10y", "1wk"),
}

# ─────────── Indicator Settings (Optimised) ───────────
# Each indicator has its own parameters + a weight (w)
INDICATOR_CFG = {
    # ──── Oscillators ────
    "rsi":          {"len": 14, "ob": 70, "os": 30,              "w": 1.5},
    "stoch":        {"k": 14, "d": 3, "smooth": 3,               "w": 1.3},
    "stoch_rsi":    {"len": 14, "rsi_len": 14, "k": 3, "d": 3,   "w": 1.3},
    "cci":          {"len": 20,                                    "w": 1.0},
    "williams":     {"len": 14,                                    "w": 1.0},
    "mfi":          {"len": 14,                                    "w": 1.3},
    "uo":           {"s": 7, "m": 14, "l": 28,                    "w": 1.0},
    "roc":          {"len": 12,                                    "w": 1.0},
    "trix":         {"len": 15,                                    "w": 1.0},
    # ──── Trend ────
    "macd":         {"f": 12, "s": 26, "sig": 9,                  "w": 2.0},
    "adx":          {"len": 14, "thresh": 25,                      "w": 1.5},
    "supertrend":   {"len": 10, "mult": 3.0,                      "w": 1.8},
    "psar":         {"af": 0.02, "max_af": 0.2,                   "w": 1.5},
    "ichimoku":     {"tenkan": 9, "kijun": 26, "senkou": 52,      "w": 2.0},
    "aroon":        {"len": 25,                                    "w": 1.0},
    # ──── Moving Averages ────
    "ema_short":    {"f": 9, "s": 21,                             "w": 1.8},
    "ema_long":     {"f": 50, "s": 200,                           "w": 2.5},
    "sma_trend":    {"periods": [20, 50, 200],                     "w": 1.5},
    "hma":          {"len": 9,                                     "w": 1.3},
    "ma_ribbon":    {"periods": [8, 13, 21, 34, 55, 89],          "w": 1.3},
    # ──── Volatility ────
    "bbands":       {"len": 20, "std": 2.0,                       "w": 1.5},
    "keltner":      {"len": 20, "mult": 2.0,                      "w": 1.2},
    "donchian":     {"len": 20,                                    "w": 1.0},
    "atr":          {"len": 14,                                    "w": 0.8},
    # ──── Volume ────
    "obv":          {                                              "w": 1.2},
    "cmf":          {"len": 20,                                    "w": 1.2},
    "vwap":         {                                              "w": 1.5},
    "vol_analysis": {                                              "w": 1.5},
    # ──── Price Action ────
    "fibonacci":    {                                              "w": 1.2},
    "pivot":        {                                              "w": 1.0},
}

# ─────────── Confidence Tiers ───────────
TIER_STRONG = 85    # ≥85% → STRONG BUY / STRONG SELL
TIER_NORMAL = 70    # ≥70% → BUY / SELL

TIER_WEAK   = 55    # ≥55% → WEAK signal
