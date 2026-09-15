"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { DriftTestResult, useDriftTest } from "@/components/DriftTest";
import { useConsole } from "@/components/Shell";
import {
  Arrow,
  Button,
  buttonClass,
  Disposition,
  EmptyState,
  Icon,
  PageHeader,
  Section,
  Skeleton,
  SkeletonRows,
  Status,
  StatusMark,
  TD,
  TH,
  TONE_TEXT,
} from "@/components/ui";
import { api, OCSFEvent, QuarantineItem } from "@/lib/api";
import { driftSummary, endpoint, endpoints, eventTitle, formatNumber, pct, sourceName, Tone, utc } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";

function Figure({ label, value, detail, tone }: { label: string; value: ReactNode; detail: ReactNode; tone?: Tone }) {
  return (
    <div className="min-w-0 bg-surface px-4 py-3">
      <dt className="text-xs text-ink-2">{label}</dt>
      <dd className={`mt-1 text-xl font-semibold tabular-nums ${tone ? TONE_TEXT[tone] : "text-ink"}`}>{value}</dd>
      <dd className="mt-0.5 truncate text-xs text-ink-2">{detail}</dd>
    </div>
  );
}

interface ReviewItem {
  key: string;
  tone: Tone;
  title: string;
  detail: string;
  href: string;
}

export default function DashboardMetrics() {
  const router = useRouter();
  const { metrics, pendingProposals } = useConsole();
  const [held, setHeld] = useState<QuarantineItem[] | null>(null);
  const [latest, setLatest] = useState<OCSFEvent[] | null>(null);

  const loadHeld = () => api.quarantineList("quarantine").then(setHeld).catch(() => {});
  usePolling(loadHeld, 4000);
  const drift = useDriftTest(loadHeld);

  // new events are what change this list, so refetch only when the normalized total moves
  const total = metrics?.total_normalized;
  useEffect(() => {
    api
      .search("", undefined, undefined, 8)
      .then((r) => setLatest(r.results))
      .catch(() => {});
  }, [total]);

  const received = metrics ? metrics.total_normalized + metrics.drift_count : 0;
  const sources = metrics
    ? Array.from(new Set([...Object.keys(metrics.normalized_by_source), ...Object.keys(metrics.drift_by_source)])).sort(
        (a, b) => (metrics.normalized_by_source[b] ?? 0) - (metrics.normalized_by_source[a] ?? 0),
      )
    : [];

  const review: ReviewItem[] = [
    ...(metrics && !metrics.chain_verified
      ? [{ key: "chain", tone: "bad" as const, title: "Hash chain verification failed", detail: "A stored raw event no longer matches the chain.", href: "/integrity" }]
      : []),
    ...(held ?? []).slice(0, 5).map((item) => ({
      key: `drift-${item.id}`,
      tone: "warn" as const,
      title: `Schema drift from ${sourceName(item.source_format)}`,
      detail: `${driftSummary(item)} · ${utc(item.created_at)} UTC`,
      href: `/quarantine#item-${item.id}`,
    })),
    ...(pendingProposals
      ? [
          {
            key: "proposals",
            tone: "accent" as const,
            title: `${pendingProposals} parser ${pendingProposals === 1 ? "proposal" : "proposals"} awaiting approval`,
            detail: "Drafted by the local model for unrecognized formats.",
            href: "/proposals",
          },
        ]
      : []),
  ];
  const moreHeld = (held?.length ?? 0) - 5;

  return (
    <div className="space-y-10">
      <PageHeader title="Overview" description="Pipeline health across every connected perimeter source." />

      {metrics ? (
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-3 xl:grid-cols-6">
          <Figure label="Ingest rate" value={`${metrics.events_per_sec.toFixed(1)}/s`} detail="10-second rolling window" />
          <Figure
            label="Normalized"
            value={received ? pct(metrics.total_normalized / received, 1) : "—"}
            detail={`${formatNumber(metrics.total_normalized)} stored · ${formatNumber(metrics.drift_count)} held`}
          />
          <Figure
            label="Held for review"
            value={formatNumber(metrics.drift_count)}
            tone={metrics.drift_count ? "warn" : undefined}
            detail={
              metrics.drift_count ? (
                <Link href="/quarantine" className="link">
                  Review quarantine
                </Link>
              ) : (
                "No schema drift"
              )
            }
          />
          <Figure label="Unmapped fields" value={pct(metrics.unmapped_field_ratio, 1)} detail="Kept, not dropped" />
          <Figure label="Raw logs preserved" value={pct(metrics.raw_preservation_pct / 100)} detail="Byte-for-byte, hash-linked" />
          <Figure
            label="Hash chain"
            value={
              <Status tone={metrics.chain_verified ? "ok" : "bad"} className={metrics.chain_verified ? "text-ink" : "text-bad"}>
                {metrics.chain_verified ? "Verified" : "Tampered"}
              </Status>
            }
            detail={
              <Link href="/integrity" className="link">
                Run full verification
              </Link>
            }
          />
        </dl>
      ) : (
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line sm:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="space-y-2 bg-surface px-4 py-3">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-3 w-28" />
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-10 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Section
          title="Sources"
          description="Normalized volume and schema health for each log format."
          actions={
            <Button size="sm" loading={drift.sending} onClick={drift.send} title="Sends a Cisco ASA event with a changed field type">
              Send drifted test event
            </Button>
          }
        >
          <div className="space-y-3">
            <DriftTestResult result={drift.result} showLink />
            <div className="relative overflow-x-auto rounded-md border border-line">
              <table className="w-full min-w-[40rem] text-sm">
                <thead className="border-b border-line bg-canvas">
                  <tr>
                    <th className={TH}>Source</th>
                    <th className={TH}>Schema</th>
                    <th className={`${TH} text-right`}>Normalized</th>
                    <th className={`${TH} text-right`}>Held</th>
                    <th className={`${TH} w-48`}>Share of volume</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {!metrics && <SkeletonRows cols={5} rows={4} />}
                  {metrics &&
                    sources.map((source) => {
                      const count = metrics.normalized_by_source[source] ?? 0;
                      const heldCount = metrics.drift_by_source[source] ?? 0;
                      const share = metrics.total_normalized ? count / metrics.total_normalized : 0;
                      return (
                        <tr key={source}>
                          <td className={TD}>
                            <Link
                              href={`/events?source=${encodeURIComponent(source)}`}
                              title={`View ${sourceName(source)} events`}
                              className="rounded-sm font-medium text-ink hover:underline"
                            >
                              {sourceName(source)}
                            </Link>
                            <div className="font-mono text-xs text-ink-2">{source}</div>
                          </td>
                          <td className={TD}>
                            <Status tone={heldCount ? "warn" : "ok"}>{heldCount ? "Drift detected" : "Matches learned schema"}</Status>
                          </td>
                          <td className={`${TD} text-right tabular-nums`}>{formatNumber(count)}</td>
                          <td className={`${TD} text-right tabular-nums ${heldCount ? "font-medium text-warn" : "text-ink-2"}`}>
                            {formatNumber(heldCount)}
                          </td>
                          <td className={TD}>
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                                <div className="h-full rounded-full bg-ink-3" style={{ width: `${share * 100}%` }} />
                              </div>
                              <span className="w-9 text-right text-xs tabular-nums text-ink-2">{pct(share)}</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
              {metrics && sources.length === 0 && (
                <EmptyState icon="activity" title="No sources yet">
                  Send logs to UDP or TCP 514 through Vector, or POST raw lines to /ingest. Each recognized format appears
                  here with its volume and schema health.
                </EmptyState>
              )}
            </div>
          </div>
        </Section>

        <Section title="Needs review">
          {held === null && !metrics ? (
            <div className="space-y-3 rounded-md border border-line p-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ) : review.length === 0 ? (
            <div className="rounded-md border border-line">
              <EmptyState icon="circleCheck" title="Nothing needs review">
                Every source matches its learned schema, the chain verifies, and no parser proposals are pending.
              </EmptyState>
            </div>
          ) : (
            <ul className="divide-y divide-line overflow-hidden rounded-md border border-line">
              {review.map((item) => (
                <li key={item.key}>
                  <Link href={item.href} className="group flex items-start gap-3 px-3 py-2.5 transition-colors duration-150 hover:bg-raised">
                    <StatusMark tone={item.tone} className="mt-1.5 h-2 w-2" />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-ink">{item.title}</span>
                      <span className="block truncate text-xs text-ink-2">{item.detail}</span>
                    </span>
                    <Icon name="chevronRight" className="mt-0.5 h-4 w-4 text-ink-3 group-hover:text-ink" />
                  </Link>
                </li>
              ))}
              {moreHeld > 0 && (
                <li className="px-3 py-2 text-xs">
                  <Link href="/quarantine" className="link">
                    {moreHeld} more held in quarantine
                  </Link>
                </li>
              )}
            </ul>
          )}
        </Section>
      </div>

      <Section
        title="Latest events"
        description="Most recently ingested, across all sources."
        actions={
          <Link href="/events" className={buttonClass("secondary", "sm")}>
            Open Events
          </Link>
        }
      >
        <div className="relative overflow-x-auto rounded-md border border-line">
          <table className="w-full min-w-[48rem] text-sm">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className={TH}>Time (UTC)</th>
                <th className={TH}>Product</th>
                <th className={TH}>Event</th>
                <th className={TH}>
                  Source <Arrow /> destination
                </th>
                <th className={TH}>Disposition</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {latest === null && <SkeletonRows cols={5} rows={5} />}
              {latest?.map((e) => {
                const id = e.ulpf.raw_event_id;
                const { src, dst } = endpoints(e);
                return (
                  <tr
                    key={id}
                    onClick={() => router.push(`/events?id=${id}`)}
                    className="cursor-pointer transition-colors duration-150 hover:bg-raised/60"
                  >
                    <td className={`${TD} whitespace-nowrap`}>
                      <Link
                        href={`/events?id=${id}`}
                        onClick={(ev) => ev.stopPropagation()}
                        className="font-mono text-xs tabular-nums text-ink hover:underline"
                      >
                        {utc(e.time)}
                      </Link>
                    </td>
                    <td className={`${TD} whitespace-nowrap`}>{e.metadata.product.name}</td>
                    <td className={`${TD} max-w-[20rem]`}>
                      <span className="block truncate" title={eventTitle(e)}>
                        {eventTitle(e)}
                      </span>
                    </td>
                    <td className={`${TD} whitespace-nowrap font-mono text-xs`}>
                      {endpoint(src)}
                        <Arrow />
                        {endpoint(dst)}
                    </td>
                    <td className={TD}>
                      <Disposition value={e.disposition} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {latest?.length === 0 && <EmptyState icon="list" title="No events yet">Normalized events appear here as they arrive.</EmptyState>}
        </div>
      </Section>
    </div>
  );
}
