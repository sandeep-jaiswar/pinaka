"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { queryScreener, type StockRow } from "@/lib/api";
import Link from "next/link";

export default function ScreenerPage() {
  const [results, setResults] = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<Record<string, string>>({
    minPrice: "",
    maxPrice: "",
    minVolume: "",
    minRsi: "",
    maxRsi: "",
    aboveSma: "",
    macdBullish: "",
  });

  function runSearch() {
    setLoading(true);
    const params: Record<string, string | undefined> = {};
    if (filters.minPrice) params.minPrice = filters.minPrice;
    if (filters.maxPrice) params.maxPrice = filters.maxPrice;
    if (filters.minVolume) params.minVolume = filters.minVolume;
    if (filters.minRsi) params.minRsi = filters.minRsi;
    if (filters.maxRsi) params.maxRsi = filters.maxRsi;
    if (filters.aboveSma === "yes") params.aboveSma = "true";
    if (filters.aboveSma === "no") params.aboveSma = "false";
    if (filters.macdBullish === "yes") params.macdBullish = "true";
    if (filters.macdBullish === "no") params.macdBullish = "false";

    queryScreener(params as any)
      .then(setResults)
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    runSearch();
  }, []);

  return (
    <div className="max-w-screen-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Stock Screener</h1>
        <Badge variant="outline" className="text-zinc-400 border-zinc-700">
          {results.length} results
        </Badge>
      </div>

      {/* Filters */}
      <Card className="bg-zinc-900/60 border-zinc-800 p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Min Price
            </label>
            <Input
              type="number"
              placeholder="Any"
              value={filters.minPrice}
              onChange={(e) =>
                setFilters({ ...filters, minPrice: e.target.value })
              }
              className="h-8 text-xs bg-zinc-800 border-zinc-700"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Max Price
            </label>
            <Input
              type="number"
              placeholder="Any"
              value={filters.maxPrice}
              onChange={(e) =>
                setFilters({ ...filters, maxPrice: e.target.value })
              }
              className="h-8 text-xs bg-zinc-800 border-zinc-700"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Min Volume
            </label>
            <Input
              type="number"
              placeholder="Any"
              value={filters.minVolume}
              onChange={(e) =>
                setFilters({ ...filters, minVolume: e.target.value })
              }
              className="h-8 text-xs bg-zinc-800 border-zinc-700"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Min RSI
            </label>
            <Input
              type="number"
              placeholder="Any"
              value={filters.minRsi}
              onChange={(e) =>
                setFilters({ ...filters, minRsi: e.target.value })
              }
              className="h-8 text-xs bg-zinc-800 border-zinc-700"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Max RSI
            </label>
            <Input
              type="number"
              placeholder="Any"
              value={filters.maxRsi}
              onChange={(e) =>
                setFilters({ ...filters, maxRsi: e.target.value })
              }
              className="h-8 text-xs bg-zinc-800 border-zinc-700"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              Above SMA-20
            </label>
            <Select
              value={filters.aboveSma}
              onValueChange={(v) =>
                setFilters({ ...filters, aboveSma: v ?? "" })
              }
            >
              <SelectTrigger className="h-8 text-xs bg-zinc-800 border-zinc-700">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Yes</SelectItem>
                <SelectItem value="no">No</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block">
              MACD Bullish
            </label>
            <Select
              value={filters.macdBullish}
              onValueChange={(v) =>
                setFilters({ ...filters, macdBullish: v ?? "" })
              }
            >
              <SelectTrigger className="h-8 text-xs bg-zinc-800 border-zinc-700">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Yes</SelectItem>
                <SelectItem value="no">No</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <button
              onClick={runSearch}
              className="w-full h-8 rounded text-xs font-medium bg-emerald-600 hover:bg-emerald-500 transition-colors text-black"
            >
              {loading ? "…" : "Apply"}
            </button>
          </div>
        </div>
      </Card>

      {/* Results Table */}
      <Card className="bg-zinc-900/60 border-zinc-800 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono">
                Symbol
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                Close
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                Chg %
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                Volume
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                Deliv %
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                RSI-14
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                SMA-20
              </TableHead>
              <TableHead className="text-[10px] uppercase text-zinc-500 font-mono text-right">
                MACD
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((r) => {
              const chg =
                r.open && r.close
                  ? ((r.close - r.open) / r.open) * 100
                  : 0;
              return (
                <TableRow
                  key={r.symbol}
                  className="border-zinc-800/50 hover:bg-zinc-800/30"
                >
                  <TableCell className="font-mono text-sm">
                    <Link
                      href={`/stocks/${r.symbol}`}
                      className="text-emerald-400 hover:text-emerald-300"
                    >
                      {r.symbol}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-right text-zinc-100">
                    {r.close?.toFixed(2) ?? "—"}
                  </TableCell>
                  <TableCell
                    className={`font-mono text-xs text-right ${
                      chg >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {chg >= 0 ? "+" : ""}
                    {chg.toFixed(2)}%
                  </TableCell>
                  <TableCell className="font-mono text-xs text-right text-zinc-400">
                    {r.totaltradedquantity
                      ? r.totaltradedquantity > 1_000_000
                        ? `${(r.totaltradedquantity / 1_000_000).toFixed(1)}M`
                        : `${(r.totaltradedquantity / 1_000).toFixed(0)}K`
                      : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-right text-zinc-400">
                    {r.deliv_per != null ? `${r.deliv_per.toFixed(1)}%` : "—"}
                  </TableCell>
                  <TableCell
                    className={`font-mono text-xs text-right ${
                      r.rsi_14 != null
                        ? r.rsi_14 > 70
                          ? "text-red-400"
                          : r.rsi_14 < 30
                          ? "text-emerald-400"
                          : "text-zinc-300"
                        : "text-zinc-600"
                    }`}
                  >
                    {r.rsi_14?.toFixed(1) ?? "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-right text-zinc-300">
                    {r.sma_20?.toFixed(2) ?? "—"}
                  </TableCell>
                  <TableCell
                    className={`font-mono text-xs text-right ${
                      r.macd != null
                        ? r.macd > 0
                          ? "text-emerald-400"
                          : "text-red-400"
                        : "text-zinc-600"
                    }`}
                  >
                    {r.macd?.toFixed(2) ?? "—"}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
