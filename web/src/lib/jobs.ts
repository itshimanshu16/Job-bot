import type { Job, Marks, Sort, Tab } from "../types";

export interface View {
  tab: Tab;
  query: string;
  company: string; // "" = all companies
  sort: Sort;
  track?: string; // "all" or track id, default: "all"
}

export function inTab(job: Job, marks: Marks, tab: Tab): boolean {
  const status = marks[job.uid]?.status;
  switch (tab) {
    case "review":
      return !status;
    case "new":
      return job.is_new && !status;
    case "applied":
      return status === "applied";
    case "hidden":
      return status === "hidden";
  }
}

export function tabCounts(jobs: Job[], marks: Marks, track = "all"): Record<Tab, number> {
  const counts: Record<Tab, number> = { review: 0, new: 0, applied: 0, hidden: 0 };
  const filtered = track && track !== "all" ? jobs.filter((j) => j.track === track) : jobs;
  for (const j of filtered) {
    for (const t of Object.keys(counts) as Tab[]) {
      if (inTab(j, marks, t)) counts[t]++;
    }
  }
  return counts;
}

export function trackCounts(jobs: Job[], marks: Marks, tab: Tab): Record<string, number> {
  const counts: Record<string, number> = { all: 0 };
  for (const j of jobs) {
    if (inTab(j, marks, tab)) {
      counts.all++;
      if (j.track) {
        counts[j.track] = (counts[j.track] || 0) + 1;
      }
    }
  }
  return counts;
}

export function matchesQuery(job: Job, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = `${job.title} ${job.company} ${job.location} ${job.department} ${job.track_label || ""} ${job.resume || ""}`.toLowerCase();
  return q.split(/\s+/).every((word) => hay.includes(word));
}

export function visibleJobs(jobs: Job[], marks: Marks, view: View): Job[] {
  const rows = jobs.filter(
    (j) =>
      inTab(j, marks, view.tab) &&
      matchesQuery(j, view.query) &&
      (!view.company || j.company === view.company) &&
      (!view.track || view.track === "all" || j.track === view.track),
  );
  if (view.tab === "applied") {
    return rows.sort((a, b) => (marks[b.uid]?.at ?? "").localeCompare(marks[a.uid]?.at ?? ""));
  }
  if (view.sort === "date") {
    return rows.sort((a, b) => (b.posted ?? "").localeCompare(a.posted ?? ""));
  }
  return rows.sort((a, b) => b.score - a.score || (b.posted ?? "").localeCompare(a.posted ?? ""));
}

export function companies(jobs: Job[]): string[] {
  return [...new Set(jobs.map((j) => j.company))].sort((a, b) => a.localeCompare(b));
}

/** "posted today", "posted 3 days ago", ... */
export function postedAgo(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "";
  const days = (now.getTime() - new Date(iso).getTime()) / 86_400_000;
  if (Number.isNaN(days)) return "";
  if (days < 1) return "posted today";
  if (days < 2) return "posted yesterday";
  if (days < 30) return `posted ${Math.floor(days)} days ago`;
  return `posted ${new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
}

export function safeUrl(url: string | undefined): string {
  return url && /^https?:\/\//i.test(url) ? url : "#";
}

/** YYYY-MM-DD in the viewer's own time zone. */
export function localDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function csvCell(value: unknown): string {
  const s = value == null ? "" : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function appliedCsv(jobs: Job[], marks: Marks): string {
  const header = ["applied_on", "title", "company", "location", "resume", "url"];
  const rows = jobs
    .filter((j) => marks[j.uid]?.status === "applied")
    .sort((a, b) => (marks[a.uid].at ?? "").localeCompare(marks[b.uid].at ?? ""))
    .map((j) => [
      localDate(marks[j.uid].at),
      j.title,
      j.company,
      j.location,
      marks[j.uid].resume || j.resume || "",
      j.apply_url || j.url,
    ]);
  return [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\n") + "\n";
}
