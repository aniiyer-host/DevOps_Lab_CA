import os
import sys
import logging
from flask import Blueprint, jsonify, request

# Ensure parent directory of app is in sys.path if app directory is execution context
app_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(app_dir) == 'app':
    parent_dir = os.path.dirname(app_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

try:
    from app.config import config
    from app.models import db, Configuration
except (ImportError, ModuleNotFoundError):
    from config import config
    from models import db, Configuration

# Create blueprint
bp = Blueprint('main', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@bp.route("/")
def home():
    """Root endpoint returning application status."""
    return jsonify({
        "message": "Secure DevSecOps Configuration API is running",
        "status": "success",
        "version": "1.0.0",
        "environment": os.getenv('FLASK_ENV', 'development')
    })


@bp.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "configuration-api",
        "environment": os.getenv('FLASK_ENV', 'development')
    })


@bp.route("/configs", methods=["GET"])
def get_configs():
    """Get all configurations."""
    try:
        configs = Configuration.query.all()
        return jsonify({
            "status": "success",
            "data": [config.to_dict() for config in configs],
            "count": len(configs)
        })
    except Exception as e:
        logger.error(f"Error retrieving configurations: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve configurations"
        }), 500


@bp.route("/configs", methods=["POST"])
def create_config():
    """Create a new configuration."""
    try:
        data = request.get_json()

        if not data or 'key' not in data or 'value' not in data:
            return jsonify({
                "status": "error",
                "message": "Key and value are required"
            }), 400

        # Check if configuration already exists
        existing = Configuration.query.filter_by(key=data['key']).first()
        if existing:
            return jsonify({
                "status": "error",
                "message": f"Configuration with key '{data['key']}' already exists"
            }), 409

        # Create new configuration
        new_config = Configuration(
            key=data['key'],
            value=data['value'],
            description=data.get('description', ''),
            environment=data.get('environment', os.getenv('FLASK_ENV', 'development'))
        )

        db.session.add(new_config)
        db.session.commit()

        logger.info(f"Created configuration: {new_config.key}")
        return jsonify({
            "status": "success",
            "data": new_config.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating configuration: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to create configuration"
        }), 500


@bp.route("/configs/<int:config_id>", methods=["GET"])
def get_config(config_id):
    """Get a specific configuration by ID."""
    try:
        config = db.get_or_404(Configuration, config_id)
        return jsonify({
            "status": "success",
            "data": config.to_dict()
        })
    except Exception as e:
        logger.error(f"Error retrieving configuration {config_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Configuration not found"
        }), 404


@bp.route("/configs/<int:config_id>", methods=["PUT"])
def update_config(config_id):
    """Update a specific configuration."""
    try:
        config = db.get_or_404(Configuration, config_id)
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        # Update fields if provided
        if 'value' in data:
            config.value = data['value']
        if 'description' in data:
            config.description = data['description']
        if 'environment' in data:
            config.environment = data['environment']

        db.session.commit()

        logger.info(f"Updated configuration: {config.key}")
        return jsonify({
            "status": "success",
            "data": config.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating configuration {config_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to update configuration"
        }), 500


@bp.route("/configs/<int:config_id>", methods=["DELETE"])
def delete_config(config_id):
    """Delete a specific configuration."""
    try:
        config = db.get_or_404(Configuration, config_id)
        db.session.delete(config)
        db.session.commit()

        logger.info(f"Deleted configuration: {config.key}")
        return jsonify({
            "status": "success",
            "message": f"Configuration '{config.key}' deleted successfully"
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting configuration {config_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to delete configuration"
        }), 500


@bp.route("/configs/<key>", methods=["GET"])
def get_config_by_key(key):
    """Get a configuration by its key."""
    try:
        config = Configuration.query.filter_by(key=key).first_or_404()
        return jsonify({
            "status": "success",
            "data": config.to_dict()
        })
    except Exception as e:
        logger.error(f"Error retrieving configuration with key {key}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Configuration not found"
        }), 404


def register_routes(app):
    """Register routes with the Flask application."""
    app.register_blueprint(bp)


if __name__ == '__main__':
    try:
        from app import create_app
    except (ImportError, ModuleNotFoundError):
        from __init__ import create_app
    application = create_app()
    port = int(os.getenv('PORT', 5000))
    application.run(host='0.0.0.0', port=port)