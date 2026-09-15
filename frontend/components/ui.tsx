"use client";

import { ButtonHTMLAttributes, ReactNode, useId, useState } from "react";
import { dispositionTone, Tone } from "@/lib/format";

// 24px stroke icons, drawn to one grid so they sit together.
const ICONS = {
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  alert: "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01",
  branch: "M6 3v12M21 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM18 9a9 9 0 0 1-9 9",
  link: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  search: "M18 11a7 7 0 1 1-14 0 7 7 0 0 1 14 0zM21 21l-4.35-4.35",
  sun: "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41",
  moon: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z",
  monitor: "M3 5a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM8 20h8M12 16v4",
  copy: "M9 9h11v11H9zM5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18M6 6l12 12",
  chevronRight: "m9 18 6-6-6-6",
  arrowRight: "M5 12h14M13 6l6 6-6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  circleCheck: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zM9 12l2 2 4-4",
  circleX: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zM15 9l-6 6M9 9l6 6",
  info: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zM12 16v-4M12 8h.01",
  wifi: "M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01",
  wifiOff:
    "M2 2l20 20M8.5 16.5a5 5 0 0 1 7 0M2 8.82a15 15 0 0 1 4.17-2.65M10.66 5c4.01-.36 8.14.9 11.34 3.76M16.85 11.25a10 10 0 0 1 2.22 1.68M5 13a10 10 0 0 1 5.24-2.76M12 20h.01",
} as const;

export type IconName = keyof typeof ICONS;

export function Icon({ name, className = "h-4 w-4" }: { name: IconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/** The self-hosted font subsets have no U+2192, so the arrow is drawn. */
export const Arrow = () => (
  <>
    <Icon name="arrowRight" className="mx-0.5 inline h-3 w-3 align-[-1px] text-ink-3" />
    <span className="sr-only"> to </span>
  </>
);

/* ---------- Buttons ---------- */

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-on-accent hover:bg-accent-hover",
  secondary: "border border-control bg-surface text-ink hover:bg-raised",
  ghost: "text-ink-2 hover:bg-raised hover:text-ink",
};

/** For links that act as buttons. */
export function buttonClass(variant: Variant = "secondary", size: Size = "md") {
  return [
    "inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50",
    size === "sm" ? "h-7 px-2.5 text-xs" : "h-8 px-3 text-sm",
    VARIANTS[variant],
  ].join(" ");
}

export function Button({
  variant,
  size,
  loading = false,
  disabled,
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean }) {
  return (
    <button
      type="button"
      {...props}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${buttonClass(variant, size)} ${className}`}
    >
      {loading && (
        <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
      )}
      {children}
    </button>
  );
}

/* ---------- Form controls, readouts, tables ---------- */

export const CONTROL =
  "h-8 rounded border border-control bg-surface px-2.5 text-sm text-ink placeholder:text-ink-3 transition-colors duration-150 hover:border-ink-3 disabled:opacity-50";

/** Evidentiary data: raw logs, hashes, JSON, YAML. */
export const READOUT = "overflow-auto rounded border border-line bg-sunken p-3 font-mono text-xs leading-5 text-ink";

export const TH = "whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-ink-2";
export const TD = "px-3 py-2 align-middle";

/* ---------- Status ---------- */

export const TONE_TEXT: Record<Tone, string> = {
  ok: "text-ok",
  warn: "text-warn",
  bad: "text-bad",
  neutral: "text-ink-3",
  accent: "text-accent-ink",
};

/** A different shape per tone, so status never depends on color alone. */
export function StatusMark({ tone, className = "h-2 w-2" }: { tone: Tone; className?: string }) {
  return (
    <svg viewBox="0 0 8 8" aria-hidden="true" className={`shrink-0 ${TONE_TEXT[tone]} ${className}`}>
      {tone === "ok" && <circle cx="4" cy="4" r="3.5" fill="currentColor" />}
      {tone === "warn" && <path d="M4 .4 7.7 7.4H.3z" fill="currentColor" />}
      {tone === "bad" && <rect x=".5" y=".5" width="7" height="7" rx=".5" fill="currentColor" />}
      {tone === "accent" && <path d="M4 .3 7.7 4 4 7.7.3 4z" fill="currentColor" />}
      {tone === "neutral" && <circle cx="4" cy="4" r="3" fill="none" stroke="currentColor" strokeWidth="1.5" />}
    </svg>
  );
}

export function Status({ tone, children, className = "" }: { tone: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap ${className}`}>
      <StatusMark tone={tone} />
      {children}
    </span>
  );
}

export const Disposition = ({ value }: { value: string }) => <Status tone={dispositionTone(value)}>{value}</Status>;

const CALLOUT: Record<Tone, { box: string; icon: IconName }> = {
  ok: { box: "border-ok/30 bg-ok-soft", icon: "circleCheck" },
  warn: { box: "border-warn/35 bg-warn-soft", icon: "alert" },
  bad: { box: "border-bad/30 bg-bad-soft", icon: "circleX" },
  neutral: { box: "border-line bg-raised", icon: "info" },
  accent: { box: "border-accent/25 bg-accent-soft", icon: "info" },
};

export function Callout({
  tone = "neutral",
  title,
  children,
  action,
  className = "",
}: {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === "bad" ? "alert" : tone === "ok" || tone === "warn" ? "status" : undefined}
      className={`flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-sm ${CALLOUT[tone].box} ${className}`}
    >
      <span className={`mt-0.5 ${TONE_TEXT[tone]}`}>
        <Icon name={CALLOUT[tone].icon} />
      </span>
      <div className="min-w-0 flex-1 [overflow-wrap:anywhere]">
        {title && <p className="font-medium text-ink">{title}</p>}
        {children && <div className="text-ink-2">{children}</div>}
      </div>
      {action}
    </div>
  );
}

/* ---------- Layout pieces ---------- */

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 max-w-[72ch]">
        <h1 className="text-xl font-semibold text-ink [text-wrap:balance]">{title}</h1>
        {description && <p className="mt-1 text-base text-ink-2 [text-wrap:pretty]">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Section({
  title,
  description,
  actions,
  children,
  className = "",
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <section aria-labelledby={id} className={`min-w-0 ${className}`}>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div className="min-w-0">
          <h2 id={id} className="text-lg font-semibold text-ink">
            {title}
          </h2>
          {description && <p className="text-sm text-ink-2">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

/** One key/value row; use inside <dl className="divide-y divide-line">. */
export function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return (
    <div className={`grid grid-cols-[8.5rem_minmax(0,1fr)] gap-3 py-2 ${className}`}>
      <dt className="text-ink-2">{label}</dt>
      <dd className="min-w-0 text-ink [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: ReactNode }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded border border-line bg-canvas p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
          className={`h-7 rounded-sm px-2.5 text-xs font-medium transition-colors duration-150 ${
            o.value === value
              ? "bg-surface text-ink shadow-[0_0_0_1px_oklch(var(--line-strong))]"
              : "text-ink-2 hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function EmptyState({
  icon = "info",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <span className="mb-3 grid h-9 w-9 place-items-center rounded-full bg-raised text-ink-2">
        <Icon name={icon} />
      </span>
      <p className="text-base font-medium text-ink">{title}</p>
      {children && <p className="mt-1 max-w-[52ch] text-sm text-ink-2 [text-wrap:pretty]">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export const Skeleton = ({ className = "" }: { className?: string }) => (
  <span aria-hidden="true" className={`block animate-pulse rounded bg-raised ${className}`} />
);

export function SkeletonRows({ cols, rows = 8 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r}>
          {Array.from({ length: cols }, (_, c) => (
            <td key={c} className="px-3 py-2.5">
              <Skeleton className={`h-3.5 ${c === 0 ? "w-4" : "w-full max-w-[9rem]"}`} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function Disclosure({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <details className="group rounded border border-line">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded px-3 py-2 text-sm font-medium text-ink hover:bg-raised [&::-webkit-details-marker]:hidden">
        <Icon name="chevronRight" className="h-4 w-4 text-ink-3 transition-transform duration-150 group-open:rotate-90" />
        {title}
      </summary>
      <div className="border-t border-line">{children}</div>
    </details>
  );
}

/* ---------- Copy ---------- */

/** Clipboard API needs a secure context; air-gapped installs are often served over plain http on the LAN. */
export async function copyText(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = value;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    if (await copyText(value)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}
      className="inline-grid h-6 w-6 shrink-0 place-items-center rounded text-ink-3 transition-colors duration-150 hover:bg-raised hover:text-ink"
    >
      <Icon name={copied ? "check" : "copy"} className="h-3.5 w-3.5" />
    </button>
  );
}
