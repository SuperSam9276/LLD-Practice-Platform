// Single adapter between the UI and the FastAPI layer (Phase 7, decision #42).
//
// Design intent: the six endpoints are described in exactly one module. Components
// never see raw response shapes, HTTP status codes, or field-name variations.
// If api/schemas.py and this file disagree, this file is the only thing to change.
//
// Backend contract assumed here (verify against api/schemas.py):
//   GET  /problems                 -> [{ id, title, description }]
//   GET  /problems/{id}            -> { id, title, description }
//   POST /attempts                 -> body { problem_id } -> { id, problem_id, status }
//   POST /attempts/{id}/submit     -> body { content_text } -> { submission_id, evaluation_id, status }
//   GET  /evaluations/{id}         -> { id, status, failure_reason, assessments: [...] }
//   GET  /attempts                 -> [{ id, problem_id, problem_title, status, created_at,
//                                        evaluation_id, evaluation_status }]

const BASE = "/api";

// ---- error types the UI can branch on -------------------------------------
// Mirrors the backend error mapping (decision #44): 422 validation, 409 conflict.

export class ValidationError extends Error {
  constructor(issues) {
    super("Submission did not pass the structural checks");
    this.name = "ValidationError";
    this.issues = issues;
  }
}

export class ConflictError extends Error {
  constructor(message) {
    super(message);
    this.name = "ConflictError";
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the server. Is the API running on port 8000?");
  }

  if (res.status === 204) return null;

  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (res.ok) return body;

  const detail = body?.detail ?? body;

  if (res.status === 422) {
    const issues = detail?.issues ?? body?.issues ?? [];
    throw new ValidationError(
      Array.isArray(issues) && issues.length
        ? issues
        : ["The submission was rejected but no issue list was returned."]
    );
  }
  if (res.status === 409) {
    throw new ConflictError(
      typeof detail === "string" ? detail : "This attempt has already been submitted."
    );
  }
  if (res.status === 404) {
    throw new Error(typeof detail === "string" ? detail : "Not found.");
  }
  throw new Error(
    typeof detail === "string" ? detail : `Request failed (${res.status}).`
  );
}

// ---- normalizers ----------------------------------------------------------
// Tolerant on the way in, exact on the way out. Components consume these shapes only.

const pick = (obj, ...keys) => {
  for (const k of keys) {
    if (obj?.[k] !== undefined && obj?.[k] !== null) return obj[k];
  }
  return undefined;
};

const toProblem = (p) => ({
  id: pick(p, "id", "problem_id"),
  title: pick(p, "title") ?? "Untitled problem",
  description: pick(p, "description") ?? "",
});

const toAssessment = (a) => ({
  criterionName: pick(a, "criterion_name", "criterionName") ?? "Unnamed criterion",
  criterionDescription: pick(a, "criterion_description", "criterionDescription") ?? "",
  score: pick(a, "score") ?? "unknown",
  evidence: pick(a, "evidence") ?? "",
  concern: pick(a, "concern") ?? "",
  suggestion: pick(a, "suggestion") ?? "",
  confidence: pick(a, "confidence") ?? "unknown",
});

const toEvaluation = (e) => ({
  id: pick(e, "id", "evaluation_id"),
  status: String(pick(e, "status", "evaluation_status") ?? "PENDING").toUpperCase(),
  failureReason: pick(e, "failure_reason", "failureReason") ?? null,
  assessments: (pick(e, "assessments", "criterion_assessments") ?? []).map(toAssessment),
});

const toAttemptSummary = (a) => ({
  id: pick(a, "id", "attempt_id"),
  problemId: pick(a, "problem_id", "problemId"),
  problemTitle: pick(a, "problem_title", "problemTitle") ?? "Problem",
  status: String(pick(a, "status", "attempt_status") ?? "STARTED").toUpperCase(),
  createdAt: pick(a, "created_at", "createdAt") ?? null,
  evaluationId: pick(a, "evaluation_id", "evaluationId") ?? null,
  evaluationStatus: pick(a, "evaluation_status", "evaluationStatus")
    ? String(pick(a, "evaluation_status", "evaluationStatus")).toUpperCase()
    : null,
});

// ---- the six calls --------------------------------------------------------

export const listProblems = async () => (await request("/problems")).map(toProblem);

export const getProblem = async (problemId) =>
  toProblem(await request(`/problems/${problemId}`));

export const startAttempt = async (problemId) => {
  const a = await request("/attempts", {
    method: "POST",
    body: JSON.stringify({ problem_id: problemId }),
  });
  return { id: pick(a, "id", "attempt_id"), status: pick(a, "status") };
};

export const submitAttempt = async (attemptId, contentText) => {
  const r = await request(`/attempts/${attemptId}/submit`, {
    method: "POST",
    body: JSON.stringify({ content_text: contentText }),
  });
  return {
    submissionId: pick(r, "submission_id", "submissionId"),
    evaluationId: pick(r, "evaluation_id", "evaluationId", "id"),
    status: String(pick(r, "status", "evaluation_status") ?? "PENDING").toUpperCase(),
  };
};

export const getEvaluation = async (evaluationId) =>
  toEvaluation(await request(`/evaluations/${evaluationId}`));

export const listAttempts = async () => (await request("/attempts")).map(toAttemptSummary);

export const isTerminal = (status) => status === "COMPLETED" || status === "FAILED";
