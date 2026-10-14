"""Sanctions check adapter (ADR-017) — the other leg of `SupplierVerificationPort`.

Never makes a live network call per check: it queries the locally indexed
`sanctions_entries` table (`SanctionsRepository`), populated on a schedule by
`refresh_sanctions_index` (`infrastructure/tasks.py`) from the real CEIS/CNEP/CEPIM bulk
extracts (`sanctions_source.py`). If a list has never been refreshed in an environment,
or has gone stale (older than `Settings.sanctions_max_age_seconds` -- security audit,
2026-10-12), this reports `status="unavailable"` — sanctions is a mandatory source
(`docs/03-domain/supplier-compliance.md` step 3), so an empty, never-refreshed, or stale
index must never be reported as "checked, no hits", which would silently look like a
clean supplier.
"""

from datetime import UTC, date, datetime

from app.core.config import get_settings
from app.integrations.domain.constants import SanctionsList
from app.integrations.domain.ports import SourceResult
from app.integrations.infrastructure.sanctions_repository import SanctionsRepository


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).strip().upper()


class SanctionsAdapter:
    """Checks a supplier's `tax_id` and its known responsible-party names against every
    locally indexed sanctions list.

    Responsible-party matching is name-based, not CPF-based: BrasilAPI (and the Receita
    Federal source data it mirrors) masks partner CPFs for LGPD reasons (e.g.
    `***550179**`), so exact-CPF cross-referencing against sanctions lists is not
    possible from this data source — a documented precision limitation (ADR-017), not a
    silent gap.
    """

    def __init__(self, repository: SanctionsRepository) -> None:
        self._repository = repository

    async def check(self, *, tax_id: str, responsible_party_names: list[str]) -> SourceResult:
        lists = list(SanctionsList)
        availability = {lst: await self._repository.has_data(list_name=lst.value) for lst in lists}
        unavailable_lists = [lst.value for lst, available in availability.items() if not available]

        if unavailable_lists:
            return SourceResult(
                source="sanctions",
                status="unavailable",
                data={
                    "reason": "sanctions index not yet refreshed for: "
                    + ", ".join(unavailable_lists),
                    "lists_checked": [],
                },
            )

        # Security audit (2026-10-12): `has_data` alone only proves a list was refreshed
        # at SOME point, not recently -- `refresh_sanctions_index` previously had no
        # scheduled cadence at all (`celery_app.beat_schedule`), so a once-populated
        # index could silently go stale for weeks/months while still reporting "ok".
        # Treated the same as "unavailable" (never as a clean "no hits") -- sanctions is
        # a mandatory source (`docs/03-domain/supplier-compliance.md` step 3), and a
        # stale check is not a verified one.
        max_age = get_settings().sanctions_max_age_seconds
        now = datetime.now(UTC).date()
        stale_lists: list[str] = []
        for lst in lists:
            extract_date = await self._repository.get_latest_extract_date(list_name=lst.value)
            if extract_date is None:
                continue  # already covered by `unavailable_lists` above
            age_days = (now - date.fromisoformat(extract_date)).days
            if age_days * 86_400 > max_age:
                stale_lists.append(lst.value)

        if stale_lists:
            return SourceResult(
                source="sanctions",
                status="unavailable",
                data={
                    "reason": "sanctions index is stale (older than "
                    f"{max_age // 86_400} days) for: " + ", ".join(stale_lists),
                    "lists_checked": [],
                },
            )

        hits: list[dict] = []
        document = _digits_only(tax_id)
        by_document = await self._repository.find_by_document(document)
        for entry in by_document:
            hits.append(
                {
                    "list_name": entry.list_name,
                    "matched_entity": entry.name_normalized,
                    "matched_on": "tax_id",
                    "extract_date": entry.extract_date,
                    "raw": entry.raw,
                }
            )

        for name in responsible_party_names:
            normalized = _normalize_name(name)
            if not normalized:
                continue
            for entry in await self._repository.find_by_name(normalized):
                hits.append(
                    {
                        "list_name": entry.list_name,
                        "matched_entity": entry.name_normalized,
                        "matched_on": "responsible_party",
                        "matched_party": name,
                        "extract_date": entry.extract_date,
                        "raw": entry.raw,
                    }
                )

        return SourceResult(
            source="sanctions",
            status="ok",
            data={"lists_checked": [lst.value for lst in lists], "hits": hits},
        )
