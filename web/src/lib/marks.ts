import { useCallback, useState } from "react";
import type { MarkStatus, Marks } from "../types";

const KEY = "jobradar.marks.v2";

// Browser storage can be blocked (private mode, strict settings). Marks then
// last until the page is closed, and the app keeps working.
export function loadMarks(): Marks {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, { status: MarkStatus; at: string; resume?: string }>;
    const clean: Marks = {};
    for (const [uid, m] of Object.entries(parsed)) {
      if (m && m.status && m.at) {
        clean[uid] = {
          status: m.status,
          at: m.at,
          resume: m.resume || "",
        };
      }
    }
    return clean;
  } catch {
    return {};
  }
}

export function saveMarks(marks: Marks): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(marks));
  } catch {
    /* storage unavailable */
  }
}

/** Toggle a status: setting the same status again clears it. */
export function toggleMark(
  marks: Marks,
  uid: string,
  status: MarkStatus,
  resume = "",
  now = new Date()
): Marks {
  const next = { ...marks };
  if (next[uid]?.status === status) {
    delete next[uid];
  } else {
    next[uid] = {
      status,
      at: now.toISOString(),
      resume: status === "applied" ? (resume || next[uid]?.resume || "") : (next[uid]?.resume || ""),
    };
  }
  return next;
}

export function useMarks() {
  const [marks, setMarks] = useState<Marks>(loadMarks);
  const toggle = useCallback((uid: string, status: MarkStatus, resume = "") => {
    setMarks((prev) => {
      const next = toggleMark(prev, uid, status, resume);
      saveMarks(next);
      return next;
    });
  }, []);
  return { marks, toggle };
}
