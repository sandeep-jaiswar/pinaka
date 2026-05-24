"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getMarketIndices,
  getMarketOverview,
  type IndexConstituent,
  type MarketOverview,
} from "@/lib/api";
import Link from "next/link";

export default function MarketPage() {
  const [indices, setIndices] = useState<IndexConstituent[]>([]);
  const [market, setMarket] = useState<MarketOverview | null>(null);

  useEffect(() => {
    getMarketIndices().then(setIndices).catch(console.error);
    getMarketOverview().then(setMarket).catch(console.error);
  }, []);

  const indexGroups = indices.reduce<Record<string, IndexConstituent[]>>(
    (acc, c) => {
      const name = c.index_name ?? "Other";
      if (!acc[name]) acc[name] = [];
      acc[name].push(c);
      return acc;
    },
    {}
  );

  return (
    <div className="max-w-screen-2xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-bold">Market Overview</h1>

      {/* Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900/60 border-zinc-800 p-3">
          <div className="text-[10px] uppercase text-zinc-500">Advancers</div>
          <div className="text-lg font-bold text-emerald-400 font-mono">
            {market?.gainers.length ?? "—"}
          </div>
        </Card>
        <Card className="bg-zinc-900/60 border-zinc-800 p-3">
          <div className="text-[10px] uppercase text-zinc-500">Decliners</div>
          <div className="text-lg font-bold text-red-400 font-mono">
            {market?.losers.length ?? "—"}
          </div>
        </Card>
        <Card className="bg-zinc-900/60 border-zinc-800 p-3">
          <div className="text-[10px] uppercase text-zinc-500">Most Active</div>
          <div className="text-lg font-bold text-blue-400 font-mono">
            {market?.most_active.length ?? "—"}
          </div>
        </Card>
        <Card className="bg-zinc-900/60 border-zinc-800 p-3">
          <div className="text-[10px] uppercase text-zinc-500">Trade Date</div>
          <div className="text-lg font-bold text-zinc-200 font-mono text-sm">
            {market?.trade_date ?? "—"}
          </div>
        </Card>
      </div>

      <Tabs defaultValue="indices" className="space-y-4">
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger
            value="indices"
            className="text-xs data-[state=active]:bg-zinc-800"
          >
            Indices
          </TabsTrigger>
          <TabsTrigger
            value="fo-oi"
            className="text-xs data-[state=active]:bg-zinc-800"
          >
            F&O / OI
          </TabsTrigger>
          <TabsTrigger
            value="gainers-losers"
            className="text-xs data-[state=active]:bg-zinc-800"
          >
            Gainers &amp; Losers
          </TabsTrigger>
        </TabsList>

        <TabsContent value="indices" className="space-y-4">
          {Object.entries(indexGroups).map(([indexName, members]) => (
            <Card
              key={indexName}
              className="bg-zinc-900/60 border-zinc-800 p-4"
            >
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
                {indexName}
              </h3>
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-transparent">
                    <TableHead className="text-[10px] text-zinc-600 font-mono">
                      Symbol
                    </TableHead>
                    <TableHead className="text-[10px] text-zinc-600 font-mono">
                      Company
                    </TableHead>
                    <TableHead className="text-[10px] text-zinc-600 font-mono text-right">
                      Weight %
                    </TableHead>
                    <TableHead className="text-[10px] text-zinc-600 font-mono">
                      Industry
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members
                    .sort(
                      (a, b) =>
                        (b.weight_percentage ?? 0) -
                        (a.weight_percentage ?? 0)
                    )
                    .map((m) => (
                      <TableRow
                        key={m.symbol}
                        className="border-zinc-800/50 hover:bg-zinc-800/30"
                      >
                        <TableCell className="font-mono text-xs">
                          <Link
                            href={`/stocks/${m.symbol}`}
                            className="text-emerald-400 hover:text-emerald-300"
                          >
                            {m.symbol}
                          </Link>
                        </TableCell>
                        <TableCell className="text-xs text-zinc-400">
                          {m.company_name ?? "—"}
                        </TableCell>
                        <TableCell className="text-xs font-mono text-right text-zinc-300">
                          {m.weight_percentage != null
                            ? `${m.weight_percentage.toFixed(2)}%`
                            : "—"}
                        </TableCell>
                        <TableCell className="text-xs text-zinc-500">
                          {m.industry ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="gainers-losers">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-zinc-900/60 border-zinc-800 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3">
                Top Gainers
              </h3>
              <GainerLoserTable rows={market?.gainers ?? []} up />
            </Card>
            <Card className="bg-zinc-900/60 border-zinc-800 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-3">
                Top Losers
              </h3>
              <GainerLoserTable rows={market?.losers ?? []} up={false} />
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function GainerLoserTable({
  rows,
  up,
}: {
  rows: { symbol: string; open: number | null; close: number | null }[];
  up: boolean;
}) {
  return (
    <div className="space-y-1">
      {rows.slice(0, 15).map((r) => {
        const chg =
          r.open && r.close ? ((r.close - r.open) / r.open) * 100 : 0;
        return (
          <Link
            key={r.symbol}
            href={`/stocks/${r.symbol}`}
            className="flex items-center justify-between text-xs py-1 px-1.5 rounded hover:bg-zinc-800/50 transition-colors group"
          >
            <span className="font-mono text-zinc-300 group-hover:text-emerald-400">
              {r.symbol}
            </span>
            <div className="flex items-center gap-3 font-mono">
              <span className="text-zinc-100">{r.close?.toFixed(2)}</span>
              <span className={up ? "text-emerald-400" : "text-red-400"}>
                {chg >= 0 ? "+" : ""}
                {chg.toFixed(2)}%
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
