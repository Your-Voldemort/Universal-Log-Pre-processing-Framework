"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function ComplianceReport() {
  const [eventIds, setEventIds] = useState("");
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const ids = eventIds.split(/[\s,]+/).filter(Boolean);
      const { report_markdown } = await api.complianceReport(ids);
      setReport(report_markdown);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="border border-line bg-panel p-4">
        <div className="text-fg3 mb-2 text-[10px] uppercase tracking-wider2">
          Generate a CERT-In-format incident report from flagged event(s)
        </div>
        <input
          value={eventIds}
          onChange={(e) => setEventIds(e.target.value)}
          placeholder="raw_event_id(s), comma or space separated"
          className="readout w-full p-3 font-mono text-xs text-fg placeholder:text-fg3"
        />
        <button
          onClick={generate}
          disabled={loading || !eventIds.trim()}
          className="mt-2 border border-brass/50 bg-brass/10 px-4 py-2 text-[13px] font-medium text-brass transition-colors hover:bg-brass/20 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate report"}
        </button>
        {error && <div className="mt-2 text-xs text-crit">{error}</div>}
      </div>

      {report && (
        <div className="border border-brass/25 bg-paper p-5">
          <div className="mb-3 flex items-center justify-between border-b border-brass/25 pb-2">
            <span className="font-mono text-[10px] uppercase tracking-wider2 text-brassDim">
              CERT-In Incident Report
            </span>
            <span className="font-mono text-[10px] uppercase tracking-wider2 text-brassDim">
              ULPF · Draft for review
            </span>
          </div>
          <pre className="max-h-[30rem] overflow-auto whitespace-pre-wrap font-mono text-xs text-[#1E1808]">
            {report}
          </pre>
        </div>
      )}
    </div>
  );
}
