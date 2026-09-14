"use client";

import { useEffect, useState } from "react";
import AirGapDemo from "@/components/AirGapDemo";
import ComplianceReport from "@/components/ComplianceReport";
import DashboardMetrics from "@/components/DashboardMetrics";
import DriftAlerts from "@/components/DriftAlerts";
import MappingReview from "@/components/MappingReview";
import SearchTable from "@/components/SearchTable";
import VerificationSeal, { SealState } from "@/components/VerificationSeal";
import { api } from "@/lib/api";

const TABS = [
  { key: "dashboard", label: "Dashboard", component: DashboardMetrics },
  { key: "search", label: "Search & Traceability", component: SearchTable },
  { key: "drift", label: "Drift Queue", component: DriftAlerts },
  { key: "mapping", label: "AI Mapping Review", component: MappingReview },
  { key: "compliance", label: "Compliance Report", component: ComplianceReport },
  { key: "airgap", label: "Air-Gap / Hash Chain", component: AirGapDemo },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function RailLamp({ count, urgent }: { count: number; urgent?: boolean }) {
  if (count === 0) return null;
  return (
    <span
      className={`lamp lamp-live h-1.5 w-1.5 ${urgent ? "bg-warn" : "bg-brass"}`}
      aria-label={`${count} pending`}
    />
  );
}

export default function Home() {
  const [active, setActive] = useState<TabKey>("dashboard");
  const [driftCount, setDriftCount] = useState(0);
  const [pendingProposals, setPendingProposals] = useState(0);
  const [chainState, setChainState] = useState<SealState>("idle");

  useEffect(() => {
    const poll = () => {
      api
        .metrics()
        .then((m) => {
          setDriftCount(m.drift_count);
          setChainState(m.chain_verified ? "intact" : "tampered");
        })
        .catch(() => {});
      api
        .listProposals("pending")
        .then((p) => setPendingProposals(p.length))
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  const ActiveComponent = TABS.find((t) => t.key === active)!.component;

  return (
    <div className="flex min-h-screen">
      {/* Instrument rail — each item is a live subsystem, not a static tab */}
      <nav className="flex w-56 shrink-0 flex-col border-r border-line bg-panel">
        <div className="flex items-center gap-2 border-b border-line px-4 py-4">
          <span className="text-brass text-lg leading-none">▮</span>
          <div>
            <div className="text-fg text-sm font-semibold leading-tight">ULPF</div>
            <div className="text-fg3 text-[10px] leading-tight tracking-wider2">CONSOLE</div>
          </div>
        </div>

        <ul className="flex-1 py-2">
          {TABS.map((t) => {
            const isActive = t.key === active;
            const lampCount = t.key === "drift" ? driftCount : t.key === "mapping" ? pendingProposals : 0;
            return (
              <li key={t.key}>
                <button
                  onClick={() => setActive(t.key)}
                  aria-current={isActive ? "page" : undefined}
                  className={`group flex w-full items-center justify-between border-l-2 px-4 py-2.5 text-left text-[13px] transition-colors ${
                    isActive
                      ? "border-brass bg-panel2 text-fg font-medium"
                      : "border-transparent text-fg2 hover:border-line hover:bg-panel2/60 hover:text-fg"
                  }`}
                >
                  <span>{t.label}</span>
                  <RailLamp count={lampCount} urgent={t.key === "drift"} />
                </button>
              </li>
            );
          })}
        </ul>

        <div className="border-t border-line px-4 py-3">
          <div className="text-fg3 text-[10px] leading-relaxed tracking-wider2">
            SIH26156 · NTRO / NCIIPC
          </div>
        </div>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Nameplate header — the chain-integrity lamp is visible from every tab */}
        <header className="flex items-center justify-between border-b border-line bg-panel px-6 py-3">
          <div>
            <h1 className="text-fg text-[15px] font-semibold">
              {TABS.find((t) => t.key === active)!.label}
            </h1>
            <p className="text-fg3 font-mono text-[11px]">
              perimeter-log normalization · OCSF class 4001
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="text-fg3 font-mono text-[10px] tracking-wider2">CHAIN</span>
            <VerificationSeal state={chainState} size="sm" />
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto p-6">
          <ActiveComponent />
        </main>
      </div>
    </div>
  );
}
