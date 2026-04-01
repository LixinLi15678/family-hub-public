"""
Data export routes
"""
import csv
import io
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, extract
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.expense import Expense, Income, ExpenseCategory
from app.utils.security import get_current_user

router = APIRouter(prefix="/export", tags=["Export"])


def generate_csv(headers: list, rows: list) -> io.StringIO:
    """Generate CSV content from headers and rows"""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return output


@router.get("/expenses")
async def export_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    format: str = Query("csv", pattern="^(csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export expense records to CSV.
    
    Parameters:
    - start_date: Filter expenses from this date
    - end_date: Filter expenses until this date
    - category_id: Filter by specific category
    - format: Export format (currently only CSV supported)
    """
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Build query
    query = (
        select(Expense)
        .options(selectinload(Expense.category), selectinload(Expense.user))
        .where(Expense.family_id == current_user.family_id)
    )
    
    if start_date:
        query = query.where(Expense.expense_date >= start_date)
    if end_date:
        query = query.where(Expense.expense_date <= end_date)
    if category_id:
        query = query.where(Expense.category_id == category_id)
    
    query = query.order_by(Expense.expense_date.desc())
    
    result = await db.execute(query)
    expenses = result.scalars().all()
    
    # Prepare CSV data
    headers = ["日期", "分类", "金额", "描述", "记录人", "创建时间"]
    rows = []
    
    for expense in expenses:
        rows.append([
            str(expense.expense_date),
            expense.category.name if expense.category else "未分类",
            float(expense.amount),
            expense.description or "",
            expense.user.username if expense.user else "",
            expense.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    # Generate CSV
    csv_content = generate_csv(headers, rows)
    
    # Return as downloadable file
    filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([csv_content.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/incomes")
async def export_incomes(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    format: str = Query("csv", pattern="^(csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export income records to CSV.
    
    Parameters:
    - start_date: Filter incomes from this date
    - end_date: Filter incomes until this date
    - format: Export format (currently only CSV supported)
    """
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Build query
    query = (
        select(Income)
        .options(selectinload(Income.user))
        .where(Income.family_id == current_user.family_id)
    )
    
    if start_date:
        query = query.where(Income.income_date >= start_date)
    if end_date:
        query = query.where(Income.income_date <= end_date)
    
    query = query.order_by(Income.income_date.desc())
    
    result = await db.execute(query)
    incomes = result.scalars().all()
    
    # Prepare CSV data
    headers = ["日期", "金额", "来源", "描述", "记录人", "创建时间"]
    rows = []
    
    for income in incomes:
        rows.append([
            str(income.income_date),
            float(income.amount),
            income.source or "",
            income.description or "",
            income.user.username if income.user else "",
            income.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    # Generate CSV
    csv_content = generate_csv(headers, rows)
    
    # Return as downloadable file
    filename = f"incomes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([csv_content.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/monthly-report")
async def export_monthly_report(
    year: int,
    month: int,
    format: str = Query("csv", pattern="^(csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export monthly financial report to CSV.
    
    Includes:
    - Summary (total income, expense, balance)
    - Expense breakdown by category
    - Income breakdown by source
    - Daily totals
    """
    if not current_user.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are not in a family")
    
    # Get expenses for the month
    expense_query = (
        select(Expense)
        .options(selectinload(Expense.category))
        .where(
            Expense.family_id == current_user.family_id,
            extract('year', Expense.expense_date) == year,
            extract('month', Expense.expense_date) == month
        )
    )
    expense_result = await db.execute(expense_query)
    expenses = expense_result.scalars().all()
    
    # Get incomes for the month
    income_query = (
        select(Income)
        .where(
            Income.family_id == current_user.family_id,
            extract('year', Income.income_date) == year,
            extract('month', Income.income_date) == month
        )
    )
    income_result = await db.execute(income_query)
    incomes = income_result.scalars().all()
    
    # Calculate totals
    total_expense = sum(float(e.amount) for e in expenses)
    total_income = sum(float(i.amount) for i in incomes)
    balance = total_income - total_expense
    
    # Group expenses by category
    expense_by_category = {}
    for expense in expenses:
        cat_name = expense.category.name if expense.category else "未分类"
        expense_by_category[cat_name] = expense_by_category.get(cat_name, 0) + float(expense.amount)
    
    # Group incomes by source
    income_by_source = {}
    for income in incomes:
        source = income.source or "其他"
        income_by_source[source] = income_by_source.get(source, 0) + float(income.amount)
    
    # Build CSV content
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    # Summary section
    writer.writerow([f"月度财务报告 - {year}年{month}月"])
    writer.writerow([])
    writer.writerow(["== 总览 =="])
    writer.writerow(["项目", "金额"])
    writer.writerow(["总收入", total_income])
    writer.writerow(["总支出", total_expense])
    writer.writerow(["结余", balance])
    writer.writerow([])
    
    # Expense by category
    writer.writerow(["== 支出分类 =="])
    writer.writerow(["分类", "金额", "占比"])
    for cat_name, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_expense * 100) if total_expense > 0 else 0
        writer.writerow([cat_name, amount, f"{percentage:.1f}%"])
    writer.writerow([])
    
    # Income by source
    writer.writerow(["== 收入来源 =="])
    writer.writerow(["来源", "金额", "占比"])
    for source, amount in sorted(income_by_source.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        writer.writerow([source, amount, f"{percentage:.1f}%"])
    
    output.seek(0)
    
    # Return as downloadable file
    filename = f"monthly_report_{year}{month:02d}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

