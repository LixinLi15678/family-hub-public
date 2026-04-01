"""
Currency and Exchange Rate schemas
"""
from datetime import datetime
from pydantic import BaseModel


class CurrencyResponse(BaseModel):
    """Schema for currency response"""
    id: int
    code: str
    name: str
    symbol: str

    class Config:
        from_attributes = True


class ExchangeRateResponse(BaseModel):
    """Schema for exchange rate response"""
    id: int
    from_currency_id: int
    to_currency_id: int
    from_currency_code: str
    to_currency_code: str
    rate: float
    updated_at: datetime

    class Config:
        from_attributes = True

