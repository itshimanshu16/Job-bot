import type { View } from "../lib/jobs";
import type { Sort } from "../types";

interface Props {
  view: View;
  companies: string[];
  shown: number;
  onChange: (patch: Partial<View>) => void;
  onDownloadApplied?: () => void;
}

export function Controls({ view, companies, shown, onChange, onDownloadApplied }: Props) {
  return (
    <div className="controls" role="search">
      <input
        type="search"
        value={view.query}
        onChange={(e) => onChange({ query: e.target.value })}
        placeholder="Search title, company or place"
        aria-label="Search jobs"
      />
      <select value={view.company} onChange={(e) => onChange({ company: e.target.value })} aria-label="Company">
        <option value="">All companies</option>
        {companies.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      {view.tab !== "applied" && (
        <select value={view.sort} onChange={(e) => onChange({ sort: e.target.value as Sort })} aria-label="Sort">
          <option value="score">Best match first</option>
          <option value="date">Newest posting first</option>
        </select>
      )}
      {onDownloadApplied && (
        <button type="button" className="quiet" onClick={onDownloadApplied}>
          Download applied list
        </button>
      )}
      <span className="shown" aria-live="polite">
        {shown} {shown === 1 ? "job" : "jobs"}
      </span>
    </div>
  );
}
