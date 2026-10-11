import type { Tab } from "../types";

const LABELS: Record<Tab, string> = {
  review: "To review",
  new: "New",
  applied: "Applied",
  hidden: "Hidden",
};

export function Tabs({ tab, counts, onChange }: { tab: Tab; counts: Record<Tab, number>; onChange: (t: Tab) => void }) {
  return (
    <nav className="tabs" aria-label="Job lists">
      {(Object.keys(LABELS) as Tab[]).map((t) => (
        <button
          key={t}
          type="button"
          className="tab"
          aria-current={tab === t ? "page" : undefined}
          onClick={() => onChange(t)}
        >
          {LABELS[t]} <span className="tab-count">{counts[t]}</span>
        </button>
      ))}
    </nav>
  );
}
