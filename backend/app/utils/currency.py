"""
Currency and exchange rate utilities
"""
import math
import httpx
from typing import Dict, Optional
from datetime import date

from app.config import settings


async def fetch_exchange_rates(base_currency: str = "USD") -> Optional[Dict[str, float]]:
    """
    Fetch exchange rates from external API
    Returns a dict of currency code -> rate relative to base currency
    """
    try:
        url = settings.EXCHANGE_RATE_API_URL
        if "{base}" in url:
            url = url.format(base=base_currency)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("rates", {}) or data.get("conversion_rates", {})
    except Exception as e:
        print(f"Error fetching exchange rates: {e}")
        return None


async def fetch_exchange_rates_for_date(
    rate_date: date,
    base_currency: str = "USD"
) -> Optional[Dict[str, float]]:
    """
    Fetch historical exchange rates for a specific date.
    Returns a dict of currency code -> rate relative to base currency.
    """
    try:
        url = settings.EXCHANGE_RATE_HISTORICAL_API_URL
        if "{date}" in url or "{base}" in url:
            url = url.format(date=rate_date.isoformat(), base=base_currency)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("rates", {}) or data.get("conversion_rates", {})
    except Exception as e:
        print(f"Error fetching historical exchange rates: {e}")
        return None


def convert_amount(
    amount: float,
    from_rate: float,
    to_rate: float
) -> float:
    """
    Convert amount between currencies using their rates relative to USD
    """
    # Be defensive: bad exchange-rate rows (0/NaN/inf) should not crash writes.
    if not (isinstance(from_rate, (int, float)) and math.isfinite(from_rate) and from_rate > 0):
        from_rate = 1.0
    if not (isinstance(to_rate, (int, float)) and math.isfinite(to_rate) and to_rate > 0):
        to_rate = 1.0

    # Convert to USD first, then to target currency
    usd_amount = amount / from_rate
    return usd_amount * to_rate


# Default exchange rates (used as fallback)
DEFAULT_RATES = {
    "USD": 1.0,
    "CNY": 7.2,
    "HKD": 7.8,
    "CAD": 1.35,
    "JPY": 149.0,
}


def get_default_rates() -> Dict[str, float]:
    """Get default exchange rates"""
    return DEFAULT_RATES.copy()
