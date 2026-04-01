"""
Chore and Points system models
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Chore(Base):
    """Chore task table"""
    __tablename__ = "chores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    recurrence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # daily/weekly/monthly/once
    repeat_days: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)  # [0-6] for Sun-Sat when weekly
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="chores")
    assigned_user = relationship("User", back_populates="chores_assigned", foreign_keys=[assigned_to])
    created_by_user = relationship("User", back_populates="chores_created", foreign_keys=[created_by])
    completions = relationship("ChoreCompletion", back_populates="chore", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Chore(id={self.id}, name='{self.name}', points={self.points_reward})>"


class ChoreCompletion(Base):
    """Chore completion record table"""
    __tablename__ = "chore_completions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chore_id: Mapped[int] = mapped_column(ForeignKey("chores.id"), nullable=False)
    completed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    chore = relationship("Chore", back_populates="completions")
    completed_by_user = relationship("User", back_populates="chore_completions", foreign_keys=[completed_by])
    verified_by_user = relationship("User", back_populates="chore_verifications", foreign_keys=[verified_by])

    def __repr__(self) -> str:
        return f"<ChoreCompletion(id={self.id}, chore_id={self.chore_id}, points={self.points_earned})>"


class PointProduct(Base):
    """Point shop product table"""
    __tablename__ = "point_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    points_price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL means unlimited
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="point_products")
    created_by_user = relationship("User", back_populates="point_products_created")
    purchases = relationship("Purchase", back_populates="product")

    def __repr__(self) -> str:
        return f"<PointProduct(id={self.id}, name='{self.name}', price={self.points_price})>"


class Purchase(Base):
    """Purchase record table"""
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("point_products.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="owned")  # owned/used
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    product = relationship("PointProduct", back_populates="purchases")
    user = relationship("User", back_populates="purchases")

    def __repr__(self) -> str:
        return f"<Purchase(id={self.id}, product_id={self.product_id}, points={self.points_spent})>"


class PointTransaction(Base):
    """Point transaction record table"""
    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Positive for earning, negative for spending
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # chore/purchase/bonus/expire
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID of chore_completion or purchase
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="point_transactions")

    def __repr__(self) -> str:
        return f"<PointTransaction(id={self.id}, user_id={self.user_id}, amount={self.amount})>"

