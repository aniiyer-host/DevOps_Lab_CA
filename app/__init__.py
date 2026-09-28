"""Flask application package."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import sys
import logging

# Ensure parent directory of app is in sys.path if app directory is execution context
app_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(app_dir) == 'app':
    parent_dir = os.path.dirname(app_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration based on environment
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    try:
        from app.config import config
    except (ImportError, ModuleNotFoundError):
        from config import config

    config_class = config.get(config_name, config['default'])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Import models
    try:
        from app.models import Configuration
    except (ImportError, ModuleNotFoundError):
        from models import Configuration

    # Import and register routes
    try:
        from app.app import register_routes
    except (ImportError, ModuleNotFoundError):
        import app as app_module
        register_routes = getattr(app_module, 'register_routes')

    register_routes(app)

    # Ensure database tables are created
    with app.app_context():
        db.create_all()

    return app


# For backward compatibility and direct access
app = create_app()

__all__ = ['app', 'db', 'create_app']