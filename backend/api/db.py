import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/lld_platform")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_evaluator():
    """Env-var switch: LLM_EVALUATOR=mock for local dev/tests without an
    API key; anything else (default) uses the real LLMEvaluator."""
    if os.environ.get("LLM_EVALUATOR", "").lower() == "mock":
        from infrastructure.evaluators.mock_evaluator import MockEvaluator
        return MockEvaluator()
    from infrastructure.evaluators.llm_evaluator import LLMEvaluator
    return LLMEvaluator()
