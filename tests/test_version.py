import re
from pathlib import Path

import agent_core


def test_package_version_matches_project_metadata():
    text = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    declared = re.search(r'^version = "([^"]+)"', text, re.M)
    assert declared is not None and declared.group(1) == agent_core.__version__
