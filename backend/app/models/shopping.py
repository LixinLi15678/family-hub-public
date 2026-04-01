"""
Shopping list models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Store(Base):
    """Store table - stores for shopping items"""
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    family = relationship("Family", back_populates="stores")
    shopping_items = relationship("ShoppingItem", back_populates="store")

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name='{self.name}')>"


class ShoppingList(Base):
    """Shopping list table"""
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="shopping_lists")
    created_by_user = relationship("User", back_populates="shopping_lists_created")
    items = relationship("ShoppingItem", back_populates="list", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ShoppingList(id={self.id}, name='{self.name}')>"


class ShoppingItem(Base):
    """Shopping item table"""
    __tablename__ = "shopping_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"), nullable=False)
    store_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stores.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)  # Optimistic locking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    list = relationship("ShoppingList", back_populates="items")
    store = relationship("Store", back_populates="shopping_items")
    added_by_user = relationship("User", back_populates="shopping_items_added", foreign_keys=[added_by])
    checked_by_user = relationship("User", back_populates="shopping_items_checked", foreign_keys=[checked_by])

    def __repr__(self) -> str:
        return f"<ShoppingItem(id={self.id}, name='{self.name}', checked={self.is_checked})>"

