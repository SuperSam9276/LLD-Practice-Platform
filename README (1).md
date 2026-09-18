# LLD Practice Platform

Practice a low-level design problem, submit a written design, and get back per-criterion
feedback with the evidence behind each judgement. Every attempt is kept, so the point is
improving across attempts rather than solving a problem once.

Built as a two-day assignment. It is a prototype: it works end to end, and it is small on
purpose.

- **[DESIGN.md](DESIGN.md)** — domain model, evaluation approach, trade-offs
- **[RESEARCH.md](RESEARCH.md)** — the learner problem and what already exists
- **[AI_USAGE.md](AI_USAGE.md)** — where AI helped and where it was overruled
- **[STRUCTURE.md](STRUCTURE.md)** — repository layout and dependency direction

## What it does

```
Pick a problem → write a design → submit → structural checks → AI evaluation
→ per-criterion feedback → history → try again with a fresh attempt
```

Three problems ship with it: Parking Lot, Vending Machine, Elevator System.

## Running it

### Requirements

- Python 3.11+
- PostgreSQL 14+
- Node 18+
- An Anthropic API key (optional — there is a mock evaluator)

### 1. Database

```bash
createdb lld_practice
psql lld_practice -f backend/schema.sql
```

### 2. Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # then fill it in
export $(grep -v '^#' .env | xargs)

python backend/scripts/seed_problems.py     # inserts the three problems
uvicorn backend.api.main:app --reload --port 8000
```

Environment variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | e.g. `postgresql+psycopg://user:pass@localhost:5432/lld_practice` |
| `ANTHROPIC_API_KEY` | needed only when the real evaluator is in use |
| `LLM_EVALUATOR` | set to `mock` to run without an API key |

Set `LLM_EVALUATOR=mock` and the platform runs fully offline with canned but
well-formed feedback. Useful for tests, and for demoing when the network is not
cooperating.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to port 8000, so there is no
CORS configuration to do.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/problems` | list problems |
| `GET` | `/problems/{id}` | one problem with its requirements |
| `POST` | `/attempts` | start an attempt on a problem |
| `POST` | `/attempts/{id}/submit` | submit a design; evaluation starts in the background |
| `GET` | `/evaluations/{id}` | evaluation status and, once complete, the assessments |
| `GET` | `/attempts` | attempt history, newest first |

Error responses that matter: `422` carries an `issues` list when the structural checks
reject a submission; `409` means the attempt was already submitted.

## Key decisions

The reasoning is in DESIGN.md; the short version:

- **Feedback is a rubric, not a reference solution.** Several LLD designs can be right.
  Diffing against one "correct" answer teaches imitation, so each criterion is judged on
  its own with quoted evidence from the learner's own text.
- **No overall score.** Categorical bands — weak, adequate, strong — per criterion. The
  model never emits a number.
- **Deterministic checks are real code, not prompt instructions.** Structure and required
  sections are validated before the model is involved. That separation is what makes a
  rule-based evaluator addable later.
- **Submissions are immutable and retrying starts a new attempt.** Rewriting after
  feedback teaches more than patching.
- **The submission is stored before evaluation starts.** An evaluator failure costs
  feedback, never work.
- **Two seams carry the extensibility story**: `SubmissionContent` for new submission
  formats, `Evaluator` for new evaluation approaches. Neither has a second implementation
  in the MVP, and that is deliberate — the interfaces earn their place by being the
  answer to a specific change, not by being populated with features nobody asked for.

## Limitations

Chosen, not missed. The full list is in DESIGN.md §8; the ones a reader will hit first:

- No user accounts — every attempt belongs to the same implicit learner.
- Draft text is not saved; refreshing the practice page loses in-progress writing.
- Opening the practice page creates the attempt, so abandoning it leaves a `STARTED` row
  in history.
- A server crash mid-evaluation strands an evaluation in `EVALUATING`; there is no
  recovery sweep.
- Evaluation runs in a background task inside the web process, not a queue.
- History is global rather than per problem, and there is no recurring-weakness view yet
  — though the per-criterion table is stored in a shape that would support one.

## Tests

```bash
pytest
```

Tests run against the mock evaluator and fake repositories, so no database or API key is
needed. They cover the state transitions, duplicate submit and duplicate evaluation,
submission validation failures, evaluator failure moving an evaluation to `FAILED`, and
attempt history.
