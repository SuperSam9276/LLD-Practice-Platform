import { useEffect, useState } from "react";
import { getProblem, startAttempt, submitAttempt, ValidationError, ConflictError } from "../api.js";
import { navigate } from "../App.jsx";

// Merged problem + practice page (decision #11): requirements stay on screen while
// the learner writes, so they can check their design against them without navigating.
//
// The Attempt is created when this page opens, not when the learner submits.
// Consequence: an abandoned page leaves a STARTED attempt in history. Accepted —
// STARTED is a real domain state (decision #14) and creating it lazily at submit time
// would make it unreachable in the product. The draft text itself is not persisted,
// so a refresh loses it; noted as a limitation, not designed around.

const TEMPLATE = `## Requirements and assumptions
(What are you building? What did you decide to leave out, and why?)

## Classes and responsibilities
(One line per class: what it owns, what it does NOT own.)

## Relationships
(Who holds a reference to whom, and what the cardinality is.)

## Design reasoning
(Key trade-offs, patterns you used and why, what you would change if a requirement changed.)
`;

export default function PracticePage({ problemId }) {
  const [problem, setProblem] = useState(null);
  const [attemptId, setAttemptId] = useState(null);
  const [text, setText] = useState(TEMPLATE);
  const [issues, setIssues] = useState([]);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await getProblem(problemId);
        if (cancelled) return;
        setProblem(p);
        const a = await startAttempt(problemId);
        if (!cancelled) setAttemptId(a.id);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [problemId]);

  const onSubmit = async () => {
    setSubmitting(true);
    setIssues([]);
    setError(null);
    try {
      const result = await submitAttempt(attemptId, text);
      navigate(`/feedback/${result.evaluationId}`);
    } catch (e) {
      if (e instanceof ValidationError) setIssues(e.issues);
      else if (e instanceof ConflictError) setError(e.message);
      else setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (error && !problem) return <p className="error">{error}</p>;
  if (!problem) return <p className="muted">Loading…</p>;

  return (
    <section className="practice">
      <div className="brief">
        <h1>{problem.title}</h1>
        <pre className="description">{problem.description}</pre>
      </div>

      <div className="workspace">
        <h2>Your design</h2>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck="false"
          rows={28}
        />

        {issues.length > 0 && (
          <div className="issues">
            <p>Fix these before the design can be evaluated:</p>
            <ul>
              {issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="error">{error}</p>}

        <button
          className="button"
          onClick={onSubmit}
          disabled={submitting || !attemptId || text.trim().length === 0}
        >
          {submitting ? "Submitting…" : "Submit design"}
        </button>
        <p className="muted small">
          Submitting ends this attempt. To try the problem again you start a fresh attempt —
          submissions are never edited in place.
        </p>
      </div>
    </section>
  );
}
