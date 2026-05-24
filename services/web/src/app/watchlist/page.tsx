"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  getWatchlists,
  createWatchlist,
  deleteWatchlist,
  type Watchlist,
} from "@/lib/api";
import Link from "next/link";

export default function WatchlistPage() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    getWatchlists()
      .then(setWatchlists)
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      await createWatchlist(newName.trim().toUpperCase());
      setNewName("");
      load();
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleDelete(name: string) {
    await deleteWatchlist(name);
    load();
  }

  return (
    <div className="max-w-screen-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Watchlists</h1>
        <Badge variant="outline" className="border-zinc-700 text-zinc-400">
          {watchlists.length} lists
        </Badge>
      </div>

      <Card className="bg-zinc-900/60 border-zinc-800 p-4">
        <div className="flex items-center gap-3">
          <Input
            placeholder="New watchlist name…"
            value={newName}
            onChange={(e) => setNewName(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            className="h-9 text-sm bg-zinc-800 border-zinc-700 max-w-xs"
          />
          <button
            onClick={handleCreate}
            className="h-9 px-4 rounded text-xs font-medium bg-emerald-600 hover:bg-emerald-500 transition-colors text-black"
          >
            + Create
          </button>
        </div>
      </Card>

      {loading ? (
        <div className="text-sm text-zinc-500">Loading…</div>
      ) : watchlists.length === 0 ? (
        <div className="text-sm text-zinc-600">No watchlists yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {watchlists.map((wl) => (
            <Card
              key={wl.id}
              className="bg-zinc-900/60 border-zinc-800 p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm">{wl.name}</h3>
                <button
                  onClick={() => handleDelete(wl.name)}
                  className="text-[10px] text-zinc-600 hover:text-red-400 transition-colors"
                >
                  delete
                </button>
              </div>
              {wl.symbols.length === 0 ? (
                <p className="text-xs text-zinc-600">
                  Empty — add symbols using the + button below
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {wl.symbols.map((sym) => (
                    <Link key={sym} href={`/stocks/${sym}`}>
                      <Badge
                        variant="outline"
                        className="border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400 cursor-pointer text-[10px] font-mono"
                      >
                        {sym}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
