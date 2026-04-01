"""
User model
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property

from app.database import Base
from app.models.expense import ExpenseDiamondSpend
from app.models.chore import PointTransaction
from app.models.admin_tools import UserLevelAdjustment


class User(Base):
    """User table"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[Optional[int]] = mapped_column(ForeignKey("families.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    points_spent_total: Mapped[int] = column_property(
        (
            select(func.coalesce(func.sum(ExpenseDiamondSpend.diamonds), 0))
            .where(ExpenseDiamondSpend.user_id == id)
            .correlate_except(ExpenseDiamondSpend)
            .scalar_subquery()
            + select(func.coalesce(func.sum(-PointTransaction.amount), 0))
            .where(
                PointTransaction.user_id == id,
                PointTransaction.amount < 0,
                PointTransaction.type != "expire",
                PointTransaction.type != "admin_adjust",
            )
            .correlate_except(PointTransaction)
            .scalar_subquery()
            + select(func.coalesce(func.sum(UserLevelAdjustment.diamonds), 0))
            .where(UserLevelAdjustment.user_id == id)
            .correlate_except(UserLevelAdjustment)
            .scalar_subquery()
        )
    )
    # Stored as YYYY-MM-DD using client's local date when claiming the reward
    last_daily_login_reward_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin/member
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    family = relationship("Family", back_populates="members")
    expenses = relationship("Expense", back_populates="user", foreign_keys="Expense.user_id")
    expense_splits = relationship("ExpenseSplit", back_populates="user")
    incomes = relationship("Income", back_populates="user")
    shopping_items_added = relationship(
        "ShoppingItem", back_populates="added_by_user", foreign_keys="ShoppingItem.added_by"
    )
    shopping_items_checked = relationship(
        "ShoppingItem", back_populates="checked_by_user", foreign_keys="ShoppingItem.checked_by"
    )
    shopping_lists_created = relationship("ShoppingList", back_populates="created_by_user")
    chores_assigned = relationship(
        "Chore", back_populates="assigned_user", foreign_keys="Chore.assigned_to"
    )
    chores_created = relationship(
        "Chore", back_populates="created_by_user", foreign_keys="Chore.created_by"
    )
    chore_completions = relationship(
        "ChoreCompletion", back_populates="completed_by_user", foreign_keys="ChoreCompletion.completed_by"
    )
    chore_verifications = relationship(
        "ChoreCompletion", back_populates="verified_by_user", foreign_keys="ChoreCompletion.verified_by"
    )
    point_products_created = relationship("PointProduct", back_populates="created_by_user")
    purchases = relationship("Purchase", back_populates="user")
    point_transactions = relationship("PointTransaction", back_populates="user")
    level_adjustments = relationship(
        "UserLevelAdjustment",
        back_populates="user",
        foreign_keys="UserLevelAdjustment.user_id",
    )
    coupons = relationship(
        "UserCoupon",
        back_populates="user",
        foreign_keys="UserCoupon.user_id",
    )
    trips_created = relationship("Trip", back_populates="created_by_user")
    trip_expenses = relationship("TripExpense", back_populates="user")
    todos_assigned = relationship("Todo", back_populates="assigned_user", foreign_keys="Todo.assigned_to")
    todos_created = relationship("Todo", back_populates="created_by_user", foreign_keys="Todo.created_by")
    todos_completed = relationship("Todo", back_populates="completed_by_user", foreign_keys="Todo.completed_by")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
