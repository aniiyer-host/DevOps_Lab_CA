"""
Configuration models for the Flask application.
"""
from datetime import datetime, timezone

try:
    from app import db
except (ImportError, ModuleNotFoundError):
    from __init__ import db


class Configuration(db.Model):
    """Model for storing application configurations."""
    __tablename__ = 'configurations'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    environment = db.Column(db.String(50), default='development')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'environment': self.environment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Configuration {self.key}={self.value}>'