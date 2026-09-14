"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Metrics } from "@/lib/api";

function Tile({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="border border-line bg-panel p-4">
      <div className="text-fg3 text-[10px] uppercase tracking-wider2">{label}</div>
      <div className={`mt-1.5 font-mono text-2xl tabular-nums ${accent ?? "text-fg"}`}>{value}</div>
    </div>
  );
}

export default function DashboardMetrics() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [injecting, setInjecting] = useState(false);

  const refresh = useCallback(() => {
    api.metrics().then(setMetrics).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  const injectMalformed = async () => {
    setInjecting(true);
    try {
      await api.injectMalformed();
      await new Promise((r) => setTimeout(r, 300));
      refresh();
    } finally {
      setInjecting(false);
    }
  };

  if (!metrics) return <div className="text-fg2 font-mono text-sm">Loading metrics…</div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-px border border-line bg-line md:grid-cols-4">
        <Tile label="Events / sec" value={metrics.events_per_sec.toFixed(2)} />
        <Tile
          label="Normalized %"
          value={
            metrics.total_normalized + metrics.drift_count > 0
              ? `${((metrics.total_normalized / (metrics.total_normalized + metrics.drift_count)) * 100).toFixed(0)}%`
              : "—"
          }
        />
        <Tile
          label="Schema Drift Count"
          value={String(metrics.drift_count)}
          accent={metrics.drift_count > 0 ? "text-warn" : undefined}
        />
        <Tile label="Unmapped Field %" value={`${(metrics.unmapped_field_ratio * 100).toFixed(1)}%`} />
        <Tile label="Raw Preservation" value={`${metrics.raw_preservation_pct.toFixed(0)}%`} accent="text-ok" />
        <Tile
          label="Hash Chain"
          value={metrics.chain_verified ? "INTACT" : "TAMPERED"}
          accent={metrics.chain_verified ? "text-ok" : "text-crit"}
        />
      </div>

      <div className="border border-line bg-panel p-4">
        <div className="text-fg3 mb-2 text-[10px] uppercase tracking-wider2">Per-source health</div>
        <div className="space-y-1.5">
          {Object.entries(metrics.normalized_by_source).map(([source, count]) => (
            <div key={source} className="flex items-center justify-between text-[13px]">
              <span className="flex items-center gap-2 font-mono text-fg">
                <span
                  className={`lamp h-1.5 w-1.5 ${metrics.drift_count > 0 ? "bg-warn" : "bg-ok"}`}
                />
                {source}
              </span>
              <span className="text-fg2 font-mono tabular-nums">{count} events</span>
            </div>
          ))}
          {Object.keys(metrics.normalized_by_source).length === 0 && (
            <div className="text-fg3 text-sm">No events ingested yet.</div>
          )}
        </div>
      </div>

      <button
        onClick={injectMalformed}
        disabled={injecting}
        className="border border-warn/50 bg-warn/10 px-4 py-2 text-[13px] font-medium text-warn transition-colors hover:bg-warn/20 disabled:opacity-50"
      >
        {injecting ? "Injecting…" : "Inject malformed log"}
      </button>
    </div>
  );
}
