"""
╔══════════════════════════════════════════════════════════╗
║  30 TECHNICAL INDICATORS                                ║
║                                                          ║
║  Each indicator returns a dict:                          ║
║  {                                                       ║
║    name:   "RSI"                                         ║
║    value:  "32.5"        (display string)                ║
║    signal: 0.7           (-1 to +1, buy/sell strength)   ║
║    weight: 1.5           (how much this vote matters)    ║
║    desc:   "Oversold"    (human explanation)             ║
║    category: "oscillator"                                ║
║  }                                                       ║
╚══════════════════════════════════════════════════════════╝

SIGNAL VALUES EXPLAINED:
────────────────────────
  +1.0 = Maximum bullish (STRONG BUY signal)
  +0.5 = Moderate bullish
   0.0 = Neutral / no signal
  -0.5 = Moderate bearish
  -1.0 = Maximum bearish (STRONG SELL signal)

Think of it like a voting scale. Each indicator is a voter
who says "I think the price will go UP (+) or DOWN (-)
and I'm THIS confident (0.1 = barely, 1.0 = absolutely sure)."
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from config import INDICATOR_CFG


def _r(name, value, signal, weight, desc, category="oscillator"):
    """Build standardised result dict."""
    return {
        "name": name,
        "value": str(value),
        "signal": float(np.clip(signal, -1, 1)),
        "weight": weight,
        "desc": desc,
        "category": category,
    }


class IndicatorEngine:
    """
    Runs all 30 indicators on a DataFrame and returns a list of results.

    Usage:
        engine = IndicatorEngine(df)
        results = engine.run_all()  # → list of 30 dicts
    """

    def __init__(self, df: pd.DataFrame, cfg: dict | None = None):
        self.df = df.copy()
        self.c = df["close"]
        self.h = df["high"]
        self.l = df["low"]
        self.o = df["open"]
        self.v = df["volume"]
        self.cfg = cfg or INDICATOR_CFG
        self._has_vol = self.v.sum() > 0

    def run_all(self) -> list[dict]:
        """Run every indicator, skip any that fail."""
        methods = [
            self._rsi, self._macd, self._bbands, self._stoch,
            self._ema_short, self._ema_long, self._sma_trend,
            self._adx, self._cci, self._williams, self._mfi,
            self._obv, self._psar, self._ichimoku, self._roc,
            self._cmf, self._aroon, self._supertrend, self._hma,
            self._trix, self._keltner, self._stoch_rsi, self._uo,
            self._donchian, self._vwap, self._vol_analysis,
            self._ma_ribbon, self._fibonacci, self._pivot, self._atr,
        ]
        results = []
        for fn in methods:
            try:
                r = fn()
                if r is not None:
                    results.append(r)
            except Exception:
                continue
        return results

    # ═══════════════════════════════════════
    #  OSCILLATORS — measure momentum
    #  (Is the price moving too fast up/down?)
    # ═══════════════════════════════════════

    def _rsi(self):
        """
        RSI (Relative Strength Index)
        ─────────────────────────────
        Measures speed of price changes on a 0-100 scale.
        - Below 30 = oversold (price fell too fast → might bounce UP)
        - Above 70 = overbought (price rose too fast → might drop DOWN)
        - The middle zone (30-70) is less informative
        """
        p = self.cfg["rsi"]
        rsi = ta.rsi(self.c, length=p["len"])
        if rsi is None or rsi.dropna().empty:
            return None
        v = rsi.iloc[-1]
        pv = rsi.iloc[-2]

        if v < p["os"]:
            s = 0.7 + (p["os"] - v) / (p["os"] * 3)
            d = f"Oversold {v:.1f} — expect bounce"
        elif v > p["ob"]:
            s = -(0.7 + (v - p["ob"]) / ((100 - p["ob"]) * 3))
            d = f"Overbought {v:.1f} — expect pullback"
        elif v < 45:
            s = 0.15 + (45 - v) / 60
            d = f"Lean bullish {v:.1f}"
        elif v > 55:
            s = -(0.15 + (v - 55) / 60)
            d = f"Lean bearish {v:.1f}"
        else:
            s = 0.05 if v > pv else -0.05
            d = f"Neutral {v:.1f}"
        return _r("RSI", f"{v:.1f}", s, p["w"], d, "oscillator")

    def _stoch(self):
        """
        Stochastic Oscillator
        ─────────────────────
        Compares closing price to its price range over N periods.
        Two lines: %K (fast) and %D (slow signal line).
        - K < 20 = oversold
        - K > 80 = overbought
        - K crossing above D = bullish
        """
        p = self.cfg["stoch"]
        st = ta.stoch(self.h, self.l, self.c,
                      k=p["k"], d=p["d"], smooth_k=p["smooth"])
        if st is None or st.dropna().empty:
            return None
        k_val = st.iloc[-1, 0]
        d_val = st.iloc[-1, 1]
        pk = st.iloc[-2, 0]

        if k_val < 20:
            s, d = 0.7 + (20 - k_val) / 100, f"Oversold K={k_val:.0f}"
        elif k_val > 80:
            s, d = -(0.7 + (k_val - 80) / 100), f"Overbought K={k_val:.0f}"
        else:
            cross = 0.3 if (pk <= st.iloc[-2, 1] and k_val > d_val) else \
                   -0.3 if (pk >= st.iloc[-2, 1] and k_val < d_val) else 0
            s, d = cross, f"K={k_val:.0f} D={d_val:.0f}"
        return _r("Stochastic", f"{k_val:.0f}/{d_val:.0f}", s, p["w"], d, "oscillator")

    def _stoch_rsi(self):
        """
        Stochastic RSI — RSI of RSI
        ────────────────────────────
        Even more sensitive than regular Stochastic.
        Good for catching early reversals but can give false signals.
        """
        p = self.cfg["stoch_rsi"]
        sr = ta.stochrsi(self.c, length=p["len"],
                         rsi_length=p["rsi_len"], k=p["k"], d=p["d"])
        if sr is None or sr.dropna().empty:
            return None
        k = sr.iloc[-1, 0] * 100 if sr.iloc[-1, 0] <= 1 else sr.iloc[-1, 0]
        if k < 20:
            s, d = 0.7, f"Oversold {k:.0f}"
        elif k > 80:
            s, d = -0.7, f"Overbought {k:.0f}"
        else:
            s, d = 0.0, f"Neutral {k:.0f}"
        return _r("Stoch RSI", f"{k:.0f}", s, p["w"], d, "oscillator")

    def _cci(self):
        """
        CCI (Commodity Channel Index)
        ──────────────────────────────
        Measures how far price has deviated from its average.
        - Below -100 = oversold
        - Above +100 = overbought
        - Below -200 / above +200 = extreme
        """
        p = self.cfg["cci"]
        cci = ta.cci(self.h, self.l, self.c, length=p["len"])
        if cci is None or cci.dropna().empty:
            return None
        v = cci.iloc[-1]
        if v < -200:
            s, d = 0.9, f"Extreme oversold {v:.0f}"
        elif v < -100:
            s, d = 0.6, f"Oversold {v:.0f}"
        elif v > 200:
            s, d = -0.9, f"Extreme overbought {v:.0f}"
        elif v > 100:
            s, d = -0.6, f"Overbought {v:.0f}"
        else:
            s = v / 250
            d = f"{'Bullish' if v > 0 else 'Bearish'} {v:.0f}"
        return _r("CCI", f"{v:.0f}", s, p["w"], d, "oscillator")

    def _williams(self):
        """
        Williams %R
        ───────────
        Similar to Stochastic but inverted (0 to -100).
        - Below -80 = oversold (bullish)
        - Above -20 = overbought (bearish)
        """
        p = self.cfg["williams"]
        wr = ta.willr(self.h, self.l, self.c, length=p["len"])
        if wr is None or wr.dropna().empty:
            return None
        v = wr.iloc[-1]
        if v < -80:
            s, d = 0.7, f"Oversold {v:.1f}"
        elif v > -20:
            s, d = -0.7, f"Overbought {v:.1f}"
        else:
            s = -(v + 50) / 50
            d = f"{'Bullish' if v < -50 else 'Bearish'} {v:.1f}"
        return _r("Williams %R", f"{v:.1f}", s, p["w"], d, "oscillator")

    def _mfi(self):
        """
        MFI (Money Flow Index) — "Volume-weighted RSI"
        ───────────────────────────────────────────────
        Like RSI but also considers volume. If price goes up
        on HIGH volume → stronger signal than low volume.
        """
        if not self._has_vol:
            return None
        p = self.cfg["mfi"]
        mfi = ta.mfi(self.h, self.l, self.c, self.v, length=p["len"])
        if mfi is None or mfi.dropna().empty:
            return None
        v = mfi.iloc[-1]
        if v < 20:
            s, d = 0.8, f"Oversold {v:.0f}"
        elif v > 80:
            s, d = -0.8, f"Overbought {v:.0f}"
        else:
            s = -(v - 50) / 60
            d = f"{'Inflow' if v < 50 else 'Outflow'} {v:.0f}"
        return _r("MFI", f"{v:.0f}", s, p["w"], d, "oscillator")

    def _uo(self):
        """
        Ultimate Oscillator — uses 3 timeframes (7, 14, 28)
        ────────────────────────────────────────────────────
        Reduces false signals by combining short/medium/long momentum.
        """
        p = self.cfg["uo"]
        uo = ta.uo(self.h, self.l, self.c,
                   fast=p["s"], medium=p["m"], slow=p["l"])
        if uo is None or uo.dropna().empty:
            return None
        v = uo.iloc[-1]
        if v < 30:
            s, d = 0.7, f"Oversold {v:.1f}"
        elif v > 70:
            s, d = -0.7, f"Overbought {v:.1f}"
        else:
            s = (v - 50) / 40
            d = f"{'Bullish' if v > 50 else 'Bearish'} {v:.1f}"
        return _r("Ultimate Osc", f"{v:.1f}", s, p["w"], d, "oscillator")

    def _roc(self):
        """
        ROC (Rate of Change)
        ────────────────────
        Simply: how much has price changed over N periods (%).
        Positive = price going up, Negative = going down.
        """
        p = self.cfg["roc"]
        roc = ta.roc(self.c, length=p["len"])
        if roc is None or roc.dropna().empty:
            return None
        v = roc.iloc[-1]
        s = np.clip(v / 10, -1, 1)
        d = f"{'Positive' if v > 0 else 'Negative'} momentum {v:.2f}%"
        return _r("ROC", f"{v:.2f}%", s, p["w"], d, "oscillator")

    def _trix(self):
        """
        TRIX — Triple Exponential Average
        ──────────────────────────────────
        Super-smooth momentum indicator. Filters out market noise.
        Positive = bullish, Negative = bearish.
        """
        p = self.cfg["trix"]
        tr = ta.trix(self.c, length=p["len"])
        if tr is None or tr.dropna().empty:
            return None
        v = tr.iloc[-1, 0]
        s = np.clip(v * 50, -1, 1)
        d = f"{'Bullish' if v > 0 else 'Bearish'} {v:.4f}"
        return _r("TRIX", f"{v:.4f}", s, p["w"], d, "oscillator")

    # ═══════════════════════════════════════
    #  TREND — which direction is the market going?
    # ═══════════════════════════════════════

    def _macd(self):
        """
        MACD (Moving Average Convergence Divergence)
        ─────────────────────────────────────────────
        The KING of trend indicators. Uses 3 components:
        - MACD line: difference between fast EMA and slow EMA
        - Signal line: EMA of the MACD line
        - Histogram: MACD minus Signal (shows momentum)

        KEY SIGNALS:
        - Histogram crosses from - to + = BULLISH CROSSOVER (buy)
        - Histogram crosses from + to - = BEARISH CROSSOVER (sell)
        """
        p = self.cfg["macd"]
        m = ta.macd(self.c, fast=p["f"], slow=p["s"], signal=p["sig"])
        if m is None or m.dropna().empty:
            return None
        macd_v = m.iloc[-1, 0]
        hist = m.iloc[-1, 1]
        prev_hist = m.iloc[-2, 1]

        if hist > 0 and prev_hist <= 0:
            s, d = 0.9, "🔥 Bullish crossover"
        elif hist < 0 and prev_hist >= 0:
            s, d = -0.9, "🔥 Bearish crossover"
        elif hist > 0:
            s = 0.4 + min(0.4, abs(hist) / (abs(macd_v) + 1e-9))
            d = f"Bullish histogram {hist:.4f}"
        elif hist < 0:
            s = -(0.4 + min(0.4, abs(hist) / (abs(macd_v) + 1e-9)))
            d = f"Bearish histogram {hist:.4f}"
        else:
            s, d = 0, "Flat"
        return _r("MACD", f"{macd_v:.4f}", s, p["w"], d, "trend")

    def _adx(self):
        """
        ADX (Average Directional Index)
        ────────────────────────────────
        Measures TREND STRENGTH (not direction).
        - ADX < 25 = weak/no trend (choppy market)
        - ADX > 25 = strong trend
        - DI+ > DI- = uptrend
        - DI- > DI+ = downtrend
        """
        p = self.cfg["adx"]
        a = ta.adx(self.h, self.l, self.c, length=p["len"])
        if a is None or a.dropna().empty:
            return None
        adx_v = a.iloc[-1, 0]
        dip = a.iloc[-1, 1]
        din = a.iloc[-1, 2]

        if adx_v < p["thresh"]:
            s, d = 0.0, f"Weak trend ADX={adx_v:.0f}"
        elif dip > din:
            s = 0.3 + min(0.6, (adx_v - p["thresh"]) / 50 + (dip - din) / 60)
            d = f"Bullish trend ADX={adx_v:.0f}"
        else:
            s = -(0.3 + min(0.6, (adx_v - p["thresh"]) / 50 + (din - dip) / 60))
            d = f"Bearish trend ADX={adx_v:.0f}"
        return _r("ADX", f"{adx_v:.0f}", s, p["w"], d, "trend")

    def _supertrend(self):
        """
        Supertrend — clean binary trend indicator
        ──────────────────────────────────────────
        Uses ATR (volatility) to create a trailing line.
        - Price above line = BULLISH (green)
        - Price below line = BEARISH (red)
        - When it FLIPS = very strong signal
        """
        p = self.cfg["supertrend"]
        st = ta.supertrend(self.h, self.l, self.c,
                           length=p["len"], multiplier=p["mult"])
        if st is None or st.dropna().empty:
            return None
        direction = st.iloc[-1, 1]
        prev_dir = st.iloc[-2, 1]

        if direction == 1 and prev_dir == -1:
            s, d = 0.95, "🔥 Bullish flip!"
        elif direction == -1 and prev_dir == 1:
            s, d = -0.95, "🔥 Bearish flip!"
        elif direction == 1:
            s, d = 0.6, "Bullish trend"
        else:
            s, d = -0.6, "Bearish trend"
        return _r("Supertrend",
                  "Bullish" if direction == 1 else "Bearish",
                  s, p["w"], d, "trend")

    def _psar(self):
        """
        Parabolic SAR — trailing stop indicator
        ────────────────────────────────────────
        Dots appear below price (bullish) or above price (bearish).
        When dots flip side = trend reversal signal.
        """
        p = self.cfg["psar"]
        ps = ta.psar(self.h, self.l, self.c,
                     af0=p["af"], af=p["af"], max_af=p["max_af"])
        if ps is None or ps.dropna(how="all").empty:
            return None

        long_col = [c for c in ps.columns if "PSARl" in c]
        short_col = [c for c in ps.columns if "PSARs" in c]
        last = ps.iloc[-1]
        price = self.c.iloc[-1]

        if long_col and pd.notna(last[long_col[0]]):
            psar_v = last[long_col[0]]
            dist = (price - psar_v) / price * 100
            s, d = 0.6, f"Bullish — SAR below ({dist:.2f}%)"
        elif short_col and pd.notna(last[short_col[0]]):
            psar_v = last[short_col[0]]
            dist = (psar_v - price) / price * 100
            s, d = -0.6, f"Bearish — SAR above ({dist:.2f}%)"
        else:
            s, d = 0, "Undetermined"
        return _r("Parabolic SAR", "▲" if s > 0 else "▼",
                  s, p["w"], d, "trend")

    def _ichimoku(self):
        """
        Ichimoku Cloud — the "one glance" system
        ─────────────────────────────────────────
        Japanese indicator with 5 lines + a "cloud" (kumo).

        Rules:
        1. Price above cloud = bullish
        2. Price below cloud = bearish
        3. Tenkan > Kijun = bullish cross
        4. Green cloud (Span A > Span B) = bullish
        """
        p = self.cfg["ichimoku"]
        try:
            ich, _ = ta.ichimoku(self.h, self.l, self.c,
                                  tenkan=p["tenkan"], kijun=p["kijun"],
                                  senkou=p["senkou"])
        except Exception:
            return None
        if ich is None or ich.dropna().empty:
            return None

        price = self.c.iloc[-1]
        tenkan = ich.iloc[-1, 0]
        kijun = ich.iloc[-1, 1]
        spa = ich.iloc[-1, 2] if ich.shape[1] > 2 else None
        spb = ich.iloc[-1, 3] if ich.shape[1] > 3 else None

        score = 0
        if tenkan > kijun:
            score += 0.25
        else:
            score -= 0.25

        if spa is not None and spb is not None:
            cloud_top = max(spa, spb)
            cloud_bot = min(spa, spb)
            if price > cloud_top:
                score += 0.5
            elif price < cloud_bot:
                score -= 0.5
            if spa > spb:
                score += 0.15
            else:
                score -= 0.15

        d = f"{'Above' if score > 0 else 'Below'} cloud"
        return _r("Ichimoku", f"{score:+.2f}", score, p["w"], d, "trend")

    def _aroon(self):
        """
        Aroon — measures how recently the highest/lowest prices occurred.
        Aroon Up high + Aroon Down low = strong uptrend.
        """
        p = self.cfg["aroon"]
        ar = ta.aroon(self.h, self.l, length=p["len"])
        if ar is None or ar.dropna().empty:
            return None
        osc_col = [c for c in ar.columns if "OSC" in c.upper()]
        v = ar[osc_col[0]].iloc[-1] if osc_col else ar.iloc[-1, 1] - ar.iloc[-1, 0]
        s = v / 100
        d = f"{'Bullish' if v > 0 else 'Bearish'} Aroon {v:.0f}"
        return _r("Aroon", f"{v:.0f}", s, p["w"], d, "trend")

    # ═══════════════════════════════════════
    #  MOVING AVERAGES — smoothed price lines
    # ═══════════════════════════════════════

    def _ema_short(self):
        """
        EMA 9/21 Cross — short-term trend detection
        ─────────────────────────────────────────────
        When fast EMA (9) crosses ABOVE slow EMA (21) = buy signal.
        When it crosses BELOW = sell signal.
        """
        p = self.cfg["ema_short"]
        fast = ta.ema(self.c, length=p["f"])
        slow = ta.ema(self.c, length=p["s"])
        if fast is None or slow is None:
            return None

        f_v, s_v = fast.iloc[-1], slow.iloc[-1]
        f_p, s_p = fast.iloc[-2], slow.iloc[-2]

        if f_p <= s_p and f_v > s_v:
            s, d = 0.9, f"Bullish cross EMA{p['f']}/{p['s']}"
        elif f_p >= s_p and f_v < s_v:
            s, d = -0.9, f"Bearish cross EMA{p['f']}/{p['s']}"
        elif f_v > s_v:
            gap = (f_v - s_v) / s_v * 100
            s, d = 0.4, f"EMA{p['f']} above ({gap:.2f}%)"
        else:
            gap = (s_v - f_v) / s_v * 100
            s, d = -0.4, f"EMA{p['f']} below ({gap:.2f}%)"
        return _r(f"EMA {p['f']}/{p['s']}", "▲" if s > 0 else "▼",
                  s, p["w"], d, "ma")

    def _ema_long(self):
        """
        EMA 50/200 — the legendary Golden Cross / Death Cross
        ──────────────────────────────────────────────────────
        Golden Cross (50 crosses above 200) = strong long-term BUY
        Death Cross  (50 crosses below 200) = strong long-term SELL

        These are the most watched signals in all of trading.
        """
        p = self.cfg["ema_long"]
        fast = ta.ema(self.c, length=p["f"])
        slow = ta.ema(self.c, length=p["s"])
        if fast is None or slow is None or fast.dropna().shape[0] < 5:
            return None

        f_v, s_v = fast.iloc[-1], slow.iloc[-1]
        f_p, s_p = fast.iloc[-2], slow.iloc[-2]

        if f_p <= s_p and f_v > s_v:
            s, d = 1.0, "🔥 GOLDEN CROSS — mega bullish"
        elif f_p >= s_p and f_v < s_v:
            s, d = -1.0, "💀 DEATH CROSS — mega bearish"
        elif f_v > s_v:
            s, d = 0.5, f"EMA{p['f']} above EMA{p['s']} (bullish structure)"
        else:
            s, d = -0.5, f"EMA{p['f']} below EMA{p['s']} (bearish structure)"
        return _r(f"EMA {p['f']}/{p['s']}", "▲" if s > 0 else "▼",
                  s, p["w"], d, "ma")

    def _sma_trend(self):
        """
        SMA Alignment — is price above or below key SMAs?
        ──────────────────────────────────────────────────
        If price is above ALL major SMAs (20, 50, 200) = strong uptrend.
        If below ALL = strong downtrend.
        """
        p = self.cfg["sma_trend"]
        smas = {}
        for per in p["periods"]:
            sv = ta.sma(self.c, length=per)
            if sv is not None and not sv.dropna().empty:
                smas[per] = sv.iloc[-1]
        if len(smas) < 2:
            return None

        price = self.c.iloc[-1]
        above = sum(1 for v in smas.values() if price > v)
        total = len(smas)
        s = (above / total - 0.5) * 2
        d = f"Price above {above}/{total} SMAs"
        return _r("SMA Trend", f"{above}/{total}", s, p["w"], d, "ma")

    def _hma(self):
        """
        Hull Moving Average — fast and smooth
        ──────────────────────────────────────
        Reduces lag compared to regular MAs. Good for catching
        trend changes early. We check slope + acceleration.
        """
        p = self.cfg["hma"]
        hma = ta.hma(self.c, length=p["len"])
        if hma is None or hma.dropna().shape[0] < 3:
            return None

        v, pv, ppv = hma.iloc[-1], hma.iloc[-2], hma.iloc[-3]
        price = self.c.iloc[-1]
        slope = v - pv
        accel = (v - pv) - (pv - ppv)

        s = 0.3 if price > v else -0.3
        if slope > 0 and accel > 0:
            s += 0.3
        elif slope < 0 and accel < 0:
            s -= 0.3

        d = f"HMA {'rising' if slope > 0 else 'falling'}, " \
            f"price {'above' if price > v else 'below'}"
        return _r("Hull MA", "▲" if slope > 0 else "▼",
                  s, p["w"], d, "ma")

    def _ma_ribbon(self):
        """
        MA Ribbon — 6 EMAs fanning out
        ───────────────────────────────
        When ALL EMAs are perfectly stacked (8 > 13 > 21 > 34 > 55 > 89)
        = perfect uptrend. Reverse = perfect downtrend.
        """
        p = self.cfg["ma_ribbon"]
        emas = {}
        for per in p["periods"]:
            e = ta.ema(self.c, length=per)
            if e is not None and not e.dropna().empty:
                emas[per] = e.iloc[-1]
        if len(emas) < 4:
            return None

        vals = list(emas.values())
        bullish = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
        bearish = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
        price = self.c.iloc[-1]
        above = sum(1 for v in vals if price > v)

        if bullish:
            s, d = 0.8, "Perfect bullish ribbon"
        elif bearish:
            s, d = -0.8, "Perfect bearish ribbon"
        else:
            s = (above / len(vals) - 0.5) * 1.4
            d = f"Price above {above}/{len(vals)} ribbon EMAs"
        return _r("MA Ribbon", f"{above}/{len(vals)}", s, p["w"], d, "ma")

    # ═══════════════════════════════════════
    #  VOLATILITY — how "wild" is the market?
    # ═══════════════════════════════════════

    def _bbands(self):
        """
        Bollinger Bands — price channels based on standard deviation
        ────────────────────────────────────────────────────────────
        %B tells us where price is within the bands:
        - %B < 0.05 = at/below lower band (oversold)
        - %B > 0.95 = at/above upper band (overbought)
        - The bands squeeze before big moves (low volatility → breakout)
        """
        p = self.cfg["bbands"]
        bb = ta.bbands(self.c, length=p["len"], std=p["std"])
        if bb is None or bb.dropna().empty:
            return None

        lower, mid, upper = bb.iloc[-1, 0], bb.iloc[-1, 1], bb.iloc[-1, 2]
        price = self.c.iloc[-1]
        pct_b = (price - lower) / (upper - lower) if upper != lower else 0.5

        if pct_b < 0.05:
            s, d = 0.8, f"At lower band (%B={pct_b:.2f})"
        elif pct_b < 0.2:
            s, d = 0.4, f"Near lower band (%B={pct_b:.2f})"
        elif pct_b > 0.95:
            s, d = -0.8, f"At upper band (%B={pct_b:.2f})"
        elif pct_b > 0.8:
            s, d = -0.4, f"Near upper band (%B={pct_b:.2f})"
        else:
            s = -(pct_b - 0.5)
            d = f"Mid-band (%B={pct_b:.2f})"
        return _r("Bollinger", f"%B={pct_b:.2f}", s, p["w"], d, "volatility")

    def _keltner(self):
        p = self.cfg["keltner"]
        kc = ta.kc(self.h, self.l, self.c,
                   length=p["len"], scalar=p["mult"])
        if kc is None or kc.dropna().empty:
            return None
        lower, mid, upper = kc.iloc[-1, 0], kc.iloc[-1, 1], kc.iloc[-1, 2]
        price = self.c.iloc[-1]

        if price < lower:
            s, d = 0.6, "Below Keltner lower"
        elif price > upper:
            s, d = -0.6, "Above Keltner upper"
        else:
            s = -((price - mid) / (upper - mid)) * 0.3 if upper != mid else 0
            d = "Inside Keltner channel"
        return _r("Keltner", "▲" if s > 0 else "▼",
                  s, p["w"], d, "volatility")

    def _donchian(self):
        p = self.cfg["donchian"]
        dc = ta.donchian(self.h, self.l,
                         lower_length=p["len"], upper_length=p["len"])
        if dc is None or dc.dropna().empty:
            return None
        lower, mid, upper = dc.iloc[-1, 0], dc.iloc[-1, 1], dc.iloc[-1, 2]
        price = self.c.iloc[-1]
        rang = upper - lower if upper != lower else 1
        pos = (price - lower) / rang

        if pos > 0.95:
            s, d = -0.6, "At Donchian high"
        elif pos < 0.05:
            s, d = 0.6, "At Donchian low"
        else:
            s = -(pos - 0.5)
            d = f"Position {pos:.0%} in channel"
        return _r("Donchian", f"{pos:.0%}", s, p["w"], d, "volatility")

    def _atr(self):
        """
        ATR (Average True Range) — measures volatility
        ───────────────────────────────────────────────
        Not directly bullish/bearish, but HIGH ATR during a move
        = stronger conviction. We also use ATR for stop-loss calc.
        """
        p = self.cfg["atr"]
        atr_s = ta.atr(self.h, self.l, self.c, length=p["len"])
        if atr_s is None or atr_s.dropna().shape[0] < 20:
            return None
        v = atr_s.iloc[-1]
        avg = atr_s.rolling(50).mean().iloc[-1]
        pct = v / self.c.iloc[-1] * 100
        chg = self.c.iloc[-1] - self.c.iloc[-5]

        if v > avg * 1.5:
            s = 0.3 if chg > 0 else -0.3
            d = f"High volatility {pct:.2f}%"
        else:
            s = 0
            d = f"Normal volatility {pct:.2f}%"
        return _r("ATR", f"{pct:.2f}%", s, p["w"], d, "volatility")

    # ═══════════════════════════════════════
    #  VOLUME — is the move backed by money?
    # ═══════════════════════════════════════

    def _obv(self):
        """
        OBV (On Balance Volume)
        ───────────────────────
        Running total: +volume on up days, -volume on down days.
        If OBV is rising but price is flat → hidden buying pressure
        (bullish divergence = great buy signal).
        """
        if not self._has_vol:
            return None
        obv = ta.obv(self.c, self.v)
        if obv is None or obv.dropna().shape[0] < 20:
            return None

        slope = obv.iloc[-1] - obv.iloc[-5]
        price_slope = self.c.iloc[-1] - self.c.iloc[-5]

        if slope > 0 and price_slope > 0:
            s, d = 0.5, "OBV confirms uptrend"
        elif slope < 0 and price_slope < 0:
            s, d = -0.5, "OBV confirms downtrend"
        elif slope > 0 and price_slope < 0:
            s, d = 0.6, "Bullish divergence"
        elif slope < 0 and price_slope > 0:
            s, d = -0.6, "Bearish divergence"
        else:
            s, d = 0, "OBV flat"
        return _r("OBV", "▲" if slope > 0 else "▼",
                  s, self.cfg["obv"]["w"], d, "volume")

    def _cmf(self):
        if not self._has_vol:
            return None
        p = self.cfg["cmf"]
        cmf = ta.cmf(self.h, self.l, self.c, self.v, length=p["len"])
        if cmf is None or cmf.dropna().empty:
            return None
        v = cmf.iloc[-1]
        s = np.clip(v * 5, -1, 1)
        d = f"{'Accumulation' if v > 0 else 'Distribution'} {v:.3f}"
        return _r("CMF", f"{v:.3f}", s, p["w"], d, "volume")

    def _vwap(self):
        if not self._has_vol:
            return None
        try:
            vwap = ta.vwap(self.h, self.l, self.c, self.v)
            if vwap is None or vwap.dropna().empty:
                return None
        except Exception:
            return None
        v = vwap.iloc[-1]
        price = self.c.iloc[-1]
        diff_pct = (price - v) / v * 100

        if diff_pct > 1:
            s, d = -0.4, f"Above VWAP (+{diff_pct:.2f}%)"
        elif diff_pct < -1:
            s, d = 0.4, f"Below VWAP ({diff_pct:.2f}%)"
        else:
            s, d = 0, f"Near VWAP ({diff_pct:+.2f}%)"
        return _r("VWAP", f"{diff_pct:+.2f}%",
                  s, self.cfg["vwap"]["w"], d, "volume")

    def _vol_analysis(self):
        if not self._has_vol:
            return None
        avg = self.v.rolling(20).mean().iloc[-1]
        cur = self.v.iloc[-1]
        ratio = cur / avg if avg > 0 else 1
        price_chg = self.c.iloc[-1] - self.c.iloc[-2]

        if ratio > 2 and price_chg > 0:
            s, d = 0.7, f"Very high bullish vol ({ratio:.1f}×)"
        elif ratio > 1.5 and price_chg > 0:
            s, d = 0.4, f"High bullish vol ({ratio:.1f}×)"
        elif ratio > 2 and price_chg < 0:
            s, d = -0.7, f"Very high bearish vol ({ratio:.1f}×)"
        elif ratio > 1.5 and price_chg < 0:
            s, d = -0.4, f"High bearish vol ({ratio:.1f}×)"
        else:
            s = 0.05 if price_chg > 0 else -0.05
            d = f"Normal volume ({ratio:.1f}×)"
        return _r("Volume", f"{ratio:.1f}×",
                  s, self.cfg["vol_analysis"]["w"], d, "volume")

    # ═══════════════════════════════════════
    #  PRICE ACTION — key levels
    # ═══════════════════════════════════════

    def _fibonacci(self):
        """
        Fibonacci Retracement
        ─────────────────────
        After a big move, price tends to "retrace" to specific %:
        23.6%, 38.2%, 50%, 61.8% (golden ratio), 78.6%

        Near 61.8% or 78.6% retracement = strong support zone.
        Near 23.6% = price barely pulled back (strong trend).
        """
        lookback = min(100, len(self.df))
        recent = self.df.tail(lookback)
        hi, lo = recent["high"].max(), recent["low"].min()
        diff = hi - lo
        if diff == 0:
            return None

        price = self.c.iloc[-1]
        pos = (hi - price) / diff

        if pos > 0.786:
            s, d = 0.7, "Near 78.6% support"
        elif pos > 0.618:
            s, d = 0.5, "Near golden ratio (61.8%)"
        elif pos > 0.5:
            s, d = 0.2, "Near 50% level"
        elif pos > 0.382:
            s, d = 0, "Between 38.2-50%"
        elif pos > 0.236:
            s, d = -0.3, "Near 23.6%"
        else:
            s, d = -0.6, "Near swing high"
        return _r("Fibonacci", f"{pos:.1%}", s,
                  self.cfg["fibonacci"]["w"], d, "price_action")

    def _pivot(self):
        if len(self.df) < 3:
            return None
        prev = self.df.iloc[-2]
        price = self.c.iloc[-1]
        pp = (prev["high"] + prev["low"] + prev["close"]) / 3
        s1 = 2 * pp - prev["high"]
        s2 = pp - (prev["high"] - prev["low"])
        r1 = 2 * pp - prev["low"]
        r2 = pp + (prev["high"] - prev["low"])

        if price < s2:
            s, d = 0.7, f"Below S2 ({s2:.4f})"
        elif price < s1:
            s, d = 0.4, f"Below S1 ({s1:.4f})"
        elif price < pp:
            s, d = 0.15, f"Below Pivot ({pp:.4f})"
        elif price < r1:
            s, d = -0.15, f"Above Pivot ({pp:.4f})"
        elif price < r2:
            s, d = -0.4, f"Above R1 ({r1:.4f})"
        else:
            s, d = -0.7, f"Above R2 ({r2:.4f})"
        return _r("Pivot Points", f"PP={pp:.4f}", s,
                  self.cfg["pivot"]["w"], d, "price_action")