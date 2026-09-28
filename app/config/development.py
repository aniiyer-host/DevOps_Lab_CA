"""
Development-specific configuration.
"""
from .default import DefaultConfig

class DevelopmentConfig(DefaultConfig):
    """Development configuration overrides."""

    DEBUG = True
    ENV = 'development'
    SQLALCHEMY_ECHO = True  # Log SQL queries
    LOG_LEVEL = 'DEBUG'

    # Development-specific settings
    FEATURE_AUDIT_LOG = False  # Disable audit log in dev for simplicity