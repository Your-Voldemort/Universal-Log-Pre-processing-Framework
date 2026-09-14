"use client";

import { useEffect, useState } from "react";
import { api, QuarantineItem } from "@/lib/api";

export default function DriftAlerts() {
  const [items, setItems] = useState<QuarantineItem[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);

  const refresh = () => api.quarantineList().then(setItems);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, []);

  const resolve = async (id: number, action: "quarantine" | "auto-fix" | "ignore") => {
    setBusyId(id);
    try {
      await api.resolveQuarantine(id, action);
      await refresh();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-3">
      {items.length === 0 && (
        <div className="text-fg3 text-sm">
          Quarantine queue is empty. Use the "Inject malformed log" button on the Dashboard tab to
          see this in action.
        </div>
      )}
      {items.map((item) => (
        <div key={item.id} className="border border-warn/30 bg-panel p-4">
          <div className="mb-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono text-xs text-warn">
              <span className="lamp lamp-live h-1.5 w-1.5 bg-warn" />
              {item.source_format} — quarantine #{item.id}
            </div>
            <span className="text-fg3 border border-line px-2 py-0.5 text-[10px] uppercase tracking-wider2">
              {item.status}
            </span>
          </div>

          {Object.keys(item.alert.type_drift ?? {}).length > 0 && (
            <div className="text-fg2 mb-1 text-xs">
              Type drift:{" "}
              {Object.entries(item.alert.type_drift).map(([field, d]: [string, any]) => (
                <span key={field} className="mr-2 font-mono text-fg">
                  {field}: {d.expected}→{d.received}
                </span>
              ))}
            </div>
          )}
          {(item.alert.new_fields?.length ?? 0) > 0 && (
            <div className="text-fg2 mb-1 text-xs">
              New fields: <span className="font-mono text-fg">{item.alert.new_fields.join(", ")}</span>
            </div>
          )}

          <pre className="readout mb-3 max-h-32 overflow-auto p-3 font-mono text-xs text-fg2">
            {JSON.stringify(item.fields, null, 2)}
          </pre>

          <div className="flex gap-2">
            {(["quarantine", "auto-fix", "ignore"] as const).map((action) => (
              <button
                key={action}
                onClick={() => resolve(item.id, action)}
                disabled={busyId === item.id || item.status !== "quarantine"}
                className="border border-line px-3 py-1 text-xs text-fg2 transition-colors hover:border-brass/50 hover:text-fg disabled:opacity-40"
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
