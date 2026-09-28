"""
Default application configuration.
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class DefaultConfig:
    """Default configuration settings."""

    # Application settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    TESTING = False

    # API settings
    API_TITLE = 'Secure DevSecOps Configuration API'
    API_VERSION = '1.0.0'
    API_DESCRIPTION = 'A configuration management service for demonstrating Policy as Code'

    # CORS settings (if needed in future)
    CORS_ENABLED = os.getenv('CORS_ENABLED', 'False').lower() in ('true', '1', 't')

    # Rate limiting (placeholder for future enhancement)
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'False').lower() in ('true', '1', 't')
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '100 per hour')

    # File upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(basedir, 'uploads'))

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(basedir, 'logs', 'app.log'))

    # Security settings (complementary to Dockerfile policies)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')

    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', 5)),
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', 10)),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 300)),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 10))
    }

    # Feature flags
    FEATURE_AUDIT_LOG = os.getenv('FEATURE_AUDIT_LOG', 'False').lower() in ('true', '1', 't')
    FEATURE_CONFIG_VALIDATION = os.getenv('FEATURE_CONFIG_VALIDATION', 'True').lower() in ('true', '1', 't')