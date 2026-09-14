export interface OCSFEvent {
  class_uid: number;
  category_uid: number;
  activity_name: string;
  time?: number; // epoch ms, from the log's own timestamp
  disposition: string;
  metadata: { product: { name: string; vendor_name: string }; version: string };
  src_endpoint?: { ip?: string; port?: number };
  dst_endpoint?: { ip?: string; port?: number };
  connection_info?: { protocol_name?: string };
  observables: { name: string; value: string }[];
  unmapped: Record<string, unknown>;
  ulpf: {
    raw_event_id: string;
    raw_event_hash: string;
    parser_version: string;
    mapping_confidence: number;
  };
}

export interface Metrics {
  events_per_sec: number;
  normalized_by_source: Record<string, number>;
  total_normalized: number;
  drift_by_source: Record<string, number>;
  drift_count: number;
  unmapped_field_ratio: number;
  raw_preservation_pct: number;
  chain_verified: boolean;
}

export interface QuarantineItem {
  id: number;
  source_format: string;
  fields: Record<string, unknown>;
  alert: { type_drift: Record<string, unknown>; new_fields: string[] };
  status: string;
  created_at: string;
  raw_event_id: string | null;
}

export interface MappingProposal {
  id: number;
  source_format: string;
  proposed_yaml: string;
  sample_raw: string;
  status: string;
  created_at: string;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  ingest: (raw: string) =>
    fetch("/ingest", { method: "POST", body: raw }).then((r) => json<unknown>(r)),

  metrics: () => fetch("/metrics").then((r) => json<Metrics>(r)),

  verifyChain: () => fetch("/verify-chain").then((r) => json<{ verified: boolean }>(r)),

  search: (q: string, source?: string, timeRange?: string) =>
    fetch(
      `/search?${new URLSearchParams({
        ...(q ? { q } : {}),
        ...(source ? { source } : {}),
        ...(timeRange ? { time_range: timeRange } : {}),
      })}`,
    ).then((r) => json<{ results: OCSFEvent[] }>(r)),

  getEvent: (rawEventId: string) =>
    fetch(`/events/${rawEventId}`).then(
      (r) => json<{ raw_event_id: string; ocsf_event: OCSFEvent | null; raw_log: string | null }>(r),
    ),

  quarantineList: (status?: string) =>
    fetch(`/drift/quarantine${status ? `?status=${status}` : ""}`).then((r) => json<QuarantineItem[]>(r)),

  resolveQuarantine: (id: number, action: "quarantine" | "auto-fix" | "ignore") =>
    fetch(`/drift/quarantine/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    }).then((r) => json<unknown>(r)),

  injectMalformed: () => fetch("/drift/inject-malformed", { method: "POST" }).then((r) => json<unknown>(r)),

  proposeMapping: (rawSamples: string) =>
    fetch("/mapping/propose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_samples: rawSamples }),
    }).then((r) => json<{ proposal_id: number; source_format: string; yaml: string }>(r)),

  listProposals: (status?: string) =>
    fetch(`/mapping/proposals${status ? `?status=${status}` : ""}`).then((r) => json<MappingProposal[]>(r)),

  approveMapping: (id: number) =>
    fetch(`/mapping/${id}/approve`, { method: "POST" }).then((r) => json<{ status: string; source_format: string; replayed: Record<string, number> }>(r)),

  rejectMapping: (id: number) =>
    fetch(`/mapping/${id}/reject`, { method: "POST" }).then((r) => json<{ status: string; id: number }>(r)),

  complianceReport: (rawEventIds: string[]) =>
    fetch("/compliance/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_event_ids: rawEventIds }),
    }).then((r) => json<{ report_markdown: string }>(r)),
};
