import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthModal } from "./components/AuthModal";
import { Controls } from "./components/Controls";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { JobCard } from "./components/JobCard";
import { LandingPage } from "./components/LandingPage";
import { Tabs } from "./components/Tabs";
import { TrackFilter } from "./components/TrackFilter";
import { clearAuthSession, isSessionAuthed } from "./lib/auth";
import { useJobData } from "./lib/data";
import { appliedCsv, companies, tabCounts, trackCounts, visibleJobs, type View } from "./lib/jobs";
import { useMarks } from "./lib/marks";
import type { Payload } from "./types";

export default function App() {
  const state = useJobData();
  const [isAuthed, setIsAuthed] = useState<boolean>(isSessionAuthed);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);

  if (state.kind === "loading") {
    return <Shell><p className="status">Loading Job Radar…</p></Shell>;
  }

  if (state.kind === "error") {
    return <Shell><p className="status error" role="alert">{state.message}</p></Shell>;
  }

  if (!isAuthed) {
    const totalJobs = state.kind === "ready" ? state.data.jobs.length : 7300;
    const totalBoards = state.kind === "ready" ? state.data.meta.boards?.length : 21;
    return (
      <>
        <LandingPage
          onOpenLogin={() => setShowAuthModal(true)}
          totalJobs={totalJobs}
          totalBoards={totalBoards}
        />
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onSuccess={() => {
            setShowAuthModal(false);
            setIsAuthed(true);
          }}
        />
      </>
    );
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
          <button
            type="button"
            className="quiet"
            onClick={() => {
              clearAuthSession();
              setIsAuthed(false);
            }}
            style={{ marginTop: "1rem" }}
          >
            ← Return to Homepage
          </button>
        </div>
      </Shell>
    );
  }

  return (
    <Radar
      data={state.data}
      onLogout={() => {
        clearAuthSession();
        setIsAuthed(false);
      }}
    />
  );
}

function Shell({ children }: { children: ReactNode }) {
  return <main className="wrap">{children}</main>;
}

function Radar({ data, onLogout }: { data: Payload; onLogout: () => void }) {
  const { meta, jobs } = data;
  const { marks, toggle } = useMarks();
  const [view, setView] = useState<View>({
    tab: "review",
    query: "",
    company: "",
    sort: "score",
    track: "all",
  });

  useEffect(() => {
    document.title = `${meta.title || "Job Radar"} — Candidate Portal`;
  }, [meta.title]);

  const counts = useMemo(() => tabCounts(jobs, marks, view.track), [jobs, marks, view.track]);
  const tCounts = useMemo(() => trackCounts(jobs, marks, view.tab), [jobs, marks, view.tab]);
  const rows = useMemo(() => visibleJobs(jobs, marks, view), [jobs, marks, view]);
  const companyList = useMemo(() => companies(jobs), [jobs]);

  const trackLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    if (meta.tracks) {
      for (const t of meta.tracks) {
        map[t.id] = t.label;
      }
    }
    return map;
  }, [meta.tracks]);

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
      {/* ── Top Portal Bar ── */}
      <div className="portal-bar">
        <div className="portal-status">
          <span className="portal-indicator" aria-hidden="true" />
          <span>Candidate Portal (Personal Radar)</span>
        </div>
        <button
          type="button"
          className="portal-exit-btn"
          onClick={onLogout}
          title="Lock and return to public website"
        >
          🔒 Lock & Return Home
        </button>
      </div>

      <Header meta={meta} jobs={jobs} />
      <div className="bar">
        <Tabs tab={view.tab} counts={counts} onChange={(tab) => setView((v) => ({ ...v, tab }))} />
        <TrackFilter
          track={view.track || "all"}
          tracks={meta.tracks}
          counts={tCounts}
          onChange={(track) => setView((v) => ({ ...v, track }))}
        />
        <Controls
          view={view}
          companies={companyList}
          onChange={(patch) => setView((v) => ({ ...v, ...patch }))}
          shown={rows.length}
          onDownloadApplied={view.tab === "applied" && counts.applied > 0 ? downloadApplied : undefined}
        />
      </div>

      {rows.length === 0 ? (
        <EmptyState
          tab={view.tab}
          filtered={Boolean(view.query || view.company || (view.track && view.track !== "all"))}
          total={jobs.length}
        />
      ) : (
        <ol className="jobs">
          {rows.map((job) => (
            <JobCard
              key={job.uid}
              job={job}
              mark={marks[job.uid]}
              onToggle={toggle}
              trackLabels={trackLabelMap}
            />
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
    body = "Clear the search box, change track or pick All companies to see more.";
  } else if (total === 0) {
    title = "No matching jobs yet";
    body = "Add more companies to companies.yaml. The next run will pick them up.";
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
