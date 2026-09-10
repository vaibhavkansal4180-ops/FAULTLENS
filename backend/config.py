import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or "faultlens-industrial-sec-k9284j20f83h"
    ENV = os.environ.get("FLASK_ENV", "development").lower()
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    # Safe file/payload handling
    try:
        max_content = os.environ.get("MAX_CONTENT_LENGTH")
        MAX_CONTENT_LENGTH = int(max_content) if max_content and max_content.strip() else 16 * 1024 * 1024
    except (ValueError, TypeError):
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # CORS configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Session cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in ("1", "true", "yes")

    # Database configuration
    db_url = os.environ.get("DATABASE_URL", "").strip()

    if db_url:
        # Standardize postgres:// to postgresql:// for SQLAlchemy 2.x
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        if ENV == "production":
            raise RuntimeError(
                "CRITICAL CONFIGURATION ERROR: DATABASE_URL environment variable is required "
                "in production environments. Do not use local SQLite in production."
            )
        # Local development / test fallback
        local_db_path = BASE_DIR / "faultlens.db"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{local_db_path.as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    } if "sqlite" not in SQLALCHEMY_DATABASE_URI else {}


class TestingConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-faultlens"
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
