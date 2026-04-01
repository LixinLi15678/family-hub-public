"""
Scheduled tasks using APScheduler
"""
from datetime import datetime, timedelta, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.currency import Currency, ExchangeRate
from app.models.chore import Chore, PointTransaction
from app.models.trip import Trip
from app.models.user import User
from app.utils.currency import fetch_exchange_rates, get_default_rates

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def update_exchange_rates():
    """Update exchange rates from external API"""
    print(f"[{datetime.utcnow()}] Running exchange rate update job...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Fetch latest rates
            rates = await fetch_exchange_rates("USD")
            
            if not rates:
                print("Failed to fetch rates, using defaults")
                rates = get_default_rates()
            
            # Get all currencies
            result = await db.execute(select(Currency))
            currencies = {c.code: c.id for c in result.scalars().all()}
            
            usd_id = currencies.get("USD")
            if not usd_id:
                print("USD currency not found")
                return
            
            updated_count = 0
            for code, rate in rates.items():
                if code not in currencies or code == "USD":
                    continue
                
                to_id = currencies[code]
                
                # Check if rate exists
                result = await db.execute(
                    select(ExchangeRate).where(
                        ExchangeRate.from_currency_id == usd_id,
                        ExchangeRate.to_currency_id == to_id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.rate = rate
                else:
                    new_rate = ExchangeRate(
                        from_currency_id=usd_id,
                        to_currency_id=to_id,
                        rate=rate
                    )
                    db.add(new_rate)
                
                updated_count += 1
            
            await db.commit()
            print(f"Updated {updated_count} exchange rates")
            
        except Exception as e:
            print(f"Error updating exchange rates: {e}")
            await db.rollback()


async def expire_points():
    """Expire old points (90 days)"""
    print(f"[{datetime.utcnow()}] Running points expiration job...")
    
    async with AsyncSessionLocal() as db:
        try:
            expiry_date = datetime.utcnow() - timedelta(days=settings.POINTS_EXPIRY_DAYS)
            
            # Get all users with points
            result = await db.execute(
                select(User).where(User.points_balance > 0)
            )
            users = result.scalars().all()
            
            total_expired = 0
            for user in users:
                # Find old point transactions (simplified logic)
                result = await db.execute(
                    select(PointTransaction).where(
                        PointTransaction.user_id == user.id,
                        PointTransaction.type == "chore",
                        PointTransaction.amount > 0,
                        PointTransaction.created_at < expiry_date
                    )
                )
                old_transactions = result.scalars().all()
                
                if old_transactions:
                    # In production, would need more sophisticated tracking
                    print(f"User {user.id} has {len(old_transactions)} old transactions")
            
            await db.commit()
            print(f"Points expiration check completed")
            
        except Exception as e:
            print(f"Error expiring points: {e}")
            await db.rollback()


async def generate_recurring_chores():
    """
    Generate recurring chore tasks.
    
    Supports:
    - daily: Reset every day
    - weekly: Reset on specified days (repeat_days) or Monday by default
    - monthly: Reset on the 1st of each month
    """
    print(f"[{datetime.utcnow()}] Running recurring chores job...")
    
    async with AsyncSessionLocal() as db:
        try:
            today = datetime.utcnow().date()
            # weekday(): Monday=0, Sunday=6
            # But repeat_days uses: Sunday=0, Saturday=6 (JS convention)
            # Convert: Python weekday to JS weekday
            js_weekday = (today.weekday() + 1) % 7
            
            # Get all active recurring chores
            result = await db.execute(
                select(Chore).where(
                    Chore.is_active == True,
                    Chore.recurrence.in_(["daily", "weekly", "monthly"])
                )
            )
            recurring_chores = result.scalars().all()
            
            for chore in recurring_chores:
                should_reset = False
                
                if chore.recurrence == "daily":
                    # Reset daily tasks
                    should_reset = True
                elif chore.recurrence == "weekly":
                    # Check if today matches repeat_days
                    if chore.repeat_days and isinstance(chore.repeat_days, list):
                        # repeat_days: [0-6] for Sunday-Saturday
                        should_reset = js_weekday in chore.repeat_days
                    else:
                        # Default: Monday (1 in JS weekday)
                        should_reset = js_weekday == 1
                elif chore.recurrence == "monthly" and today.day == 1:
                    # Reset monthly tasks on the 1st
                    should_reset = True
                
                if should_reset:
                    # Update due date for recurring chores
                    if chore.recurrence == "daily":
                        chore.due_date = today + timedelta(days=1)
                    elif chore.recurrence == "weekly":
                        # Find next occurrence
                        if chore.repeat_days and isinstance(chore.repeat_days, list) and chore.repeat_days:
                            # Find next day in repeat_days
                            next_day = None
                            for days_ahead in range(1, 8):
                                future_js_weekday = (js_weekday + days_ahead) % 7
                                if future_js_weekday in chore.repeat_days:
                                    next_day = today + timedelta(days=days_ahead)
                                    break
                            chore.due_date = next_day or today + timedelta(weeks=1)
                        else:
                            chore.due_date = today + timedelta(weeks=1)
                    elif chore.recurrence == "monthly":
                        # Next month same day (simplified)
                        if today.month == 12:
                            chore.due_date = today.replace(year=today.year + 1, month=1)
                        else:
                            chore.due_date = today.replace(month=today.month + 1)
            
            await db.commit()
            print(f"Processed {len(recurring_chores)} recurring chores")
            
        except Exception as e:
            print(f"Error generating recurring chores: {e}")
            await db.rollback()


async def backup_database():
    """
    Backup database using pg_dump.
    
    Creates a timestamped SQL backup file in the /backups directory.
    Keeps the last 7 daily backups.
    """
    import asyncio
    import os
    import glob
    
    print(f"[{datetime.utcnow()}] Running database backup job...")
    
    # Configuration
    backup_dir = os.environ.get("BACKUP_DIR", "/app/backups")
    db_host = os.environ.get("DB_HOST", "db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "family_hub")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres_dev")
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"family_hub_{timestamp}.sql")
    
    try:
        # Set PGPASSWORD environment variable for pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        # Run pg_dump
        process = await asyncio.create_subprocess_exec(
            "pg_dump",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-f", backup_file,
            "--format=plain",
            "--no-owner",
            "--no-privileges",
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # Get file size
            file_size = os.path.getsize(backup_file)
            print(f"Database backup completed: {backup_file} ({file_size} bytes)")
            
            # Clean up old backups (keep last 7)
            backup_files = sorted(glob.glob(os.path.join(backup_dir, "family_hub_*.sql")))
            if len(backup_files) > 7:
                for old_file in backup_files[:-7]:
                    os.remove(old_file)
                    print(f"Removed old backup: {old_file}")
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            print(f"Database backup failed: {error_msg}")
            
    except FileNotFoundError:
        print("pg_dump not found. Skipping database backup.")
        print("Install PostgreSQL client tools to enable backups.")
    except Exception as e:
        print(f"Error during database backup: {e}")


async def update_trip_statuses():
    """
    自动更新旅行状态
    
    状态转换规则:
    - planned: 开始日期在未来
    - active: 开始日期 <= 今天 <= 结束日期
    - completed: 结束日期已过
    """
    print(f"[{datetime.utcnow()}] Running trip status update job...")
    
    async with AsyncSessionLocal() as db:
        try:
            today = date.today()
            
            # 更新为进行中 (planned -> active)
            # 条件: 状态为planned，开始日期已到，结束日期未过
            active_result = await db.execute(
                update(Trip)
                .where(
                    Trip.status == 'planned',
                    Trip.start_date <= today,
                    Trip.end_date >= today
                )
                .values(status='active')
            )
            active_count = active_result.rowcount
            
            # 更新为已完成 (planned/active -> completed)
            # 条件: 状态为planned或active，结束日期已过
            completed_result = await db.execute(
                update(Trip)
                .where(
                    Trip.status.in_(['planned', 'active']),
                    Trip.end_date < today
                )
                .values(status='completed')
            )
            completed_count = completed_result.rowcount
            
            await db.commit()
            print(f"Trip status update: {active_count} -> active, {completed_count} -> completed")
            
        except Exception as e:
            print(f"Error updating trip statuses: {e}")
            await db.rollback()


def start_scheduler():
    """Start the scheduler with all jobs"""
    # Exchange rate update - every 6 hours
    scheduler.add_job(
        update_exchange_rates,
        trigger=IntervalTrigger(hours=6),
        id="update_exchange_rates",
        name="Update Exchange Rates",
        replace_existing=True
    )
    
    # Points expiration - daily at midnight
    scheduler.add_job(
        expire_points,
        trigger=CronTrigger(hour=0, minute=0),
        id="expire_points",
        name="Expire Old Points",
        replace_existing=True
    )
    
    # Generate recurring chores - daily at midnight
    scheduler.add_job(
        generate_recurring_chores,
        trigger=CronTrigger(hour=0, minute=5),
        id="generate_recurring_chores",
        name="Generate Recurring Chores",
        replace_existing=True
    )
    
    # Database backup - daily at 3am
    scheduler.add_job(
        backup_database,
        trigger=CronTrigger(hour=3, minute=0),
        id="backup_database",
        name="Database Backup",
        replace_existing=True
    )
    
    # Trip status update - daily at 0:10
    scheduler.add_job(
        update_trip_statuses,
        trigger=CronTrigger(hour=0, minute=10),
        id="update_trip_statuses",
        name="Update Trip Statuses",
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started with jobs: exchange rates, points expiry, recurring chores, backup, trip status")


def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("Scheduler shut down")

