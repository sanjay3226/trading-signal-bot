import numpy as np
import pandas as pd
import ta as ta_lib
from config import INDICATOR_CFG


def _r(name, value, signal, weight, desc, category="oscillator"):
    return {
        "name": name,
        "value": str(value),
        "signal": float(np.clip(signal, -1, 1)),
        "weight": weight,
        "desc": desc,
        "category": category,
    }


class IndicatorEngine:
    def __init__(self, df, cfg=None):
        self.df = df.copy()
        self.c = df["close"]
        self.h = df["high"]
        self.l = df["low"]
        self.o = df["open"]
        self.v = df["volume"]
        self.cfg = cfg or INDICATOR_CFG
        self._has_vol = self.v.sum() > 0

    def run_all(self):
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

    def _ema(self, series, length):
        return series.ewm(span=length, adjust=False).mean()

    def _sma(self, series, length):
        return series.rolling(window=length).mean()

    def _rsi(self):
        p = self.cfg["rsi"]
        rsi = ta_lib.momentum.RSIIndicator(self.c, window=p["len"]).rsi()
        if rsi.dropna().empty:
            return None
        v = rsi.iloc[-1]
        pv = rsi.iloc[-2]
        if v < p["os"]:
            s = 0.7 + (p["os"] - v) / (p["os"] * 3)
            d = f"Oversold {v:.1f}"
        elif v > p["ob"]:
            s = -(0.7 + (v - p["ob"]) / ((100 - p["ob"]) * 3))
            d = f"Overbought {v:.1f}"
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
        p = self.cfg["stoch"]
        stoch = ta_lib.momentum.StochasticOscillator(self.h, self.l, self.c, window=p["k"], smooth_window=p["d"])
        k_series = stoch.stoch()
        d_series = stoch.stoch_signal()
        if k_series.dropna().empty:
            return None
        k_val = k_series.iloc[-1]
        d_val = d_series.iloc[-1]
        pk = k_series.iloc[-2]
        if k_val < 20:
            s, d = 0.7 + (20 - k_val) / 100, f"Oversold K={k_val:.0f}"
        elif k_val > 80:
            s, d = -(0.7 + (k_val - 80) / 100), f"Overbought K={k_val:.0f}"
        else:
            cross = 0.3 if (pk <= d_series.iloc[-2] and k_val > d_val) else -0.3 if (pk >= d_series.iloc[-2] and k_val < d_val) else 0
            s, d = cross, f"K={k_val:.0f} D={d_val:.0f}"
        return _r("Stochastic", f"{k_val:.0f}/{d_val:.0f}", s, p["w"], d, "oscillator")

    def _stoch_rsi(self):
        p = self.cfg["stoch_rsi"]
        rsi = ta_lib.momentum.RSIIndicator(self.c, window=p["rsi_len"]).rsi()
        if rsi.dropna().shape[0] < p["len"] + 5:
            return None
        stoch = ta_lib.momentum.StochasticOscillator(rsi, rsi, rsi, window=p["len"], smooth_window=p["k"])
        k = stoch.stoch().iloc[-1]
        if np.isnan(k):
            return None
        if k < 20:
            s, d = 0.7, f"Oversold {k:.0f}"
        elif k > 80:
            s, d = -0.7, f"Overbought {k:.0f}"
        else:
            s, d = 0.0, f"Neutral {k:.0f}"
        return _r("Stoch RSI", f"{k:.0f}", s, p["w"], d, "oscillator")

    def _cci(self):
        p = self.cfg["cci"]
        cci = ta_lib.trend.CCIIndicator(self.h, self.l, self.c, window=p["len"]).cci()
        if cci.dropna().empty:
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
        p = self.cfg["williams"]
        wr = ta_lib.momentum.WilliamsRIndicator(self.h, self.l, self.c, lbp=p["len"]).williams_r()
        if wr.dropna().empty:
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
        if not self._has_vol:
            return None
        p = self.cfg["mfi"]
        mfi = ta_lib.volume.MFIIndicator(self.h, self.l, self.c, self.v, window=p["len"]).money_flow_index()
        if mfi.dropna().empty:
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
        p = self.cfg["uo"]
        uo = ta_lib.momentum.UltimateOscillator(self.h, self.l, self.c, window1=p["s"], window2=p["m"], window3=p["l"]).ultimate_oscillator()
        if uo.dropna().empty:
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
        p = self.cfg["roc"]
        roc = ta_lib.momentum.ROCIndicator(self.c, window=p["len"]).roc()
        if roc.dropna().empty:
            return None
        v = roc.iloc[-1]
        s = np.clip(v / 10, -1, 1)
        d = f"{'Positive' if v > 0 else 'Negative'} momentum {v:.2f}%"
        return _r("ROC", f"{v:.2f}%", s, p["w"], d, "oscillator")

    def _trix(self):
        p = self.cfg["trix"]
        trix = ta_lib.trend.TRIXIndicator(self.c, window=p["len"]).trix()
        if trix.dropna().empty:
            return None
        v = trix.iloc[-1]
        s = np.clip(v * 50, -1, 1)
        d = f"{'Bullish' if v > 0 else 'Bearish'} {v:.4f}"
        return _r("TRIX", f"{v:.4f}", s, p["w"], d, "oscillator")

    def _macd(self):
        p = self.cfg["macd"]
        macd_ind = ta_lib.trend.MACD(self.c, window_fast=p["f"], window_slow=p["s"], window_sign=p["sig"])
        macd_line = macd_ind.macd()
        hist = macd_ind.macd_diff()
        if hist.dropna().empty:
            return None
        macd_v = macd_line.iloc[-1]
        h = hist.iloc[-1]
        ph = hist.iloc[-2]
        if h > 0 and ph <= 0:
            s, d = 0.9, "Bullish crossover"
        elif h < 0 and ph >= 0:
            s, d = -0.9, "Bearish crossover"
        elif h > 0:
            s = 0.4 + min(0.4, abs(h) / (abs(macd_v) + 1e-9))
            d = f"Bullish histogram {h:.4f}"
        elif h < 0:
            s = -(0.4 + min(0.4, abs(h) / (abs(macd_v) + 1e-9)))
            d = f"Bearish histogram {h:.4f}"
        else:
            s, d = 0, "Flat"
        return _r("MACD", f"{macd_v:.4f}", s, p["w"], d, "trend")

    def _adx(self):
        p = self.cfg["adx"]
        adx_ind = ta_lib.trend.ADXIndicator(self.h, self.l, self.c, window=p["len"])
        adx_v = adx_ind.adx().iloc[-1]
        dip = adx_ind.adx_pos().iloc[-1]
        din = adx_ind.adx_neg().iloc[-1]
        if np.isnan(adx_v):
            return None
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
        p = self.cfg["supertrend"]
        atr = ta_lib.volatility.AverageTrueRange(self.h, self.l, self.c, window=p["len"]).average_true_range()
        if atr.dropna().empty:
            return None
        hl2 = (self.h + self.l) / 2
        upper = hl2 + p["mult"] * atr
        lower = hl2 - p["mult"] * atr
        price = self.c.iloc[-1]
        prev_price = self.c.iloc[-2]
        if price > upper.iloc[-1]:
            s, d = 0.6, "Bullish (above upper band)"
        elif price < lower.iloc[-1]:
            s, d = -0.6, "Bearish (below lower band)"
        elif price > prev_price:
            s, d = 0.3, "Leaning bullish"
        else:
            s, d = -0.3, "Leaning bearish"
        return _r("Supertrend", "▲" if s > 0 else "▼", s, p["w"], d, "trend")

    def _psar(self):
        p = self.cfg["psar"]
        psar = ta_lib.trend.PSARIndicator(self.h, self.l, self.c, step=p["af"], max_step=p["max_af"])
        psar_up = psar.psar_up()
        psar_down = psar.psar_down()
        price = self.c.iloc[-1]
        last_up = psar_up.iloc[-1]
        last_down = psar_down.iloc[-1]
        if not np.isnan(last_up):
            dist = (price - last_up) / price * 100
            s, d = 0.6, f"Bullish SAR below ({dist:.2f}%)"
        elif not np.isnan(last_down):
            dist = (last_down - price) / price * 100
            s, d = -0.6, f"Bearish SAR above ({dist:.2f}%)"
        else:
            s, d = 0, "Undetermined"
        return _r("Parabolic SAR", "▲" if s > 0 else "▼", s, p["w"], d, "trend")

    def _ichimoku(self):
        p = self.cfg["ichimoku"]
        ich = ta_lib.trend.IchimokuIndicator(self.h, self.l, window1=p["tenkan"], window2=p["kijun"], window3=p["senkou"])
        tenkan = ich.ichimoku_conversion_line().iloc[-1]
        kijun = ich.ichimoku_base_line().iloc[-1]
        spa = ich.ichimoku_a().iloc[-1]
        spb = ich.ichimoku_b().iloc[-1]
        price = self.c.iloc[-1]
        if any(np.isnan(x) for x in [tenkan, kijun, spa, spb]):
            return None
        score = 0
        if tenkan > kijun:
            score += 0.25
        else:
            score -= 0.25
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
        p = self.cfg["aroon"]
        aroon = ta_lib.trend.AroonIndicator(self.h, self.l, window=p["len"])
        up = aroon.aroon_up().iloc[-1]
        down = aroon.aroon_down().iloc[-1]
        if np.isnan(up) or np.isnan(down):
            return None
        v = up - down
        s = v / 100
        d = f"{'Bullish' if v > 0 else 'Bearish'} Aroon {v:.0f}"
        return _r("Aroon", f"{v:.0f}", s, p["w"], d, "trend")

    def _ema_short(self):
        p = self.cfg["ema_short"]
        fast = self._ema(self.c, p["f"])
        slow = self._ema(self.c, p["s"])
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
        return _r(f"EMA {p['f']}/{p['s']}", "▲" if s > 0 else "▼", s, p["w"], d, "ma")

    def _ema_long(self):
        p = self.cfg["ema_long"]
        fast = self._ema(self.c, p["f"])
        slow = self._ema(self.c, p["s"])
        if fast.dropna().shape[0] < 5 or slow.dropna().shape[0] < 5:
            return None
        f_v, s_v = fast.iloc[-1], slow.iloc[-1]
        f_p, s_p = fast.iloc[-2], slow.iloc[-2]
        if f_p <= s_p and f_v > s_v:
            s, d = 1.0, "GOLDEN CROSS"
        elif f_p >= s_p and f_v < s_v:
            s, d = -1.0, "DEATH CROSS"
        elif f_v > s_v:
            s, d = 0.5, f"EMA{p['f']} above EMA{p['s']}"
        else:
            s, d = -0.5, f"EMA{p['f']} below EMA{p['s']}"
        return _r(f"EMA {p['f']}/{p['s']}", "▲" if s > 0 else "▼", s, p["w"], d, "ma")

    def _sma_trend(self):
        p = self.cfg["sma_trend"]
        smas = {}
        for per in p["periods"]:
            sv = self._sma(self.c, per)
            if not sv.dropna().empty:
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
        p = self.cfg["hma"]
        n = p["len"]
        half_ema = self._ema(self.c, max(n // 2, 1))
        full_ema = self._ema(self.c, n)
        diff = 2 * half_ema - full_ema
        hma = self._ema(diff, max(int(np.sqrt(n)), 1))
        if hma.dropna().shape[0] < 3:
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
        d = f"HMA {'rising' if slope > 0 else 'falling'}"
        return _r("Hull MA", "▲" if slope > 0 else "▼", s, p["w"], d, "ma")

    def _ma_ribbon(self):
        p = self.cfg["ma_ribbon"]
        emas = {}
        for per in p["periods"]:
            e = self._ema(self.c, per)
            if not e.dropna().empty:
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

    def _bbands(self):
        p = self.cfg["bbands"]
        bb = ta_lib.volatility.BollingerBands(self.c, window=p["len"], window_dev=p["std"])
        lower = bb.bollinger_lband().iloc[-1]
        upper = bb.bollinger_hband().iloc[-1]
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
        kc = ta_lib.volatility.KeltnerChannel(self.h, self.l, self.c, window=p["len"], window_atr=p["len"], multiplier=p["mult"])
        lower = kc.keltner_channel_lband().iloc[-1]
        mid = kc.keltner_channel_mband().iloc[-1]
        upper = kc.keltner_channel_hband().iloc[-1]
        price = self.c.iloc[-1]
        if price < lower:
            s, d = 0.6, "Below Keltner lower"
        elif price > upper:
            s, d = -0.6, "Above Keltner upper"
        else:
            s = -((price - mid) / (upper - mid)) * 0.3 if upper != mid else 0
            d = "Inside Keltner channel"
        return _r("Keltner", "▲" if s > 0 else "▼", s, p["w"], d, "volatility")

    def _donchian(self):
        p = self.cfg["donchian"]
        dc = ta_lib.volatility.DonchianChannel(self.h, self.l, self.c, window=p["len"])
        lower = dc.donchian_channel_lband().iloc[-1]
        upper = dc.donchian_channel_hband().iloc[-1]
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
        p = self.cfg["atr"]
        atr_s = ta_lib.volatility.AverageTrueRange(self.h, self.l, self.c, window=p["len"]).average_true_range()
        if atr_s.dropna().shape[0] < 20:
            return None
        v = atr_s.iloc[-1]
        avg = atr_s.rolling(50).mean().iloc[-1]
        pct = v / self.c.iloc[-1] * 100
        chg = self.c.iloc[-1] - self.c.iloc[-5] if len(self.c) > 5 else 0
        if v > avg * 1.5:
            s = 0.3 if chg > 0 else -0.3
            d = f"High volatility {pct:.2f}%"
        else:
            s = 0
            d = f"Normal volatility {pct:.2f}%"
        return _r("ATR", f"{pct:.2f}%", s, p["w"], d, "volatility")

    def _obv(self):
        if not self._has_vol:
            return None
        obv = ta_lib.volume.OnBalanceVolumeIndicator(self.c, self.v).on_balance_volume()
        if obv.dropna().shape[0] < 20:
            return None
        slope = obv.iloc[-1] - obv.iloc[-5] if len(obv) > 5 else 0
        price_slope = self.c.iloc[-1] - self.c.iloc[-5] if len(self.c) > 5 else 0
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
        return _r("OBV", "▲" if slope > 0 else "▼", s, self.cfg["obv"]["w"], d, "volume")

    def _cmf(self):
        if not self._has_vol:
            return None
        p = self.cfg["cmf"]
        cmf = ta_lib.volume.ChaikinMoneyFlowIndicator(self.h, self.l, self.c, self.v, window=p["len"]).chaikin_money_flow()
        if cmf.dropna().empty:
            return None
        v = cmf.iloc[-1]
        s = np.clip(v * 5, -1, 1)
        d = f"{'Accumulation' if v > 0 else 'Distribution'} {v:.3f}"
        return _r("CMF", f"{v:.3f}", s, p["w"], d, "volume")

    def _vwap(self):
        if not self._has_vol:
            return None
        try:
            vwap = ta_lib.volume.VolumeWeightedAveragePrice(self.h, self.l, self.c, self.v).volume_weighted_average_price()
            if vwap.dropna().empty:
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
        return _r("VWAP", f"{diff_pct:+.2f}%", s, self.cfg["vwap"]["w"], d, "volume")

    def _vol_analysis(self):
        if not self._has_vol:
            return None
        avg = self.v.rolling(20).mean().iloc[-1]
        cur = self.v.iloc[-1]
        ratio = cur / avg if avg > 0 else 1
        price_chg = self.c.iloc[-1] - self.c.iloc[-2]
        if ratio > 2 and price_chg > 0:
            s, d = 0.7, f"Very high bullish vol ({ratio:.1f}x)"
        elif ratio > 1.5 and price_chg > 0:
            s, d = 0.4, f"High bullish vol ({ratio:.1f}x)"
        elif ratio > 2 and price_chg < 0:
            s, d = -0.7, f"Very high bearish vol ({ratio:.1f}x)"
        elif ratio > 1.5 and price_chg < 0:
            s, d = -0.4, f"High bearish vol ({ratio:.1f}x)"
        else:
            s = 0.05 if price_chg > 0 else -0.05
            d = f"Normal volume ({ratio:.1f}x)"
        return _r("Volume", f"{ratio:.1f}x", s, self.cfg["vol_analysis"]["w"], d, "volume")

    def _fibonacci(self):
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
        return _r("Fibonacci", f"{pos:.1%}", s, self.cfg["fibonacci"]["w"], d, "price_action")

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
            s, d = 0.7, "Below S2"
        elif price < s1:
            s, d = 0.4, "Below S1"
        elif price < pp:
            s, d = 0.15, "Below Pivot"
        elif price < r1:
            s, d = -0.15, "Above Pivot"
        elif price < r2:
            s, d = -0.4, "Above R1"
        else:
            s, d = -0.7, "Above R2"
        return _r("Pivot Points", f"PP={pp:.4f}", s, self.cfg["pivot"]["w"], d, "price_action")
