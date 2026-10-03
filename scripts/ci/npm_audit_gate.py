"""Fails the frontend CI job on any high/critical npm advisory that is not explicitly
allowlisted, and fails when an allowlisted entry has expired. The allowlist is
scripts/ci/npm-audit-allowlist.json; every entry names its advisory, its reason, and an
expiry date so a temporary exception cannot silently become permanent."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ALLOWLIST = Path(__file__).with_name("npm-audit-allowlist.json")
BLOCKING = {"high", "critical"}


def advisory_ids(vulnerability: dict) -> list[str]:
    return [
        via["url"].rsplit("/", 1)[-1]
        for via in vulnerability.get("via", [])
        if isinstance(via, dict) and "url" in via
    ]


def main() -> int:
    report = json.loads(
        subprocess.run(
            ["npm", "audit", "--json"], capture_output=True, text=True, check=False
        ).stdout
    )
    entries = json.loads(ALLOWLIST.read_text())["entries"]
    allowed = {entry["advisory"]: entry for entry in entries}
    today = date.today()
    failures: list[str] = []

    for entry in entries:
        if date.fromisoformat(entry["expires"]) < today:
            failures.append(f"allowlist entry {entry['advisory']} expired on {entry['expires']}")

    for name, vulnerability in report.get("vulnerabilities", {}).items():
        if vulnerability.get("severity") not in BLOCKING:
            continue
        ids = advisory_ids(vulnerability)
        if not ids:
            # Transitive dependant of a vulnerable package: its risk is reported by the root
            # package that carries the advisory, so it is not counted twice.
            continue
        unexcused = [advisory for advisory in ids if advisory not in allowed]
        if unexcused:
            failures.append(f"{name} ({vulnerability['severity']}): {unexcused}")

    if failures:
        print("npm audit gate failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("npm audit gate passed (high/critical advisories are all allowlisted and unexpired).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
