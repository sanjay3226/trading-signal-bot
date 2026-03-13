import numpy as np


def classify(confidence, direction):
    TIER_STRONG = 85
    TIER_NORMAL = 70
    TIER_WEAK = 55
    if confidence >= TIER_STRONG:
        tier = f"STRONG {direction}"
        emoji = "🟢🟢" if direction == "BUY" else "🔴🔴"
        color = "#00ff88" if direction == "BUY" else "#ff4444"
    elif confidence >= TIER_NORMAL:
        tier = direction
        emoji = "🟢" if direction == "BUY" else "🔴"
        color = "#22c55e" if direction == "BUY" else "#ef4444"
    elif confidence >= TIER_WEAK:
        tier = f"WEAK {direction}"
        emoji = "🟡"
        color = "#f59e0b"
    else:
        tier = "NEUTRAL"
        emoji = "⚪"
        color = "#6b7280"
    return {"tier": tier, "emoji": emoji, "color": color}


def aggregate(indicator_results):
    if not indicator_results:
        return {
            "direction": "NEUTRAL", "confidence": 0,
            **classify(0, "BUY"),
            "buy_count": 0, "sell_count": 0, "neutral_count": 0,
            "indicators": [], "entry_bias": "No data",
        }
    total_weight = sum(r["weight"] for r in indicator_results)
    weighted_sum = sum(r["signal"] * r["weight"] for r in indicator_results)
    normalised = weighted_sum / total_weight
    direction = "BUY" if normalised > 0 else "SELL"
    raw_confidence = abs(normalised) * 100
    buy_c = sum(1 for r in indicator_results if r["signal"] > 0.05)
    sell_c = sum(1 for r in indicator_results if r["signal"] < -0.05)
    neut_c = len(indicator_results) - buy_c - sell_c
    agree_ratio = max(buy_c, sell_c) / len(indicator_results)
    if agree_ratio > 0.8:
        confidence = min(raw_confidence * 1.15, 99)
    elif agree_ratio > 0.65:
        confidence = raw_confidence * 1.05
    else:
        confidence = raw_confidence * 0.95
    confidence = round(min(confidence, 99), 1)
    info = classify(confidence, direction)
    sorted_ind = sorted(indicator_results, key=lambda x: abs(x["signal"]), reverse=True)
    return {
        "direction": direction,
        "confidence": confidence,
        **info,
        "buy_count": buy_c,
        "sell_count": sell_c,
        "neutral_count": neut_c,
        "indicators": sorted_ind,
        "entry_bias": f"{info['tier']} — {buy_c} buy / {sell_c} sell / {neut_c} neutral ({agree_ratio:.0%} agreement)",
    }


def compute_levels(df, timeframe="1h"):
    import ta as ta_lib
    tf_settings = {
        "1h": {"sl": 1.5, "tp": 2.5},
        "4h": {"sl": 2.0, "tp": 3.0},
        "1d": {"sl": 2.5, "tp": 4.0},
        "1w": {"sl": 3.0, "tp": 5.0},
    }
    settings = tf_settings.get(timeframe, {"sl": 1.5, "tp": 2.5})
    atr_mult_sl = settings["sl"]
    atr_mult_tp = settings["tp"]
    atr = ta_lib.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()
    if atr is None or atr.dropna().empty:
        return None
    atr_v = atr.iloc[-1]
    price = df["close"].iloc[-1]
    return {
        "price": round(price, 6),
        "atr": round(atr_v, 6),
        "long_sl": round(price - atr_mult_sl * atr_v, 6),
        "long_tp": round(price + atr_mult_tp * atr_v, 6),
        "short_sl": round(price + atr_mult_sl * atr_v, 6),
        "short_tp": round(price - atr_mult_tp * atr_v, 6),
        "rr_ratio": round(atr_mult_tp / atr_mult_sl, 2),
    }


def analyse_mtf(symbol, market, primary_tf, limit=500, skip_mtf=False):
    from data_fetcher import fetch
    from indicators import IndicatorEngine
    from patterns import detect_patterns
    from divergence import detect_divergences
    from config import MTF_MAP

    df = fetch(symbol, market, primary_tf, limit)
    if df.empty or len(df) < 20:
        return {"error": f"Not enough data for {symbol}"}

    engine = IndicatorEngine(df)
    ind_results = engine.run_all()
    patterns = detect_patterns(df)
    divergences = detect_divergences(df)
    all_signals = ind_results + patterns + divergences
    primary_verdict = aggregate(all_signals)

    higher_tfs = [] if skip_mtf else MTF_MAP.get(primary_tf, [])
    htf_results = []
    for htf in higher_tfs:
        try:
            htf_df = fetch(symbol, market, htf, limit)
            if htf_df.empty or len(htf_df) < 20:
                continue
            htf_engine = IndicatorEngine(htf_df)
            htf_ind = htf_engine.run_all()
            htf_verdict = aggregate(htf_ind)
            htf_results.append({
                "timeframe": htf,
                "direction": htf_verdict["direction"],
                "confidence": htf_verdict["confidence"],
                "tier": htf_verdict["tier"],
                "emoji": htf_verdict["emoji"],
                "color": htf_verdict["color"],
                "buy_count": htf_verdict["buy_count"],
                "sell_count": htf_verdict["sell_count"],
            })
        except Exception:
            continue

    final_confidence = primary_verdict["confidence"]
    if htf_results:
        agreement_scores = []
        for htf in htf_results:
            if htf["direction"] == primary_verdict["direction"]:
                score = 0.5 + (htf["confidence"] / 200)
            else:
                score = -(0.5 + (htf["confidence"] / 200))
            agreement_scores.append(score)
        avg_agreement = np.mean(agreement_scores)
        if avg_agreement > 0.5:
            boost = avg_agreement * 0.2
            final_confidence = min(final_confidence * (1 + boost), 99)
        elif avg_agreement < -0.3:
            penalty = abs(avg_agreement) * 0.3
            final_confidence = final_confidence * (1 - penalty)
        final_confidence = round(max(min(final_confidence, 99), 0), 1)

    final_info = classify(final_confidence, primary_verdict["direction"])
    levels = compute_levels(df, primary_tf)

    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(idx.timestamp()) if hasattr(idx, "timestamp") else 0,
            "open": round(row["open"], 6),
            "high": round(row["high"], 6),
            "low": round(row["low"], 6),
            "close": round(row["close"], 6),
            "volume": round(row["volume"], 2),
        })

    price = df["close"].iloc[-1]
    prev_price = df["close"].iloc[-2] if len(df) > 1 else price
    chg = (price / prev_price - 1) * 100

    return {
        "symbol": symbol,
        "market": market,
        "timeframe": primary_tf,
        "price": price,
        "change_pct": round(chg, 2),
        "direction": primary_verdict["direction"],
        "confidence": final_confidence,
        **final_info,
        "buy_count": primary_verdict["buy_count"],
        "sell_count": primary_verdict["sell_count"],
        "neutral_count": primary_verdict["neutral_count"],
        "entry_bias": primary_verdict["entry_bias"],
        "indicators": primary_verdict["indicators"],
        "patterns": patterns,
        "divergences": divergences,
        "htf_results": htf_results,
        "levels": levels,
        "chart_data": chart_data[-300:],
        "total_signals": len(all_signals),
    }
