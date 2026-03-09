"""
Configuration manager for Predatory Velocity.
Centralizes all environment variables and constants with validation.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field, validator
from loguru import logger

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = Field(..., env="FIREBASE_PROJECT_ID")
    FIREBASE_CREDENTIALS_PATH: Path = Field(
        default=Path("serviceAccountKey.json"),
        env="FIREBASE_CREDENTIALS_PATH"
    )
    
    # Base RPC Endpoints (prioritized)
    BASE_RPC_PRIMARY: str = Field(
        default="https://mainnet.base.org",
        env="BASE_RPC_PRIMARY"
    )
    BASE_RPC_SECONDARY: str = Field(
        default="https://base.publicnode.com",
        env="BASE_RPC_SECONDARY"
    )
    BASE_RPC_EMERGENCY: str = Field(
        default="https://base.llamarpc.com",
        env="BASE_RPC_EMERGENCY"
    )
    
    # Telegram Bot Control
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    
    # Trading Parameters
    INITIAL_CAPITAL_USD: float = Field(default=5.0, env="INITIAL_CAPITAL_USD")
    MAX_DAILY_LOSS_PCT: float = Field(default=15.0, env="MAX_DAILY_LOSS_PCT")
    MIN_PROFIT_PCT: float = Field(default=0.5, env="MIN_PROFIT_PCT")
    MAX_SLIPPAGE_PCT: float = Field(default=2.0, env="MAX_SLIPPAGE_PCT")
    
    # Signal Thresholds
    MIN_SIGNAL_SCORE: float = Field(default=0.8, env="MIN_SIGNAL_SCORE")
    MIN_LIQUIDITY_USD: float = Field(default=1000.0, env="MIN_LIQUIDITY_USD")
    
    # File Paths
    LOG_DIR: Path = Field(default=Path("logs"), env="LOG_DIR")
    MODELS_DIR: Path = Field(default=Path("models"), env="MODELS_DIR")
    DATA_DIR: Path = Field(default=Path("data"), env="DATA_DIR")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("FIREBASE_CREDENTIALS_PATH")
    def validate_firebase_credentials(cls, v):
        if not v.exists():
            logger.error(f"Firebase credentials not found at: {v}")
            raise FileNotFoundError(f"Firebase credentials missing: {v}")
        return v
    
    @validator("LOG_DIR", "MODELS_DIR", "DATA_DIR")
    def create_directories(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

# Global settings instance
try:
    settings = Settings()
    logger.info(f"Configuration loaded for environment: {settings.ENVIRONMENT}")
except Exception as e:
    logger.critical(f"Failed to load configuration: {e}")
    raise

# Export for easy import
__all__ = ['settings']