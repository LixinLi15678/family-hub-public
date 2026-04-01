"""
Family model
"""
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Family(Base):
    """Family table - groups of users"""
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    members = relationship("User", back_populates="family")
    expense_categories = relationship("ExpenseCategory", back_populates="family")
    expenses = relationship("Expense", back_populates="family")
    incomes = relationship("Income", back_populates="family")
    stores = relationship("Store", back_populates="family")
    shopping_lists = relationship("ShoppingList", back_populates="family")
    chores = relationship("Chore", back_populates="family")
    point_products = relationship("PointProduct", back_populates="family")
    trips = relationship("Trip", back_populates="family")
    todos = relationship("Todo", back_populates="family")

    def __repr__(self) -> str:
        return f"<Family(id={self.id}, name='{self.name}')>"
