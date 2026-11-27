from pathlib import Path

import pytest

from agent_core import Store


@pytest.fixture
def store(tmp_path: Path):
    instance = Store(tmp_path / "runs.sqlite")
    yield instance
    instance.close()
