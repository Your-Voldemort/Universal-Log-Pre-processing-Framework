"use client";

import Link from "next/link";
import { useState } from "react";
import { useConsole } from "@/components/Shell";
import { Callout } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

type Result = { ok: true; eventId: string } | { ok: false; message: string };

/** The drift firewall self-test: a real Cisco ASA sample with dst_port flipped from int to str. */
export function useDriftTest(onSent?: () => void) {
  const { refresh } = useConsole();
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  const send = async () => {
    setSending(true);
    setResult(null);
    try {
      const { event_id } = await api.injectMalformed();
      setResult({ ok: true, eventId: event_id });
      refresh();
      onSent?.();
    } catch (e) {
      setResult({ ok: false, message: errorMessage(e) });
    } finally {
      setSending(false);
    }
  };

  return { send, sending, result };
}

export function DriftTestResult({ result, showLink = false }: { result: Result | null; showLink?: boolean }) {
  if (!result) return null;
  if (!result.ok) {
    return (
      <Callout tone="bad" title="The test event was not sent">
        {result.message}
      </Callout>
    );
  }
  return (
    <Callout tone="warn" title="Drift detected and held">
      A Cisco ASA event with <code className="code-inline">dst_port</code> sent as a string was quarantined as{" "}
      <code className="code-inline">{result.eventId}</code>.{" "}
      {showLink && (
        <Link href="/quarantine" className="link">
          Review it in quarantine
        </Link>
      )}
    </Callout>
  );
}
