"""
Todo model
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Todo(Base):
    """Family todo item"""
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    family = relationship("Family", back_populates="todos")
    assigned_user = relationship("User", back_populates="todos_assigned", foreign_keys=[assigned_to])
    created_by_user = relationship("User", back_populates="todos_created", foreign_keys=[created_by])
    completed_by_user = relationship("User", back_populates="todos_completed", foreign_keys=[completed_by])

    def __repr__(self) -> str:
        return f"<Todo(id={self.id}, title='{self.title}', completed={self.is_completed})>"
