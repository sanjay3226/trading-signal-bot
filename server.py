"""
╔══════════════════════════════════════════════════════════╗
║  FASTAPI SERVER — API endpoints for the frontend         ║
╚══════════════════════════════════════════════════════════╝

RUN: uvicorn server:app --reload --port 8000

ENDPOINTS:
──────────
GET  /api/analyze?symbol=BTC/USDT&market=crypto&tf=1h
GET  /api/scan?market=crypto&tf=1h
GET  /api/trending
POST /api/alert   (send signal to Telegram/Discord)
"""

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import CRYPTO_ASSETS, FOREX_ASSETS, STOCK_ASSETS
from signal_engine import analyse_mtf
from data_fetcher import fetch_trending
from alerts import send_alert

app = FastAPI(title="Trading Signal Bot API")
executor = ThreadPoolExecutor(max_workers=8)

# Serve the frontend files from /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/api/analyze")
async def analyze(
    symbol: str = Query(..., description="e.g. BTC/USDT"),
    market: str = Query("crypto"),
    tf: str = Query("1h"),
    limit: int = Query(500),
):
    """
    Analyse a single asset with full MTF confluence.
    This is the MAIN endpoint the frontend calls.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        analyse_mtf, symbol, market, tf, limit
    )
    return result


@app.get("/api/scan")
async def scan(
    market: str = Query("crypto"),
    tf: str = Query("1h"),
    limit: int = Query(300),
):
    """Scan all assets in a market and return ranked results."""
    assets = {
        "crypto": CRYPTO_ASSETS,
        "stocks": STOCK_ASSETS,
        "forex": FOREX_ASSETS,
    }.get(market.lower(), CRYPTO_ASSETS)

    loop = asyncio.get_event_loop()
    results = []

    for sym in assets:
        try:
            r = await loop.run_in_executor(
                executor,
                analyse_mtf, sym, market, tf, limit
            )
            if "error" not in r:
                results.append({
                    "symbol": r["symbol"],
                    "price": r["price"],
                    "change_pct": r["change_pct"],
                    "direction": r["direction"],
                    "confidence": r["confidence"],
                    "tier": r["tier"],
                    "emoji": r["emoji"],
                    "color": r["color"],
                    "buy_count": r["buy_count"],
                    "sell_count": r["sell_count"],
                    "neutral_count": r["neutral_count"],
                    "total_signals": r.get("total_signals", 0),
                    "htf_results": r.get("htf_results", []),
                })
        except Exception:
            continue

    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return {"results": results, "total": len(results)}


@app.get("/api/trending")
async def trending():
    """Get CoinGecko trending coins."""
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(executor, fetch_trending)
    return {"trending": data}


@app.post("/api/alert")
async def alert_endpoint(
    symbol: str = Query(...),
    market: str = Query("crypto"),
    tf: str = Query("1h"),
):
    """Analyse + send alert to Telegram/Discord."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        analyse_mtf, symbol, market, tf, 500
    )
    if "error" not in result:
        await loop.run_in_executor(executor, send_alert, result)
    return {"status": "sent", "symbol": symbol}


@app.get("/api/assets")
async def get_assets(market: str = Query("crypto")):
    """Return the watchlist for a market."""
    assets = {
        "crypto": CRYPTO_ASSETS,
        "stocks": STOCK_ASSETS,
        "forex": FOREX_ASSETS,
    }.get(market.lower(), CRYPTO_ASSETS)
    return {"assets": assets}