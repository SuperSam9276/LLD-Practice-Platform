from abc import ABC, abstractmethod


class SubmissionContent(ABC):
    """Abstraction over 'what form did the learner's design take'.

    Change Test A answer: adding a new submission format (e.g. a class
    diagram) means adding one new subclass here. Nothing else in the
    domain (Submission, Evaluation, Evaluator, SubmissionValidator)
    needs to change, because they all depend on this interface, not on
    a concrete format.
    """

    @abstractmethod
    def get_evaluatable_text(self) -> str:
        """Return the text representation an Evaluator can reason about.

        Every format -- text, a future diagram, a future code
        submission -- must be able to produce *some* textual
        description, because the evaluator (today an LLM) consumes
        text/prompts. A DiagramSubmissionContent would store diagram
        source separately but still implement this method (e.g. by
        returning a structured textual description of the diagram).
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Discriminator value matching the DB's content_type column."""
        raise NotImplementedError


class TextSubmissionContent(SubmissionContent):
    """MVP's only concrete format: free-form structured text containing
    requirements/assumptions, classes, responsibilities, relationships,
    and design explanation."""

    def __init__(self, raw_text: str):
        self._raw_text = raw_text

    def get_evaluatable_text(self) -> str:
        return self._raw_text

    @property
    def content_type(self) -> str:
        return "TEXT"

    @property
    def raw_text(self) -> str:
        return self._raw_text
