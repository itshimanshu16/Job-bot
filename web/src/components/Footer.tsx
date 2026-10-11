import type { Meta } from "../types";

export function Footer({ meta }: { meta: Meta }) {
  const drops = Object.entries(meta.drops).sort((a, b) => b[1] - a[1]);
  return (
    <footer className="foot">
      <p>Searching for: {meta.keywords.join(", ")}.</p>
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
