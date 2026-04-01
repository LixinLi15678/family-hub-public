import pytest

from app.validators import normalize_local_date


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2025-01-01", "2025-01-01"),
        (" 2025-12-31 ", "2025-12-31"),
        ("2024-02-29", "2024-02-29"),
    ],
)
def test_normalize_local_date_accepts_valid_calendar_dates(value: str, expected: str) -> None:
    assert normalize_local_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2025-1-01",
        "2025-01-1",
        "2025/01/01",
        "not-a-date",
    ],
)
def test_normalize_local_date_rejects_invalid_format(value: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_local_date(value)
    assert "format" in str(exc_info.value).lower()


@pytest.mark.parametrize(
    "value",
    [
        "2025-00-01",
        "2025-13-01",
        "2025-01-00",
        "2025-01-32",
        "2025-02-29",
        "2025-04-31",
    ],
)
def test_normalize_local_date_rejects_invalid_calendar_dates(value: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        normalize_local_date(value)
    assert "value" in str(exc_info.value).lower()
