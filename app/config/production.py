"""
Production-specific configuration.
"""
from .default import DefaultConfig

class ProductionConfig(DefaultConfig):
    """Production configuration overrides."""

    DEBUG = False
    ENV = 'production'
    SQLALCHEMY_ECHO = False
    LOG_LEVEL = 'WARNING'

    # Production security enhancements
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

    # Feature flags for production
    FEATURE_AUDIT_LOG = True  # Enable audit log in production