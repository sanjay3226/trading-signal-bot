"""
╔══════════════════════════════════════════════════════════╗
║  SIGNAL ENGINE — Multi-Timeframe Confluence              ║
╚══════════════════════════════════════════════════════════╝

HOW MULTI-TIMEFRAME (MTF) ANALYSIS WORKS:
──────────────────────────────────────────
Imagine you're looking at a 1H chart and see a "BUY" signal.
But if you zoom out to the 4H chart, it shows "SELL".

Who's right? Usually the HIGHER timeframe wins, because
bigger players (institutions) trade on higher timeframes.

Our approach:
1. Analyse the PRIMARY timeframe the user selected (e.g., 1H)
2. Also analyse 1-2 HIGHER timeframes (e.g., 4H, 1D)
3. If all agree → BOOST confidence (they confirm each other)
4. If they disagree → REDUCE confidence (conflict)

EXAMPLE:
  1H says BUY  (70% confidence)
  4H says BUY  (65% confidence)
  1D says BUY  (60% confidence)
  → All three agree! Final: BUY at 82% confidence (boosted!)

  1H says BUY  (70% confidence)
  4H says SELL (60% confidence)
  → Conflict! Final: BUY at 55% confidence (reduced!)
"""

import numpy as np
import ta as ta_lib
from config import TIER_STRONG, TIER_NORMAL, TIER_WEAK, MTF_MAP
from data_fetcher import fetch
from indicators import IndicatorEngine
from patterns import detect_patterns
from divergence import detect_divergences


# ═══════════════════════════════════════
#  CLASSIFICATION
# ═══════════════════════════════════════
def classify(confidence: float, direction: str) -> dict:
    """Map confidence % → tier label + emoji + colors."""
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


# ═══════════════════════════════════════
#  SINGLE TIMEFRAME AGGREGATION
# ═══════════════════════════════════════
def aggregate(indicator_results: list[dict]) -> dict:
    """
    Combine all indicator signals into one verdict.

    Math behind it:
    ───────────────
    Each indicator casts a weighted vote:
      vote = signal × weight

    We sum all votes and divide by total weight:
      normalised = Σ(signal × weight) / Σ(weight)

    This gives us a value from -1 (all say SELL) to +1 (all say BUY).
    We convert to percentage: confidence = |normalised| × 100

    Then we apply an AGREEMENT BONUS:
    If >80% of indicators point the same direction,
    we boost confidence by 15% (capped at 99%).
    """
    if not indicator_results:
        return {
            "direction": "NEUTRAL", "confidence": 0,
            **classify(0, "BUY"),
            "buy_count": 0, "sell_count": 0, "neutral_count": 0,
            "indicators": [], "entry_bias": "No data",
        }

    total_weight = sum(r["weight"] for r in indicator_results)
    weighted_sum = sum(r["signal"] * r["weight"] for r in indicator_results)
    normalised = weighted_sum / total_weight  # -1 … +1

    direction = "BUY" if normalised > 0 else "SELL"
    raw_confidence = abs(normalised) * 100

    # Count votes
    buy_c = sum(1 for r in indicator_results if r["signal"] > 0.05)
    sell_c = sum(1 for r in indicator_results if r["signal"] < -0.05)
    neut_c = len(indicator_results) - buy_c - sell_c
    agree_ratio = max(buy_c, sell_c) / len(indicator_results)

    # Agreement bonus/penalty
    if agree_ratio > 0.8:
        confidence = min(raw_confidence * 1.15, 99)
    elif agree_ratio > 0.65:
        confidence = raw_confidence * 1.05
    else:
        confidence = raw_confidence * 0.95

    confidence = round(min(confidence, 99), 1)
    info = classify(confidence, direction)

    sorted_ind = sorted(indicator_results,
                        key=lambda x: abs(x["signal"]), reverse=True)

    return {
        "direction": direction,
        "confidence": confidence,
        **info,
        "buy_count": buy_c,
        "sell_count": sell_c,
        "neutral_count": neut_c,
        "indicators": sorted_ind,
        "entry_bias": (
            f"{info['tier']} — {buy_c} buy / {sell_c} sell / "
            f"{neut_c} neutral ({agree_ratio:.0%} agreement)"
        ),
    }


# ═══════════════════════════════════════
#  MULTI-TIMEFRAME ANALYSIS (the big one)
# ═══════════════════════════════════════
def analyse_mtf(symbol: str, market: str, primary_tf: str,
                limit: int = 500) -> dict:
    """
    Full multi-timeframe analysis pipeline:

    Step 1: Fetch data for primary TF
    Step 2: Run 30 indicators
    Step 3: Detect candlestick patterns
    Step 4: Detect divergences
    Step 5: Combine everything → primary verdict
    Step 6: Fetch + analyse higher TFs
    Step 7: Adjust confidence based on MTF agreement

    Returns complete analysis dict.
    """

    # ─── Step 1: Fetch primary data ───
    df = fetch(symbol, market, primary_tf, limit)
    if df.empty or len(df) < 50:
        return {"error": f"Not enough data for {symbol}"}

    # ─── Step 2: Run 30 indicators ───
    engine = IndicatorEngine(df)
    ind_results = engine.run_all()

    # ─── Step 3: Detect candlestick patterns ───
    patterns = detect_patterns(df)

    # ─── Step 4: Detect divergences ───
    divergences = detect_divergences(df)

    # ─── Combine all signals ───
    all_signals = ind_results + patterns + divergences

    # ─── Step 5: Primary TF verdict ───
    primary_verdict = aggregate(all_signals)

    # ─── Step 6: Higher timeframe analysis ───
    higher_tfs = MTF_MAP.get(primary_tf, [])
    htf_results = []

    for htf in higher_tfs:
        try:
            htf_df = fetch(symbol, market, htf, limit)
            if htf_df.empty or len(htf_df) < 30:
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

    # ─── Step 7: MTF Confluence adjustment ───
    """
    HOW THE MTF ADJUSTMENT WORKS:
    ─────────────────────────────
    We check if higher TFs agree with the primary TF.

    Agreement scoring:
    - Same direction + high confidence = +1.0 (strong agree)
    - Same direction + low confidence  = +0.5 (weak agree)
    - Different direction              = -1.0 (conflict!)

    We average the agreement scores and use it to adjust:
    - All agree    → boost primary confidence by up to 20%
    - All conflict → reduce primary confidence by up to 30%
    """
    final_confidence = primary_verdict["confidence"]

    if htf_results:
        agreement_scores = []
        for htf in htf_results:
            if htf["direction"] == primary_verdict["direction"]:
                # Same direction — boost based on HTF confidence
                score = 0.5 + (htf["confidence"] / 200)  # 0.5 to 1.0
            else:
                # Opposite direction — penalty
                score = -(0.5 + (htf["confidence"] / 200))
            agreement_scores.append(score)

        avg_agreement = np.mean(agreement_scores)

        if avg_agreement > 0.5:
            # Strong agreement → boost up to 20%
            boost = avg_agreement * 0.2
            final_confidence = min(final_confidence * (1 + boost), 99)
        elif avg_agreement < -0.3:
            # Conflict → reduce up to 30%
            penalty = abs(avg_agreement) * 0.3
            final_confidence = final_confidence * (1 - penalty)

        final_confidence = round(max(min(final_confidence, 99), 0), 1)

    final_info = classify(final_confidence, primary_verdict["direction"])

    # ─── Compute SL/TP ───
    levels = compute_levels(df, primary_tf)

    # ─── Build price data for chart ───
    chart_data = []
    for idx, row in df.iterrows():
        chart_data.append({
            "time": int(idx.timestamp()) if hasattr(idx, 'timestamp') else 0,
            "open": round(row["open"], 6),
            "high": round(row["high"], 6),
            "low": round(row["low"], 6),
            "close": round(row["close"], 6),
            "volume": round(row["volume"], 2),
        })

    price = df["close"].iloc[-1]
    chg = (df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100

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
        "chart_data": chart_data[-300:],  # last 300 candles
        "total_signals": len(all_signals),
    }


# ═══════════════════════════════════════
#  SL / TP CALCULATOR
# ═══════════════════════════════════════
def compute_levels(df, timeframe="1h"):
    """
    SL/TP levels adjusted per timeframe.
    Higher TF = wider stops (more room to breathe)
    """
    import ta as ta_lib

    # Different multipliers per timeframe
    tf_settings = {
        "1h":  {"sl": 1.5, "tp": 2.5},
        "4h":  {"sl": 2.0, "tp": 3.0},
        "1d":  {"sl": 2.5, "tp": 4.0},
        "1w":  {"sl": 3.0, "tp": 5.0},
    }

    settings = tf_settings.get(timeframe, {"sl": 1.5, "tp": 2.5})
    atr_mult_sl = settings["sl"]
    atr_mult_tp = settings["tp"]

    atr = ta_lib.volatility.AverageTrueRange(
        df["high"], df["low"], df["close"], window=14
    ).average_true_range()

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


