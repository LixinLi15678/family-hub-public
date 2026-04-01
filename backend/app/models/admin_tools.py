"""
Admin tools related models
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserLevelAdjustment(Base):
    """Manual level experience adjustment for a user (in diamonds)."""
    __tablename__ = "user_level_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    diamonds: Mapped[int] = mapped_column(Integer, nullable=False)  # signed delta
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="level_adjustments")
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<UserLevelAdjustment(user_id={self.user_id}, diamonds={self.diamonds})>"


class UserCoupon(Base):
    """Coupon inventory owned by a user and managed by family admin."""
    __tablename__ = "user_coupons"
    __table_args__ = (
        UniqueConstraint("family_id", "user_id", "name", name="uq_user_coupon_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expires_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="coupons")
    created_by_user = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<UserCoupon(user_id={self.user_id}, name='{self.name}', quantity={self.quantity})>"
