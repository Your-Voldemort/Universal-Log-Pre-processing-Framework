import { useEffect, useRef } from "react";

/** Runs fn now and every `ms` while the tab is visible, and again as soon as it becomes visible. */
export function usePolling(fn: () => unknown, ms: number) {
  const latest = useRef(fn);
  latest.current = fn;

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") latest.current();
    };
    tick();
    const id = setInterval(tick, ms);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [ms]);
}
