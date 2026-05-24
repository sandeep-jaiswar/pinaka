"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getStockDetail,
  getStockHistory,
  getStockCorpActions,
  getStockConstituents,
  type StockDetail,
  type PricePoint,
  type CorpAction,
  type IndexConstituent,
} from "@/lib/api";

export default function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [corpActions, setCorpActions] = useState<CorpAction[]>([]);
  const [constituents, setConstituents] = useState<IndexConstituent[]>([]);

  useEffect(() => {
    if (!symbol) return;
    getStockDetail(symbol).then(setDetail).catch(console.error);
    getStockHistory(symbol, 120).then(setHistory).catch(console.error);
    getStockCorpActions(symbol).then(setCorpActions).catch(console.error);
    getStockConstituents(symbol).then(setConstituents).catch(console.error);
  }, [symbol]);

  if (!detail) {
    return (
      <div className="max-w-screen-2xl mx-auto p-6">
        <div className="text-zinc-500 text-sm">Loading {symbol}…</div>
      </div>
    );
  }

  const chg =
    detail.open && detail.close
      ? ((detail.close - detail.open) / detail.open) * 100
      : 0;

  const formattedHistory = history.slice().reverse();

  return (
    <div className="max-w-screen-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold font-mono">{detail.symbol}</h1>
          <div className="flex items-center gap-3 mt-1 text-sm text-zinc-500">
            <Badge
              variant="outline"
              className="border-zinc-700 text-zinc-400 text-[10px]"
            >
              {detail.series ?? "EQ"}
            </Badge>
            <span>{detail.trade_date}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold font-mono">
            {detail.close?.toFixed(2) ?? "—"}
          </div>
          <div
            className={`font-mono text-sm ${
              chg >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {chg >= 0 ? "+" : ""}
            {chg.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price Chart */}
        <Card className="lg:col-span-2 bg-zinc-900/60 border-zinc-800 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Price History
          </h3>
          <div className="h-64 relative">
            {formattedHistory.length > 1 && (
              <MiniChart data={formattedHistory} />
            )}
          </div>
        </Card>

        {/* Key Stats */}
        <Card className="bg-zinc-900/60 border-zinc-800 p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Key Stats
          </h3>
          <StatRow label="Open" value={detail.open} />
          <StatRow label="High" value={detail.high} />
          <StatRow label="Low" value={detail.low} />
          <StatRow label="Close" value={detail.close} />
          <StatRow label="Prev Close" value={detail.prev_close} />
          <StatRow
            label="Volume"
            value={
              detail.totaltradedquantity != null
                ? detail.totaltradedquantity > 1_000_000
                  ? `${(detail.totaltradedquantity / 1_000_000).toFixed(2)}M`
                  : `${(detail.totaltradedquantity / 1_000).toFixed(0)}K`
                : null
            }
            raw
          />
          <StatRow label="Delivery %" value={detail.deliv_per} suffix="%" />
          <StatRow label="Avg Price" value={detail.avg_price} />
          <StatRow label="Trades" value={detail.no_of_trades} />
          <StatRow
            label="Value (Cr)"
            value={
              detail.totaltradedvalue != null
                ? (detail.totaltradedvalue / 10_000_000).toFixed(2)
                : null
            }
            raw
          />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Corporate Actions */}
        <Card className="bg-zinc-900/60 border-zinc-800 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Corporate Actions
          </h3>
          {corpActions.length === 0 ? (
            <p className="text-xs text-zinc-600">No corporate actions</p>
          ) : (
            <div className="space-y-2">
              {corpActions.slice(0, 10).map((ca, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs py-1 border-b border-zinc-800/50 last:border-0"
                >
                  <div>
                    <span className="text-zinc-300">{ca.purpose}</span>
                    {ca.face_value && (
                      <span className="text-zinc-500 ml-2">
                        FV: {ca.face_value}
                      </span>
                    )}
                  </div>
                  <span className="text-zinc-500 font-mono">{ca.ex_date}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Index Constituents */}
        <Card className="bg-zinc-900/60 border-zinc-800 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Index Membership
          </h3>
          {constituents.length === 0 ? (
            <p className="text-xs text-zinc-600">Not in any index</p>
          ) : (
            <div className="space-y-2">
              {constituents.map((c, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs py-1 border-b border-zinc-800/50 last:border-0"
                >
                  <span className="text-zinc-300">{c.index_name}</span>
                  <span className="text-zinc-500 font-mono">
                    {c.weight_percentage != null
                      ? `${c.weight_percentage.toFixed(2)}%`
                      : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function StatRow({
  label,
  value,
  suffix,
  raw,
}: {
  label: string;
  value: number | string | null | undefined;
  suffix?: string;
  raw?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-zinc-500">{label}</span>
      <span className="font-mono text-zinc-200">
        {value != null ? `${value}${suffix ?? ""}` : "—"}
      </span>
    </div>
  );
}

function MiniChart({ data }: { data: PricePoint[] }) {
  const values = data
    .map((d) => d.close)
    .filter((v): v is number => v != null);
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const w = values.length;
  const h = 220;

  const points = values.map((v, i) => {
    const x = (i / (w - 1)) * 100;
    const y = h - ((v - min) / range) * (h - 20) - 10;
    return `${x}%,${y}`;
  });

  const color =
    values[values.length - 1] >= values[0]
      ? "rgb(52,211,153)"
      : "rgb(248,113,113)";

  return (
    <svg
      viewBox={`0 0 100 ${h}`}
      preserveAspectRatio="none"
      className="w-full h-full"
    >
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        points={points.join(" ")}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
