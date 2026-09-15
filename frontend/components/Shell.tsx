"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, FormEvent, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { CONTROL, Icon, IconName, Status } from "@/components/ui";
import { api, Metrics } from "@/lib/api";
import { utcTime } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

interface ConsoleData {
  metrics: Metrics | null;
  pendingProposals: number;
  apiDown: boolean;
  /** Re-poll now, e.g. right after an action changes counts. */
  refresh: () => void;
}

const ConsoleContext = createContext<ConsoleData>({
  metrics: null,
  pendingProposals: 0,
  apiDown: false,
  refresh: () => {},
});

export const useConsole = () => useContext(ConsoleContext);

const NAV: { group: string; items: { href: string; label: string; icon: IconName; badge?: "drift" | "proposals" }[] }[] = [
  {
    group: "Monitor",
    items: [
      { href: "/", label: "Overview", icon: "activity" },
      { href: "/events", label: "Events", icon: "list" },
    ],
  },
  {
    group: "Review",
    items: [
      { href: "/quarantine", label: "Drift quarantine", icon: "alert", badge: "drift" },
      { href: "/proposals", label: "Parser proposals", icon: "branch", badge: "proposals" },
    ],
  },
  {
    group: "Evidence",
    items: [
      { href: "/integrity", label: "Integrity", icon: "link" },
      { href: "/reports", label: "Incident reports", icon: "file" },
    ],
  },
];

/** Many uneven inputs converging on one normalized line. */
function Mark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-7 w-7 shrink-0">
      <rect width="24" height="24" rx="5" className="fill-accent" />
      <path
        d="M5 7.5h5l3 4.5M5 12h8M5 16.5h5l3-4.5M13 12h6"
        fill="none"
        className="stroke-on-accent"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type Theme = "system" | "light" | "dark";
const THEMES: { value: Theme; label: string; icon: IconName }[] = [
  { value: "system", label: "Use system theme", icon: "monitor" },
  { value: "light", label: "Light theme", icon: "sun" },
  { value: "dark", label: "Dark theme", icon: "moon" },
];

function ThemeSwitcher() {
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    const saved = document.documentElement.dataset.theme;
    if (saved === "light" || saved === "dark") setTheme(saved);
  }, []);

  const choose = (next: Theme) => {
    setTheme(next);
    const root = document.documentElement;
    if (next === "system") delete root.dataset.theme;
    else root.dataset.theme = next;
    try {
      if (next === "system") localStorage.removeItem("ulpf-theme");
      else localStorage.setItem("ulpf-theme", next);
    } catch {
      // storage blocked: the choice still applies for this visit
    }
  };

  return (
    <div role="group" aria-label="Color theme" className="flex rounded border border-line bg-surface p-0.5">
      {THEMES.map((t) => (
        <button
          key={t.value}
          type="button"
          aria-pressed={theme === t.value}
          aria-label={t.label}
          title={t.label}
          onClick={() => choose(t.value)}
          className={`grid h-7 flex-1 place-items-center rounded-sm transition-colors duration-150 ${
            theme === t.value ? "bg-raised text-ink" : "text-ink-3 hover:text-ink"
          }`}
        >
          <Icon name={t.icon} className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [pendingProposals, setPendingProposals] = useState(0);
  const [apiDown, setApiDown] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [navOpen, setNavOpen] = useState(false);

  const refresh = useCallback(() => {
    Promise.all([api.metrics(), api.listProposals("pending")])
      .then(([m, pending]) => {
        setMetrics(m);
        setPendingProposals(pending.length);
        setApiDown(false);
        setUpdatedAt(Date.now());
      })
      .catch(() => setApiDown(true));
  }, []);

  usePolling(refresh, 4000);

  useEffect(() => setNavOpen(false), [pathname]);

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setNavOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  const search = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = String(new FormData(e.currentTarget).get("q") ?? "").trim();
    router.push(q ? `/events?q=${encodeURIComponent(q)}` : "/events");
  };

  const chain = !metrics
    ? { tone: "neutral" as const, label: "Chain status" }
    : metrics.chain_verified
      ? { tone: "ok" as const, label: "Chain verified" }
      : { tone: "bad" as const, label: "Chain tampered" };

  return (
    <ConsoleContext.Provider value={{ metrics, pendingProposals, apiDown, refresh }}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-drawer focus:rounded focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:text-ink"
      >
        Skip to content
      </a>

      <div className="flex min-h-screen">
        {navOpen && (
          <div aria-hidden="true" onClick={() => setNavOpen(false)} className="fixed inset-0 z-scrim bg-scrim/40 lg:hidden" />
        )}

        <nav
          aria-label="Primary"
          className={`fixed inset-y-0 left-0 z-drawer flex w-60 flex-col border-r border-line bg-canvas transition-[transform,visibility] duration-200 ease-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
            navOpen ? "translate-x-0" : "-translate-x-full max-lg:invisible"
          }`}
        >
          <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-line px-4">
            <Mark />
            <div className="min-w-0 flex-1 leading-tight">
              <p className="text-sm font-semibold text-ink">ULPF</p>
              <p className="truncate text-xs text-ink-2">Log normalization console</p>
            </div>
            <button
              type="button"
              onClick={() => setNavOpen(false)}
              aria-label="Close navigation"
              className="grid h-8 w-8 place-items-center rounded text-ink-2 hover:bg-raised lg:hidden"
            >
              <Icon name="x" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-4">
            {NAV.map((group) => (
              <div key={group.group} className="mb-5 last:mb-0">
                <p className="px-2 pb-1.5 text-xs font-medium text-ink-3">{group.group}</p>
                <ul className="space-y-px">
                  {group.items.map((item) => {
                    const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                    const count =
                      item.badge === "drift" ? (metrics?.drift_count ?? 0) : item.badge === "proposals" ? pendingProposals : 0;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          aria-current={active ? "page" : undefined}
                          className={`flex h-8 items-center gap-2.5 rounded px-2 text-sm transition-colors duration-150 ${
                            active
                              ? "bg-surface font-medium text-ink shadow-[0_0_0_1px_oklch(var(--line))]"
                              : "text-ink-2 hover:bg-raised hover:text-ink"
                          }`}
                        >
                          <Icon name={item.icon} className={`h-4 w-4 ${active ? "text-accent-ink" : ""}`} />
                          <span className="flex-1 truncate">{item.label}</span>
                          {count > 0 && (
                            <span className="rounded-full bg-warn-soft px-1.5 text-xs font-medium tabular-nums text-warn">
                              {count}
                              <span className="sr-only"> awaiting review</span>
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>

          <div className="shrink-0 space-y-2 border-t border-line p-3">
            <ThemeSwitcher />
          </div>
        </nav>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-sticky flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface px-4 lg:px-8">
            <button
              type="button"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
              aria-expanded={navOpen}
              className="-ml-1 grid h-8 w-8 shrink-0 place-items-center rounded text-ink-2 hover:bg-raised lg:hidden"
            >
              <Icon name="menu" />
            </button>

            <form role="search" onSubmit={search} className="relative min-w-0 max-w-md flex-1">
              <label htmlFor="global-search" className="sr-only">
                Search events
              </label>
              <Icon
                name="search"
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
              />
              <input
                id="global-search"
                name="q"
                type="search"
                placeholder="Search events by IP, product, disposition"
                className={`${CONTROL} w-full pl-8`}
              />
            </form>

            <div className="ml-auto flex shrink-0 items-center gap-3">
              {updatedAt && (
                <span className="hidden text-xs tabular-nums text-ink-3 md:inline">Updated {utcTime(updatedAt)} UTC</span>
              )}
              <Link href="/integrity" className="flex h-8 items-center rounded px-2 text-sm text-ink hover:bg-raised">
                <Status tone={chain.tone}>
                  <span className="max-sm:sr-only">{chain.label}</span>
                </Status>
              </Link>
            </div>
          </header>

          {apiDown && (
            <div role="status" className="flex items-center gap-2 border-b border-bad/30 bg-bad-soft px-4 py-2 text-sm text-ink lg:px-8">
              <Icon name="circleX" className="h-4 w-4 text-bad" />
              Can&apos;t reach the ULPF API.{metrics ? " Showing the last data received." : ""} Retrying every few seconds.
            </div>
          )}

          <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-4 py-6 focus:outline-none lg:px-8 lg:py-8">
            {children}
          </main>
        </div>
      </div>
    </ConsoleContext.Provider>
  );
}
