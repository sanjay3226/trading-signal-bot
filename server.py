from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

app = FastAPI(title="Trading Signal Bot API")
executor = ThreadPoolExecutor(max_workers=1)

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.head("/")
async def root_head():
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok"}


def _do_analyse(symbol, market, tf, limit):
    from signal_engine import analyse_mtf
    return analyse_mtf(symbol, market, tf, limit)


def _do_scan(market, tf, limit):
    from config import CRYPTO_ASSETS, FOREX_ASSETS, STOCK_ASSETS
    from signal_engine import analyse_mtf
    assets = {
        "crypto": CRYPTO_ASSETS,
        "stocks": STOCK_ASSETS,
        "forex": FOREX_ASSETS,
    }.get(market.lower(), CRYPTO_ASSETS)
    results = []
    for sym in assets:
        try:
            r = analyse_mtf(sym, market, tf, limit, skip_mtf=True)
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
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


@app.get("/api/analyze")
async def analyze(
    symbol: str = Query(...),
    market: str = Query("crypto"),
    tf: str = Query("1h"),
    limit: int = Query(300),
):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _do_analyse, symbol, market, tf, limit)
    return result


@app.get("/api/scan")
async def scan(
    market: str = Query("crypto"),
    tf: str = Query("1h"),
    limit: int = Query(200),
):
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, _do_scan, market, tf, limit)
    return {"results": results, "total": len(results)}


@app.get("/api/trending")
async def trending():
    def _get():
        from data_fetcher import fetch_trending
        return fetch_trending()
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(executor, _get)
    return {"trending": data}


@app.post("/api/alert")
async def alert_endpoint(
    symbol: str = Query(...),
    market: str = Query("crypto"),
    tf: str = Query("1h"),
):
    def _send():
        from signal_engine import analyse_mtf
        from alerts import send_alert
        result = analyse_mtf(symbol, market, tf, 300)
        if "error" not in result:
            send_alert(result)
        return result
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _send)
    return {"status": "sent", "symbol": symbol}


@app.get("/api/assets")
async def get_assets(market: str = Query("crypto")):
    from config import CRYPTO_ASSETS, FOREX_ASSETS, STOCK_ASSETS
    assets = {
        "crypto": CRYPTO_ASSETS,
        "stocks": STOCK_ASSETS,
        "forex": FOREX_ASSETS,
    }.get(market.lower(), CRYPTO_ASSETS)
    return {"assets": assets}
