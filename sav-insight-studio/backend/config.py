"""
Application configuration using environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sav_insight"
    
    # Gemini API (legacy)
    GEMINI_API_KEY: Optional[str] = None
    
    # OpenAI API (for Twin Transformer)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-5-mini"
    OPENAI_REASONING_EFFORT: str = "minimal"
    
    # Upload settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # App settings
    DEBUG: bool = True
    
    # ==========================================================================
    # SECURITY SETTINGS
    # ==========================================================================
    
    # JWT Configuration
    JWT_SECRET: str = "dev-secret-change-in-production-min-32-chars!"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 168  # 7 days
    
    # CSRF Configuration
    CSRF_SECRET: str = "csrf-secret-change-in-production"
    
    # Cookie Configuration
    SESSION_COOKIE_SECURE: bool = True  # Set to False for local dev without HTTPS
    SESSION_COOKIE_DOMAIN: Optional[str] = None  # e.g., ".example.com" for subdomains
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list, e.g., "https://app.example.com,https://admin.example.com"
    
    # Email Configuration (for Magic Links)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "Aletheia <noreply@example.com>"
    EMAIL_ENABLED: bool = False
    
    # Magic Link Configuration
    MAGIC_LINK_EXPIRE_MINUTES: int = 15
    
    # Base URL for magic links (frontend URL)
    APP_BASE_URL: str = "http://localhost:3000"
    
    # Rate Limiting
    RATE_LIMIT_LOGIN: int = 5  # requests per minute
    RATE_LIMIT_API: int = 100
    
    # Celery Configuration (for background tasks)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"  # Redis broker URL
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"  # Redis result backend URL  # requests per minute
    
    # ==========================================================================
    # RESEARCH WORKFLOW VERSIONING
    # ==========================================================================
    
    # Router heuristics version (increment when router logic changes)
    ROUTER_VERSION: str = "1.0"
    
    # Narration policy version (increment when quantifier policy changes)
    NARRATION_POLICY_VERSION: str = "1.0"
    
    # Embedding model ID (for cache invalidation)
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list"""
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

