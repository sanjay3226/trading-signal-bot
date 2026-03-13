import numpy as np
import pandas as pd
import ta as ta_lib


def _find_swing_highs(series, window=5):
    highs = []
    vals = series.values
    for i in range(window, len(vals) - window):
        if vals[i] == max(vals[i - window:i + window + 1]):
            highs.append((i, vals[i]))
    return highs


def _find_swing_lows(series, window=5):
    lows = []
    vals = series.values
    for i in range(window, len(vals) - window):
        if vals[i] == min(vals[i - window:i + window + 1]):
            lows.append((i, vals[i]))
    return lows


def detect_divergences(df, lookback=60):
    results = []
    close = df["close"]
    recent = close.tail(lookback)

    rsi = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
    if rsi is not None and rsi.dropna().shape[0] >= lookback:
        rsi_recent = rsi.tail(lookback)
        price_lows = _find_swing_lows(recent, window=5)
        rsi_lows = _find_swing_lows(rsi_recent, window=5)
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            rl1, rl2 = rsi_lows[-2], rsi_lows[-1]
            if pl2[1] < pl1[1] and rl2[1] > rl1[1]:
                results.append({"name": "RSI Bullish Divergence", "signal": 0.8, "weight": 2.2, "desc": "Price lower low + RSI higher low", "category": "divergence", "value": "BD"})
        price_highs = _find_swing_highs(recent, window=5)
        rsi_highs = _find_swing_highs(rsi_recent, window=5)
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            rh1, rh2 = rsi_highs[-2], rsi_highs[-1]
            if ph2[1] > ph1[1] and rh2[1] < rh1[1]:
                results.append({"name": "RSI Bearish Divergence", "signal": -0.8, "weight": 2.2, "desc": "Price higher high + RSI lower high", "category": "divergence", "value": "BD"})

    macd_ind = ta_lib.trend.MACD(close, window_fast=12, window_slow=26, window_sign=9)
    macd_line = macd_ind.macd()
    if macd_line is not None and macd_line.dropna().shape[0] >= lookback:
        macd_recent = macd_line.tail(lookback)
        price_lows = _find_swing_lows(recent, window=5)
        macd_lows = _find_swing_lows(macd_recent, window=5)
        if len(price_lows) >= 2 and len(macd_lows) >= 2:
            pl1, pl2 = price_lows[-2], price_lows[-1]
            ml1, ml2 = macd_lows[-2], macd_lows[-1]
            if pl2[1] < pl1[1] and ml2[1] > ml1[1]:
                results.append({"name": "MACD Bullish Divergence", "signal": 0.75, "weight": 2.0, "desc": "MACD diverging bullishly", "category": "divergence", "value": "BD"})
        price_highs = _find_swing_highs(recent, window=5)
        macd_highs = _find_swing_highs(macd_recent, window=5)
        if len(price_highs) >= 2 and len(macd_highs) >= 2:
            ph1, ph2 = price_highs[-2], price_highs[-1]
            mh1, mh2 = macd_highs[-2], macd_highs[-1]
            if ph2[1] > ph1[1] and mh2[1] < mh1[1]:
                results.append({"name": "MACD Bearish Divergence", "signal": -0.75, "weight": 2.0, "desc": "MACD diverging bearishly", "category": "divergence", "value": "BD"})

    return results
