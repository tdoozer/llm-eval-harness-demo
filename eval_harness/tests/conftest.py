from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import fresh_db  # noqa: E402
from app.fake_llm import FakeLLM, FlakyOnceLLM  # noqa: E402


@pytest.fixture
def db():
    """A brand-new, empty SQLite DB for this test only. Deleted on teardown."""
    with fresh_db() as conn:
        yield conn


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def flaky_llm() -> FlakyOnceLLM:
    return FlakyOnceLLM()
