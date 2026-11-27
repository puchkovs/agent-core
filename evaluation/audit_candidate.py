"""Reproducible candidate history, archive and documentation checks.

Pattern checks are limited evidence, not a proof that no possible secret exists.
No matched content is printed.
"""

from __future__ import annotations

import ast
import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
secret = re.compile(
    rb"gsk_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{24,}|"
    rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----|AKIA[A-Z0-9]{16}"
)
original = "c931cf976fa51e4eb664f529e818c40df2c872d0"
subprocess.run(["git", "merge-base", "--is-ancestor", original, "HEAD"], cwd=root, check=True)
objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=root, text=True)
blobs = 0
for line in objects.splitlines():
    oid, _, name = line.partition(" ")
    kind = subprocess.check_output(["git", "cat-file", "-t", oid], cwd=root).strip()
    if kind != b"blob":
        continue
    blobs += 1
    data = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=root)
    if secret.search(data):
        raise SystemExit("Credential pattern in historical path: " + name)
    parts = Path(name).parts
    if any(p in {".venv", "__pycache__", ".env", "graphify-out"} for p in parts):
        raise SystemExit("Unexpected historical material: " + name)

for path in [root / "README.md", *sorted((root / "docs").rglob("*.md"))]:
    text = path.read_text()
    for link in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in link and not link.startswith("#"):
            assert (path.parent / link.split("#")[0]).exists(), (path, link)
    for block in re.findall(r"```python\n(.*?)```", text, re.S):
        ast.parse(block)

wheel = root / "dist/agent_core_runtime-0.1.0a1-py3-none-any.whl"
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert any(name.endswith("/licenses/LICENSE") for name in names)
    assert "agent_core/py.typed" in names
    for path in (root / "src/agent_core").rglob("*.py"):
        relative = str(path.relative_to(root / "src"))
        assert archive.read(relative) == path.read_bytes(), relative
    for name in names:
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert not any(p in {".git", ".venv", "__pycache__", ".env"} for p in Path(name).parts)

with tarfile.open(root / "dist/agent_core_runtime-0.1.0a1.tar.gz") as archive:
    for member in archive.getmembers():
        path = Path(member.name)
        assert not path.is_absolute() and ".." not in path.parts
        assert not member.issym() and not member.islnk()
        assert not any(p in {".git", ".venv", "__pycache__", ".env"} for p in path.parts)
        if member.isfile():
            handle = archive.extractfile(member)
            assert handle is not None
            assert not secret.search(handle.read()), member.name

print(f"Candidate audit passed: {blobs} historical blobs; archive/source and doc checks.")
