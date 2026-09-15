"use client";

import Link from "next/link";
import { ReactNode, useEffect, useRef, useState } from "react";
import { DriftTestResult, useDriftTest } from "@/components/DriftTest";
import { useConsole } from "@/components/Shell";
import { Button, Callout, EmptyState, Icon, PageHeader, Segmented, Skeleton, Status, TH } from "@/components/ui";
import { api, errorMessage, QuarantineItem, ResolveAction } from "@/lib/api";
import { driftSummary, sourceName, Tone, typeName, utc } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

type Filter = "held" | "resolved" | "all";

const STATUS: Record<string, { tone: Tone; label: string }> = {
  quarantine: { tone: "warn", label: "Held" },
  "auto-fix": { tone: "ok", label: "Released after coercion" },
  ignore: { tone: "neutral", label: "Released as received" },
};
const statusOf = (s: string) => STATUS[s] ?? { tone: "neutral" as const, label: s };

export default function DriftAlerts() {
  const { refresh } = useConsole();
  const [items, setItems] = useState<QuarantineItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("held");
  const [notice, setNotice] = useState<ReactNode>(null);

  const load = () =>
    api
      .quarantineList()
      .then((list) => {
        setItems(list);
        setLoadError(null);
      })
      .catch((e) => setLoadError(errorMessage(e)));
  usePolling(load, 4000);
  const drift = useDriftTest(load);

  // links like /quarantine#item-3 arrive before the list has rendered
  const scrolled = useRef(false);
  useEffect(() => {
    if (!items || scrolled.current) return;
    scrolled.current = true;
    if (window.location.hash) document.querySelector(window.location.hash)?.scrollIntoView({ block: "start" });
  }, [items]);

  const onResolved = (item: QuarantineItem, action: ResolveAction) => {
    setNotice(
      <>
        Quarantine #{item.id} from {sourceName(item.source_format)} was {statusOf(action).label.toLowerCase()}.{" "}
        {item.raw_event_id && (
          <Link href={`/events?id=${item.raw_event_id}`} className="link">
            View the normalized event
          </Link>
        )}
      </>,
    );
    load();
    refresh();
  };

  const heldCount = items?.filter((i) => i.status === "quarantine").length ?? 0;
  const resolvedCount = (items?.length ?? 0) - heldCount;
  const visible = (items ?? []).filter((i) =>
    filter === "all" ? true : filter === "held" ? i.status === "quarantine" : i.status !== "quarantine",
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Drift quarantine"
        description="When a known source sends a field with a changed type, or fields it has never sent before, the event is held here instead of being dropped or mis-mapped. Decide how each one enters the normalized store."
        actions={
          <Button loading={drift.sending} onClick={drift.send}>
            Send drifted test event
          </Button>
        }
      />

      <DriftTestResult result={drift.result} />
      {notice && <Callout tone="ok">{notice}</Callout>}
      {loadError && (
        <Callout tone="bad" title="The quarantine queue could not be loaded">
          {loadError}
        </Callout>
      )}

      <Segmented
        label="Filter by status"
        value={filter}
        onChange={setFilter}
        options={[
          { value: "held", label: `Held · ${heldCount}` },
          { value: "resolved", label: `Resolved · ${resolvedCount}` },
          { value: "all", label: "All" },
        ]}
      />

      {items === null && !loadError && (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <div key={i} className="space-y-2 rounded-md border border-line p-4">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          ))}
        </div>
      )}

      {items && visible.length === 0 && (
        <div className="rounded-md border border-line">
          {filter === "resolved" ? (
            <EmptyState icon="list" title="Nothing resolved yet">
              Items you release or keep appear here with the decision that was made.
            </EmptyState>
          ) : (
            <EmptyState
              icon="circleCheck"
              title="No events are held"
              action={
                <Button loading={drift.sending} onClick={drift.send}>
                  Send drifted test event
                </Button>
              }
            >
              Every source matches its learned schema. Send a drifted test event to see how the firewall responds.
            </EmptyState>
          )}
        </div>
      )}

      <div className="space-y-3">
        {visible.map((item) => (
          <QuarantineCard key={item.id} item={item} onResolved={onResolved} />
        ))}
      </div>
    </div>
  );
}

function QuarantineCard({
  item,
  onResolved,
}: {
  item: QuarantineItem;
  onResolved: (item: QuarantineItem, action: ResolveAction) => void;
}) {
  const held = item.status === "quarantine";
  const [open, setOpen] = useState(held);
  const [busy, setBusy] = useState<ResolveAction | null>(null);
  const [result, setResult] = useState<{ tone: Tone; text: string } | null>(null);

  const drift = item.alert.type_drift ?? {};
  const driftFields = Object.keys(drift);
  const newFields = item.alert.new_fields ?? [];
  const status = statusOf(item.status);
  const bodyId = `item-${item.id}-body`;

  const resolve = async (action: ResolveAction) => {
    setBusy(action);
    setResult(null);
    try {
      await api.resolveQuarantine(item.id, action);
      if (action === "quarantine") setResult({ tone: "neutral", text: "Still held. Nothing was written to the normalized store." });
      else onResolved(item, action);
    } catch (e) {
      setResult({ tone: "bad", text: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  };

  const actions: { action: ResolveAction; label: string; variant: "primary" | "secondary" | "ghost"; detail: string; show: boolean }[] = [
    {
      action: "auto-fix",
      label: "Coerce types and release",
      variant: "primary",
      detail: `Converts ${driftFields
        .map((f) => `${f} to ${drift[f].expected}`)
        .join(", ")}, records the conversion on the event, then normalizes it. Refused if the conversion would lose data.`,
      show: driftFields.length > 0,
    },
    {
      action: "ignore",
      label: "Release as received",
      variant: driftFields.length ? "secondary" : "primary",
      detail: "Normalizes this event once with the types it arrived with. The learned schema stays unchanged.",
      show: true,
    },
    {
      action: "quarantine",
      label: "Keep holding",
      variant: "ghost",
      detail: "Leaves the event in quarantine for later review.",
      show: true,
    },
  ];

  return (
    <article id={`item-${item.id}`} className="scroll-mt-20 overflow-hidden rounded-md border border-line">
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => setOpen((o) => !o)}
          className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-left transition-colors duration-150 hover:bg-raised/60"
        >
          <Icon name="chevronRight" className={`h-4 w-4 text-ink-3 transition-transform duration-150 ${open ? "rotate-90" : ""}`} />
          <Status tone={status.tone} className="text-sm">
            {status.label}
          </Status>
          <span className="text-sm font-medium text-ink">{sourceName(item.source_format)}</span>
          <span className="font-mono text-xs text-ink-2">{driftSummary(item)}</span>
          <span className="ml-auto text-xs tabular-nums text-ink-2">
            #{item.id} · {utc(item.created_at)} UTC
          </span>
        </button>
      </h3>

      {open && (
        <div id={bodyId} className="grid grid-cols-1 gap-6 border-t border-line p-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="min-w-0">
            <h4 className="mb-2 text-sm font-medium text-ink">Parsed fields</h4>
            <div className="relative overflow-x-auto rounded border border-line">
              <table className="w-full text-sm">
                <thead className="border-b border-line bg-canvas">
                  <tr>
                    <th className={TH}>Field</th>
                    <th className={TH}>Value</th>
                    <th className={TH}>Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line font-mono text-xs">
                  {Object.entries(item.fields).map(([field, value]) => {
                    const d = drift[field];
                    const isNew = newFields.includes(field);
                    return (
                      <tr key={field} className={d ? "bg-warn-soft" : isNew ? "bg-accent-soft" : undefined}>
                        <td className="whitespace-nowrap px-3 py-1.5 text-ink">{field}</td>
                        <td className="break-all px-3 py-1.5 text-ink">{JSON.stringify(value)}</td>
                        <td className="whitespace-nowrap px-3 py-1.5">
                          {d ? (
                            <span className="font-medium text-warn">
                              {d.received} <span className="font-sans font-normal text-ink-2">expected {d.expected}</span>
                            </span>
                          ) : (
                            <span className="text-ink-2">
                              {typeName(value)}
                              {isNew && <span className="ml-1.5 font-sans text-accent-ink">new field</span>}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="min-w-0">
            <h4 className="mb-2 text-sm font-medium text-ink">Decision</h4>
            {item.raw_event_id && (
              <p className="mb-3 text-sm text-ink-2">
                Raw event{" "}
                <Link href={`/events?id=${item.raw_event_id}`} className="link font-mono text-xs">
                  {item.raw_event_id}
                </Link>{" "}
                stays stored and hash-chained whatever you decide.
              </p>
            )}

            {held ? (
              item.raw_event_id ? (
                <ul className="divide-y divide-line">
                  {actions
                    .filter((a) => a.show)
                    .map((a) => (
                      <li key={a.action} className="py-3 first:pt-0 last:pb-0">
                        <Button
                          variant={a.variant}
                          loading={busy === a.action}
                          disabled={busy !== null}
                          onClick={() => resolve(a.action)}
                        >
                          {a.label}
                        </Button>
                        <p className="mt-1.5 text-xs text-ink-2">{a.detail}</p>
                      </li>
                    ))}
                </ul>
              ) : (
                <p className="text-sm text-ink-2">
                  No raw event is linked to this item, so it can only stay quarantined.
                </p>
              )
            ) : (
              <p className="text-sm text-ink">
                <Status tone={status.tone}>{status.label}</Status>
              </p>
            )}

            {result && (
              <Callout tone={result.tone} className="mt-3">
                {result.text}
              </Callout>
            )}
          </div>
        </div>
      )}
    </article>
  );
}
