"""
Job Portal and Application Tracking System (ATS)
Security Configuration Module
Phase 4: Security, Access Control & Environment Management
"""

import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


class Config:
    """Base Security and Application Configuration."""

    # Cryptographic Secret Key for Sessions and CSRF (never hard-code production secrets)
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Session Cookie Hardening
    SESSION_COOKIE_NAME = "ats_session"
    SESSION_COOKIE_HTTPONLY = True  # Neutralize XSS session theft
    SESSION_COOKIE_SAMESITE = "Lax"  # Mitigate CSRF on top-level navigations
    SESSION_COOKIE_SECURE = _parse_bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # CSRF Protection (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # Token valid for 1 hour

    # Database Configuration (MySQL 8.0+)
    DATABASE_HOST = os.environ.get("DATABASE_HOST", "localhost")
    DATABASE_PORT = int(os.environ.get("DATABASE_PORT", 3306))
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "job_portal_ats")
    DATABASE_USER = os.environ.get("DATABASE_USER", "ats_app_user")
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")
    DATABASE_CHARSET = "utf8mb4"

    # Security Headers and Flags
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB request limit


class DevelopmentConfig(Config):
    """Development Environment Settings."""

    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing Environment Settings."""

    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False
    SECRET_KEY = os.environ.get("TEST_SECRET_KEY") or secrets.token_hex(32)
    DATABASE_USER = os.environ.get("TEST_DATABASE_USER", os.environ.get("DATABASE_USER", "root"))
    DATABASE_PASSWORD = os.environ.get(
        "TEST_DATABASE_PASSWORD", os.environ.get("DATABASE_PASSWORD", "")
    )


class ProductionConfig(Config):
    """Production Environment Hardening."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SECRET_KEY = os.environ.get("SECRET_KEY", "")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
