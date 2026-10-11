import { useCallback, useState } from "react";
import type { MarkStatus, Marks } from "../types";

const KEY = "jobradar.marks.v2";

// Browser storage can be blocked (private mode, strict settings). Marks then
// last until the page is closed, and the app keeps working.
function load(): Marks {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Marks) : {};
  } catch {
    return {};
  }
}

function save(marks: Marks): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(marks));
  } catch {
    /* storage unavailable */
  }
}

/** Toggle a status: setting the same status again clears it. */
export function toggleMark(marks: Marks, uid: string, status: MarkStatus, now = new Date()): Marks {
  const next = { ...marks };
  if (next[uid]?.status === status) delete next[uid];
  else next[uid] = { status, at: now.toISOString() };
  return next;
}

export function useMarks() {
  const [marks, setMarks] = useState<Marks>(load);
  const toggle = useCallback((uid: string, status: MarkStatus) => {
    setMarks((prev) => {
      const next = toggleMark(prev, uid, status);
      save(next);
      return next;
    });
  }, []);
  return { marks, toggle };
}
