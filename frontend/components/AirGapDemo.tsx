"use client";

import { useEffect, useState } from "react";
import { useConsole } from "@/components/Shell";
import { Button, Callout, Field, Icon, IconName, PageHeader, Section, Status, TD, TH } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { Tone, utcTime } from "@/lib/format";

interface Check {
  at: number;
  verified: boolean;
  ms: number;
}

const HEAD: Record<"idle" | "intact" | "tampered", { tone: Tone; icon: IconName; circle: string }> = {
  idle: { tone: "neutral", icon: "link", circle: "bg-raised text-ink-2" },
  intact: { tone: "ok", icon: "circleCheck", circle: "bg-ok-soft text-ok" },
  tampered: { tone: "bad", icon: "circleX", circle: "bg-bad-soft text-bad" },
};

export default function AirGapDemo() {
  const { metrics } = useConsole();
  const [online, setOnline] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);
  const [checks, setChecks] = useState<Check[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const verify = async () => {
    setChecking(true);
    setError(null);
    const started = performance.now();
    try {
      const { verified } = await api.verifyChain();
      setChecks((c) => [{ at: Date.now(), verified, ms: Math.round(performance.now() - started) }, ...c].slice(0, 10));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setChecking(false);
    }
  };

  const last = checks[0];
  const state = !last ? "idle" : last.verified ? "intact" : "tampered";
  const head = HEAD[state];

  return (
    <div className="space-y-10">
      <PageHeader
        title="Integrity"
        description="Each raw log is SHA-256 hash-chained when it arrives. A full verification replays the chain and re-hashes every stored raw event from disk, so an altered or deleted record is detected, not assumed absent."
      />

      <div className="grid grid-cols-1 items-start gap-10 xl:grid-cols-2">
        <Section title="Hash chain">
          <div className="overflow-hidden rounded-md border border-line">
            <div className="relative flex flex-wrap items-center gap-4 p-4">
              {checking && (
                <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden" aria-hidden="true">
                  <div className="progress-indeterminate h-full w-2/5 bg-accent" />
                </div>
              )}
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${head.circle}`}>
                <Icon name={head.icon} className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-[1_1_14rem]" aria-live="polite">
                <p className={`text-base font-semibold ${state === "tampered" ? "text-bad" : "text-ink"}`}>
                  {state === "intact" && "Chain verified intact"}
                  {state === "tampered" && "Tampering detected"}
                  {state === "idle" && (checking ? "Verifying the full chain…" : "Not verified in this session")}
                </p>
                <p className="text-sm text-ink-2">
                  {state === "intact" && `Full verification at ${utcTime(last.at)} UTC, ${last.ms} ms round trip.`}
                  {state === "tampered" &&
                    "A stored raw event no longer matches the chain. Preserve the raw store as evidence before changing anything."}
                  {state === "idle" && "Run a full verification to re-hash every stored raw event."}
                </p>
              </div>
              <Button variant="primary" loading={checking} onClick={verify}>
                {checking ? "Verifying…" : "Verify now"}
              </Button>
            </div>

            {error && (
              <div className="px-4 pb-4">
                <Callout tone="bad" title="Verification did not run">
                  {error}
                </Callout>
              </div>
            )}

            <dl className="divide-y divide-line border-t border-line px-4 text-sm">
              <Field label="Background status">
                {metrics ? (
                  <Status tone={metrics.chain_verified ? "ok" : "bad"}>
                    {metrics.chain_verified ? "Verified" : "Tampered"}
                    <span className="text-ink-2">· refreshed every few seconds</span>
                  </Status>
                ) : (
                  "—"
                )}
              </Field>
              <Field label="Method">Each record&apos;s SHA-256 hash includes the previous record&apos;s hash</Field>
              <Field label="Scope">Every raw event on disk, including unrecognized and quarantined ones</Field>
            </dl>

            {checks.length > 0 && (
              <div className="border-t border-line">
                <h3 className="px-4 pb-1 pt-3 text-sm font-medium text-ink">Verifications this session</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line">
                      <th className={`${TH} pl-4`}>Time (UTC)</th>
                      <th className={TH}>Result</th>
                      <th className={`${TH} pr-4 text-right`}>Round trip</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {checks.map((c) => (
                      <tr key={c.at}>
                        <td className={`${TD} pl-4 font-mono text-xs tabular-nums`}>{utcTime(c.at)}</td>
                        <td className={TD}>
                          <Status tone={c.verified ? "ok" : "bad"}>{c.verified ? "Intact" : "Tampered"}</Status>
                        </td>
                        <td className={`${TD} pr-4 text-right tabular-nums text-ink-2`}>{c.ms} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Section>

        <Section title="Network isolation">
          <div className="overflow-hidden rounded-md border border-line">
            <div className="flex items-center gap-4 p-4">
              <span
                className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${
                  online === false ? "bg-ok-soft text-ok" : "bg-raised text-ink-2"
                }`}
              >
                <Icon name={online === false ? "wifiOff" : "wifi"} className="h-5 w-5" />
              </span>
              <div className="min-w-0" aria-live="polite">
                <p className="text-base font-semibold text-ink">
                  {online === false ? "This browser is offline" : "This browser has a network connection"}
                </p>
                <p className="text-sm text-ink-2">
                  {online === false
                    ? "The console is still served by the local stack, with no outside connection."
                    : "The console talks only to this deployment's own API, never to an outside service."}
                </p>
              </div>
            </div>

            <dl className="divide-y divide-line border-t border-line px-4 text-sm">
              <Field label="Runtime calls out">None: no telemetry, update checks, or license callbacks</Field>
              <Field label="OCSF schema">Vendored in the image, not fetched at runtime</Field>
              <Field label="Mapping model">Local Ollama server on the Docker network</Field>
              <Field label="Raw log storage">Local disk, indexed in PostgreSQL</Field>
              <Field label="Fonts and assets">Bundled at build time</Field>
            </dl>

            <div className="border-t border-line p-4 text-sm">
              <h3 className="font-medium text-ink">How to verify isolation</h3>
              <p className="mt-1 max-w-[65ch] text-ink-2">
                Add <code className="code-inline">internal: true</code> to the <code className="code-inline">ulpf_net</code>{" "}
                network in docker-compose.yml and restart. Ingestion, search, mapping review, and chain verification keep
                working with no route out.
              </p>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}
