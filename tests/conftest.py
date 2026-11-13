from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
FIXED_TIME = "2026-11-13T00:00:00Z"


@pytest.fixture
def samples() -> Path:
    return SAMPLES
