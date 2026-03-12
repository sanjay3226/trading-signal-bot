"""
╔══════════════════════════════════════════════════════════╗
║  DIVERGENCE DETECTION                                    ║
╚══════════════════════════════════════════════════════════╝

WHAT IS DIVERGENCE?
───────────────────
Divergence = price says one thing, indicator says another.

BULLISH DIVERGENCE (strong buy signal):
  Price:  makes a LOWER LOW  (falling)
  RSI:    makes a HIGHER LOW (recovering)
  → The selling is weakening even though price keeps dropping
  → Often predicts a reversal UP

BEARISH DIVERGENCE (strong sell signal):
  Price:  makes a HIGHER HIGH (rising)
  RSI:    makes a LOWER HIGH  (weakening)
  → The buying is weakening even though price keeps rising
  → Often predicts a reversal DOWN

This is one of the MOST RELIABLE signals in technical analysis.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta


def _find_swing_highs(series: pd.Series, window: int = 5) -> list[tuple]:
    """Find local maxima (peaks) in a series."""
    highs = []
    vals = series.values
    for i in range(window, len(vals) - window):
        if vals[i] == max(vals[i - window:i + window + 1]):
            highs.append((i, vals[i]))
    return highs


def _find_swing_lows(series: pd.Series, window: int = 5) -> list[tuple]:
    """Find local minima (valleys) in a series."""
    lows = []
    vals = series.values
    for i in range(window, len(vals) - window):
        if vals[i] == min(vals[i - window:i + window + 1]):
            lows.append((i, vals[i]))
    return lows


def detect_divergences(df: pd.DataFrame, lookback: int = 60) -> list[dict]:
    """
    Detect RSI and MACD divergences.

    How it works step by step:
    1. Calculate RSI and MACD on the price data
    2. Find swing highs/lows in both price AND the indicator
    3. Compare the last 2 swings:
       - Price lower low + RSI higher low = bullish divergence
       - Price higher high + RSI lower high = bearish divergence

    Returns list of divergence signals.
    """
    results = []
    close = df["close"]
    recent = close.tail(lookback)

    # ─── RSI Divergence ───
    rsi = ta.rsi(close, length=14)
    if rsi is not None and rsi.dropna().shape[0] >= lookback:
        rsi_recent = rsi.tail(lookback)

        # Check for BULLISH divergence (lows)
        price_lows = _find_swing_lows(recent, window=5)
        rsi_lows = _find_swing_lows(rsi_recent, window=5)

        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            # Last two price lows
            pl1, pl2 = price_lows[-2], price_lows[-1]  # older, newer
            # Last two RSI lows
            rl1, rl2 = rsi_lows[-2], rsi_lows[-1]

            # Bullish: price lower low, RSI higher low
            if pl2[1] < pl1[1] and rl2[1] > rl1[1]:
                results.append({
                    "name": "RSI Bullish Divergence",
                    "signal": 0.8,
                    "weight": 2.2,
                    "desc": "Price lower low + RSI higher low → reversal UP expected",
                    "category": "divergence",
                    "value": "🟢↗",
                })

        # Check for BEARISH divergence (highs)
        price_highs = _find_swing_highs(recent, window=5)
        rsi_highs = _find_swing_highs(rsi_recent, window=5)

        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            rh1, rh2 = rsi_highs[-2], rsi_highs[-1]

            # Bearish: price higher high, RSI lower high
            if ph2[1] > ph1[1] and rh2[1] < rh1[1]:
                results.append({
                    "name": "RSI Bearish Divergence",
                    "signal": -0.8,
                    "weight": 2.2,
                    "desc": "Price higher high + RSI lower high → reversal DOWN expected",
                    "category": "divergence",
                    "value": "🔴↘",
                })

    # ─── MACD Divergence ───
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is not None and macd_df.dropna().shape[0] >= lookback:
        macd_line = macd_df.iloc[:, 0].tail(lookback)

        price_lows = _find_swing_lows(recent, window=5)
        macd_lows = _find_swing_lows(macd_line, window=5)

        if len(price_lows) >= 2 and len(macd_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            ml1, ml2 = macd_lows[-2], macd_lows[-1]

            if pl2[1] < pl1[1] and ml2[1] > ml1[1]:
                results.append({
                    "name": "MACD Bullish Divergence",
                    "signal": 0.75,
                    "weight": 2.0,
                    "desc": "MACD diverging bullishly from price",
                    "category": "divergence",
                    "value": "🟢↗",
                })

        price_highs = _find_swing_highs(recent, window=5)
        macd_highs = _find_swing_highs(macd_line, window=5)

        if len(price_highs) >= 2 and len(macd_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            mh1, mh2 = macd_highs[-2], macd_highs[-1]

            if ph2[1] > ph1[1] and mh2[1] < mh1[1]:
                results.append({
                    "name": "MACD Bearish Divergence",
                    "signal": -0.75,
                    "weight": 2.0,
                    "desc": "MACD diverging bearishly from price",
                    "category": "divergence",
                    "value": "🔴↘",
                })

    return results