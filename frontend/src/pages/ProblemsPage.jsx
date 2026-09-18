import { useEffect, useState } from "react";
import { listProblems } from "../api.js";

export default function ProblemsPage() {
  const [problems, setProblems] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listProblems()
      .then(setProblems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading problems…</p>;
  if (error) return <p className="error">{error}</p>;
  if (problems.length === 0)
    return (
      <p className="muted">
        No problems in the database yet. Run <code>python backend/scripts/seed_problems.py</code>.
      </p>
    );

  return (
    <section>
      <h1>Pick a problem</h1>
      <p className="muted">
        Write a design, submit it, and get per-criterion feedback on what to fix next time.
      </p>
      <ul className="list">
        {problems.map((p) => (
          <li key={p.id} className="card">
            <h2>{p.title}</h2>
            <p className="clamp">{p.description}</p>
            <a className="button" href={`#/practice/${p.id}`}>
              Start an attempt
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
