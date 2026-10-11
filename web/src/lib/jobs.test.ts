import { describe, expect, it } from "vitest";
import type { Job, Marks } from "../types";
import { appliedCsv, companies, inTab, matchesQuery, postedAgo, safeUrl, tabCounts, trackCounts, visibleJobs } from "./jobs";
import { loadMarks, toggleMark } from "./marks";

function job(over: Partial<Job>): Job {
  return {
    uid: "u1", source: "lever", company: "Acme", title: "Data Analyst", url: "https://x.test/1",
    apply_url: "", location: "Pune, India", remote: false, posted: "2026-10-10T00:00:00+00:00",
    department: "", employment_type: "", seniority: "", score: 50, reasons: [], flags: [], min_years: null,
    is_new: false, first_seen: "", llm_score: null, llm_reason: "", snippet: "",
    track: "analyst", track_label: "Analyst & Consulting", resume: "INTERN_ADDED_NON_TECH.pdf",
    resume_reason: "default for this track", track_scores: { analyst: 50 }, ...over,
  };
}

const jobs = [
  job({
    uid: "a", title: "Data Analyst", company: "Acme", score: 70, is_new: true,
    posted: "2026-10-01T00:00:00Z", track: "analyst", track_label: "Analyst & Consulting",
    resume: "INTERN_ADDED_NON_TECH.pdf",
  }),
  job({
    uid: "b", title: "Frontend Developer", company: "Zeta", score: 90,
    posted: "2026-10-09T00:00:00Z", track: "software", track_label: "Software / Full-stack",
    resume: "HIMANSHU_FINAL_TECH.pdf",
  }),
  job({
    uid: "c", title: "Supply Chain Analyst", company: "Acme", score: 40, is_new: true,
    location: "Remote", track: "supply_chain", track_label: "Supply Chain & Operations",
    resume: "Supply_chain.pdf",
  }),
];

describe("tabs", () => {
  const marks: Marks = { c: { status: "applied", at: "2026-10-11T10:00:00Z", resume: "Supply_chain.pdf" } };

  it("puts each job in the right list", () => {
    expect(inTab(jobs[0], marks, "review")).toBe(true);
    expect(inTab(jobs[2], marks, "review")).toBe(false);
    expect(inTab(jobs[2], marks, "new")).toBe(false); // applied jobs leave the New list
    expect(tabCounts(jobs, marks)).toEqual({ review: 2, new: 1, applied: 1, hidden: 0 });
  });

  it("calculates tab counts scoped to a track", () => {
    expect(tabCounts(jobs, marks, "software")).toEqual({ review: 1, new: 0, applied: 0, hidden: 0 });
    expect(tabCounts(jobs, marks, "analyst")).toEqual({ review: 1, new: 1, applied: 0, hidden: 0 });
    expect(tabCounts(jobs, marks, "supply_chain")).toEqual({ review: 0, new: 0, applied: 1, hidden: 0 });
  });

  it("calculates track counts for the active tab", () => {
    const tReview = trackCounts(jobs, marks, "review");
    expect(tReview.all).toBe(2);
    expect(tReview.analyst).toBe(1);
    expect(tReview.software).toBe(1);
    expect(tReview.supply_chain).toBeUndefined();

    const tApplied = trackCounts(jobs, marks, "applied");
    expect(tApplied.all).toBe(1);
    expect(tApplied.supply_chain).toBe(1);
  });
});

describe("visibleJobs", () => {
  it("sorts by score by default and by posting date on request", () => {
    const base = { tab: "review" as const, query: "", company: "" };
    expect(visibleJobs(jobs, {}, { ...base, sort: "score" }).map((j) => j.uid)).toEqual(["b", "a", "c"]);
    expect(visibleJobs(jobs, {}, { ...base, sort: "date" }).map((j) => j.uid)).toEqual(["c", "b", "a"]);
  });

  it("filters by search words and company", () => {
    const v = { tab: "review" as const, sort: "score" as const };
    expect(visibleJobs(jobs, {}, { ...v, query: "analyst acme", company: "" }).map((j) => j.uid)).toEqual(["a", "c"]);
    expect(visibleJobs(jobs, {}, { ...v, query: "remote", company: "" }).map((j) => j.uid)).toEqual(["c"]);
    expect(visibleJobs(jobs, {}, { ...v, query: "", company: "Zeta" }).map((j) => j.uid)).toEqual(["b"]);
  });

  it("filters by track", () => {
    const v = { tab: "review" as const, sort: "score" as const, query: "", company: "" };
    expect(visibleJobs(jobs, {}, { ...v, track: "software" }).map((j) => j.uid)).toEqual(["b"]);
    expect(visibleJobs(jobs, {}, { ...v, track: "analyst" }).map((j) => j.uid)).toEqual(["a"]);
    expect(visibleJobs(jobs, {}, { ...v, track: "all" }).map((j) => j.uid)).toEqual(["b", "a", "c"]);
  });

  it("does not change the input array", () => {
    const copy = [...jobs];
    visibleJobs(jobs, {}, { tab: "review", query: "", company: "", sort: "date" });
    expect(jobs).toEqual(copy);
  });
});

describe("marks", () => {
  it("toggles and records when and resume", () => {
    const now = new Date("2026-10-12T05:00:00Z");
    const m1 = toggleMark({}, "a", "applied", "HIMANSHU_FINAL_TECH.pdf", now);
    expect(m1.a).toEqual({ status: "applied", at: now.toISOString(), resume: "HIMANSHU_FINAL_TECH.pdf" });
    expect(toggleMark(m1, "a", "applied", "", now).a).toBeUndefined();
    expect(toggleMark(m1, "a", "hidden", "", now).a.status).toBe("hidden");
  });

  it("loads older marks without resume safely as empty string", () => {
    const storageKey = "jobradar.marks.v2";
    const legacy = JSON.stringify({
      old_job: { status: "applied", at: "2026-10-10T12:00:00Z" },
    });
    const mockStorage: Record<string, string> = { [storageKey]: legacy };
    const originalLocalStorage = globalThis.localStorage;
    (globalThis as unknown as { localStorage: Storage }).localStorage = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => { mockStorage[key] = val; },
      removeItem: (key: string) => { delete mockStorage[key]; },
      clear: () => {},
      key: () => null,
      length: 1,
    } as Storage;

    try {
      const loaded = loadMarks();
      expect(loaded.old_job).toEqual({
        status: "applied",
        at: "2026-10-10T12:00:00Z",
        resume: "",
      });
    } finally {
      (globalThis as unknown as { localStorage: Storage | undefined }).localStorage = originalLocalStorage;
    }
  });
});

describe("helpers", () => {
  it("formats posting age", () => {
    const now = new Date("2026-10-12T12:00:00Z");
    expect(postedAgo("2026-10-12T08:00:00Z", now)).toBe("posted today");
    expect(postedAgo("2026-10-11T06:00:00Z", now)).toBe("posted yesterday");
    expect(postedAgo("2026-10-02T12:00:00Z", now)).toBe("posted 10 days ago");
    expect(postedAgo(null, now)).toBe("");
  });

  it("only allows web links", () => {
    expect(safeUrl("https://ok.test")).toBe("https://ok.test");
    expect(safeUrl("javascript:alert(1)")).toBe("#");
  });

  it("matches every search word including track and resume", () => {
    expect(matchesQuery(jobs[0], "data pune")).toBe(true);
    expect(matchesQuery(jobs[0], "intern_added")).toBe(true);
    expect(matchesQuery(jobs[1], "software")).toBe(true);
    expect(matchesQuery(jobs[0], "data mumbai")).toBe(false);
  });

  it("lists companies once, sorted", () => {
    expect(companies(jobs)).toEqual(["Acme", "Zeta"]);
  });

  it("exports applied jobs as CSV including resume column", () => {
    const marks: Marks = {
      b: { status: "applied", at: "2026-10-11T10:00:00Z", resume: "HIMANSHU_FINAL_TECH.pdf" },
    };
    const withComma = [{ ...jobs[1], title: 'Analyst, "Growth"' }];
    expect(appliedCsv(withComma, marks)).toBe(
      'applied_on,title,company,location,resume,url\n2026-10-11,"Analyst, ""Growth""",Zeta,"Pune, India",HIMANSHU_FINAL_TECH.pdf,https://x.test/1\n',
    );
  });
});
