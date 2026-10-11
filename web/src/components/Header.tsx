import type { Job, Meta } from "../types";

export function Header({ meta, jobs }: { meta: Meta; jobs: Job[] }) {
  const newCount = jobs.filter((j) => j.is_new).length;
  const updated = new Date(meta.generated).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
  const failed = meta.boards.filter((b) => b.error).length;

  return (
    <header className="top">
      <h1 className="headline">
        {meta.first_run ? (
          <>
            <span className="count">{jobs.length}</span> matching {jobs.length === 1 ? "job" : "jobs"} on the first run
          </>
        ) : (
          <>
            <span className="count">{newCount}</span> new {newCount === 1 ? "job" : "jobs"} since yesterday
          </>
        )}
      </h1>
      <p className="sub">
        {jobs.length} jobs match your search, out of {meta.total_fetched} open roles on {meta.boards_ok} company
        boards. Updated {updated}.
        {failed > 0 && ` ${failed} ${failed === 1 ? "board" : "boards"} couldn't be read; see the list at the bottom.`}
      </p>
      {meta.notes.length > 0 && (
        <div className="notes">
          {meta.notes.map((n) => (
            <p key={n}>{n}</p>
          ))}
        </div>
      )}
    </header>
  );
}
