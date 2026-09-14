"use client";

import { useState } from "react";
import { api, OCSFEvent } from "@/lib/api";

export default function SearchTable() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<OCSFEvent[]>([]);
  const [selected, setSelected] = useState<{ ocsf: OCSFEvent; raw: string | null } | null>(null);
  const [loading, setLoading] = useState(false);

  const runSearch = async () => {
    setLoading(true);
    try {
      const { results } = await api.search(q);
      setResults(results);
    } finally {
      setLoading(false);
    }
  };

  const openEvent = async (rawEventId: string) => {
    const { ocsf_event, raw_log } = await api.getEvent(rawEventId);
    if (ocsf_event) setSelected({ ocsf: ocsf_event, raw: raw_log });
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
          placeholder="Search by IP, vendor, disposition…"
          className="flex-1 border border-line bg-readout px-3 py-2 font-mono text-[13px] text-fg placeholder:text-fg3"
        />
        <button
          onClick={runSearch}
          disabled={loading}
          className="border border-brass/50 bg-brass/10 px-4 py-2 text-[13px] font-medium text-brass transition-colors hover:bg-brass/20 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      <div className="overflow-x-auto border border-line">
        <table className="w-full text-[13px]">
          <thead className="bg-panel text-left">
            <tr>
              <th className="text-fg3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider2">Event ID</th>
              <th className="text-fg3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider2">Source</th>
              <th className="text-fg3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider2">Src → Dst</th>
              <th className="text-fg3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider2">Disposition</th>
            </tr>
          </thead>
          <tbody>
            {results.map((e) => (
              <tr
                key={e.ulpf.raw_event_id}
                onClick={() => openEvent(e.ulpf.raw_event_id)}
                className="cursor-pointer border-t border-line hover:bg-panel"
              >
                <td className="px-3 py-2 font-mono text-xs text-fg2">{e.ulpf.raw_event_id}</td>
                <td className="px-3 py-2 text-fg">{e.metadata.product.name}</td>
                <td className="px-3 py-2 font-mono text-fg">
                  {e.src_endpoint?.ip ?? "—"} → {e.dst_endpoint?.ip ?? "—"}
                  {e.dst_endpoint?.port ? `:${e.dst_endpoint.port}` : ""}
                </td>
                <td className="px-3 py-2">
                  <span className={e.disposition === "Allowed" ? "text-ok" : "text-crit"}>
                    {e.disposition}
                  </span>
                </td>
              </tr>
            ))}
            {results.length === 0 && (
              <tr>
                <td colSpan={4} className="text-fg3 px-3 py-4 text-center">
                  No results. Try a search, or ingest some events first.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="border border-line bg-panel p-4">
          <div className="text-fg3 mb-3 text-[10px] uppercase tracking-wider2">
            Raw ↔ Normalized traceability — linked by <span className="text-brass">ulpf.raw_event_hash</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="text-fg3 mb-1 text-[10px] uppercase tracking-wider2">Raw log</div>
              <pre className="readout max-h-64 overflow-auto p-3 font-mono text-xs text-fg2">
                {selected.raw ?? "(raw bytes not found)"}
              </pre>
            </div>
            <div>
              <div className="text-fg3 mb-1 text-[10px] uppercase tracking-wider2">Normalized OCSF</div>
              <pre className="readout max-h-64 overflow-auto p-3 font-mono text-xs text-fg2">
                {JSON.stringify(selected.ocsf, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
