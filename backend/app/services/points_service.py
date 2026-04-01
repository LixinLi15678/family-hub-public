"""
Points system service
"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.chore import PointTransaction, ChoreCompletion
from app.config import settings


class PointsService:
    """Points system business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def add_points(
        self,
        user: User,
        amount: int,
        transaction_type: str,
        reference_id: int | None = None,
        description: str | None = None
    ) -> PointTransaction:
        """Add points to a user"""
        user.points_balance += amount
        
        transaction = PointTransaction(
            user_id=user.id,
            amount=amount,
            type=transaction_type,
            reference_id=reference_id,
            balance_after=user.points_balance,
            description=description
        )
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def deduct_points(
        self,
        user: User,
        amount: int,
        transaction_type: str,
        reference_id: int | None = None,
        description: str | None = None
    ) -> PointTransaction | None:
        """Deduct points from a user"""
        if user.points_balance < amount:
            return None
        
        user.points_balance -= amount
        
        transaction = PointTransaction(
            user_id=user.id,
            amount=-amount,
            type=transaction_type,
            reference_id=reference_id,
            balance_after=user.points_balance,
            description=description
        )
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def expire_old_points(self, user: User) -> int:
        """Expire points older than configured expiry days"""
        expiry_date = datetime.utcnow() - timedelta(days=settings.POINTS_EXPIRY_DAYS)
        
        # Get points earned from chores before expiry date that haven't been used
        result = await self.db.execute(
            select(PointTransaction)
            .where(
                and_(
                    PointTransaction.user_id == user.id,
                    PointTransaction.type == "chore",
                    PointTransaction.amount > 0,
                    PointTransaction.created_at < expiry_date
                )
            )
        )
        old_transactions = result.scalars().all()
        
        # Calculate total expired points (simplified - would need more complex logic in production)
        total_expired = sum(t.amount for t in old_transactions)
        
        if total_expired > 0 and user.points_balance >= total_expired:
            await self.deduct_points(
                user=user,
                amount=total_expired,
                transaction_type="expire",
                description=f"钻石过期（超过{settings.POINTS_EXPIRY_DAYS}天）"
            )
        
        return total_expired
    
    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> list[PointTransaction]:
        """Get user's point transactions"""
        result = await self.db.execute(
            select(PointTransaction)
            .where(PointTransaction.user_id == user_id)
            .order_by(PointTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_points_earned_today(self, user_id: int) -> int:
        """Get points earned today"""
        today = datetime.utcnow().date()
        
        result = await self.db.execute(
            select(PointTransaction)
            .where(
                and_(
                    PointTransaction.user_id == user_id,
                    PointTransaction.amount > 0,
                    PointTransaction.created_at >= datetime.combine(today, datetime.min.time())
                )
            )
        )
        transactions = result.scalars().all()
        return sum(t.amount for t in transactions)
