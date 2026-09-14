"use client";

import { useEffect, useState } from "react";
import VerificationSeal, { SealState } from "@/components/VerificationSeal";
import { api } from "@/lib/api";

export default function AirGapDemo() {
  const [online, setOnline] = useState(navigator.onLine);
  const [sealState, setSealState] = useState<SealState>("idle");

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  const runVerify = async () => {
    setSealState("checking");
    try {
      const { verified } = await api.verifyChain();
      setSealState(verified ? "intact" : "tampered");
    } catch {
      setSealState("idle");
    }
  };

  return (
    <div className="space-y-4">
      <div className="border border-line bg-panel p-6 text-center">
        <span
          className={`lamp mx-auto h-2.5 w-2.5 ${online ? "bg-ok" : "bg-crit lamp-live"}`}
        />
        <div className="text-fg mt-3 text-base font-medium">
          {online ? "Browser reports network connectivity" : "OFFLINE — zero phone-home, still serving"}
        </div>
        <div className="text-fg3 mx-auto mt-1.5 max-w-xl text-xs">
          Everything on this page runs against this container's own Postgres + Ollama — no
          runtime call ever leaves the Docker network. Pull the cable, or rerun Compose with
          `internal: true`, and this page keeps working.
        </div>
      </div>

      <div className="border border-line bg-panel p-6">
        <div className="text-fg3 mb-4 text-[10px] uppercase tracking-wider2">
          Provable losslessness — run HashChain.verify() against the full chain
        </div>

        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:justify-center">
          <VerificationSeal state={sealState} size="lg" />

          <div className="flex flex-col items-center gap-3 sm:items-start">
            <button
              onClick={runVerify}
              disabled={sealState === "checking"}
              className="border border-brass/50 bg-brass/10 px-5 py-2.5 text-[13px] font-medium text-brass transition-colors hover:bg-brass/20 disabled:opacity-50"
            >
              {sealState === "checking" ? "Verifying…" : "Verify hash chain"}
            </button>
            {sealState === "intact" && (
              <div className="font-mono text-sm text-ok">True — nothing altered or removed</div>
            )}
            {sealState === "tampered" && (
              <div className="font-mono text-sm text-crit">False — TAMPERING DETECTED</div>
            )}
            {sealState === "idle" && (
              <div className="text-fg3 font-mono text-sm">Awaiting first verification</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
