from datetime import date
import re


LOCAL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_local_date(local_date: str) -> str:
    """
    Normalize and validate a client-provided local date.

    Ensures the value is in YYYY-MM-DD format and represents a real calendar date.
    Returns the canonical ISO string (YYYY-MM-DD).
    """
    local_date = local_date.strip()
    if not LOCAL_DATE_RE.match(local_date):
        raise ValueError("Invalid local_date format, expected YYYY-MM-DD")

    try:
        return date.fromisoformat(local_date).isoformat()
    except ValueError:
        raise ValueError(
            "Invalid local_date value, expected a real calendar date in YYYY-MM-DD"
        )
