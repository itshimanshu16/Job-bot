import { describe, expect, it } from "vitest";
import type { Job, Marks } from "../types";
import { appliedCsv, companies, inTab, matchesQuery, postedAgo, safeUrl, tabCounts, visibleJobs } from "./jobs";
import { toggleMark } from "./marks";

function job(over: Partial<Job>): Job {
  return {
    uid: "u1", source: "lever", company: "Acme", title: "Data Analyst", url: "https://x.test/1",
    apply_url: "", location: "Pune, India", remote: false, posted: "2026-10-10T00:00:00+00:00",
    department: "", employment_type: "", seniority: "", score: 50, reasons: [], flags: [], min_years: null,
    is_new: false, first_seen: "", llm_score: null, llm_reason: "", snippet: "", ...over,
  };
}

const jobs = [
  job({ uid: "a", title: "Data Analyst", company: "Acme", score: 70, is_new: true, posted: "2026-10-01T00:00:00Z" }),
  job({ uid: "b", title: "Business Analyst", company: "Zeta", score: 90, posted: "2026-10-09T00:00:00Z" }),
  job({ uid: "c", title: "Product Analyst", company: "Acme", score: 40, is_new: true, location: "Remote" }),
];

describe("tabs", () => {
  const marks: Marks = { c: { status: "applied", at: "2026-10-11T10:00:00Z" } };
  it("puts each job in the right list", () => {
    expect(inTab(jobs[0], marks, "review")).toBe(true);
    expect(inTab(jobs[2], marks, "review")).toBe(false);
    expect(inTab(jobs[2], marks, "new")).toBe(false); // applied jobs leave the New list
    expect(tabCounts(jobs, marks)).toEqual({ review: 2, new: 1, applied: 1, hidden: 0 });
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

  it("does not change the input array", () => {
    const copy = [...jobs];
    visibleJobs(jobs, {}, { tab: "review", query: "", company: "", sort: "date" });
    expect(jobs).toEqual(copy);
  });
});

describe("marks", () => {
  it("toggles and records when", () => {
    const now = new Date("2026-10-12T05:00:00Z");
    const m1 = toggleMark({}, "a", "applied", now);
    expect(m1.a).toEqual({ status: "applied", at: now.toISOString() });
    expect(toggleMark(m1, "a", "applied", now).a).toBeUndefined();
    expect(toggleMark(m1, "a", "hidden", now).a.status).toBe("hidden");
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

  it("matches every search word", () => {
    expect(matchesQuery(jobs[0], "data pune")).toBe(true);
    expect(matchesQuery(jobs[0], "data mumbai")).toBe(false);
  });

  it("lists companies once, sorted", () => {
    expect(companies(jobs)).toEqual(["Acme", "Zeta"]);
  });

  it("exports applied jobs as CSV with quoting", () => {
    const marks: Marks = { b: { status: "applied", at: "2026-10-11T10:00:00Z" } };
    const withComma = [{ ...jobs[1], title: 'Analyst, "Growth"' }];
    expect(appliedCsv(withComma, marks)).toBe(
      'applied_on,title,company,location,url\n2026-10-11,"Analyst, ""Growth""",Zeta,"Pune, India",https://x.test/1\n',
    );
  });
});
