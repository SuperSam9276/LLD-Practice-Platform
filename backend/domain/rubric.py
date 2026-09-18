from dataclasses import dataclass


@dataclass(frozen=True)
class RubricCriterion:
    name: str
    description: str


@dataclass(frozen=True)
class Rubric:
    key: str
    criteria: list[RubricCriterion]


# MVP: a single shared rubric, referenced by key from Problem.rubric_key
# (decision 5.2 -- rubric is configuration, defined in code, not DB rows,
# because there is no runtime write path / editing UI for it in the MVP).
DEFAULT_RUBRIC = Rubric(
    key="lld-default-v1",
    criteria=[
        RubricCriterion("requirement_understanding",
                         "Does the design address the stated requirements and reasonable assumptions?"),
        RubricCriterion("responsibilities",
                         "Are class responsibilities well-defined and appropriately scoped (SRP)?"),
        RubricCriterion("coupling_cohesion",
                         "Is coupling between classes low and cohesion within classes high?"),
        RubricCriterion("encapsulation_interfaces",
                         "Are internals properly encapsulated, with clear interfaces between components?"),
        RubricCriterion("abstraction_patterns",
                         "Is abstraction/pattern usage appropriate -- neither missing nor overused?"),
        RubricCriterion("extensibility",
                         "How well would the design absorb plausible future requirement changes?"),
        RubricCriterion("edge_cases_testability",
                         "Are edge cases considered, and is the design structured to be testable?"),
        RubricCriterion("explanation_quality",
                         "Is the design reasoning clearly and specifically explained?"),
    ],
)

RUBRICS_BY_KEY: dict[str, Rubric] = {
    DEFAULT_RUBRIC.key: DEFAULT_RUBRIC,
}


def get_rubric(rubric_key: str) -> Rubric:
    return RUBRICS_BY_KEY[rubric_key]
