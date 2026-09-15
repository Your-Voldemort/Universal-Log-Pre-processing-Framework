export interface Endpoint {
  ip?: string;
  port?: number;
}

export interface OCSFEvent {
  class_uid: number;
  category_uid: number;
  activity_name: string;
  time?: number; // epoch ms, from the log's own timestamp
  disposition: string;
  metadata: { product: { name: string; vendor_name: string }; version: string };
  src_endpoint?: Endpoint;
  dst_endpoint?: Endpoint;
  connection_info?: { protocol_name?: string };
  // Detection Finding (class 2004, e.g. Suricata alerts): endpoints live in evidences
  finding_info?: { uid: string; title: string; types?: string[] };
  severity_id?: number;
  evidences?: {
    src_endpoint?: Endpoint;
    dst_endpoint?: Endpoint;
    connection_info?: { protocol_name?: string };
  }[];
  observables: { name: string; value: string }[];
  unmapped: Record<string, unknown>;
  ulpf: {
    raw_event_id: string;
    raw_event_hash: string;
    parser_version: string;
    mapping_confidence: number;
    drift_resolution?: { action: string; coerced?: Record<string, { from: string; to: string }> };
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
  alert: { type_drift: Record<string, { expected: string; received: string }>; new_fields: string[] };
  status: string; // "quarantine" while held, otherwise the resolving action
  created_at: string;
  raw_event_id: string | null;
}

export type ResolveAction = "quarantine" | "auto-fix" | "ignore";

export interface MappingProposal {
  id: number;
  source_format: string;
  proposed_yaml: string;
  sample_raw: string;
  status: string;
  created_at: string;
}

export interface ReplayCounts {
  normalized: number;
  quarantined: number;
  still_unrecognized: number;
  failed_validation: number;
}

export interface ComplianceProfile {
  regulator: string;
  retention_days: number;
  jurisdiction: string;
  incident_report_deadline_hours: number;
  ntp_server: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export const errorMessage = (e: unknown) => (e instanceof Error ? e.message : String(e));

// Every call goes through the /api rewrite in next.config.js.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(0, "Can't reach the ULPF API. Check that the ulpf-api service is running.");
  }
  if (!res.ok) {
    const text = await res.text();
    let detail: unknown;
    try {
      detail = JSON.parse(text).detail;
    } catch {
      // not a FastAPI error body, e.g. the proxy's own 500 when the API is down
    }
    if (typeof detail === "string") throw new ApiError(res.status, detail);
    throw new ApiError(
      res.status,
      res.status >= 500 ? `The ULPF API is unavailable (HTTP ${res.status}).` : `Request failed (HTTP ${res.status}).`,
    );
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  });

const withStatus = (path: string, status?: string) => (status ? `${path}?status=${encodeURIComponent(status)}` : path);

export const api = {
  metrics: () => request<Metrics>("/metrics"),

  verifyChain: () => request<{ verified: boolean }>("/verify-chain"),

  search: (q: string, source?: string, timeRange?: string, limit = 50) =>
    request<{ results: OCSFEvent[] }>(
      `/search?${new URLSearchParams({
        ...(q ? { q } : {}),
        ...(source ? { source } : {}),
        ...(timeRange ? { time_range: timeRange } : {}),
        limit: String(limit),
      })}`,
    ),

  getEvent: (rawEventId: string) =>
    request<{ raw_event_id: string; ocsf_event: OCSFEvent | null; raw_log: string | null }>(
      `/events/${encodeURIComponent(rawEventId)}`,
    ),

  quarantineList: (status?: string) => request<QuarantineItem[]>(withStatus("/drift/quarantine", status)),

  resolveQuarantine: (id: number, action: ResolveAction) =>
    post<{ status: string; id: number; action: ResolveAction }>(`/drift/quarantine/${id}/resolve`, { action }),

  injectMalformed: () =>
    post<{ status: string; event_id: string; alert: QuarantineItem["alert"] }>("/drift/inject-malformed"),

  proposeMapping: (rawSamples: string) =>
    post<{ proposal_id: number; source_format: string; yaml: string }>("/mapping/propose", { raw_samples: rawSamples }),

  listProposals: (status?: string) => request<MappingProposal[]>(withStatus("/mapping/proposals", status)),

  approveMapping: (id: number) =>
    post<{ status: string; source_format: string; replayed: ReplayCounts }>(`/mapping/${id}/approve`),

  rejectMapping: (id: number) => post<{ status: string; id: number }>(`/mapping/${id}/reject`),

  complianceProfile: () => request<ComplianceProfile>("/compliance/profile"),

  complianceReport: (rawEventIds: string[], pointOfContact: string) =>
    post<{ report_markdown: string }>("/compliance/report", {
      raw_event_ids: rawEventIds,
      point_of_contact: pointOfContact,
    }),
};
