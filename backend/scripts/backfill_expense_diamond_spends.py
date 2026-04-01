#!/usr/bin/env python3
"""
历史记账“消费钻石”回填脚本（用于等级进度）

用途：
- 为过去所有支出（expenses）生成 expense_diamond_spends 记录
- 规则与线上一致：
  - split_only==False 才计入
  - 有 splits 则按 split 成员分摊（不是付款人）
  - 无 splits 则算到付款人
  - 金额先换算到人民币(CNY)，钻石=round(CNY*10)

运行：
  python scripts/backfill_expense_diamond_spends.py --help
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.currency import Currency, ExchangeRate
from app.models.expense import Expense, ExpenseSplit, ExpenseDiamondSpend
from app.utils.currency import convert_amount, get_default_rates


async def load_usd_rates(session: AsyncSession) -> Tuple[Dict[int, float], Dict[int, str], int | None, int | None]:
    """Load USD->currency rates and currency metadata."""
    currency_rows = (await session.execute(select(Currency.id, Currency.code))).all()
    currency_id_to_code = {int(r[0]): str(r[1]) for r in currency_rows}
    usd_id = next((cid for cid, code in currency_id_to_code.items() if code == "USD"), None)
    cny_id = next((cid for cid, code in currency_id_to_code.items() if code == "CNY"), None)

    rates_by_currency_id: Dict[int, float] = {}
    if usd_id is not None:
        rate_rows = (
            await session.execute(
                select(ExchangeRate.to_currency_id, ExchangeRate.rate).where(
                    ExchangeRate.from_currency_id == usd_id
                )
            )
        ).all()
        rates_by_currency_id = {int(r[0]): float(r[1]) for r in rate_rows}

    return rates_by_currency_id, currency_id_to_code, usd_id, cny_id


def resolve_rate(
    currency_id: int,
    currency_id_to_code: Dict[int, str],
    rates_by_currency_id: Dict[int, float],
    usd_id: int | None,
    defaults: Dict[str, float],
) -> float:
    if usd_id is not None and currency_id == usd_id:
        return 1.0
    if currency_id in rates_by_currency_id:
        return float(rates_by_currency_id[currency_id])
    code = currency_id_to_code.get(currency_id)
    return float(defaults.get(code or "USD", 1.0))


async def backfill(
    family_id: int | None,
    batch_size: int,
    start_id: int,
    dry_run: bool,
    reset_all: bool,
) -> int:
    defaults = get_default_rates()
    started_at = datetime.utcnow()

    async with AsyncSession(engine) as session:
        if reset_all and not dry_run:
            await session.execute(delete(ExpenseDiamondSpend))
            await session.commit()

        rates_by_currency_id, currency_id_to_code, usd_id, cny_id = await load_usd_rates(session)
        cny_rate = resolve_rate(int(cny_id or 0), currency_id_to_code, rates_by_currency_id, usd_id, defaults) if cny_id else float(defaults.get("CNY", 7.2))

        filters = [Expense.split_only == False]  # noqa: E712
        if family_id is not None:
            filters.append(Expense.family_id == family_id)
        if start_id:
            filters.append(Expense.id >= start_id)

        total = int(
            (
                await session.execute(
                    select(func.count()).select_from(select(Expense.id).where(*filters).subquery())
                )
            ).scalar()
            or 0
        )

        print("=" * 80)
        print("历史记账“消费钻石”回填")
        print("=" * 80)
        print(f"family_id={family_id or 'ALL'} batch_size={batch_size} start_id={start_id} dry_run={dry_run} reset_all={reset_all}")
        print(f"预计处理支出条数: {total}")
        print()

        processed_expenses = 0
        inserted_rows = 0
        last_id = start_id - 1 if start_id else 0

        while True:
            expense_rows = (
                await session.execute(
                    select(
                        Expense.id,
                        Expense.user_id,
                        Expense.amount,
                        Expense.currency_id,
                    )
                    .where(*filters, Expense.id > last_id)
                    .order_by(Expense.id.asc())
                    .limit(batch_size)
                )
            ).all()

            if not expense_rows:
                break

            expenses = [
                {
                    "id": int(r[0]),
                    "user_id": int(r[1]),
                    "amount": float(r[2]),
                    "currency_id": int(r[3]),
                }
                for r in expense_rows
            ]
            expense_ids = [e["id"] for e in expenses]
            last_id = expense_ids[-1]

            split_rows = (
                await session.execute(
                    select(ExpenseSplit.expense_id, ExpenseSplit.user_id, ExpenseSplit.share_amount).where(
                        ExpenseSplit.expense_id.in_(expense_ids)
                    )
                )
            ).all()

            splits_by_expense: Dict[int, List[Tuple[int, float]]] = {}
            for expense_id, user_id, share_amount in split_rows:
                splits_by_expense.setdefault(int(expense_id), []).append((int(user_id), float(share_amount)))

            now = datetime.utcnow()
            values = []
            for exp in expenses:
                from_rate = resolve_rate(exp["currency_id"], currency_id_to_code, rates_by_currency_id, usd_id, defaults)
                allocations = splits_by_expense.get(exp["id"])
                if allocations:
                    pairs = allocations
                else:
                    pairs = [(exp["user_id"], float(exp["amount"]))]

                for uid, original_amount in pairs:
                    cny_amount = convert_amount(float(original_amount), float(from_rate), float(cny_rate))
                    diamonds = max(0, int(round(float(cny_amount) * 10)))
                    values.append(
                        {
                            "expense_id": exp["id"],
                            "user_id": uid,
                            "original_amount": round(float(original_amount), 2),
                            "original_currency_id": exp["currency_id"],
                            "amount_cny": round(float(cny_amount), 2),
                            "diamonds": diamonds,
                            "created_at": now,
                        }
                    )

            processed_expenses += len(expenses)

            if not dry_run:
                await session.execute(
                    delete(ExpenseDiamondSpend).where(ExpenseDiamondSpend.expense_id.in_(expense_ids))
                )
                if values:
                    await session.execute(insert(ExpenseDiamondSpend).values(values))
                    inserted_rows += len(values)
                await session.commit()

            if processed_expenses % (batch_size * 5) == 0 or processed_expenses == total:
                elapsed = (datetime.utcnow() - started_at).total_seconds()
                rate = processed_expenses / elapsed if elapsed > 0 else 0
                print(f"进度: {processed_expenses}/{total} expenses, 已生成 {inserted_rows} rows, {rate:.1f} expenses/s")

        elapsed = (datetime.utcnow() - started_at).total_seconds()
        print()
        print("=" * 80)
        print("完成")
        print("=" * 80)
        print(f"处理支出: {processed_expenses}")
        print(f"写入记录: {inserted_rows}{' (dry-run未写入)' if dry_run else ''}")
        print(f"耗时: {elapsed:.1f}s")
        return 0


async def main():
    parser = argparse.ArgumentParser(description="历史记账“消费钻石”回填脚本（用于等级）")
    parser.add_argument("--family-id", type=int, default=None, help="仅回填指定家庭ID（可选）")
    parser.add_argument("--batch-size", type=int, default=500, help="每批处理支出条数（默认 500）")
    parser.add_argument("--start-id", type=int, default=0, help="从指定 expense_id 开始（默认 0）")
    parser.add_argument("--dry-run", action="store_true", help="只计算不写入数据库")
    parser.add_argument("--reset-all", action="store_true", help="先清空 expense_diamond_spends 再回填")

    args = parser.parse_args()
    return await backfill(
        family_id=args.family_id,
        batch_size=max(1, args.batch_size),
        start_id=max(0, args.start_id),
        dry_run=bool(args.dry_run),
        reset_all=bool(args.reset_all),
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

