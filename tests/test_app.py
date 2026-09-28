import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Configuration


@pytest.fixture
def app():
    """Create and configure a clean test application instance for each test."""
    test_app = create_app('testing')
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the application."""
    return app.test_client()


def test_home(client):
    """Test the home endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["message"] == "Secure DevSecOps Configuration API is running"


def test_health(client):
    """Test the health endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"
    assert response.json["service"] == "configuration-api"


def test_get_configs_empty(client):
    """Test getting configurations when none exist."""
    response = client.get("/configs")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["data"] == []
    assert response.json["count"] == 0


def test_create_and_get_config(client):
    """Test creating and retrieving a configuration."""
    config_data = {
        "key": "test.key",
        "value": "test_value",
        "description": "Test configuration"
    }

    response = client.post("/configs",
                          json=config_data,
                          content_type='application/json')

    assert response.status_code == 201
    assert response.json["status"] == "success"
    assert response.json["data"]["key"] == "test.key"
    assert response.json["data"]["value"] == "test_value"

    config_id = response.json["data"]["id"]

    # Get the configuration by ID
    response = client.get(f"/configs/{config_id}")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["data"]["id"] == config_id
    assert response.json["data"]["key"] == "test.key"

    # Get the configuration by key
    response = client.get("/configs/test.key")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["data"]["key"] == "test.key"


def test_get_nonexistent_config(client):
    """Test retrieving non-existent configurations."""
    response = client.get("/configs/999")
    assert response.status_code == 404
    assert response.json["status"] == "error"

    response = client.get("/configs/nonexistent.key")
    assert response.status_code == 404
    assert response.json["status"] == "error"


def test_update_config(client):
    """Test updating a configuration."""
    config_data = {
        "key": "update.test",
        "value": "original_value",
        "description": "Original description"
    }

    response = client.post("/configs",
                          json=config_data,
                          content_type='application/json')
    config_id = response.json["data"]["id"]

    update_data = {
        "value": "updated_value",
        "description": "Updated description"
    }

    response = client.put(f"/configs/{config_id}",
                         json=update_data,
                         content_type='application/json')

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["data"]["value"] == "updated_value"
    assert response.json["data"]["description"] == "Updated description"


def test_delete_config(client):
    """Test deleting a configuration."""
    config_data = {
        "key": "delete.test",
        "value": "to_be_deleted"
    }

    response = client.post("/configs",
                          json=config_data,
                          content_type='application/json')
    config_id = response.json["data"]["id"]

    response = client.delete(f"/configs/{config_id}")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert "deleted successfully" in response.json["message"]

    response = client.get(f"/configs/{config_id}")
    assert response.status_code == 404


def test_duplicate_config_key(client):
    """Test that duplicate config keys are rejected."""
    config_data = {
        "key": "duplicate.test",
        "value": "first_value"
    }

    response = client.post("/configs",
                          json=config_data,
                          content_type='application/json')
    assert response.status_code == 201

    response = client.post("/configs",
                          json=config_data,
                          content_type='application/json')
    assert response.status_code == 409
    assert response.json["status"] == "error"
    assert "already exists" in response.json["message"]


def test_missing_required_fields(client):
    """Test that missing required fields return error."""
    # Missing key
    response = client.post("/configs",
                      json={"value": "test"},
                      content_type='application/json')
    assert response.status_code == 400

    # Missing value
    response = client.post("/configs",
                      json={"key": "test"},
                      content_type='application/json')
    assert response.status_code == 400