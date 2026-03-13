import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        return True
    except Exception:
        return False


def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
        return True
    except Exception:
        return False


def format_alert(result):
    r = result
    msg = f"{'BUY' if r['direction'] == 'BUY' else 'SELL'} -- {r['tier']} -- {r['symbol']}\n"
    msg += f"Price: {r['price']}\n"
    msg += f"Confidence: {r['confidence']:.1f}%\n"
    msg += f"Change: {r['change_pct']:+.2f}%\n"
    msg += f"Votes: {r['buy_count']} buy / {r['sell_count']} sell\n"
    msg += f"TF: {r['timeframe']}\n"
    if r.get("levels"):
        lv = r["levels"]
        if r["direction"] == "BUY":
            msg += f"TP: {lv['long_tp']}\nSL: {lv['long_sl']}\nR:R: 1:{lv['rr_ratio']}\n"
        else:
            msg += f"TP: {lv['short_tp']}\nSL: {lv['short_sl']}\nR:R: 1:{lv['rr_ratio']}\n"
    return msg


def send_alert(result):
    msg = format_alert(result)
    send_telegram(msg)
    send_discord(msg)
