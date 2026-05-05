#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, Company

def reset_amazooh():
    db = SessionLocal()
    try:
        # Delete existing Amazooh company
        company = db.query(Company).filter(Company.name == 'Amazooh Electronics Ltd').first()
        if company:
            # Delete users first
            db.query(User).filter(User.company_id == company.id).delete()
            # Delete company
            db.delete(company)
            db.commit()
            print('✅ Deleted existing Amazooh company')
        else:
            print('ℹ️ No existing Amazooh company found')
    except Exception as e:
        print(f'❌ Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_amazooh()
