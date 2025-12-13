"""
Application configuration using environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sav_insight"
    
    # Gemini API
    GEMINI_API_KEY: Optional[str] = None
    
    # Upload settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # App settings
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

