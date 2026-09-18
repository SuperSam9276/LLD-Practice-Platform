import { useEffect, useRef, useState } from "react";
import { getEvaluation, isTerminal } from "../api.js";

// Evaluation runs in a FastAPI BackgroundTask (decision #37), so the UI polls.
// Fixed 2s interval, capped at ~2 minutes, then it stops and tells the learner
// what to do rather than spinning forever. No websockets, no exponential backoff —
// one learner, one evaluation, seconds-scale latency.

const POLL_MS = 2000;
const MAX_POLLS = 60;

export default function FeedbackPage({ evaluationId }) {
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState(null);
  const [timedOut, setTimedOut] = useState(false);
  const polls = useRef(0);

  useEffect(() => {
    let timer = null;
    let cancelled = false;

    const tick = async () => {
      try {
        const e = await getEvaluation(evaluationId);
        if (cancelled) return;
        setEvaluation(e);
        if (isTerminal(e.status)) return;
        if (++polls.current >= MAX_POLLS) {
          setTimedOut(true);
          return;
        }
        timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [evaluationId]);

  if (error) return <p className="error">{error}</p>;
  if (!evaluation) return <p className="muted">Loading evaluation…</p>;

  if (evaluation.status === "FAILED") {
    return (
      <section>
        <h1>Evaluation failed</h1>
        <p className="error">
          {evaluation.failureReason ?? "The evaluator did not return a usable result."}
        </p>
        <p className="muted">
          Your submission is saved — it was stored before evaluation started. Start a new
          attempt to try again.
        </p>
        <a className="button" href="#/history">
          Back to history
        </a>
      </section>
    );
  }

  if (!isTerminal(evaluation.status)) {
    return (
      <section>
        <h1>Evaluating your design</h1>
        {timedOut ? (
          <p className="error">
            Still running after two minutes. Reload this page to check again, or look for the
            attempt in your history.
          </p>
        ) : (
          <p className="muted">
            Status: {evaluation.status.toLowerCase()}. This page updates on its own.
          </p>
        )}
      </section>
    );
  }

  return (
    <section>
      <h1>Feedback</h1>
      <p className="muted">
        Each criterion is judged on its own, with the evidence the evaluator used. There is no
        single score — two good designs can differ.
      </p>

      <table className="rubric">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Score</th>
            <th>Evidence</th>
            <th>Concern</th>
            <th>Suggestion</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {evaluation.assessments.map((a) => (
            <tr key={a.criterionName}>
              <td>
                <strong>{a.criterionName}</strong>
                <div className="muted small">{a.criterionDescription}</div>
              </td>
              <td>
                <span className={`score score-${a.score}`}>{a.score}</span>
              </td>
              <td>{a.evidence}</td>
              <td>{a.concern || <span className="muted">—</span>}</td>
              <td>{a.suggestion || <span className="muted">—</span>}</td>
              <td className="muted">{a.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="actions">
        <a className="button" href="#/">
          Try another problem
        </a>
        <a className="button secondary" href="#/history">
          See all attempts
        </a>
      </div>
    </section>
  );
}
