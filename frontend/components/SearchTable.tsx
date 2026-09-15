"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { useConsole } from "@/components/Shell";
import {
  Arrow,
  Button,
  buttonClass,
  Callout,
  CONTROL,
  CopyButton,
  Disclosure,
  Disposition,
  EmptyState,
  Field,
  Icon,
  PageHeader,
  READOUT,
  Skeleton,
  SkeletonRows,
  TD,
  TH,
} from "@/components/ui";
import { api, errorMessage, OCSFEvent } from "@/lib/api";
import { endpoint, endpoints, eventClass, eventTitle, pct, protocol, SEVERITY, sourceName, utc } from "@/lib/format";

const LIMIT = 100;
const FILTERS = ["q", "source", "from", "to"] as const;
type Filters = Record<(typeof FILTERS)[number], string>;

// datetime-local carries no zone; the inputs are labelled UTC, like every time ULPF shows
const bound = (value: string) => (value ? `${value}Z` : "");

export default function SearchTable() {
  const router = useRouter();
  const params = useSearchParams();
  const { metrics } = useConsole();

  // the URL holds the applied filters and the open event, so every view is linkable
  const applied = Object.fromEntries(FILTERS.map((k) => [k, params.get(k) ?? ""])) as Filters;
  const appliedKey = FILTERS.map((k) => applied[k]).join("\n");
  const selectedId = params.get("id");

  const [draft, setDraft] = useState<Filters>(applied);
  const [results, setResults] = useState<OCSFEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [checked, setChecked] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setDraft(applied);
    let cancelled = false;
    setLoading(true);
    setError(null);
    const range = applied.from || applied.to ? `${bound(applied.from)}/${bound(applied.to)}` : undefined;
    api
      .search(applied.q, applied.source || undefined, range, LIMIT)
      .then((r) => !cancelled && setResults(r.results))
      .catch((e) => !cancelled && setError(errorMessage(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // applied is derived from appliedKey
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appliedKey, attempt]);

  const setParams = (next: Record<string, string | null>, mode: "push" | "replace") => {
    const sp = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) {
      if (v) sp.set(k, v);
      else sp.delete(k);
    }
    const qs = sp.toString();
    router[mode](qs ? `/events?${qs}` : "/events", { scroll: false });
  };

  const rangeError = draft.from && draft.to && draft.from > draft.to ? "The start of the range must be before the end." : null;
  const hasFilters = FILTERS.some((k) => applied[k]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (rangeError) return;
    const next = { ...draft, q: draft.q.trim() };
    if (FILTERS.every((k) => next[k] === applied[k])) setAttempt((a) => a + 1);
    else setParams(Object.fromEntries(FILTERS.map((k) => [k, next[k] || null])), "push");
  };

  const clearFilters = () => setParams(Object.fromEntries(FILTERS.map((k) => [k, null])), "push");
  const openEvent = (id: string) => setParams({ id }, "replace");

  const toggle = (id: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const pageIds = results?.map((r) => r.ulpf.raw_event_id) ?? [];
  const allChecked = pageIds.length > 0 && pageIds.every((id) => checked.has(id));
  const toggleAll = () =>
    setChecked((prev) => {
      const next = new Set(prev);
      pageIds.forEach((id) => (allChecked ? next.delete(id) : next.add(id)));
      return next;
    });

  const sources = Array.from(
    new Set([...Object.keys(metrics?.normalized_by_source ?? {}), ...(applied.source ? [applied.source] : [])]),
  ).sort();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Events"
        description="Normalized OCSF events from every source, most recently ingested first. Open an event to trace it back to its raw log."
      />

      <form onSubmit={submit} role="search" aria-label="Filter events" className="flex flex-wrap items-end gap-3">
        <div className="min-w-[14rem] flex-[2_1_20rem]">
          <label htmlFor="events-q" className="mb-1 block text-xs font-medium text-ink-2">
            Search
          </label>
          <div className="relative">
            <Icon name="search" className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" />
            <input
              id="events-q"
              type="search"
              value={draft.q}
              onChange={(e) => setDraft({ ...draft, q: e.target.value })}
              placeholder="IP address, product, disposition"
              className={`${CONTROL} w-full pl-8`}
            />
          </div>
        </div>
        <div className="flex-[1_1_10rem]">
          <label htmlFor="events-source" className="mb-1 block text-xs font-medium text-ink-2">
            Source
          </label>
          <select
            id="events-source"
            value={draft.source}
            onChange={(e) => setDraft({ ...draft, source: e.target.value })}
            className={`${CONTROL} w-full`}
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {sourceName(s)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-[1_1_11rem]">
          <label htmlFor="events-from" className="mb-1 block text-xs font-medium text-ink-2">
            From (UTC)
          </label>
          <input
            id="events-from"
            type="datetime-local"
            value={draft.from}
            onChange={(e) => setDraft({ ...draft, from: e.target.value })}
            aria-invalid={rangeError ? true : undefined}
            aria-describedby={rangeError ? "range-error" : undefined}
            className={`${CONTROL} w-full`}
          />
        </div>
        <div className="flex-[1_1_11rem]">
          <label htmlFor="events-to" className="mb-1 block text-xs font-medium text-ink-2">
            To (UTC)
          </label>
          <input
            id="events-to"
            type="datetime-local"
            value={draft.to}
            onChange={(e) => setDraft({ ...draft, to: e.target.value })}
            aria-invalid={rangeError ? true : undefined}
            aria-describedby={rangeError ? "range-error" : undefined}
            className={`${CONTROL} w-full`}
          />
        </div>
        <div className="flex gap-2">
          <Button type="submit" variant="primary">
            Search
          </Button>
          {hasFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
        {rangeError && (
          <p id="range-error" className="basis-full text-xs text-bad">
            {rangeError}
          </p>
        )}
      </form>

      <div className={`grid grid-cols-1 items-start gap-6 ${selectedId ? "xl:grid-cols-[minmax(0,1fr)_26rem]" : ""}`}>
        <div className="min-w-0 space-y-3">
          <div className="flex min-h-8 flex-wrap items-center justify-between gap-2 text-sm">
            <p className="text-ink-2" aria-live="polite">
              {results === null
                ? loading
                  ? "Loading events…"
                  : ""
                : results.length === LIMIT
                  ? `Showing the ${LIMIT} most recent matches`
                  : `${results.length} ${results.length === 1 ? "event" : "events"}`}
            </p>
            {checked.size > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-ink-2">{checked.size} selected</span>
                <Link href={`/reports?ids=${Array.from(checked).join(",")}`} className={buttonClass("primary", "sm")}>
                  Draft incident report
                </Link>
                <Button size="sm" variant="ghost" onClick={() => setChecked(new Set())}>
                  Clear selection
                </Button>
              </div>
            )}
          </div>

          {error && (
            <Callout
              tone="bad"
              title="Search failed"
              action={
                <Button size="sm" onClick={() => setAttempt((a) => a + 1)}>
                  Retry
                </Button>
              }
            >
              {error}
            </Callout>
          )}

          <div className="relative overflow-x-auto rounded-md border border-line" aria-busy={loading}>
            <table className={`w-full min-w-[58rem] text-sm transition-opacity duration-150 ${loading && results ? "opacity-60" : ""}`}>
              <thead className="border-b border-line bg-canvas">
                <tr>
                  <th className="w-10 px-3 py-2">
                    <label className="-m-2 flex p-2">
                      <input
                        type="checkbox"
                        checked={allChecked}
                        onChange={toggleAll}
                        disabled={!pageIds.length}
                        aria-label="Select all events shown"
                        className="h-4 w-4"
                      />
                    </label>
                  </th>
                  <th className={TH}>Time (UTC)</th>
                  <th className={TH}>Product</th>
                  <th className={TH}>Event</th>
                  <th className={TH}>
                  Source <Arrow /> destination
                </th>
                  <th className={TH}>Protocol</th>
                  <th className={TH}>Disposition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {results === null && loading && <SkeletonRows cols={7} />}
                {results?.map((e) => {
                  const id = e.ulpf.raw_event_id;
                  const isOpen = id === selectedId;
                  const { src, dst } = endpoints(e);
                  return (
                    <tr
                      key={id}
                      onClick={() => openEvent(id)}
                      className={`cursor-pointer transition-colors duration-150 ${isOpen ? "bg-accent-soft" : "hover:bg-raised/60"}`}
                    >
                      <td className="px-3 py-2" onClick={(ev) => ev.stopPropagation()}>
                        <label className="-m-2 flex p-2">
                          <input
                            type="checkbox"
                            checked={checked.has(id)}
                            onChange={() => toggle(id)}
                            aria-label={`Select event ${id}`}
                            className="h-4 w-4"
                          />
                        </label>
                      </td>
                      <td className={`${TD} whitespace-nowrap`}>
                        <button
                          type="button"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            openEvent(id);
                          }}
                          aria-controls="event-detail"
                          aria-expanded={isOpen}
                          className="rounded-sm font-mono text-xs tabular-nums text-ink hover:underline"
                        >
                          {utc(e.time)}
                        </button>
                      </td>
                      <td className={`${TD} whitespace-nowrap`}>{e.metadata.product.name}</td>
                      <td className={`${TD} max-w-[20rem]`}>
                        <span className="block truncate" title={eventTitle(e)}>
                          {e.severity_id != null && <span className="text-ink-2">{SEVERITY[e.severity_id]} · </span>}
                          {eventTitle(e)}
                        </span>
                      </td>
                      <td className={`${TD} whitespace-nowrap font-mono text-xs`}>
                        {endpoint(src)}
                        <Arrow />
                        {endpoint(dst)}
                      </td>
                      <td className={`${TD} text-xs uppercase text-ink-2`}>{protocol(e) ?? "—"}</td>
                      <td className={TD}>
                        <Disposition value={e.disposition} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {results?.length === 0 && !loading && (
              <EmptyState
                icon="search"
                title={hasFilters ? "No events match these filters" : "No events ingested yet"}
                action={hasFilters ? <Button onClick={clearFilters}>Clear filters</Button> : undefined}
              >
                {hasFilters
                  ? "Try a broader search or a wider time range. Times are in UTC."
                  : "Send logs to UDP or TCP 514 through Vector, or POST raw lines to /ingest."}
              </EmptyState>
            )}
          </div>
        </div>

        {selectedId && <EventDetail id={selectedId} onClose={() => setParams({ id: null }, "replace")} />}
      </div>
    </div>
  );
}

function EventDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const [data, setData] = useState<{ ocsf: OCSFEvent | null; raw: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    api
      .getEvent(id)
      .then((r) => !cancelled && setData({ ocsf: r.ocsf_event, raw: r.raw_log }))
      .catch((e) => !cancelled && setError(errorMessage(e)));
    return () => {
      cancelled = true;
    };
  }, [id]);

  // below xl the panel covers the table: move focus in, and give it back on close
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    if (!window.matchMedia("(min-width: 1280px)").matches) closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, []);

  const e = data?.ocsf;
  const ends = e ? endpoints(e) : null;
  const resolution = e?.ulpf.drift_resolution;

  return (
    <>
      <div aria-hidden="true" onClick={onClose} className="fixed inset-0 z-scrim bg-scrim/40 xl:hidden" />
      <aside
        id="event-detail"
        aria-label={`Event ${id}`}
        className="sheet-in fixed inset-y-0 right-0 z-drawer flex w-full max-w-lg flex-col border-l border-line bg-surface xl:sticky xl:bottom-auto xl:right-auto xl:top-20 xl:z-0 xl:max-h-[calc(100vh-7rem)] xl:max-w-none xl:self-start xl:rounded-md xl:border"
      >
        <div className="flex shrink-0 items-center gap-2 border-b border-line px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs text-ink-2">Event</p>
            <p className="flex items-center gap-1 font-mono text-sm text-ink">
              <span className="truncate">{id}</span>
              <CopyButton value={id} label="Copy event ID" />
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close event details"
            className="grid h-8 w-8 place-items-center rounded text-ink-2 hover:bg-raised hover:text-ink"
          >
            <Icon name="x" />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
          {error && (
            <Callout tone="bad" title="This event could not be loaded">
              {error}
            </Callout>
          )}
          {!data && !error && (
            <div className="space-y-3" aria-label="Loading event">
              {Array.from({ length: 7 }, (_, i) => (
                <div key={i} className="grid grid-cols-[8.5rem_1fr] gap-3">
                  <Skeleton className="h-3.5 w-20" />
                  <Skeleton className="h-3.5 w-full max-w-[12rem]" />
                </div>
              ))}
            </div>
          )}

          {data && !e && (
            <Callout tone="warn" title="Not in the normalized store">
              The raw log below is stored and hash-chained, but it was not normalized: it is held in drift quarantine, or no
              parser recognized its format.
            </Callout>
          )}

          {e && ends && (
            <dl className="-my-2 divide-y divide-line text-sm">
              <Field label="Time (UTC)">
                <span className="font-mono text-xs tabular-nums">{utc(e.time)}</span>
              </Field>
              <Field label="Product">
                {e.metadata.product.name} <span className="text-ink-2">· {e.metadata.product.vendor_name}</span>
              </Field>
              <Field label="Class">
                {eventClass(e)} <span className="text-ink-2">· {e.class_uid}</span>
              </Field>
              {e.finding_info ? (
                <Field label="Finding">
                  {e.finding_info.title} <span className="text-ink-2">· rule {e.finding_info.uid}</span>
                </Field>
              ) : (
                <Field label="Activity">{e.activity_name}</Field>
              )}
              {e.severity_id != null && <Field label="Severity">{SEVERITY[e.severity_id] ?? e.severity_id}</Field>}
              <Field label="Disposition">
                <Disposition value={e.disposition} />
              </Field>
              <Field label="Source">
                <span className="font-mono text-xs">{endpoint(ends.src)}</span>
              </Field>
              <Field label="Destination">
                <span className="font-mono text-xs">{endpoint(ends.dst)}</span>
              </Field>
              <Field label="Protocol">
                <span className="uppercase">{protocol(e) ?? "—"}</span>
              </Field>
            </dl>
          )}

          {data && (
            <section aria-labelledby="raw-heading">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <h3 id="raw-heading" className="text-sm font-medium text-ink">
                  Raw log
                </h3>
                {data.raw && <CopyButton value={data.raw} label="Copy raw log" />}
              </div>
              <pre className={`${READOUT} max-h-48 whitespace-pre-wrap break-all`}>{data.raw ?? "Raw bytes not found."}</pre>
              <p className="mt-1.5 text-xs text-ink-2">
                Stored byte-for-byte. The normalized record carries this log&apos;s SHA-256 hash.
              </p>
            </section>
          )}

          {e && (
            <section aria-labelledby="trace-heading">
              <h3 id="trace-heading" className="mb-1 text-sm font-medium text-ink">
                Traceability
              </h3>
              <dl className="divide-y divide-line text-sm">
                <Field label="Raw event hash">
                  <span className="flex items-start gap-1">
                    <span className="break-all font-mono text-xs leading-5">{e.ulpf.raw_event_hash}</span>
                    <CopyButton value={e.ulpf.raw_event_hash} label="Copy hash" />
                  </span>
                </Field>
                <Field label="Parser">
                  <span className="font-mono text-xs">{e.ulpf.parser_version}</span>
                </Field>
                <Field label="Mapping confidence">{pct(e.ulpf.mapping_confidence)}</Field>
                <Field label="OCSF version">{e.metadata.version}</Field>
                {resolution && (
                  <Field label="Drift review">
                    {resolution.action === "auto-fix"
                      ? `Released after coercion: ${Object.entries(resolution.coerced ?? {})
                          .map(([field, c]) => `${field} converted from ${c.from} to ${c.to}`)
                          .join(", ")}`
                      : "Released with the types it arrived with"}
                  </Field>
                )}
              </dl>
            </section>
          )}

          {e && (
            <div className="space-y-2">
              <Disclosure title={`Unmapped fields (${Object.keys(e.unmapped ?? {}).length})`}>
                <pre className="max-h-64 overflow-auto bg-sunken p-3 font-mono text-xs leading-5 text-ink">
                  {JSON.stringify(e.unmapped, null, 2)}
                </pre>
              </Disclosure>
              <Disclosure title="Normalized OCSF event">
                <pre className="max-h-96 overflow-auto bg-sunken p-3 font-mono text-xs leading-5 text-ink">
                  {JSON.stringify(e, null, 2)}
                </pre>
              </Disclosure>
            </div>
          )}
        </div>

        {e && (
          <div className="shrink-0 border-t border-line px-4 py-3">
            <Link href={`/reports?ids=${id}`} className={buttonClass("secondary")}>
              <Icon name="file" className="h-3.5 w-3.5" />
              Draft incident report
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
