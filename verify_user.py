from app.database import SessionLocal
from app.models import User
from app.security import verify_password

db = SessionLocal()
email = "amali@gmail.com"
password = "amali123"

user = db.query(User).filter(User.email == email).first()
if user:
    print(f"User found: {user.email}")
    print(f"Role: {user.role}")
    print(f"Active: {user.is_active}")
    is_valid = verify_password(password, user.password_hash)
    print(f"Password valid: {is_valid}")
else:
    print("User NOT found")

db.close()
