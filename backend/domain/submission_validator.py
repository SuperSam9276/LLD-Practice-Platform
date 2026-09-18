from .submission_content import SubmissionContent

MIN_LENGTH = 100
REQUIRED_KEYWORDS = ["class", "responsibilit"]  # matches "responsibility"/"responsibilities"


class SubmissionValidator:
    """Deterministic, synchronous checks that gate whether an Evaluation
    is ever created (decision 18, 23). Runs BEFORE the Submission row is
    inserted -- unlike the LLM evaluator call, this has no external
    dependency and nothing is lost by validating first (decision 32).

    Deliberately NOT expressed as a DB CHECK constraint: these rules are
    business meaning that will grow (min length today, maybe "must
    mention at least one class name" tomorrow) and must live in exactly
    one place, in a language that can express growth, not duplicated
    across a migration and this class.
    """

    def validate(self, content: SubmissionContent) -> list[str]:
        issues: list[str] = []
        text = content.get_evaluatable_text()
        stripped = text.strip()

        if not stripped:
            issues.append("Submission text is empty.")
            return issues  # no point checking further on empty input

        if len(stripped) < MIN_LENGTH:
            issues.append(
                f"Submission is too short ({len(stripped)} chars; minimum {MIN_LENGTH})."
            )

        lowered = stripped.lower()
        for keyword in REQUIRED_KEYWORDS:
            if keyword not in lowered:
                issues.append(
                    f"Submission does not appear to mention '{keyword}' -- "
                    "expected some discussion of classes and responsibilities."
                )

        return issues

    def is_valid(self, content: SubmissionContent) -> bool:
        return len(self.validate(content)) == 0
