from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stocks, market, screener, watchlist

app = FastAPI(
    title="Pinaka Screening API",
    description="Stock screening and analysis API for NSE securities",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(screener.router)
app.include_router(watchlist.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
