import { useEffect, useState } from "react";
import type { Payload } from "../types";

export type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: Payload }
  | { kind: "missing" }
  | { kind: "error"; message: string };

/** Loads data/jobs.json, which the collector rewrites on every run. */
export function useJobData(): LoadState {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  useEffect(() => {
    let cancelled = false;
    // Cache-busting query so a phone that kept the page open still gets the latest run.
    fetch(`${import.meta.env.BASE_URL}data/jobs.json?t=${Date.now()}`)
      .then(async (res) => {
        if (res.status === 404) return { kind: "missing" } as const;
        if (!res.ok) return { kind: "error", message: `The job list could not be loaded (HTTP ${res.status}).` } as const;
        const data = (await res.json()) as Payload;
        if (!data?.meta || !Array.isArray(data.jobs)) {
          return { kind: "error", message: "The job list file is in an unexpected format." } as const;
        }
        return { kind: "ready", data } as const;
      })
      .catch(() => ({ kind: "error", message: "The job list could not be loaded. Check your connection and reload." }) as const)
      .then((next) => {
        if (!cancelled) setState(next);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}
