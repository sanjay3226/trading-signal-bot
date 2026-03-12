"""
╔══════════════════════════════════════════════════════════╗
║  CANDLESTICK PATTERN RECOGNITION                        ║
╚══════════════════════════════════════════════════════════╝

HOW CANDLESTICK PATTERNS WORK:
──────────────────────────────
A candlestick shows 4 prices: Open, High, Low, Close (OHLC).

  │  ← upper shadow (wick)
  ┌┐ ← if Close > Open = GREEN (bullish)
  ││    if Close < Open = RED (bearish)
  └┘
  │  ← lower shadow (wick)

BODY = |Close - Open|      (the fat rectangle)
WICK = shadows above/below (the thin lines)

The SHAPE of the candle tells a story:
- Long green body = strong buying
- Long red body  = strong selling
- Tiny body + long wicks = indecision (DOJI)
- Long lower wick + small body = HAMMER (bullish reversal)

We detect these patterns and add them as extra signals.
"""

import pandas as pd
import numpy as np


def detect_patterns(df: pd.DataFrame) -> list[dict]:
    """
    Scan the last few candles for common patterns.

    Returns list of:
    { name, signal (-1 to +1), weight, desc }
    """
    if len(df) < 5:
        return []

    results = []
    c = df["close"].values
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values

    # Helper metrics for the latest candles
    body = abs(c - o)
    full_range = h - l
    upper_shadow = h - np.maximum(c, o)
    lower_shadow = np.minimum(c, o) - l

    # Average body size for reference
    avg_body = body[-20:].mean() if len(body) >= 20 else body.mean()

    # ──────────── DOJI ────────────
    # Tiny body relative to range → indecision → possible reversal
    if full_range[-1] > 0 and body[-1] / full_range[-1] < 0.1:
        # Determine bias from context
        trend = c[-1] - c[-5] if len(c) >= 5 else 0
        if trend > 0:
            sig, desc = -0.4, "Doji after uptrend — possible reversal down"
        elif trend < 0:
            sig, desc = 0.4, "Doji after downtrend — possible reversal up"
        else:
            sig, desc = 0, "Doji — market indecision"
        results.append({
            "name": "Doji",
            "signal": sig,
            "weight": 1.2,
            "desc": desc,
            "category": "pattern",
            "value": "⊕",
        })

    # ──────────── HAMMER (bullish) ────────────
    # Small body at top, long lower shadow (≥2× body)
    # Appears after a downtrend → reversal signal
    if (body[-1] > 0 and
        lower_shadow[-1] >= 2 * body[-1] and
        upper_shadow[-1] < body[-1] * 0.5 and
        len(c) >= 5 and c[-1] < c[-5]):
        results.append({
            "name": "Hammer",
            "signal": 0.7,
            "weight": 1.5,
            "desc": "Hammer pattern — strong bullish reversal signal",
            "category": "pattern",
            "value": "🔨",
        })

    # ──────────── SHOOTING STAR (bearish) ────────────
    # Small body at bottom, long upper shadow (≥2× body)
    # Appears after uptrend → reversal signal
    if (body[-1] > 0 and
        upper_shadow[-1] >= 2 * body[-1] and
        lower_shadow[-1] < body[-1] * 0.5 and
        len(c) >= 5 and c[-1] > c[-5]):
        results.append({
            "name": "Shooting Star",
            "signal": -0.7,
            "weight": 1.5,
            "desc": "Shooting star — strong bearish reversal signal",
            "category": "pattern",
            "value": "⭐",
        })

    # ──────────── BULLISH ENGULFING ────────────
    # Previous candle was red, current green candle completely covers it
    if (c[-2] < o[-2] and          # previous was red
        c[-1] > o[-1] and          # current is green
        o[-1] <= c[-2] and         # current open ≤ prev close
        c[-1] >= o[-2] and         # current close ≥ prev open
        body[-1] > body[-2]):      # current body larger
        results.append({
            "name": "Bullish Engulfing",
            "signal": 0.8,
            "weight": 1.8,
            "desc": "Bullish engulfing — strong reversal pattern",
            "category": "pattern",
            "value": "🟢⬆",
        })

    # ──────────── BEARISH ENGULFING ────────────
    if (c[-2] > o[-2] and          # previous was green
        c[-1] < o[-1] and          # current is red
        o[-1] >= c[-2] and         # current open ≥ prev close
        c[-1] <= o[-2] and         # current close ≤ prev open
        body[-1] > body[-2]):
        results.append({
            "name": "Bearish Engulfing",
            "signal": -0.8,
            "weight": 1.8,
            "desc": "Bearish engulfing — strong reversal pattern",
            "category": "pattern",
            "value": "🔴⬇",
        })

    # ──────────── MORNING STAR (bullish 3-candle) ────────────
    if len(c) >= 3:
        # Day 1: big red candle
        # Day 2: small body (gap down)
        # Day 3: big green candle closing above midpoint of day 1
        if (c[-3] < o[-3] and                     # day1 red
            body[-3] > avg_body and                # day1 big
            body[-2] < avg_body * 0.5 and          # day2 small
            c[-1] > o[-1] and                      # day3 green
            body[-1] > avg_body and                # day3 big
            c[-1] > (o[-3] + c[-3]) / 2):          # closes above midpoint
            results.append({
                "name": "Morning Star",
                "signal": 0.85,
                "weight": 2.0,
                "desc": "Morning star — powerful bullish reversal (3 candle)",
                "category": "pattern",
                "value": "🌟",
            })

    # ──────────── EVENING STAR (bearish 3-candle) ────────────
    if len(c) >= 3:
        if (c[-3] > o[-3] and
            body[-3] > avg_body and
            body[-2] < avg_body * 0.5 and
            c[-1] < o[-1] and
            body[-1] > avg_body and
            c[-1] < (o[-3] + c[-3]) / 2):
            results.append({
                "name": "Evening Star",
                "signal": -0.85,
                "weight": 2.0,
                "desc": "Evening star — powerful bearish reversal (3 candle)",
                "category": "pattern",
                "value": "🌑",
            })

    # ──────────── THREE WHITE SOLDIERS ────────────
    if len(c) >= 3:
        if (all(c[-i] > o[-i] for i in range(1, 4)) and     # 3 green
            all(body[-i] > avg_body * 0.6 for i in range(1, 4)) and  # decent size
            c[-1] > c[-2] > c[-3]):                            # each closes higher
            results.append({
                "name": "Three White Soldiers",
                "signal": 0.9,
                "weight": 2.0,
                "desc": "Three white soldiers — very strong bullish continuation",
                "category": "pattern",
                "value": "🟢🟢🟢",
            })

    # ──────────── THREE BLACK CROWS ────────────
    if len(c) >= 3:
        if (all(c[-i] < o[-i] for i in range(1, 4)) and
            all(body[-i] > avg_body * 0.6 for i in range(1, 4)) and
            c[-1] < c[-2] < c[-3]):
            results.append({
                "name": "Three Black Crows",
                "signal": -0.9,
                "weight": 2.0,
                "desc": "Three black crows — very strong bearish continuation",
                "category": "pattern",
                "value": "🔴🔴🔴",
            })

    # ──────────── DRAGONFLY DOJI (bullish) ────────────
    if (full_range[-1] > 0 and
        body[-1] / full_range[-1] < 0.1 and
        lower_shadow[-1] > full_range[-1] * 0.6 and
        upper_shadow[-1] < full_range[-1] * 0.1):
        results.append({
            "name": "Dragonfly Doji",
            "signal": 0.6,
            "weight": 1.3,
            "desc": "Dragonfly doji — bullish reversal signal",
            "category": "pattern",
            "value": "🜸",
        })

    # ──────────── GRAVESTONE DOJI (bearish) ────────────
    if (full_range[-1] > 0 and
        body[-1] / full_range[-1] < 0.1 and
        upper_shadow[-1] > full_range[-1] * 0.6 and
        lower_shadow[-1] < full_range[-1] * 0.1):
        results.append({
            "name": "Gravestone Doji",
            "signal": -0.6,
            "weight": 1.3,
            "desc": "Gravestone doji — bearish reversal signal",
            "category": "pattern",
            "value": "🪦",
        })

    return results