"""Fails the backend CI job on any pip-audit finding that is not explicitly allowlisted, and
fails when an allowlisted entry has expired. Mirrors `scripts/ci/npm_audit_gate.py`'s exact
discipline for the frontend side: the allowlist is `scripts/ci/pip-audit-allowlist.json`, and
every entry names its advisory, its reason, and an expiry date so a temporary exception cannot
silently become permanent.

Unlike the npm gate (which only blocks high/critical), pip-audit has no severity field of its
own (it reports every known vulnerability for every installed package, regardless of severity),
so every finding here needs an allowlist entry or a real fix -- there is no "low severity,
ignore it" tier to fall back on.
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ALLOWLIST = Path(__file__).with_name("pip-audit-allowlist.json")


def main() -> int:
    report = json.loads(
        subprocess.run(
            ["uv", "run", "--with", "pip-audit", "pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    )
    entries = json.loads(ALLOWLIST.read_text())["entries"]
    allowed = {entry["advisory"]: entry for entry in entries}
    today = date.today()
    failures: list[str] = []

    for entry in entries:
        if date.fromisoformat(entry["expires"]) < today:
            failures.append(f"allowlist entry {entry['advisory']} expired on {entry['expires']}")

    found_ids: set[str] = set()
    seen: set[tuple[str, str, str]] = set()
    for dependency in report.get("dependencies", []):
        for vuln in dependency.get("vulns", []):
            vuln_id = vuln["id"]
            found_ids.add(vuln_id)
            key = (dependency["name"], dependency["version"], vuln_id)
            if key in seen:
                # pip-audit can report the same finding twice for one dependency (observed
                # with the OSV/PyPI lookup overlap) -- one failure line per unique finding.
                continue
            seen.add(key)
            if vuln_id not in allowed:
                failures.append(f"{dependency['name']} {dependency['version']}: {vuln_id}")

    if failures:
        print("pip-audit gate failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(
        "pip-audit gate passed"
        f" ({len(found_ids)} advisory(ies) found, all allowlisted and unexpired)."
        if found_ids
        else "pip-audit gate passed (no known vulnerabilities found)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
