"use client";

export type SealState = "idle" | "checking" | "intact" | "tampered";

const RING_PATH = "M 60,60 m -46,0 a 46,46 0 1,1 92,0 a 46,46 0 1,1 -92,0";

/**
 * The one signature element in the UI: a wax-seal-style stamp for the hash
 * chain's verify() result. Embodies the product's actual differentiator —
 * provable losslessness, not claimed — as a physical notary mark rather
 * than a green checkmark. Ring copy sits on the top arc only so it never
 * reads upside-down; the bottom arc carries plain bezel ticks instead.
 */
export default function VerificationSeal({
  state,
  size = "lg",
}: {
  state: SealState;
  size?: "lg" | "sm";
}) {
  const isLg = size === "lg";
  const dim = isLg ? 120 : 22;

  const face =
    state === "intact" ? "#0F2118" : state === "tampered" ? "#1F0E0C" : "#0D1B15";
  const ring =
    state === "intact" ? "#C99A3B" : state === "tampered" ? "#C1483D" : "#3A5750";
  const glyphColor =
    state === "intact" ? "#E9E1CB" : state === "tampered" ? "#E9C9C4" : "#5C7B73";
  const ringText = state === "intact" ? "CHAIN INTACT · ULPF" : "TAMPERED · ULPF";

  const animClass =
    state === "intact" ? "seal-stamp-in" : state === "tampered" ? "seal-stamp-in-hard" : "";

  const ticks = Array.from({ length: 24 }, (_, i) => {
    const angle = (i / 24) * 360;
    const long = i % 6 === 0;
    return { angle, long };
  });

  return (
    <svg
      key={state}
      width={dim}
      height={dim}
      viewBox="0 0 120 120"
      role="img"
      aria-label={
        state === "intact"
          ? "Hash chain verified intact"
          : state === "tampered"
            ? "Hash chain tampering detected"
            : state === "checking"
              ? "Verifying hash chain"
              : "Hash chain not yet verified"
      }
      className={state !== "idle" ? animClass : undefined}
    >
      <defs>
        <path id={`sealRing-${size}`} d={RING_PATH} />
      </defs>

      <circle cx="60" cy="60" r="58" fill="none" stroke={ring} strokeOpacity="0.35" strokeWidth="1" />
      <circle cx="60" cy="60" r="52" fill={face} stroke={ring} strokeWidth={isLg ? 2 : 1.5} />

      {isLg &&
        ticks.map(({ angle, long }, i) => {
          const r1 = 46;
          const r2 = long ? 41 : 43.5;
          const rad = (angle * Math.PI) / 180;
          const x1 = 60 + r1 * Math.sin(rad);
          const y1 = 60 - r1 * Math.cos(rad);
          const x2 = 60 + r2 * Math.sin(rad);
          const y2 = 60 - r2 * Math.cos(rad);
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={ring}
              strokeOpacity={long ? 0.6 : 0.3}
              strokeWidth={long ? 1.4 : 0.8}
            />
          );
        })}

      {isLg && (
        <text fontSize="7.2" fontFamily="var(--font-plex-mono)" letterSpacing="2.5" fill={ring}>
          <textPath href={`#sealRing-${size}`} startOffset="27%" textAnchor="middle">
            {ringText}
          </textPath>
        </text>
      )}

      {state === "intact" && (
        <path
          d="M 41,61 L 53,73 L 80,46"
          fill="none"
          stroke={glyphColor}
          strokeWidth={isLg ? 6 : 5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {state === "tampered" && (
        <>
          <path
            d="M 46,42 L 56,58 L 44,64 L 62,78 L 55,58 L 70,54 L 58,42"
            fill="none"
            stroke={glyphColor}
            strokeWidth={isLg ? 3.5 : 3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M 60,60 m -52,0 a 52,52 0 0,1 20,-40"
            fill="none"
            stroke={glyphColor}
            strokeOpacity="0.5"
            strokeWidth="1"
            strokeDasharray="1 3"
          />
        </>
      )}

      {state === "checking" && (
        <circle
          className="seal-spin"
          cx="60"
          cy="60"
          r="10"
          fill="none"
          stroke={glyphColor}
          strokeWidth="3"
          strokeDasharray="14 10"
          style={{ transformOrigin: "60px 60px" }}
        />
      )}

      {state === "idle" && (
        <circle cx="60" cy="60" r="6" fill="none" stroke={glyphColor} strokeWidth="2" strokeDasharray="2 4" />
      )}
    </svg>
  );
}
