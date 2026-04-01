"""
Expense, Income, and Category models
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExpenseCategory(Base):
    """Expense category table - three-level classification"""
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # fixed/supplementary/optional
    is_big_expense: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否大额开销类目
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("expense_categories.id"), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    family = relationship("Family", back_populates="expense_categories")
    parent = relationship("ExpenseCategory", remote_side="ExpenseCategory.id", backref="children")
    expenses = relationship("Expense", back_populates="category")

    def __repr__(self) -> str:
        return f"<ExpenseCategory(id={self.id}, name='{self.name}', type='{self.type}')>"


class Expense(Base):
    """Expense record table"""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("expense_categories.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # For split-only allocation: derived per-user expenses point back to the source split-only expense
    allocation_source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    allocation_payer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_big_expense: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否大额开销支出
    split_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 仅用于分摊结算，不计入统计
    version: Mapped[int] = mapped_column(Integer, default=1)  # Optimistic locking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    family = relationship("Family", back_populates="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")
    user = relationship("User", back_populates="expenses", foreign_keys=[user_id])
    currency = relationship("Currency", back_populates="expenses")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.amount}, date={self.expense_date})>"


class ExpenseSplit(Base):
    """Expense split table - for splitting costs among users"""
    __tablename__ = "expense_splits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    share_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    share_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    expense = relationship("Expense", back_populates="splits")
    user = relationship("User", back_populates="expense_splits")

    def __repr__(self) -> str:
        return f"<ExpenseSplit(id={self.id}, user_id={self.user_id}, amount={self.share_amount})>"


class ExpenseDiamondSpend(Base):
    """Diamond spend derived from ledger expenses (used for level progression)"""
    __tablename__ = "expense_diamond_spends"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_diamond_spend"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    original_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    amount_cny: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    diamonds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    expense = relationship("Expense", foreign_keys=[expense_id])
    user = relationship("User", foreign_keys=[user_id])
    currency = relationship("Currency", foreign_keys=[original_currency_id])

    def __repr__(self) -> str:
        return f"<ExpenseDiamondSpend(expense_id={self.expense_id}, user_id={self.user_id}, diamonds={self.diamonds})>"


class Income(Base):
    """Income record table"""
    __tablename__ = "incomes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Salary source, etc.
    income_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    big_expense_reserved: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 本次收入划入的大额开销预留
    reserve_mode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # percent/fixed/none
    reserve_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # 百分比或固定值
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="incomes")
    user = relationship("User", back_populates="incomes")
    currency = relationship("Currency", back_populates="incomes")

    def __repr__(self) -> str:
        return f"<Income(id={self.id}, amount={self.amount}, date={self.income_date})>"
