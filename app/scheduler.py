import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Company, Transaction
from .sms import BeemSMSService

logger = logging.getLogger(__name__)

async def send_nightly_reports():
    """
    Job that runs every night at 21:00 to send daily Z-Reports to all company owners.
    """
    logger.info("Starting nightly Z-Report job...")
    db: Session = SessionLocal()
    try:
        companies = db.query(Company).filter(Company.is_active == True).all()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for company in companies:
            if not company.phone:
                continue
                
            # Get today's transactions
            sales = db.query(Transaction).filter(
                Transaction.company_id == company.id,
                Transaction.type == "sale",
                Transaction.created_at >= today
            ).all()
            
            if not sales:
                continue # Skip if no sales today
                
            total_sales = sum(s.total for s in sales)
            txn_count = len(sales)
            
            message = (
                f"📊 DUKA-SALES Ripoti ya Leo:\n"
                f"Duka: {company.name}\n"
                f"Mauzo: Tsh {total_sales:,.0f}\n"
                f"Miamala: {txn_count}\n"
                f"Asante kwa kutumia DUKA-SALES!"
            )
            
            try:
                await BeemSMSService.send_sms(dest_addr=company.phone, message=message)
                logger.info(f"Successfully sent nightly report to {company.name} ({company.phone})")
            except Exception as e:
                logger.error(f"Failed to send nightly report to {company.name}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in nightly report job: {str(e)}")
    finally:
        db.close()

def setup_scheduler():
    scheduler = AsyncIOScheduler()
    # Schedule to run every day at 21:00 (9:00 PM)
    scheduler.add_job(send_nightly_reports, 'cron', hour=21, minute=0)
    return scheduler
