"""
Trip and Budget models
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Trip(Base):
    """Trip table"""
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_budget: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency_id: Mapped[Optional[int]] = mapped_column(ForeignKey("currencies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='planned')  # planned/active/completed
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="trips")
    currency = relationship("Currency", back_populates="trips")
    created_by_user = relationship("User", back_populates="trips_created")
    budgets = relationship("TripBudget", back_populates="trip", cascade="all, delete-orphan")
    expenses = relationship("TripExpense", back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Trip(id={self.id}, name='{self.name}', destination='{self.destination}')>"


class TripBudget(Base):
    """Trip budget category table"""
    __tablename__ = "trip_budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 交通/住宿/餐饮/门票/购物/其他
    budget_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="budgets")
    expenses = relationship("TripExpense", back_populates="budget")

    def __repr__(self) -> str:
        return f"<TripBudget(id={self.id}, category='{self.category}', budget={self.budget_amount})>"


class TripExpense(Base):
    """Trip expense table"""
    __tablename__ = "trip_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    budget_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trip_budgets.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_id: Mapped[Optional[int]] = mapped_column(ForeignKey("currencies.id"), nullable=True)  # 可选，默认使用旅行的币种
    # Link to a split-only expense record used for AA settlement (expenses.splits).
    split_source_expense_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expense_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    trip = relationship("Trip", back_populates="expenses")
    budget = relationship("TripBudget", back_populates="expenses")
    user = relationship("User", back_populates="trip_expenses")
    currency = relationship("Currency", back_populates="trip_expenses")

    def __repr__(self) -> str:
        return f"<TripExpense(id={self.id}, trip_id={self.trip_id}, amount={self.amount})>"
