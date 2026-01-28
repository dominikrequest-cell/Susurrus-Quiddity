"""
Configuration and environment setup
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    
    # Database
    MONGODB_URL: str = os.getenv(
        "MONGODB_URL",
        "mongodb+srv://admin:password@cluster.mongodb.net/pet_trading?retryWrites=true&w=majority"
    )
    
    # Discord Bot
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_GUILD_ID: Optional[int] = os.getenv("DISCORD_GUILD_ID")
    
    # API
    API_SECRET: str = os.getenv("API_SECRET", "your-secret-key-change-in-production")
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Roblox
    ROBLOX_BOT_ACCOUNT: str = os.getenv("ROBLOX_BOT_ACCOUNT", "")
    ROBLOX_BOT_USER_ID: int = int(os.getenv("ROBLOX_BOT_USER_ID", "0"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Trade Limits
    MIN_GEM_DEPOSIT: int = 50_000_000  # 50M
    MAX_GEM_DEPOSIT: int = 10_000_000_000  # 10B
    GEM_DEPOSIT_MULTIPLE: int = 50_000_000
    MAX_BOT_GEM_BALANCE: int = 100_000_000_000  # 100B
    
    # Verification
    VERIFICATION_CODE_LENGTH: int = 16
    VERIFICATION_CODE_EXPIRY_MINUTES: int = 10
    
    # Security
    PAYLOAD_MAX_AGE_SECONDS: int = 300  # 5 minutes
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN not set")
        if not cls.MONGODB_URL:
            raise ValueError("MONGODB_URL not set")
        if cls.API_SECRET == "your-secret-key-change-in-production":
            print("⚠️  WARNING: Using default API_SECRET. Change in production!")


config = Config()
