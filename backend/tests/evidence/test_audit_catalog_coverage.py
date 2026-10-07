"""FEATURE-7.2 / STORY-7.2.1: the event catalog in `docs/03-domain/audit.md` and the code agree.

Every documented event must be emitted by `app/` and named by a test under `tests/`, or be
listed in `PLANNED_NOT_YET_EMITTED` with the reason it is not emitted yet, and its catalog section
must say "not yet emitted". Emitted types are read from the AST of every `emit_audit_event(...)`
call, so a conditional like `"a" if cond else "b"` is seen as both events, and a non-literal
`event_type` fails the test.

Not checked here: that an emission shares the transaction of the change it records. The atomicity
tests cover that for the events where it matters.
"""

import ast
import re
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
APP_DIR = BACKEND / "app"
TESTS_DIR = BACKEND / "tests"
THIS_FILE = Path(__file__).resolve()
CATALOG = BACKEND.parent / "docs" / "03-domain" / "audit.md"

# Reviewed list. Every entry is documented in audit.md as "not yet emitted" and names the
# missing feature. Remove an entry (and add an emission test) when its feature lands.
PLANNED_NOT_YET_EMITTED: dict[str, str] = {
    "approval_workflow.updated": (
        "no route edits ApprovalWorkflow routing; workflows are only seeded at "
        "organization registration"
    ),
    "supplier.updated": (
        "no route edits core supplier attributes; PATCH /suppliers/{id}/status emits "
        "supplier.status_changed and POST /suppliers/{id}/recheck emits its own check events"
    ),
    "integration.disconnected": (
        "no disconnect or credential-revocation route exists; Integrations is a "
        "configuration seam until EPIC-9"
    ),
}

_CATALOG_HEADING = re.compile(r"^\*\*`([a-z_]+(?:\.[a-z_]+)+)`\*\*", re.MULTILINE)


def _documented_events() -> set[str]:
    names = _CATALOG_HEADING.findall(CATALOG.read_text(encoding="utf-8"))
    assert len(names) == len(set(names)), "a catalog heading is duplicated in audit.md"
    assert len(names) >= 30, f"catalog parse found only {len(names)} headings; regex broken?"
    return set(names)


_NEXT_HEADING = re.compile(r"^#{1,3} ", re.MULTILINE)


def _catalog_sections() -> dict[str, str]:
    """Maps each documented event to its own catalog section: from its heading to the next
    event heading or section heading, whichever comes first."""
    text = CATALOG.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for match in _CATALOG_HEADING.finditer(text):
        end_candidates = [len(text)]
        if next_event := _CATALOG_HEADING.search(text, match.end()):
            end_candidates.append(next_event.start())
        if next_heading := _NEXT_HEADING.search(text, match.end()):
            end_candidates.append(next_heading.start())
        sections[match.group(1)] = text[match.start() : min(end_candidates)]
    return sections


def _literal_event_types(node: ast.expr, where: str) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _literal_event_types(node.body, where) + _literal_event_types(node.orelse, where)
    raise AssertionError(
        f"{where}: event_type must be a string literal or a conditional of literals, "
        f"got `{ast.unparse(node)}`"
    )


def _emitted_events() -> dict[str, list[str]]:
    emitted: dict[str, list[str]] = defaultdict(list)
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", None)
            if name != "emit_audit_event":
                continue
            where = f"{path.relative_to(BACKEND)}:{node.lineno}"
            keywords = [kw for kw in node.keywords if kw.arg == "event_type"]
            assert keywords, f"{where}: emit_audit_event called without event_type=..."
            for event_type in _literal_event_types(keywords[0].value, where):
                emitted[event_type].append(where)
    return emitted


def _tested_events(documented: set[str]) -> set[str]:
    """An event counts as tested when a test module under tests/ names it as a quoted literal.
    This proves a test is wired to the event, not that the test performs the emission; the
    emission tests themselves assert the stored row (organization, actor, payload)."""
    tested: set[str] = set()
    for path in TESTS_DIR.rglob("*.py"):
        if "__pycache__" in path.parts or path.resolve() == THIS_FILE:
            continue
        text = path.read_text(encoding="utf-8")
        tested.update(event for event in documented if f'"{event}"' in text)
    return tested


def test_every_documented_event_is_emitted_or_explicitly_planned() -> None:
    documented = _documented_events()
    emitted = _emitted_events()

    neither = sorted(
        event
        for event in documented
        if event not in emitted and event not in PLANNED_NOT_YET_EMITTED
    )
    assert not neither, (
        f"documented in audit.md but neither emitted in app/ nor listed in "
        f"PLANNED_NOT_YET_EMITTED: {neither}"
    )


def test_every_emitted_event_is_documented() -> None:
    undocumented = sorted(set(_emitted_events()) - _documented_events())
    assert not undocumented, f"emitted in app/ but missing from audit.md: {undocumented}"


def test_every_emitted_event_has_an_emission_test() -> None:
    documented = _documented_events()
    emitted = set(_emitted_events())
    tested = _tested_events(documented)

    untested = sorted((documented & emitted) - tested)
    assert not untested, f"emitted events with no test under tests/ naming them: {untested}"


def test_planned_events_are_documented_unemitted_and_have_reasons() -> None:
    documented = _documented_events()
    emitted = _emitted_events()

    stale = sorted(event for event in PLANNED_NOT_YET_EMITTED if event not in documented)
    assert not stale, f"PLANNED_NOT_YET_EMITTED names undocumented events: {stale}"

    now_emitted = sorted(event for event in PLANNED_NOT_YET_EMITTED if event in emitted)
    assert not now_emitted, (
        f"now emitted, so remove from PLANNED_NOT_YET_EMITTED and add an emission test: "
        f"{now_emitted}"
    )

    reasonless = sorted(
        event for event, reason in PLANNED_NOT_YET_EMITTED.items() if not reason.strip()
    )
    assert not reasonless, f"PLANNED_NOT_YET_EMITTED entries without a reason: {reasonless}"


def test_planned_events_say_not_yet_emitted_in_their_catalog_section() -> None:
    sections = _catalog_sections()

    unmarked = sorted(
        event
        for event in PLANNED_NOT_YET_EMITTED
        if "not yet emitted" not in sections.get(event, "")
    )
    assert not unmarked, f"catalog sections missing the 'not yet emitted' status: {unmarked}"


def test_emit_calls_use_literal_event_types() -> None:
    _emitted_events()  # raises with the offending file:line if any call is non-literal
