import { useEffect, useState } from "react";
import { listAttempts } from "../api.js";

// Global history across all problems (decision #11). Per-problem filtering is a
// documented extension point, not an oversight.

const formatDate = (value) => {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
};

export default function HistoryPage() {
  const [attempts, setAttempts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAttempts()
      .then(setAttempts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading history…</p>;
  if (error) return <p className="error">{error}</p>;
  if (attempts.length === 0)
    return (
      <section>
        <h1>No attempts yet</h1>
        <p className="muted">Pick a problem and design something — it will show up here.</p>
        <a className="button" href="#/">
          Browse problems
        </a>
      </section>
    );

  return (
    <section>
      <h1>Your attempts</h1>
      <p className="muted">Newest first, across every problem.</p>
      <table className="history">
        <thead>
          <tr>
            <th>Problem</th>
            <th>Started</th>
            <th>Attempt</th>
            <th>Evaluation</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.id}>
              <td>{a.problemTitle}</td>
              <td className="muted">{formatDate(a.createdAt)}</td>
              <td>{a.status.toLowerCase()}</td>
              <td>{a.evaluationStatus ? a.evaluationStatus.toLowerCase() : "—"}</td>
              <td>
                {a.evaluationId ? (
                  <a href={`#/feedback/${a.evaluationId}`}>View feedback</a>
                ) : (
                  <a href={`#/practice/${a.problemId}`}>Try this problem</a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
