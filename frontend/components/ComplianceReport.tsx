"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ClipboardEvent, FormEvent, KeyboardEvent, useEffect, useState } from "react";
import { Button, Callout, CONTROL, copyText, EmptyState, Field, Icon, PageHeader, Section, Skeleton } from "@/components/ui";
import { api, ComplianceProfile, errorMessage } from "@/lib/api";
import { utc } from "@/lib/format";

const splitIds = (text: string) => text.split(/[\s,]+/).filter(Boolean);

export default function ComplianceReport() {
  const params = useSearchParams();
  const [ids, setIds] = useState<string[]>(() => splitIds(params.get("ids") ?? ""));
  const [pending, setPending] = useState("");
  const [contact, setContact] = useState("SOC Duty Officer");
  const [report, setReport] = useState<{ markdown: string; at: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ComplianceProfile | null>(null);
  const [profileError, setProfileError] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .complianceProfile()
      .then(setProfile)
      .catch(() => setProfileError(true));
  }, []);

  const addIds = (text: string) => {
    const next = splitIds(text);
    if (next.length) setIds((prev) => Array.from(new Set([...prev, ...next])));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === "Enter" || e.key === "," || e.key === " ") && pending.trim()) {
      e.preventDefault();
      addIds(pending);
      setPending("");
    } else if (e.key === "Backspace" && !pending && ids.length) {
      setIds(ids.slice(0, -1));
    }
  };

  const onPaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    addIds(e.clipboardData.getData("text"));
  };

  const generate = async (e: FormEvent) => {
    e.preventDefault();
    const all = Array.from(new Set([...ids, ...splitIds(pending)]));
    setIds(all);
    setPending("");
    if (!all.length) return;
    setLoading(true);
    setError(null);
    try {
      const { report_markdown } = await api.complianceReport(all, contact.trim() || "SOC Duty Officer");
      setReport({ markdown: report_markdown, at: Date.now() });
      setCopied(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (report && (await copyText(report.markdown))) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const download = () => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([report.markdown], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `cert-in-incident-draft-${new Date(report.at).toISOString().slice(0, 19).replace(/[:T]/g, "-")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Incident reports"
        description="Draft a CERT-In-format incident report from normalized events. Every field except the point of contact is derived from the events themselves."
      />
      <p className="flex max-w-[72ch] items-start gap-2 text-sm text-ink-2">
        <Icon name="info" className="mt-0.5 h-4 w-4 text-ink-3" />
        {/* the one approved sentence for any CERT-In/SEBI/NCIIPC reference (PRD §8.1); keep it verbatim */}
        <span>
          ULPF provides technical controls and evidence that support applicable{" "}
          <span className="whitespace-nowrap">CERT-In/SEBI/NCIIPC</span> requirements.
        </span>
      </p>

      <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <div className="space-y-10">
          <form onSubmit={generate} className="space-y-4" aria-label="Report details">
            <div>
              <label htmlFor="event-ids" className="text-sm font-medium text-ink">
                Events
              </label>
              <p id="event-ids-hint" className="text-xs text-ink-2">
                Paste raw event IDs, or select events on the{" "}
                <Link href="/events" className="link">
                  Events
                </Link>{" "}
                page and choose Draft incident report.
              </p>
              <div className="mt-1.5 flex min-h-8 flex-wrap items-center gap-1 rounded border border-control bg-surface p-1 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent-ink">
                {ids.map((id) => (
                  <span key={id} className="inline-flex h-7 items-center gap-0.5 rounded-sm bg-raised pl-2 font-mono text-xs text-ink">
                    {id}
                    <button
                      type="button"
                      onClick={() => setIds(ids.filter((x) => x !== id))}
                      aria-label={`Remove ${id}`}
                      className="grid h-6 w-6 place-items-center rounded-sm text-ink-3 hover:bg-line hover:text-ink"
                    >
                      <Icon name="x" className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                <input
                  id="event-ids"
                  aria-describedby="event-ids-hint"
                  value={pending}
                  onChange={(e) => setPending(e.target.value)}
                  onKeyDown={onKeyDown}
                  onPaste={onPaste}
                  onBlur={() => {
                    addIds(pending);
                    setPending("");
                  }}
                  placeholder={ids.length ? "Add another" : "evt_…"}
                  spellCheck={false}
                  className="h-7 min-w-[7rem] flex-1 bg-transparent px-1.5 font-mono text-xs text-ink placeholder:text-ink-3 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="contact" className="text-sm font-medium text-ink">
                Point of contact
              </label>
              <input id="contact" value={contact} onChange={(e) => setContact(e.target.value)} className={`${CONTROL} mt-1.5 w-full`} />
            </div>

            <Button type="submit" variant="primary" loading={loading} disabled={!ids.length && !pending.trim()}>
              Generate draft
            </Button>
            {error && (
              <Callout tone="bad" title="The draft could not be generated">
                {error}
              </Callout>
            )}
          </form>

          <Section title="Active profile">
            {profile ? (
              <dl className="divide-y divide-line rounded-md border border-line px-3 text-sm">
                <Field label="Regulator">{profile.regulator}</Field>
                <Field label="Log retention">{profile.retention_days} days</Field>
                <Field label="Jurisdiction">{profile.jurisdiction}</Field>
                <Field label="Report deadline">{profile.incident_report_deadline_hours} hours from detection</Field>
                <Field label="Time source">
                  <span className="font-mono text-xs">{profile.ntp_server}</span>
                </Field>
              </dl>
            ) : profileError ? (
              <p className="text-sm text-ink-2">The compliance profile could not be loaded.</p>
            ) : (
              <div className="space-y-2 rounded-md border border-line p-3">
                <Skeleton className="h-3.5 w-2/3" />
                <Skeleton className="h-3.5 w-1/2" />
                <Skeleton className="h-3.5 w-3/5" />
              </div>
            )}
          </Section>
        </div>

        <section aria-labelledby="report-heading" className="min-w-0">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 id="report-heading" className="text-lg font-semibold text-ink">
                Draft
              </h2>
              <p className="text-sm text-ink-2">
                {report
                  ? `Generated ${utc(report.at)} UTC. Review before submitting.`
                  : "Review every draft before submitting it."}
              </p>
            </div>
            {report && (
              <div className="flex gap-2">
                <Button size="sm" onClick={copy}>
                  <Icon name={copied ? "check" : "copy"} className="h-3.5 w-3.5" />
                  {copied ? "Copied" : "Copy Markdown"}
                </Button>
                <Button size="sm" onClick={download}>
                  <Icon name="download" className="h-3.5 w-3.5" />
                  Download .md
                </Button>
              </div>
            )}
          </div>
          <div className="rounded-md border border-line bg-sunken">
            {report ? (
              <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap p-5 font-mono text-xs leading-5 text-ink">
                {report.markdown}
              </pre>
            ) : (
              <EmptyState icon="file" title="No draft yet">
                Add one or more events and generate a draft. It appears here as Markdown you can copy or download.
              </EmptyState>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
