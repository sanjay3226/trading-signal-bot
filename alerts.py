"""
╔══════════════════════════════════════════════════════════╗
║  ALERTS — Telegram & Discord notifications               ║
╚══════════════════════════════════════════════════════════╝

SETUP:
──────
1. TELEGRAM:
   - Message @BotFather on Telegram → /newbot → get TOKEN
   - Get your chat ID from @userinfobot
   - Set env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

2. DISCORD:
   - Go to channel settings → Integrations → Webhooks
   - Create webhook → copy URL
   - Set env var: DISCORD_WEBHOOK_URL
"""

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DISCORD_WEBHOOK_URL


def send_telegram(message: str) -> bool:
    """Send alert via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        return True
    except Exception:
        return False


def send_discord(message: str) -> bool:
    """Send alert via Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={
            "content": message,
        }, timeout=10)
        return True
    except Exception:
        return False


def format_alert(result: dict) -> str:
    """Format analysis result into a nice alert message."""
    r = result
    msg = (
        f"{'🟢' if r['direction'] == 'BUY' else '🔴'} "
        f"<b>{r['tier']}</b> — {r['symbol']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Price: {r['price']:,.6g}\n"
        f"📊 Confidence: {r['confidence']:.1f}%\n"
        f"📈 Change: {r['change_pct']:+.2f}%\n"
        f"🗳 Votes: {r['buy_count']} buy / {r['sell_count']} sell\n"
        f"⏰ TF: {r['timeframe']}\n"
    )
    if r.get("levels"):
        lv = r["levels"]
        if r["direction"] == "BUY":
            msg += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎯 TP: {lv['long_tp']:,.6g}\n"
                f"🛑 SL: {lv['long_sl']:,.6g}\n"
                f"⚖️ R:R = 1:{lv['rr_ratio']}\n"
            )
        else:
            msg += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎯 TP: {lv['short_tp']:,.6g}\n"
                f"🛑 SL: {lv['short_sl']:,.6g}\n"
                f"⚖️ R:R = 1:{lv['rr_ratio']}\n"
            )

    htf = r.get("htf_results", [])
    if htf:
        msg += "━━━━━━━━━━━━━━━━━━\n📐 MTF:\n"
        for h in htf:
            msg += f"  {h['timeframe']}: {h['emoji']} {h['tier']} ({h['confidence']:.0f}%)\n"

    return msg


def send_alert(result: dict):
    """Send formatted alert to all configured channels."""
    msg = format_alert(result)
    send_telegram(msg)
    send_discord(msg)