import type { Endpoint, OCSFEvent, QuarantineItem } from "@/lib/api";

/** "2026-08-30 14:22:31". Every time in the console is UTC and labelled as such. */
export function utc(value?: number | string | null) {
  if (value == null) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : d.toISOString().slice(0, 19).replace("T", " ");
}

export const utcTime = (value: number) => new Date(value).toISOString().slice(11, 19);

export const pct = (ratio: number, digits = 0) => `${(ratio * 100).toFixed(digits)}%`;

// Indian digit grouping (1,00,000) for an Indian government and enterprise audience
const NUMBER = new Intl.NumberFormat("en-IN");
export const formatNumber = (n: number) => NUMBER.format(n);

const SOURCE_NAMES: Record<string, string> = {
  cisco_asa_syslog: "Cisco ASA",
  paloalto_cef: "Palo Alto PAN-OS",
  juniper_srx_rt_flow: "Juniper SRX",
  checkpoint_log_exporter: "Check Point",
  suricata_eve: "Suricata IDS",
};

/** Built-in formats get a product name; AI-approved formats keep their format id. */
export const sourceName = (format: string) => SOURCE_NAMES[format] ?? format;

// Network Activity has endpoints top-level; a Detection Finding (IDS alert) has them in evidences
export function endpoints(e: OCSFEvent) {
  return {
    src: e.src_endpoint ?? e.evidences?.[0]?.src_endpoint,
    dst: e.dst_endpoint ?? e.evidences?.[0]?.dst_endpoint,
  };
}

export const endpoint = (ep?: Endpoint) => (ep?.ip ? `${ep.ip}${ep.port != null ? `:${ep.port}` : ""}` : "—");

export const protocol = (e: OCSFEvent) =>
  (e.connection_info ?? e.evidences?.[0]?.connection_info)?.protocol_name;

const CLASS_NAMES: Record<number, string> = { 4001: "Network Activity", 2004: "Detection Finding" };
export const eventClass = (e: OCSFEvent) => CLASS_NAMES[e.class_uid] ?? `OCSF class ${e.class_uid}`;

export const eventTitle = (e: OCSFEvent) => e.finding_info?.title ?? e.activity_name;

// OCSF severity_id
export const SEVERITY = ["Unknown", "Informational", "Low", "Medium", "High", "Critical", "Fatal"];

export type Tone = "ok" | "warn" | "bad" | "neutral" | "accent";

/** Allowed traffic stays neutral; only outcomes an analyst may act on get color. */
export function dispositionTone(disposition: string): Tone {
  if (/denied|blocked|dropped|rejected|reset/i.test(disposition)) return "bad";
  if (/detected|alert/i.test(disposition)) return "warn";
  return "neutral";
}

/** Python type names, matching the drift firewall's expected/received vocabulary. */
export function typeName(value: unknown) {
  if (value === null) return "None";
  if (typeof value === "number") return Number.isInteger(value) ? "int" : "float";
  if (typeof value === "string") return "str";
  if (typeof value === "boolean") return "bool";
  return Array.isArray(value) ? "list" : "dict";
}

export function driftSummary(item: QuarantineItem) {
  const parts = Object.entries(item.alert.type_drift ?? {}).map(([field, d]) => `${field} was ${d.expected}, now ${d.received}`);
  const added = item.alert.new_fields?.length ?? 0;
  if (added) parts.push(`${added} new ${added === 1 ? "field" : "fields"}`);
  return parts.join(" · ") || "Field shape changed";
}
