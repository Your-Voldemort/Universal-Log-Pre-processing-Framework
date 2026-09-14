"use client";

import { useEffect, useState } from "react";
import { api, MappingProposal } from "@/lib/api";

function StepBadge({ n }: { n: 1 | 2 }) {
  return (
    <span className="border border-brass/40 bg-brass/10 px-1.5 py-0.5 font-mono text-[10px] text-brass">
      {n}
    </span>
  );
}

export default function MappingReview() {
  const [rawSamples, setRawSamples] = useState("");
  const [proposals, setProposals] = useState<MappingProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = () => api.listProposals().then(setProposals);

  useEffect(() => {
    refresh();
  }, []);

  const propose = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.proposeMapping(rawSamples);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const review = async (id: number, action: "approve" | "reject") => {
    setBusyId(id);
    setReviewError(null);
    setNotice(null);
    try {
      if (action === "approve") {
        const { source_format, replayed } = await api.approveMapping(id);
        setNotice(
          `${source_format} is active. Earlier unrecognized events replayed: ${replayed.normalized} normalized, ` +
            `${replayed.quarantined} quarantined, ${replayed.still_unrecognized} still unrecognized.`,
        );
      } else {
        await api.rejectMapping(id);
      }
      await refresh();
    } catch (e) {
      setReviewError(String(e));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="border border-line bg-panel p-4">
        <div className="text-fg2 mb-2 flex items-start gap-2 text-xs">
          <StepBadge n={1} />
          <span>
            The local model proposes a mapping for an unrecognized format. It never runs in the
            live ingestion path — a human must approve step 2 before it becomes an active parser.
          </span>
        </div>
        <textarea
          value={rawSamples}
          onChange={(e) => setRawSamples(e.target.value)}
          placeholder="Paste 1-3 unrecognized raw log lines…"
          rows={4}
          className="readout w-full p-3 font-mono text-xs text-fg placeholder:text-fg3"
        />
        <button
          onClick={propose}
          disabled={loading || !rawSamples.trim()}
          className="mt-2 border border-brass/50 bg-brass/10 px-4 py-2 text-[13px] font-medium text-brass transition-colors hover:bg-brass/20 disabled:opacity-50"
        >
          {loading ? "Asking local model…" : "Propose mapping"}
        </button>
        {error && <div className="mt-2 text-xs text-crit">{error}</div>}
      </div>

      <div className="space-y-3">
        {reviewError && <div className="text-xs text-crit">{reviewError}</div>}
        {notice && <div className="text-xs text-ok">{notice}</div>}
        {proposals.map((p) => (
          <div key={p.id} className="border border-line bg-panel p-4">
            <div className="mb-2.5 flex items-center justify-between">
              <div className="font-mono text-xs text-fg2">
                proposal #{p.id} — <span className="text-fg">{p.source_format}</span>
              </div>
              <span className="text-fg3 border border-line px-2 py-0.5 text-[10px] uppercase tracking-wider2">
                {p.status}
              </span>
            </div>
            <pre className="readout mb-3 max-h-48 overflow-auto p-3 font-mono text-xs text-fg2">
              {p.proposed_yaml}
            </pre>
            <div className="flex gap-2">
              <button
                onClick={() => review(p.id, "approve")}
                disabled={p.status !== "pending" || busyId === p.id}
                className="flex items-center gap-2 border border-ok/50 bg-ok/10 px-3 py-1.5 text-xs font-medium text-ok transition-colors hover:bg-ok/20 disabled:opacity-40"
              >
                <StepBadge n={2} />
                Approve — activate this parser
              </button>
              <button
                onClick={() => review(p.id, "reject")}
                disabled={p.status !== "pending" || busyId === p.id}
                className="border border-line px-3 py-1.5 text-xs text-fg2 transition-colors hover:border-crit/50 hover:text-crit disabled:opacity-40"
              >
                Reject
              </button>
            </div>
          </div>
        ))}
        {proposals.length === 0 && (
          <div className="text-fg3 text-sm">No mapping proposals yet.</div>
        )}
      </div>
    </div>
  );
}
