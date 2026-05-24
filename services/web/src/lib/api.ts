const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts?.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export interface StockRow {
  symbol: string;
  close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  totaltradedquantity: number | null;
  deliv_per: number | null;
  rsi_14?: number | null;
  sma_20?: number | null;
  ema_20?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_histogram?: number | null;
}

export interface StockDetail {
  symbol: string;
  series: string | null;
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  prev_close: number | null;
  totaltradedquantity: number | null;
  totaltradedvalue: number | null;
  deliv_qty: number | null;
  deliv_per: number | null;
  avg_price: number | null;
  no_of_trades: number | null;
}

export interface PricePoint {
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  totaltradedquantity: number | null;
}

export interface MarketOverview {
  trade_date: string | null;
  gainers: StockRow[];
  losers: StockRow[];
  most_active: StockRow[];
}

export interface ScreenerParams {
  minPrice?: number;
  maxPrice?: number;
  minVolume?: number;
  minRsi?: number;
  maxRsi?: number;
  aboveSma?: boolean;
  macdBullish?: boolean;
  limit?: number;
}

export interface Watchlist {
  id: number;
  name: string;
  symbols: string[];
}

export interface CorpAction {
  symbol: string;
  ex_date: string | null;
  purpose: string | null;
  face_value: number | null;
}

export interface IndexConstituent {
  symbol: string;
  company_name: string | null;
  index_name: string | null;
  weight_percentage: number | null;
  industry: string | null;
}

export async function searchSymbols(search?: string) {
  const q = search ? `?search=${encodeURIComponent(search)}` : "";
  return fetchJSON<{ symbol: string; series: string }[]>(`/api/stocks${q}`);
}

export async function getStockDetail(symbol: string) {
  return fetchJSON<StockDetail>(`/api/stocks/${encodeURIComponent(symbol)}`);
}

export async function getStockHistory(symbol: string, limit = 120) {
  return fetchJSON<PricePoint[]>(
    `/api/stocks/${encodeURIComponent(symbol)}/history?limit=${limit}`
  );
}

export async function getStockCorpActions(symbol: string) {
  return fetchJSON<CorpAction[]>(
    `/api/stocks/${encodeURIComponent(symbol)}/corp-actions`
  );
}

export async function getStockConstituents(symbol: string) {
  return fetchJSON<IndexConstituent[]>(
    `/api/stocks/${encodeURIComponent(symbol)}/constituents`
  );
}

export async function getMarketOverview() {
  return fetchJSON<MarketOverview>("/api/market/latest");
}

export async function getMarketIndices() {
  return fetchJSON<IndexConstituent[]>("/api/market/indices");
}

export async function queryScreener(params: ScreenerParams) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) qs.set(k, String(v));
  });
  return fetchJSON<StockRow[]>(`/api/screener/query?${qs}`);
}

export async function getWatchlists() {
  return fetchJSON<Watchlist[]>("/api/watchlist");
}

export async function createWatchlist(name: string, symbols: string[] = []) {
  return fetchJSON<Watchlist>(`/api/watchlist`, {
    method: "POST",
    body: JSON.stringify({ name, symbols }),
  });
}

export async function updateWatchlist(name: string, symbols: string[]) {
  return fetchJSON<Watchlist>(
    `/api/watchlist/${encodeURIComponent(name)}`,
    {
      method: "PUT",
      body: JSON.stringify({ symbols }),
    }
  );
}

export async function deleteWatchlist(name: string) {
  return fetchJSON<{ status: string }>(
    `/api/watchlist/${encodeURIComponent(name)}`,
    { method: "DELETE" }
  );
}
