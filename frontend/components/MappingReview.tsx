"use client";

import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";
import { useConsole } from "@/components/Shell";
import { Button, Callout, CONTROL, CopyButton, EmptyState, PageHeader, READOUT, Segmented, Skeleton, Status } from "@/components/ui";
import { api, errorMessage, MappingProposal, ReplayCounts } from "@/lib/api";
import { Tone, utc } from "@/lib/format";

type Filter = "pending" | "approved" | "rejected" | "all";

const STATUS: Record<string, { tone: Tone; label: string }> = {
  pending: { tone: "warn", label: "Awaiting review" },
  approved: { tone: "ok", label: "Approved" },
  rejected: { tone: "neutral", label: "Rejected" },
};

const STEPS = [
  ["Paste samples.", "A few lines of a format no parser recognizes."],
  ["Review the draft.", "The local model proposes an OCSF field mapping."],
  ["Approve to activate.", "The parser goes live and stored unrecognized events are replayed."],
];

function replaySummary({ normalized, quarantined, still_unrecognized, failed_validation }: ReplayCounts) {
  const parts = [`${normalized} normalized`, `${quarantined} held in quarantine`, `${still_unrecognized} still unrecognized`];
  if (failed_validation) parts.push(`${failed_validation} failed OCSF validation`);
  return parts.join(", ");
}

export default function MappingReview() {
  const { refresh } = useConsole();
  const [samples, setSamples] = useState("");
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<MappingProposal[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("pending");
  const [notice, setNotice] = useState<ReactNode>(null);

  const load = useCallback(
    () =>
      api
        .listProposals()
        .then((list) => {
          setProposals(list);
          setLoadError(null);
        })
        .catch((e) => setLoadError(errorMessage(e))),
    [],
  );

  useEffect(() => {
    load();
  }, [load]);

  const draft = async (e: FormEvent) => {
    e.preventDefault();
    setDrafting(true);
    setDraftError(null);
    setNotice(null);
    try {
      const { source_format } = await api.proposeMapping(samples);
      setSamples("");
      setFilter("pending");
      setNotice(
        <>
          Drafted a mapping for <code className="code-inline">{source_format}</code>. Review it below before approving.
        </>,
      );
      await load();
      refresh();
    } catch (err) {
      setDraftError(errorMessage(err));
    } finally {
      setDrafting(false);
    }
  };

  const reviewed = (text: ReactNode) => {
    setNotice(text);
    load();
    refresh();
  };

  const count = (status: string) => proposals?.filter((p) => p.status === status).length ?? 0;
  const visible = (proposals ?? []).filter((p) => filter === "all" || p.status === filter);

  return (
    <div className="space-y-10">
      <div className="space-y-5">
        <PageHeader
          title="Parser proposals"
          description="When logs arrive in a format no parser recognizes, a model running on this server drafts an OCSF mapping from sample lines. Nothing reaches the ingestion path until a reviewer approves it."
        />
        <ol className="flex flex-col gap-3 text-sm md:flex-row md:gap-8">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="flex max-w-xs gap-2.5">
              <span className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full border border-line-strong text-xs tabular-nums text-ink-2">
                {i + 1}
              </span>
              <p>
                <span className="font-medium text-ink">{title}</span> <span className="text-ink-2">{text}</span>
              </p>
            </li>
          ))}
        </ol>
      </div>

      <section aria-labelledby="draft-heading" className="max-w-3xl">
        <h2 id="draft-heading" className="text-lg font-semibold text-ink">
          Draft a mapping
        </h2>
        <form onSubmit={draft} className="mt-3 space-y-3">
          <div>
            <label htmlFor="samples" className="text-sm font-medium text-ink">
              Sample log lines
            </label>
            <p id="samples-hint" className="text-xs text-ink-2">
              Paste 1 to 3 lines of the same format. They are sent only to the local model.
            </p>
            <textarea
              id="samples"
              aria-describedby="samples-hint"
              rows={5}
              spellCheck={false}
              value={samples}
              onChange={(e) => setSamples(e.target.value)}
              placeholder={'date=2026-08-30 time=14:01:14 devname="FGT-EDGE-01" srcip=10.5.2.14 dstip=203.0.113.44 …'}
              className={`${CONTROL} mt-1.5 h-auto w-full py-2 font-mono text-xs leading-5`}
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" loading={drafting} disabled={!samples.trim()}>
              {drafting ? "Drafting…" : "Draft mapping"}
            </Button>
            {drafting && (
              <p role="status" className="text-xs text-ink-2">
                The local model is drafting. This can take up to a minute.
              </p>
            )}
          </div>
          {draftError && (
            <Callout tone="bad" title="The mapping could not be drafted">
              {draftError}
            </Callout>
          )}
        </form>
      </section>

      <section aria-labelledby="proposals-heading" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="proposals-heading" className="text-lg font-semibold text-ink">
            Proposals
          </h2>
          <Segmented
            label="Filter by status"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "pending", label: `Awaiting review · ${count("pending")}` },
              { value: "approved", label: `Approved · ${count("approved")}` },
              { value: "rejected", label: `Rejected · ${count("rejected")}` },
              { value: "all", label: "All" },
            ]}
          />
        </div>

        {notice && <Callout tone="ok">{notice}</Callout>}
        {loadError && (
          <Callout tone="bad" title="Proposals could not be loaded">
            {loadError}
          </Callout>
        )}

        {proposals === null && !loadError && (
          <div className="space-y-2 rounded-md border border-line p-4">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {proposals && visible.length === 0 && (
          <div className="rounded-md border border-line">
            <EmptyState icon="branch" title={filter === "pending" ? "No proposals awaiting review" : "No proposals here"}>
              {filter === "pending"
                ? "Paste sample lines above to draft a mapping for an unrecognized format."
                : "Proposals move here once a reviewer decides on them."}
            </EmptyState>
          </div>
        )}

        {visible.map((p) => (
          <ProposalCard key={p.id} proposal={p} onReviewed={reviewed} />
        ))}
      </section>
    </div>
  );
}

function ProposalCard({ proposal: p, onReviewed }: { proposal: MappingProposal; onReviewed: (notice: ReactNode) => void }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const status = STATUS[p.status] ?? { tone: "neutral" as const, label: p.status };

  const approve = async () => {
    setBusy("approve");
    setError(null);
    try {
      const { source_format, replayed } = await api.approveMapping(p.id);
      onReviewed(
        <>
          <code className="code-inline">{source_format}</code> is now an active parser. Stored unrecognized events replayed:{" "}
          {replaySummary(replayed)}.
        </>,
      );
    } catch (e) {
      setError(errorMessage(e));
      setBusy(null);
    }
  };

  const reject = async () => {
    setBusy("reject");
    setError(null);
    try {
      await api.rejectMapping(p.id);
      onReviewed(
        <>
          Rejected the proposal for <code className="code-inline">{p.source_format}</code>. No parser was changed.
        </>,
      );
    } catch (e) {
      setError(errorMessage(e));
      setBusy(null);
    }
  };

  return (
    <article className="overflow-hidden rounded-md border border-line">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-canvas px-4 py-2.5">
        <Status tone={status.tone} className="text-sm">
          {status.label}
        </Status>
        <h3 className="font-mono text-sm font-medium text-ink">{p.source_format}</h3>
        <span className="ml-auto text-xs tabular-nums text-ink-2">
          #{p.id} · Drafted {utc(p.created_at)} UTC
        </span>
      </header>

      <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <h4 className="text-xs font-medium text-ink-2">Sample lines</h4>
            <CopyButton value={p.sample_raw} label="Copy sample lines" />
          </div>
          <pre className={`${READOUT} max-h-72 whitespace-pre-wrap break-all`}>{p.sample_raw}</pre>
        </div>
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <h4 className="text-xs font-medium text-ink-2">Drafted mapping (YAML)</h4>
            <CopyButton value={p.proposed_yaml} label="Copy YAML" />
          </div>
          <pre className={`${READOUT} max-h-72`}>{p.proposed_yaml}</pre>
        </div>
      </div>

      {p.status === "pending" && (
        <footer className="space-y-3 border-t border-line px-4 py-3">
          {confirming ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
              <p className="min-w-0 flex-[1_1_24rem] text-sm text-ink-2">
                Approving writes this mapping to the approved mappings directory, activates{" "}
                <code className="code-inline">{p.source_format}</code> as a parser, and replays stored unrecognized events
                through it.
              </p>
              <div className="flex gap-2">
                <Button variant="primary" loading={busy === "approve"} onClick={approve}>
                  Activate parser
                </Button>
                <Button variant="ghost" autoFocus disabled={busy !== null} onClick={() => setConfirming(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" disabled={busy !== null} onClick={() => setConfirming(true)}>
                Approve…
              </Button>
              <Button loading={busy === "reject"} disabled={busy !== null} onClick={reject}>
                Reject
              </Button>
            </div>
          )}
          {error && <Callout tone="bad">{error}</Callout>}
        </footer>
      )}
    </article>
  );
}
