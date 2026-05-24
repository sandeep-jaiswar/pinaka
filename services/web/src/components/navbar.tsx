"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/screener", label: "Screener" },
  { href: "/market", label: "Market" },
  { href: "/watchlist", label: "Watchlist" },
];

export function Navbar() {
  const path = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800 bg-[#0a0a0f]/95 backdrop-blur">
      <div className="flex items-center justify-between px-6 h-12 max-w-screen-2xl mx-auto">
        <div className="flex items-center gap-8">
          <Link href="/" className="font-bold text-lg tracking-tight text-emerald-400">
            PINAKA
          </Link>
          <nav className="flex items-center gap-1">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  path === l.href
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          NSE — {new Date().toLocaleDateString("en-IN")}
        </div>
      </div>
    </header>
  );
}
