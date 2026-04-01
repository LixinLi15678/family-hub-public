"""
Currency and Exchange Rate models
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Currency(Base):
    """Currency table - supported currencies"""
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)  # USD, CNY, HKD, CAD, JPY
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False)

    # Relationships
    expenses = relationship("Expense", back_populates="currency")
    incomes = relationship("Income", back_populates="currency")
    trips = relationship("Trip", back_populates="currency")
    trip_expenses = relationship("TripExpense", back_populates="currency")
    exchange_rates_from = relationship(
        "ExchangeRate", back_populates="from_currency", foreign_keys="ExchangeRate.from_currency_id"
    )
    exchange_rates_to = relationship(
        "ExchangeRate", back_populates="to_currency", foreign_keys="ExchangeRate.to_currency_id"
    )

    def __repr__(self) -> str:
        return f"<Currency(code='{self.code}', name='{self.name}')>"


class ExchangeRate(Base):
    """Exchange rate table"""
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("from_currency_id", "to_currency_id", name="uq_exchange_rate_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    to_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    from_currency = relationship("Currency", foreign_keys=[from_currency_id], back_populates="exchange_rates_from")
    to_currency = relationship("Currency", foreign_keys=[to_currency_id], back_populates="exchange_rates_to")

    def __repr__(self) -> str:
        return f"<ExchangeRate(from={self.from_currency_id}, to={self.to_currency_id}, rate={self.rate})>"


class ExchangeRateDaily(Base):
    """Daily exchange rate table (USD base)"""
    __tablename__ = "exchange_rate_daily"
    __table_args__ = (
        UniqueConstraint("rate_date", "from_currency_id", "to_currency_id", name="uq_exchange_rate_daily"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    to_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    from_currency = relationship("Currency", foreign_keys=[from_currency_id])
    to_currency = relationship("Currency", foreign_keys=[to_currency_id])

    def __repr__(self) -> str:
        return (
            f"<ExchangeRateDaily(date={self.rate_date}, from={self.from_currency_id}, "
            f"to={self.to_currency_id}, rate={self.rate})>"
        )
