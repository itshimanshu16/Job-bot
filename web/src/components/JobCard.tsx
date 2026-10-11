import { memo, useState } from "react";
import { postedAgo, safeUrl } from "../lib/jobs";
import type { Job, Mark, MarkStatus } from "../types";

interface Props {
  job: Job;
  mark: Mark | undefined;
  onToggle: (uid: string, status: MarkStatus, resume?: string) => void;
  trackLabels?: Record<string, string>;
}

const DEFAULT_LABELS: Record<string, string> = {
  software: "Software / Full-stack",
  analyst: "Analyst & Consulting",
  supply_chain: "Supply Chain & Operations",
};

function experienceText(years: number | null): string {
  if (years === null) return "Not stated";
  if (years === 0) return "None required";
  return `${years}+ years`;
}

export const JobCard = memo(function JobCard({ job, mark, onToggle, trackLabels }: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const applied = mark?.status === "applied";
  const hidden = mark?.status === "hidden";
  const place = job.location || (job.remote ? "Remote" : "");
  const where = [place, postedAgo(job.posted)].filter(Boolean).join(", ");
  const detailsId = `d-${job.uid.replace(/[^a-z0-9]/gi, "-")}`;

  const copyResume = () => {
    if (!job.resume) return;
    try {
      navigator.clipboard.writeText(job.resume)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        })
        .catch(() => {});
    } catch {
      /* clipboard unsupported */
    }
  };

  const labelMap = { ...DEFAULT_LABELS, ...trackLabels };
  const otherTracks = Object.entries(job.track_scores || {})
    .filter(([tid, s]) => tid !== job.track && s > 0 && job.score - s <= 10)
    .sort((a, b) => b[1] - a[1]);

  return (
    <li className={`job${applied ? " is-applied" : ""}`}>
      <div className="meter" aria-hidden="true">
        <span style={{ height: `${Math.max(6, job.score)}%` }} />
      </div>

      <div className="main">
        <h2 className="title">
          <a href={safeUrl(job.url)} target="_blank" rel="noopener noreferrer">
            {job.title}
          </a>
          {job.is_new && !mark && <span className="new">New</span>}
        </h2>
        <p className="where">
          <span className="co">{job.company}</span>
          {where && `, ${where}`}
        </p>
        {job.resume && (
          <p className="resume-pick">
            Send: <strong className="resume-file">{job.resume}</strong>
            {job.resume_reason && <span className="resume-reason"> ({job.resume_reason})</span>}
            <button type="button" className="copy-btn" onClick={copyResume}>
              {copied ? "Copied!" : "Copy file name"}
            </button>
          </p>
        )}
        {applied && (
          <p className="applied-on">
            Sent {mark.resume || job.resume || "resume"} on{" "}
            {new Date(mark.at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
          </p>
        )}
        {job.reasons.length > 0 && <p className="why">Matched on {job.reasons.join("; ")}</p>}
        {job.llm_reason && (
          <p className="ai">
            <b>AI fit {job.llm_score}.</b> {job.llm_reason}
          </p>
        )}
        {otherTracks.length > 0 && (
          <p className="also-fits">
            Also fits: {otherTracks.map(([tid]) => labelMap[tid] || tid).join(", ")}
          </p>
        )}
        {job.flags.length > 0 && <p className="flag">Check before applying: {job.flags.join("; ")}</p>}

        <button
          type="button"
          className="more"
          aria-expanded={open}
          aria-controls={detailsId}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? "Fewer details" : "More details"}
        </button>
        {open && (
          <dl className="details" id={detailsId}>
            {job.department && (
              <>
                <dt>Team</dt>
                <dd>{job.department}</dd>
              </>
            )}
            {(job.employment_type || job.seniority) && (
              <>
                <dt>Type</dt>
                <dd>{[job.employment_type, job.seniority].filter(Boolean).join(", ")}</dd>
              </>
            )}
            <dt>Experience asked</dt>
            <dd>{experienceText(job.min_years)}</dd>
            <dt>Found on</dt>
            <dd className="cap">{job.source}</dd>
            {job.snippet && (
              <>
                <dt>From the posting</dt>
                <dd className="snippet">
                  {job.snippet}
                  {job.snippet.length >= 400 && "…"}
                </dd>
              </>
            )}
          </dl>
        )}
      </div>

      <div className="side">
        <div className="score-wrap">
          <div className="score">
            {job.score}
            <small>match</small>
          </div>
          {job.track_label && <span className="track-badge">{job.track_label}</span>}
        </div>
        <div className="acts">
          <a className="apply" href={safeUrl(job.apply_url || job.url)} target="_blank" rel="noopener noreferrer">
            Apply
          </a>
          <button
            type="button"
            aria-pressed={applied}
            onClick={() => onToggle(job.uid, "applied", job.resume)}
          >
            {applied ? "Applied" : "Mark applied"}
          </button>
          <button type="button" aria-pressed={hidden} onClick={() => onToggle(job.uid, "hidden")}>
            {hidden ? "Unhide" : "Hide"}
          </button>
        </div>
      </div>
    </li>
  );
});
