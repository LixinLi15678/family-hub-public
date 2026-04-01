#!/usr/bin/env python3
"""
大额开销结余池数据一致性检查工具

用途：验证结余池计算的正确性，确保数据一致
运行：python scripts/check_big_expense_consistency.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine, Base
from app.models.expense import Income, Expense
from app.models.family import Family


async def check_consistency():
    """检查所有家庭的大额开销结余池数据一致性"""
    async with AsyncSession(engine) as session:
        # 获取所有家庭
        families_result = await session.execute(select(Family))
        families = families_result.scalars().all()

        print("=" * 80)
        print("大额开销结余池数据一致性检查")
        print("=" * 80)
        print()

        total_families = len(families)
        inconsistent_families = []

        for idx, family in enumerate(families, 1):
            print(f"[{idx}/{total_families}] 检查家庭: {family.name} (ID: {family.id})")

            # 计算累计预留
            total_reserved_result = await session.execute(
                select(func.coalesce(func.sum(Income.big_expense_reserved), 0))
                .where(Income.family_id == family.id)
            )
            total_reserved = float(total_reserved_result.scalar() or 0)

            # 计算累计大额开销支出
            total_spent_result = await session.execute(
                select(func.coalesce(func.sum(Expense.amount), 0))
                .where(
                    Expense.family_id == family.id,
                    Expense.is_big_expense == True
                )
            )
            total_spent = float(total_spent_result.scalar() or 0)

            # 计算实际结余
            actual_balance = total_reserved - total_spent

            print(f"  ✓ 累计预留: {total_reserved:,.2f}")
            print(f"  ✓ 累计支出: {total_spent:,.2f}")
            print(f"  ✓ 实际结余: {actual_balance:,.2f}")

            # 检查是否透支
            if actual_balance < 0:
                print(f"  ⚠️  警告: 结余池透支 {abs(actual_balance):,.2f}")
                inconsistent_families.append({
                    'family': family,
                    'balance': actual_balance,
                    'reason': '透支'
                })

            # 验证各月度预留总和
            incomes_result = await session.execute(
                select(Income).where(Income.family_id == family.id)
            )
            incomes = incomes_result.scalars().all()

            sum_check = sum(float(inc.big_expense_reserved or 0) for inc in incomes)
            if abs(sum_check - total_reserved) > 0.01:
                print(f"  ❌ 错误: 预留金额不一致!")
                print(f"     数据库聚合: {total_reserved:,.2f}")
                print(f"     逐条求和: {sum_check:,.2f}")
                print(f"     差异: {abs(sum_check - total_reserved):,.2f}")
                inconsistent_families.append({
                    'family': family,
                    'balance': actual_balance,
                    'reason': '预留金额计算不一致'
                })

            print()

        # 总结报告
        print("=" * 80)
        print("检查完成")
        print("=" * 80)
        print(f"总家庭数: {total_families}")
        print(f"正常家庭: {total_families - len(inconsistent_families)}")
        print(f"异常家庭: {len(inconsistent_families)}")

        if inconsistent_families:
            print("\n异常详情:")
            for item in inconsistent_families:
                print(f"  - {item['family'].name} (ID: {item['family'].id})")
                print(f"    结余: {item['balance']:,.2f}")
                print(f"    原因: {item['reason']}")

            return 1  # Exit code 1 for failures
        else:
            print("\n✅ 所有家庭数据一致性检查通过!")
            return 0  # Exit code 0 for success


async def fix_inconsistencies():
    """修复数据不一致（预留功能）"""
    print("修复功能尚未实现，请手动检查和修复")
    # TODO: 实现自动修复逻辑
    pass


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="大额开销结余池数据一致性检查工具"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='自动修复数据不一致（谨慎使用）'
    )

    args = parser.parse_args()

    if args.fix:
        await fix_inconsistencies()
    else:
        exit_code = await check_consistency()
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
