import type { TrackMeta } from "../types";

interface Props {
  track: string;
  tracks?: TrackMeta[];
  counts: Record<string, number>;
  onChange: (track: string) => void;
}

const DEFAULT_TRACKS = [
  { id: "software", label: "Software / Full-stack" },
  { id: "analyst", label: "Analyst & Consulting" },
  { id: "supply_chain", label: "Supply Chain & Operations" },
];

export function TrackFilter({ track, tracks, counts, onChange }: Props) {
  const list = tracks && tracks.length > 0 ? tracks : DEFAULT_TRACKS;

  return (
    <div className="track-chips" role="group" aria-label="Filter by track">
      <button
        type="button"
        className={`chip${track === "all" ? " is-active" : ""}`}
        aria-pressed={track === "all"}
        onClick={() => onChange("all")}
      >
        All <span className="chip-count">{counts.all ?? 0}</span>
      </button>
      {list.map((t) => (
        <button
          key={t.id}
          type="button"
          className={`chip${track === t.id ? " is-active" : ""}`}
          aria-pressed={track === t.id}
          onClick={() => onChange(t.id)}
        >
          {t.label} <span className="chip-count">{counts[t.id] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
