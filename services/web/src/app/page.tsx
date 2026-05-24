"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getMarketOverview,
  searchSymbols,
  type MarketOverview,
  type StockRow,
} from "@/lib/api";
import Link from "next/link";

export default function DashboardPage() {
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [symbolSearch, setSymbolSearch] = useState("");
  const [searchResults, setSearchResults] = useState<{ symbol: string }[]>([]);

  useEffect(() => {
    getMarketOverview().then(setMarket).catch(console.error);
  }, []);

  useEffect(() => {
    if (symbolSearch.length < 1) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchSymbols(symbolSearch).then(setSearchResults).catch(console.error);
    }, 200);
    return () => clearTimeout(timer);
  }, [symbolSearch]);

  return (
    <div className="max-w-screen-2xl mx-auto p-6 space-y-6">
      {/* Header / Search */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search symbol…"
            value={symbolSearch}
            onChange={(e) => setSymbolSearch(e.target.value.toUpperCase())}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
          />
          {searchResults.length > 0 && (
            <div className="absolute top-full mt-1 w-full bg-zinc-900 border border-zinc-700 rounded shadow-xl z-10">
              {searchResults.map((s) => (
                <Link
                  key={s.symbol}
                  href={`/stocks/${s.symbol}`}
                  className="block px-3 py-2 text-sm hover:bg-zinc-800 transition-colors"
                >
                  {s.symbol}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Market Date */}
      <div className="text-sm text-zinc-500">
        Trade Date:{" "}
        <span className="text-zinc-300 font-mono">
          {market?.trade_date ?? "—"}
        </span>
      </div>

      {/* Three-panel grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MarketPanel title="Top Gainers" rows={market?.gainers ?? []} up />
        <MarketPanel title="Top Losers" rows={market?.losers ?? []} up={false} />
        <MarketPanel title="Most Active" rows={market?.most_active ?? []} volume />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Advancers"
          value={market?.gainers.length ?? 0}
          color="text-emerald-400"
        />
        <StatCard
          label="Decliners"
          value={market?.losers.length ?? 0}
          color="text-red-400"
        />
        <StatCard
          label="Total Active"
          value={market?.most_active.length ?? 0}
          color="text-blue-400"
        />
        <StatCard
          label="Latest Close"
          value={market?.gainers?.[0]?.close ?? "—"}
          color="text-zinc-100"
        />
      </div>
    </div>
  );
}

function MarketPanel({
  title,
  rows,
  up,
  volume,
}: {
  title: string;
  rows: StockRow[];
  up?: boolean;
  volume?: boolean;
}) {
  return (
    <Card className="bg-zinc-900/60 border-zinc-800 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
        {title}
      </h3>
      <div className="space-y-1.5">
        {rows.slice(0, 8).map((r) => {
          const chg = r.open && r.close ? ((r.close - r.open) / r.open) * 100 : 0;
          return (
            <Link
              key={r.symbol}
              href={`/stocks/${r.symbol}`}
              className="flex items-center justify-between text-sm py-1 px-1.5 rounded hover:bg-zinc-800/50 transition-colors group"
            >
              <span className="font-mono text-xs text-zinc-300 group-hover:text-emerald-400">
                {r.symbol}
              </span>
              <div className="flex items-center gap-3 font-mono text-xs">
                {volume ? (
                  <span className="text-zinc-400">
                    {(r.totaltradedquantity ?? 0) > 1_000_000
                      ? `${((r.totaltradedquantity ?? 0) / 1_000_000).toFixed(1)}M`
                      : `${((r.totaltradedquantity ?? 0) / 1_000).toFixed(0)}K`}
                  </span>
                ) : null}
                <span className="text-zinc-100">{r.close?.toFixed(2)}</span>
                <span
                  className={`${
                    chg >= 0 ? "text-emerald-400" : "text-red-400"
                  } min-w-[4rem] text-right`}
                >
                  {chg >= 0 ? "+" : ""}
                  {chg.toFixed(2)}%
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <Card className="bg-zinc-900/60 border-zinc-800 p-4">
      <div className="text-xs text-zinc-500 uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-bold font-mono mt-1 ${color}`}>{value}</div>
    </Card>
  );
}
