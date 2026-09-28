"""Domain validation rules shared across the Identity & Organizations use cases."""

from datetime import UTC, datetime


def as_utc(dt: datetime) -> datetime:
    """Normalizes datetimes coming from the DB (SQLite returns naive) to UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def is_expired(expires_at: datetime) -> bool:
    return datetime.now(UTC) > as_utc(expires_at)
