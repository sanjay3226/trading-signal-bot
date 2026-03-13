import pandas as pd
import numpy as np


def detect_patterns(df):
    if len(df) < 5:
        return []
    results = []
    c = df["close"].values
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    body = abs(c - o)
    full_range = h - l
    upper_shadow = h - np.maximum(c, o)
    lower_shadow = np.minimum(c, o) - l
    avg_body = body[-20:].mean() if len(body) >= 20 else body.mean()

    if full_range[-1] > 0 and body[-1] / full_range[-1] < 0.1:
        trend = c[-1] - c[-5] if len(c) >= 5 else 0
        if trend > 0:
            sig, desc = -0.4, "Doji after uptrend"
        elif trend < 0:
            sig, desc = 0.4, "Doji after downtrend"
        else:
            sig, desc = 0, "Doji indecision"
        results.append({"name": "Doji", "signal": sig, "weight": 1.2, "desc": desc, "category": "pattern", "value": "+"})

    if body[-1] > 0 and lower_shadow[-1] >= 2 * body[-1] and upper_shadow[-1] < body[-1] * 0.5:
        if len(c) >= 5 and c[-1] < c[-5]:
            results.append({"name": "Hammer", "signal": 0.7, "weight": 1.5, "desc": "Hammer bullish reversal", "category": "pattern", "value": "H"})

    if body[-1] > 0 and upper_shadow[-1] >= 2 * body[-1] and lower_shadow[-1] < body[-1] * 0.5:
        if len(c) >= 5 and c[-1] > c[-5]:
            results.append({"name": "Shooting Star", "signal": -0.7, "weight": 1.5, "desc": "Shooting star bearish reversal", "category": "pattern", "value": "S"})

    if c[-2] < o[-2] and c[-1] > o[-1] and o[-1] <= c[-2] and c[-1] >= o[-2] and body[-1] > body[-2]:
        results.append({"name": "Bullish Engulfing", "signal": 0.8, "weight": 1.8, "desc": "Bullish engulfing reversal", "category": "pattern", "value": "BE"})

    if c[-2] > o[-2] and c[-1] < o[-1] and o[-1] >= c[-2] and c[-1] <= o[-2] and body[-1] > body[-2]:
        results.append({"name": "Bearish Engulfing", "signal": -0.8, "weight": 1.8, "desc": "Bearish engulfing reversal", "category": "pattern", "value": "BE"})

    if len(c) >= 3:
        if c[-3] < o[-3] and body[-3] > avg_body and body[-2] < avg_body * 0.5 and c[-1] > o[-1] and body[-1] > avg_body and c[-1] > (o[-3] + c[-3]) / 2:
            results.append({"name": "Morning Star", "signal": 0.85, "weight": 2.0, "desc": "Morning star bullish reversal", "category": "pattern", "value": "MS"})

    if len(c) >= 3:
        if c[-3] > o[-3] and body[-3] > avg_body and body[-2] < avg_body * 0.5 and c[-1] < o[-1] and body[-1] > avg_body and c[-1] < (o[-3] + c[-3]) / 2:
            results.append({"name": "Evening Star", "signal": -0.85, "weight": 2.0, "desc": "Evening star bearish reversal", "category": "pattern", "value": "ES"})

    if len(c) >= 3:
        if all(c[-i] > o[-i] for i in range(1, 4)) and all(body[-i] > avg_body * 0.6 for i in range(1, 4)) and c[-1] > c[-2] > c[-3]:
            results.append({"name": "Three White Soldiers", "signal": 0.9, "weight": 2.0, "desc": "Strong bullish continuation", "category": "pattern", "value": "3WS"})

    if len(c) >= 3:
        if all(c[-i] < o[-i] for i in range(1, 4)) and all(body[-i] > avg_body * 0.6 for i in range(1, 4)) and c[-1] < c[-2] < c[-3]:
            results.append({"name": "Three Black Crows", "signal": -0.9, "weight": 2.0, "desc": "Strong bearish continuation", "category": "pattern", "value": "3BC"})

    return results
