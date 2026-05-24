from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

_watchlists: dict[str, list[str]] = {}


class WatchlistCreate(BaseModel):
    name: str
    symbols: list[str] = []


class WatchlistUpdate(BaseModel):
    symbols: list[str]


@router.get("")
def list_watchlists() -> list[dict[str, Any]]:
    return [
        {"id": wid, "name": name, "symbols": syms}
        for wid, (name, syms) in enumerate(_watchlists.items())
    ]


@router.post("")
def create_watchlist(body: WatchlistCreate) -> dict[str, Any]:
    if body.name in _watchlists:
        raise HTTPException(409, f"Watchlist '{body.name}' already exists")
    _watchlists[body.name] = body.symbols
    wid = list(_watchlists.keys()).index(body.name)
    return {"id": wid, "name": body.name, "symbols": body.symbols}


@router.get("/{watchlist_name}")
def get_watchlist(watchlist_name: str) -> dict[str, Any]:
    if watchlist_name not in _watchlists:
        raise HTTPException(404, f"Watchlist '{watchlist_name}' not found")
    wid = list(_watchlists.keys()).index(watchlist_name)
    return {"id": wid, "name": watchlist_name, "symbols": _watchlists[watchlist_name]}


@router.put("/{watchlist_name}")
def update_watchlist(watchlist_name: str, body: WatchlistUpdate) -> dict[str, Any]:
    if watchlist_name not in _watchlists:
        raise HTTPException(404, f"Watchlist '{watchlist_name}' not found")
    _watchlists[watchlist_name] = body.symbols
    wid = list(_watchlists.keys()).index(watchlist_name)
    return {"id": wid, "name": watchlist_name, "symbols": body.symbols}


@router.delete("/{watchlist_name}")
def delete_watchlist(watchlist_name: str) -> dict[str, str]:
    if watchlist_name not in _watchlists:
        raise HTTPException(404, f"Watchlist '{watchlist_name}' not found")
    del _watchlists[watchlist_name]
    return {"status": "deleted"}
