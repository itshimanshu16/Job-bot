import type { Meta } from "../types";

export function Footer({ meta }: { meta: Meta }) {
  const drops = Object.entries(meta.drops || {}).sort((a, b) => b[1] - a[1]);
  return (
    <footer className="foot">
      {meta.keywords && meta.keywords.length > 0 && (
        <p>Searching for: {meta.keywords.join(", ")}.</p>
      )}

      {meta.tracks && meta.tracks.length > 0 && (
        <section className="resumes-in-use">
          <h3>Resumes in use</h3>
          <div className="track-resumes-grid">
            {meta.tracks.map((t) => (
              <div key={t.id} className="track-resume-card">
                <h4>{t.label}</h4>
                <ul>
                  {t.resumes.map((r) => (
                    <li key={r.file}>
                      <code>{r.file}</code>
                      <p className="resume-desc">{r.use_for}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {meta.boards && meta.boards.length > 0 && (
        <details>
          <summary>Company boards checked this run ({meta.boards.length})</summary>
          <table>
            <thead>
              <tr>
                <th>Board</th>
                <th>Company</th>
                <th>Open jobs</th>
              </tr>
            </thead>
            <tbody>
              {meta.boards.map((b) => (
                <tr key={`${b.source}/${b.slug}`}>
                  <td>
                    {b.source}/{b.slug}
                  </td>
                  <td>{b.company}</td>
                  <td className={b.error ? "err" : undefined}>{b.error ? `Failed: ${b.error}` : b.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {drops.length > 0 && (
        <details>
          <summary>Why other jobs were left out</summary>
          <table>
            <tbody>
              {drops.map(([reason, n]) => (
                <tr key={reason}>
                  <td>{reason}</td>
                  <td>{n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </footer>
  );
}
