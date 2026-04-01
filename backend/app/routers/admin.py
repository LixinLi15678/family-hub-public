"""
Admin routes for system management
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.expense import Income, Expense
from app.models.chore import PointTransaction
from app.models.admin_tools import UserLevelAdjustment, UserCoupon
from app.schemas.common import SuccessResponse
from app.schemas.admin import (
    AdminCouponResponse,
    AdminMemberResponse,
    AdminOperationLogResponse,
    AdminMemberCenterResponse,
    AdminSetBalanceRequest,
    AdminSetBalanceResponse,
    AdminSetExperienceRequest,
    AdminSetExperienceResponse,
    AdminCreateCouponRequest,
    AdminDeleteCouponResponse,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


LEVEL_EFFECT_TIERS = [
    {"min_level": 1, "max_level": 14, "label": "基础特效", "description": "粒子 + 祝贺卡片"},
    {"min_level": 15, "max_level": 34, "label": "进阶特效", "description": "基础 + 光束环形脉冲"},
    {"min_level": 35, "max_level": 59, "label": "华丽特效", "description": "进阶 + 极光背景"},
    {"min_level": 60, "max_level": 75, "label": "传奇特效", "description": "华丽 + 流星层"},
]


def ensure_family_admin(current_user: User):
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您不在任何家庭中"
        )
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作"
        )


async def get_family_member(
    db: AsyncSession,
    family_id: int,
    user_id: int,
) -> User:
    member = await db.scalar(
        select(User).where(
            User.id == user_id,
            User.family_id == family_id,
        )
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="家庭成员不存在"
        )
    return member


def to_coupon_response(coupon: UserCoupon) -> AdminCouponResponse:
    return AdminCouponResponse.model_validate(coupon)


async def check_family_consistency(
    db: AsyncSession,
    family_id: int
) -> dict:
    """检查单个家庭的大额开销数据一致性"""
    # 累计预留
    total_reserved = float(await db.scalar(
        select(func.coalesce(func.sum(Income.big_expense_reserved), 0))
        .where(Income.family_id == family_id)
    ) or 0)

    # 累计支出
    total_spent = float(await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.family_id == family_id,
            Expense.is_big_expense == True
        )
    ) or 0)

    # 实际结余
    actual_balance = total_reserved - total_spent

    # 验证逐条求和
    incomes_result = await db.execute(
        select(Income).where(Income.family_id == family_id)
    )
    incomes = incomes_result.scalars().all()
    sum_check = sum(float(inc.big_expense_reserved or 0) for inc in incomes)

    is_consistent = abs(sum_check - total_reserved) < 0.01
    is_overdrawn = actual_balance < 0

    return {
        "family_id": family_id,
        "total_reserved": total_reserved,
        "total_spent": total_spent,
        "actual_balance": actual_balance,
        "is_overdrawn": is_overdrawn,
        "is_consistent": is_consistent,
        "sum_check": sum_check,
        "discrepancy": abs(sum_check - total_reserved) if not is_consistent else 0
    }


@router.get("/big-expense/check-consistency", response_model=SuccessResponse[dict])
async def check_big_expense_consistency(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    检查当前用户家庭的大额开销数据一致性

    返回：
    - total_reserved: 累计预留金额
    - total_spent: 累计大额开销支出
    - actual_balance: 实际结余
    - is_overdrawn: 是否透支
    - is_consistent: 数据是否一致
    """
    ensure_family_admin(current_user)

    result = await check_family_consistency(db, current_user.family_id)

    status_msg = "数据一致"
    if not result["is_consistent"]:
        status_msg = f"数据不一致，差异 {result['discrepancy']:.2f}"
    elif result["is_overdrawn"]:
        status_msg = f"结余池透支 {abs(result['actual_balance']):.2f}"

    return SuccessResponse(
        data=result,
        message=status_msg
    )


@router.get("/big-expense/summary", response_model=SuccessResponse[dict])
async def get_big_expense_admin_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取大额开销管理摘要（管理员视图）

    包含：
    - 结余池状态
    - 收入明细
    - 支出明细
    - 数据一致性检查
    """
    ensure_family_admin(current_user)

    # 一致性检查
    consistency = await check_family_consistency(db, current_user.family_id)

    # 收入明细（最近10条）
    incomes_result = await db.execute(
        select(Income)
        .where(Income.family_id == current_user.family_id)
        .order_by(Income.income_date.desc())
        .limit(10)
    )
    recent_incomes = incomes_result.scalars().all()

    # 大额支出明细（最近10条）
    expenses_result = await db.execute(
        select(Expense)
        .where(
            Expense.family_id == current_user.family_id,
            Expense.is_big_expense == True
        )
        .order_by(Expense.expense_date.desc())
        .limit(10)
    )
    recent_expenses = expenses_result.scalars().all()

    return SuccessResponse(
        data={
            "consistency": consistency,
            "recent_incomes": [
                {
                    "id": inc.id,
                    "amount": float(inc.amount),
                    "big_expense_reserved": float(inc.big_expense_reserved),
                    "reserve_mode": inc.reserve_mode,
                    "reserve_value": float(inc.reserve_value) if inc.reserve_value else None,
                    "income_date": inc.income_date.isoformat(),
                    "source": inc.source
                }
                for inc in recent_incomes
            ],
            "recent_big_expenses": [
                {
                    "id": exp.id,
                    "amount": float(exp.amount),
                    "category_id": exp.category_id,
                    "expense_date": exp.expense_date.isoformat(),
                    "description": exp.description
                }
                for exp in recent_expenses
            ]
        },
        message="获取成功"
    )


@router.get("/member-center", response_model=SuccessResponse[AdminMemberCenterResponse])
async def get_member_center(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin member center:
    - member list with points/experience
    - coupon inventories
    - recent admin operations
    - level effect tier references
    """
    ensure_family_admin(current_user)
    family_id = int(current_user.family_id)

    users_result = await db.execute(
        select(User)
        .where(User.family_id == family_id)
        .order_by(User.role.desc(), User.created_at.asc())
    )
    members = users_result.scalars().all()

    coupons_result = await db.execute(
        select(UserCoupon)
        .where(UserCoupon.family_id == family_id)
        .order_by(UserCoupon.updated_at.desc())
    )
    coupons = coupons_result.scalars().all()
    coupons_by_user: dict[int, list[AdminCouponResponse]] = {}
    for coupon in coupons:
        coupons_by_user.setdefault(int(coupon.user_id), []).append(to_coupon_response(coupon))

    exp_ops_result = await db.execute(
        select(UserLevelAdjustment)
        .where(UserLevelAdjustment.family_id == family_id)
        .order_by(UserLevelAdjustment.created_at.desc())
        .limit(40)
    )
    exp_ops = exp_ops_result.scalars().all()

    balance_ops_result = await db.execute(
        select(PointTransaction)
        .join(User, User.id == PointTransaction.user_id)
        .where(
            User.family_id == family_id,
            PointTransaction.type == "admin_adjust",
        )
        .order_by(PointTransaction.created_at.desc())
        .limit(40)
    )
    balance_ops = balance_ops_result.scalars().all()

    name_map = {int(m.id): m.username for m in members}
    spent_map = {int(m.id): int(m.points_spent_total or 0) for m in members}
    recent_operations: list[AdminOperationLogResponse] = []

    for op in exp_ops:
        recent_operations.append(
            AdminOperationLogResponse(
                id=f"exp-{op.id}",
                op_type="experience",
                user_id=int(op.user_id),
                username=name_map.get(int(op.user_id), f"用户#{op.user_id}"),
                delta=int(op.diamonds),
                target=spent_map.get(int(op.user_id), 0),
                reason=op.reason,
                created_at=op.created_at,
            )
        )

    for op in balance_ops:
        recent_operations.append(
            AdminOperationLogResponse(
                id=f"bal-{op.id}",
                op_type="balance",
                user_id=int(op.user_id),
                username=name_map.get(int(op.user_id), f"用户#{op.user_id}"),
                delta=int(op.amount),
                target=int(op.balance_after),
                reason=op.description,
                created_at=op.created_at,
            )
        )

    recent_operations.sort(key=lambda x: x.created_at, reverse=True)
    recent_operations = recent_operations[:40]

    response_members = [
        AdminMemberResponse(
            user_id=int(member.id),
            username=member.username,
            email=member.email,
            avatar_url=member.avatar_url,
            role=member.role,
            points_balance=int(member.points_balance or 0),
            points_spent_total=int(member.points_spent_total or 0),
            coupons=coupons_by_user.get(int(member.id), []),
        )
        for member in members
    ]

    return SuccessResponse(
        data=AdminMemberCenterResponse(
            members=response_members,
            recent_operations=recent_operations,
            level_effect_tiers=LEVEL_EFFECT_TIERS,
        ),
        message="获取成功",
    )


@router.post("/members/{user_id}/balance", response_model=SuccessResponse[AdminSetBalanceResponse])
async def set_member_balance(
    user_id: int,
    payload: AdminSetBalanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set target diamond balance for a family member."""
    ensure_family_admin(current_user)
    family_id = int(current_user.family_id)
    member = await get_family_member(db, family_id, user_id)

    previous = int(member.points_balance or 0)
    target = int(payload.target_balance)
    delta = target - previous

    if delta != 0:
        member.points_balance = target
        op = PointTransaction(
            user_id=member.id,
            amount=delta,
            type="admin_adjust",
            balance_after=target,
            description=payload.reason or f"管理员调整钻石余额为 {target}",
            reference_id=None,
        )
        db.add(op)
        await db.flush()

    return SuccessResponse(
        data=AdminSetBalanceResponse(
            user_id=member.id,
            previous_balance=previous,
            target_balance=target,
            delta=delta,
        ),
        message="钻石余额已更新",
    )


@router.post("/members/{user_id}/experience", response_model=SuccessResponse[AdminSetExperienceResponse])
async def set_member_experience(
    user_id: int,
    payload: AdminSetExperienceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set target spent-diamonds total (experience basis) for a family member."""
    ensure_family_admin(current_user)
    family_id = int(current_user.family_id)
    member = await get_family_member(db, family_id, user_id)

    previous = int(member.points_spent_total or 0)
    target = int(payload.target_spent_total)
    delta = target - previous

    if delta != 0:
        adj = UserLevelAdjustment(
            family_id=family_id,
            user_id=member.id,
            diamonds=delta,
            reason=payload.reason or f"管理员调整等级经验为 {target}",
            created_by=current_user.id,
        )
        db.add(adj)
        await db.flush()

    # Re-query to return latest computed spent total
    refreshed = await get_family_member(db, family_id, user_id)
    latest_total = int(refreshed.points_spent_total or 0)

    return SuccessResponse(
        data=AdminSetExperienceResponse(
            user_id=refreshed.id,
            previous_spent_total=previous,
            target_spent_total=latest_total,
            delta=delta,
        ),
        message="等级经验已更新",
    )


@router.post("/members/{user_id}/coupons", response_model=SuccessResponse[AdminCouponResponse])
async def add_member_coupon(
    user_id: int,
    payload: AdminCreateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add (or increase) a coupon for a family member."""
    ensure_family_admin(current_user)
    family_id = int(current_user.family_id)
    member = await get_family_member(db, family_id, user_id)

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="券名称不能为空")

    existing = await db.scalar(
        select(UserCoupon).where(
            UserCoupon.family_id == family_id,
            UserCoupon.user_id == member.id,
            UserCoupon.name == name,
        )
    )

    if existing:
        existing.quantity = int(existing.quantity) + int(payload.quantity)
        if payload.description is not None:
            existing.description = payload.description
        if payload.expires_on is not None:
            existing.expires_on = payload.expires_on
        await db.flush()
        coupon = existing
    else:
        coupon = UserCoupon(
            family_id=family_id,
            user_id=member.id,
            name=name,
            description=payload.description,
            quantity=int(payload.quantity),
            expires_on=payload.expires_on,
            created_by=current_user.id,
        )
        db.add(coupon)
        await db.flush()
        await db.refresh(coupon)

    return SuccessResponse(
        data=to_coupon_response(coupon),
        message="券已添加",
    )


@router.delete("/members/{user_id}/coupons/{coupon_id}", response_model=SuccessResponse[AdminDeleteCouponResponse])
async def delete_member_coupon(
    user_id: int,
    coupon_id: int,
    quantity: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete coupon or reduce coupon quantity for a family member."""
    ensure_family_admin(current_user)
    family_id = int(current_user.family_id)
    member = await get_family_member(db, family_id, user_id)

    coupon = await db.scalar(
        select(UserCoupon).where(
            UserCoupon.id == coupon_id,
            UserCoupon.family_id == family_id,
            UserCoupon.user_id == member.id,
        )
    )
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="券不存在")

    deleted = False
    remaining = int(coupon.quantity)
    if quantity >= remaining:
        await db.delete(coupon)
        deleted = True
        remaining = 0
    else:
        remaining = remaining - quantity
        coupon.quantity = remaining
        await db.flush()

    return SuccessResponse(
        data=AdminDeleteCouponResponse(
            deleted=deleted,
            remaining_quantity=remaining,
        ),
        message="券已更新",
    )
