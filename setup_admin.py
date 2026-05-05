import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password

def setup_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if super admin already exists
        email = "amali@gmail.com"
        password = "amali123"
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Creating super admin: {email}...")
            new_user = User(
                id=str(uuid4()),
                email=email,
                name="Super Admin",
                password_hash=hash_password(password),
                role="super_admin",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_user)
            db.commit()
            print("Super admin created successfully!")
        else:
            print("Super admin already exists, updating password...")
            user.password_hash = hash_password(password)
            user.role = "super_admin"
            db.commit()
            print("Super admin updated successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
