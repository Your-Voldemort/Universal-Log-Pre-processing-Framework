"use client";

import { useEffect, useState } from "react";
import { api, OCSFEvent } from "@/lib/api";

const TH = "text-fg3 px-3 py-2 text-[10px] font-medium uppercase tracking-wider2";
const CONTROL = "border border-line bg-readout px-2 py-1.5 font-mono text-xs text-fg";

function utc(ms?: number) {
  return ms === undefined ? "—" : new Date(ms).toISOString().slice(0, 19).replace("T", " ");
}

// datetime-local carries no zone; the inputs are labelled UTC, like every time ULPF shows
const bound = (value: string) => (value ? `${value}Z` : "");

export default function SearchTable() {
  const [q, setQ] = useState("");
  const [source, setSource] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [results, setResults] = useState<OCSFEvent[]>([]);
  const [selected, setSelected] = useState<{ ocsf: OCSFEvent; raw: string | null } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .metrics()
      .then((m) => setSources(Object.keys(m.normalized_by_source).sort()))
      .catch(() => {});
  }, []);

  const runSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const timeRange = from || to ? `${bound(from)}/${bound(to)}` : undefined;
      const { results } = await api.search(q, source || undefined, timeRange);
      setResults(results);
    } catch (e) {
      setError(String(e));
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

      <div className="flex flex-wrap items-center gap-4 text-[11px] text-fg3">
        <label className="flex items-center gap-2">
          Source
          <select value={source} onChange={(e) => setSource(e.target.value)} className={CONTROL}>
            <option value="">all</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          From (UTC)
          <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} className={CONTROL} />
        </label>
        <label className="flex items-center gap-2">
          To (UTC)
          <input type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} className={CONTROL} />
        </label>
      </div>
      {error && <div className="text-xs text-crit">{error}</div>}

      <div className="overflow-x-auto border border-line">
        <table className="w-full text-[13px]">
          <thead className="bg-panel text-left">
            <tr>
              <th className={TH}>Time (UTC)</th>
              <th className={TH}>Event ID</th>
              <th className={TH}>Source</th>
              <th className={TH}>Src → Dst</th>
              <th className={TH}>Disposition</th>
            </tr>
          </thead>
          <tbody>
            {results.map((e) => (
              <tr
                key={e.ulpf.raw_event_id}
                onClick={() => openEvent(e.ulpf.raw_event_id)}
                className="cursor-pointer border-t border-line hover:bg-panel"
              >
                <td className="px-3 py-2 font-mono text-xs text-fg2">{utc(e.time)}</td>
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
                <td colSpan={5} className="text-fg3 px-3 py-4 text-center">
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
