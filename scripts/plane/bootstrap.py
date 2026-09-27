#!/usr/bin/env python3
"""
Idempotent bootstrap script for the JuriSense project in Plane.

Reads the configuration-as-code in project-management/plane/{project.md,states,labels,modules,
cycles}.yaml and the issue backlog in scripts/plane/issues_data.py, and creates/updates the
corresponding objects in Plane via its REST API. Safe to re-run: every step looks up existing
objects by name/title first and updates them instead of creating duplicates.

Prerequisites:
    pip install pyyaml

Required environment variables:
    PLANE_API_KEY            Plane API key (workspace or personal access token)
    PLANE_BASE_URL           e.g. http://localhost:80  (no trailing slash, no /api/v1 suffix)
    PLANE_WORKSPACE_SLUG     e.g. astreus-develop
    PLANE_PROJECT_IDENTIFIER e.g. JURI  (the short project identifier shown in Plane)

Usage:
    export PLANE_API_KEY=...
    export PLANE_BASE_URL=http://localhost:80
    export PLANE_WORKSPACE_SLUG=astreus-develop
    export PLANE_PROJECT_IDENTIFIER=JURI
    python3 scripts/plane/bootstrap.py

Never commit an API key. This script never prints the key and never writes it to a file.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANE_DIR = REPO_ROOT / "project-management" / "plane"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from issues_data import ISSUES  # noqa: E402


def env(name):
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


API_KEY = env("PLANE_API_KEY")
BASE_URL = env("PLANE_BASE_URL").rstrip("/")
WORKSPACE = env("PLANE_WORKSPACE_SLUG")
PROJECT_IDENTIFIER = env("PLANE_PROJECT_IDENTIFIER")
API = f"{BASE_URL}/api/v1"


REQUEST_DELAY_SECONDS = float(os.environ.get("PLANE_REQUEST_DELAY", "0.6"))


def request(method, path, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", API_KEY)
    req.add_header("Content-Type", "application/json")
    max_attempts = 6
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                time.sleep(REQUEST_DELAY_SECONDS)
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < max_attempts - 1:
                wait = min(2 ** (attempt + 1), 30)
                time.sleep(wait)
                continue
            raw = e.read()
            try:
                body_err = json.loads(raw)
            except Exception:
                body_err = raw.decode("utf-8", "replace")
            time.sleep(REQUEST_DELAY_SECONDS)
            return e.code, body_err
    return None, None


def list_all(path):
    """Follows Plane's cursor pagination for a GET list endpoint."""
    results, cursor = [], None
    while True:
        p = path + (f"&cursor={cursor}" if cursor and "?" in path else f"?cursor={cursor}" if cursor else "")
        status, body = request("GET", p)
        if status != 200:
            print(f"  ! failed to list {path}: {status} {body}", file=sys.stderr)
            break
        results.extend(body["results"])
        if not body.get("next_page_results"):
            break
        cursor = body["next_cursor"]
    return results


def get_project_id():
    projects = list_all(f"/workspaces/{WORKSPACE}/projects/")
    for p in projects:
        if p["identifier"] == PROJECT_IDENTIFIER:
            return p["id"]
    print(f"Project with identifier {PROJECT_IDENTIFIER} not found in workspace {WORKSPACE}.", file=sys.stderr)
    sys.exit(1)


def sync_project_description(project_id):
    print("== Project description ==")
    description = (PLANE_DIR / "project.md").read_text(encoding="utf-8")
    # Strip the leading "how to edit" preamble before the '---' separator; Plane stores plain text/HTML.
    body_text = description.split("---", 1)[-1].strip()
    html = "".join(f"<p>{line}</p>" for line in body_text.split("\n\n") if line.strip())
    status, _ = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/", {
        "name": "JuriSense",
        "description_html": html,
    })
    print(f"  project description: {'ok' if status in (200, 204) else f'FAILED ({status})'}")


def sync_states(project_id):
    print("== States ==")
    cfg = yaml.safe_load((PLANE_DIR / "states.yaml").read_text())["states"]
    existing = {s["name"]: s for s in list_all(f"/workspaces/{WORKSPACE}/projects/{project_id}/states/")}
    result = {}
    for s in cfg:
        target_name = s["name"]
        source = existing.get(target_name)
        if not source and s.get("rename_from"):
            source = existing.get(s["rename_from"])
        payload = {"name": target_name, "group": s["group"], "color": s["color"], "description": s.get("description", "")}
        if source:
            status, body = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/states/{source['id']}/", payload)
            action = "updated"
        else:
            status, body = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/states/", payload)
            action = "created"
        ok = status in (200, 201)
        print(f"  {target_name}: {action if ok else f'FAILED ({status})'}")
        if ok:
            result[target_name] = body["id"]
        elif source:
            result[target_name] = source["id"]
    return result


def sync_labels(project_id):
    print("== Labels ==")
    cfg = yaml.safe_load((PLANE_DIR / "labels.yaml").read_text())["labels"]
    existing = {l["name"]: l for l in list_all(f"/workspaces/{WORKSPACE}/projects/{project_id}/labels/")}
    result = {}
    created = updated = 0
    for l in cfg:
        payload = {"name": l["name"], "color": l["color"]}
        if l["name"] in existing:
            status, body = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/labels/{existing[l['name']]['id']}/", payload)
            updated += 1
            result[l["name"]] = existing[l["name"]]["id"]
        else:
            status, body = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/labels/", payload)
            if status == 201:
                created += 1
                result[l["name"]] = body["id"]
            else:
                print(f"  ! failed to create label {l['name']}: {status} {body}", file=sys.stderr)
    print(f"  {created} created, {updated} updated, {len(cfg)} total")
    return result


def sync_modules(project_id):
    print("== Modules ==")
    cfg = yaml.safe_load((PLANE_DIR / "modules.yaml").read_text())["modules"]
    existing = {m["name"]: m for m in list_all(f"/workspaces/{WORKSPACE}/projects/{project_id}/modules/")}
    result = {}
    created = updated = 0
    for m in cfg:
        payload = {"name": m["name"], "description": m["description"]}
        if m["name"] in existing:
            status, body = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/modules/{existing[m['name']]['id']}/", payload)
            updated += 1
            result[m["key"]] = existing[m["name"]]["id"]
        else:
            status, body = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/modules/", payload)
            if status == 201:
                created += 1
                result[m["key"]] = body["id"]
            else:
                print(f"  ! failed to create module {m['name']}: {status} {body}", file=sys.stderr)
    print(f"  {created} created, {updated} updated, {len(cfg)} total")
    return result


def sync_cycles(project_id):
    print("== Cycles ==")
    cfg = yaml.safe_load((PLANE_DIR / "cycles.yaml").read_text())["cycles"]
    existing = {c["name"]: c for c in list_all(f"/workspaces/{WORKSPACE}/projects/{project_id}/cycles/")}
    result = {}
    created = updated = 0
    for c in cfg:
        payload = {
            "name": c["name"], "description": c["description"],
            "start_date": c["start_date"], "end_date": c["end_date"],
        }
        if c["name"] in existing:
            status, body = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/cycles/{existing[c['name']]['id']}/", payload)
            updated += 1
            result[c["key"]] = existing[c["name"]]["id"]
        else:
            status, body = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/cycles/", payload)
            if status == 201:
                created += 1
                result[c["key"]] = body["id"]
            else:
                print(f"  ! failed to create cycle {c['name']}: {status} {body}", file=sys.stderr)
    print(f"  {created} created, {updated} updated, {len(cfg)} total")
    return result


def sync_issues(project_id, states, labels, modules, cycles):
    print("== Issues ==")
    existing = {i["name"]: i for i in list_all(f"/workspaces/{WORKSPACE}/projects/{project_id}/issues/")}
    key_to_id = {}
    module_links, cycle_links = {}, {}
    created = updated = 0

    for issue in ISSUES:
        title = issue["title"]
        payload = {
            "name": title,
            "description_html": issue["description"],
            "priority": issue["priority"],
            "state": states.get(issue["state"], states["Backlog"]),
            "labels": [labels[l] for l in issue["labels"] if l in labels],
        }
        parent_key = issue.get("parent")
        if parent_key:
            parent_id = key_to_id.get(parent_key)
            if parent_id:
                payload["parent"] = parent_id

        if title in existing:
            issue_id = existing[title]["id"]
            status, body = request("PATCH", f"/workspaces/{WORKSPACE}/projects/{project_id}/issues/{issue_id}/", payload)
            updated += 1
        else:
            status, body = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/issues/", payload)
            if status == 201:
                issue_id = body["id"]
                created += 1
            else:
                print(f"  ! failed to create issue '{title}': {status} {body}", file=sys.stderr)
                continue

        key_to_id[issue["key"]] = issue_id

        module_key = issue.get("module")
        if module_key and module_key in modules:
            module_links.setdefault(modules[module_key], []).append(issue_id)

        cycle_key = issue.get("cycle")
        if cycle_key and cycle_key in cycles:
            cycle_links.setdefault(cycles[cycle_key], []).append(issue_id)

    print(f"  {created} created, {updated} updated, {len(ISSUES)} total")

    print("== Module links ==")
    for module_id, issue_ids in module_links.items():
        status, _ = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/modules/{module_id}/module-issues/", {"issues": issue_ids})
        print(f"  module {module_id}: {len(issue_ids)} issues -> {'ok' if status == 200 else f'FAILED ({status})'}")

    print("== Cycle links ==")
    for cycle_id, issue_ids in cycle_links.items():
        status, _ = request("POST", f"/workspaces/{WORKSPACE}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/", {"issues": issue_ids})
        print(f"  cycle {cycle_id}: {len(issue_ids)} issues -> {'ok' if status == 200 else f'FAILED ({status})'}")

    return created, updated


def main():
    print(f"JuriSense Plane bootstrap -- workspace={WORKSPACE} project={PROJECT_IDENTIFIER}")
    project_id = get_project_id()
    print(f"Project id: {project_id}\n")

    sync_project_description(project_id)
    states = sync_states(project_id)
    labels = sync_labels(project_id)
    modules = sync_modules(project_id)
    cycles = sync_cycles(project_id)
    created, updated = sync_issues(project_id, states, labels, modules, cycles)

    print("\n== Summary ==")
    print(f"States: {len(states)} | Labels: {len(labels)} | Modules: {len(modules)} | Cycles: {len(cycles)}")
    print(f"Issues: {created} created, {updated} updated, {len(ISSUES)} total")


if __name__ == "__main__":
    main()
