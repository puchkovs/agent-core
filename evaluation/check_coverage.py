"""Enforce branch-aware coverage for the components making execution guarantees."""

import json
import sys

report = json.load(open(sys.argv[1]))
critical = {
    "runtime.py",
    "store.py",
    "tools.py",
    "policy.py",
    "context.py",
    "contracts.py",
    "streaming.py",
    "sse.py",
    "http.py",
}
failed = []
for path, entry in report["files"].items():
    if path.rsplit("/", 1)[-1] in critical:
        percent = entry["summary"]["percent_covered"]
        if percent < 90:
            failed.append((path, percent))
if failed:
    raise SystemExit(f"Critical coverage below 90%: {failed}")
print("All critical components meet 90% branch-aware coverage.")
