from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load .env file from the backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


class Settings(BaseModel):
    app_name: str = "SaaPOS API"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./saapos.db"
    )
    upload_dir: str = "uploads"
    frontend_origin: str = "http://localhost:3000"
    
    # Beem Africa SMS Credentials (placeholder, set via env vars or update here)
    beem_api_key: str = ""
    beem_secret_key: str = ""
    beem_sender_id: str = "DUKA-SALES"

settings = Settings()
