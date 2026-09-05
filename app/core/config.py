from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Revenue Recovery Agent"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/recovery_agent"
    
    @validator("DATABASE_URL", pre=True)
    def handle_supabase_url(cls, v):
        # Supabase provides postgres:// but asyncpg requires postgresql+asyncpg://
        if v and v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v and v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # API Keys
    GROQ_API_KEY: Optional[str] = None
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
