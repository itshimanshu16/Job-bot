import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Controls } from "./components/Controls";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { JobCard } from "./components/JobCard";
import { Tabs } from "./components/Tabs";
import { useJobData } from "./lib/data";
import { appliedCsv, companies, tabCounts, visibleJobs, type View } from "./lib/jobs";
import { useMarks } from "./lib/marks";
import type { Payload } from "./types";

export default function App() {
  const state = useJobData();

  if (state.kind === "loading") {
    return <Shell><p className="status">Loading jobs…</p></Shell>;
  }
  if (state.kind === "missing") {
    return (
      <Shell>
        <div className="status">
          <h1 className="headline">No results yet</h1>
          <p>
            The first search hasn't finished. Open the repository's <strong>Actions</strong> tab, run the{" "}
            <strong>Job Radar</strong> workflow, and reload this page when it turns green.
          </p>
        </div>
      </Shell>
    );
  }
  if (state.kind === "error") {
    return <Shell><p className="status error" role="alert">{state.message}</p></Shell>;
  }
  return <Radar data={state.data} />;
}

function Shell({ children }: { children: ReactNode }) {
  return <main className="wrap">{children}</main>;
}

function Radar({ data }: { data: Payload }) {
  const { meta, jobs } = data;
  const { marks, toggle } = useMarks();
  const [view, setView] = useState<View>({ tab: "review", query: "", company: "", sort: "score" });

  useEffect(() => {
    document.title = meta.title || "Job Radar";
  }, [meta.title]);

  const counts = useMemo(() => tabCounts(jobs, marks), [jobs, marks]);
  const rows = useMemo(() => visibleJobs(jobs, marks, view), [jobs, marks, view]);
  const companyList = useMemo(() => companies(jobs), [jobs]);

  const downloadApplied = () => {
    const blob = new Blob([appliedCsv(jobs, marks)], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `applied-jobs-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };

  return (
    <main className="wrap">
      <Header meta={meta} jobs={jobs} />
      <div className="bar">
        <Tabs tab={view.tab} counts={counts} onChange={(tab) => setView((v) => ({ ...v, tab }))} />
        <Controls
          view={view}
          companies={companyList}
          onChange={(patch) => setView((v) => ({ ...v, ...patch }))}
          shown={rows.length}
          onDownloadApplied={view.tab === "applied" && counts.applied > 0 ? downloadApplied : undefined}
        />
      </div>

      {rows.length === 0 ? (
        <EmptyState tab={view.tab} filtered={Boolean(view.query || view.company)} total={jobs.length} />
      ) : (
        <ol className="jobs">
          {rows.map((job) => (
            <JobCard key={job.uid} job={job} mark={marks[job.uid]} onToggle={toggle} />
          ))}
        </ol>
      )}

      <Footer meta={meta} />
    </main>
  );
}

function EmptyState({ tab, filtered, total }: { tab: View["tab"]; filtered: boolean; total: number }) {
  let title = "Nothing here";
  let body = "";
  if (filtered) {
    title = "Nothing matches these filters";
    body = "Clear the search box or pick All companies to see more.";
  } else if (total === 0) {
    title = "No matching jobs yet";
    body = "Add more companies to companies.yaml or widen the keywords in config.yaml. The next run will pick them up.";
  } else if (tab === "review" || tab === "new") {
    title = tab === "new" ? "No new jobs to review" : "You've gone through every job";
    body = "New matches appear here after the next run.";
  } else if (tab === "applied") {
    body = "Jobs you mark as applied are listed here, so you can track them.";
  } else {
    body = "Jobs you hide are kept here in case you change your mind.";
  }
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}
