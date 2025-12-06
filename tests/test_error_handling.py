"""Tests for error handling and validation."""

import json
from unittest.mock import MagicMock, patch

import pytest
from postgrest.exceptions import APIError

from api.app import create_app
from api.error_handlers import (
    ConstraintViolationError,
    DatabaseConnectionError,
)
from api.validation import ValidationError


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    with patch("api.routes.repository") as mock_repo:
        yield mock_repo


@pytest.fixture
def mock_duplicate_engine():
    """Create mock duplicate detection engine."""
    with patch("api.routes.duplicate_engine") as mock_engine:
        yield mock_engine


@pytest.fixture
def mock_inconsistency_analyzer():
    """Create mock inconsistency analyzer."""
    with patch("api.routes.inconsistency_analyzer") as mock_analyzer:
        yield mock_analyzer


# ============================================================================
# Validation Error Tests
# ============================================================================


def test_invalid_json_body(client):
    """Test handling of invalid JSON in request body."""
    response = client.post(
        "/api/duplicates/detect",
        data="invalid json{",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "validation_error"
    assert "Invalid JSON" in data["message"]


def test_invalid_threshold_value(client):
    """Test validation of threshold parameter."""
    response = client.post(
        "/api/duplicates/detect",
        data=json.dumps({"threshold": 150}),  # Invalid: > 100
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "Threshold must be between 0 and 100" in data["message"]


def test_invalid_threshold_type(client):
    """Test validation of threshold type."""
    response = client.post(
        "/api/duplicates/detect",
        data=json.dumps({"threshold": "invalid"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "Threshold must be an integer" in data["message"]


def test_invalid_status_filter(client, mock_duplicate_engine):
    """Test validation of status filter."""
    response = client.get("/api/duplicates?status=invalid_status")

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "Invalid status" in data["message"]


def test_missing_correction_field(client):
    """Test validation of correction request without field."""
    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({"correction": {"value": 100}}),  # Missing 'field'
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "field" in data["message"].lower()


def test_missing_correction_value(client):
    """Test validation of correction request without value."""
    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({"correction": {"field": "total_amount"}}),  # Missing 'value'
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "value" in data["message"].lower()


# ============================================================================
# Database Connection Error Tests
# ============================================================================


def test_database_connection_error(client, mock_repository):
    """Test handling of database connection errors."""
    # Simulate connection error
    mock_repository.query.side_effect = APIError(
        {"message": "connection timeout", "code": "PGRST000"}
    )

    response = client.get("/api/erp/query?table=customers")

    assert response.status_code == 503
    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "database_connection_error"
    assert "database" in data["message"].lower()


# ============================================================================
# Constraint Violation Error Tests
# ============================================================================


def test_duplicate_key_constraint(client, mock_duplicate_engine):
    """Test handling of duplicate key constraint violations."""
    # Simulate duplicate key error
    mock_duplicate_engine.detect_duplicates.side_effect = APIError(
        {"message": "duplicate key value violates unique constraint", "code": "23505"}
    )

    response = client.post(
        "/api/duplicates/detect",
        data=json.dumps({"table": "customers"}),
        content_type="application/json",
    )

    assert response.status_code == 409
    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "constraint_violation"


def test_foreign_key_constraint(client, mock_inconsistency_analyzer):
    """Test handling of foreign key constraint violations."""
    # Simulate foreign key error
    mock_inconsistency_analyzer.fix_inconsistency.side_effect = APIError(
        {
            "message": "insert or update on table violates foreign key constraint",
            "code": "23503",
        }
    )

    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({"correction": {"field": "customer_id", "value": "invalid"}}),
        content_type="application/json",
    )

    assert response.status_code == 409
    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "constraint_violation"


# ============================================================================
# Transaction Rollback Tests
# ============================================================================


def test_merge_rollback_on_error(client, mock_duplicate_engine):
    """Test that merge operations rollback on error."""
    # Simulate error during merge
    mock_duplicate_engine.merge_duplicates.side_effect = ValueError(
        "Merge conflicts detected"
    )

    response = client.post(
        "/api/duplicates/group1/merge",
        data=json.dumps({"keep_values": {}}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True
    assert "conflict" in data["message"].lower()


def test_fix_rollback_on_error(client, mock_inconsistency_analyzer):
    """Test that fix operations rollback on error."""
    # Simulate error during fix
    mock_inconsistency_analyzer.fix_inconsistency.side_effect = ValueError(
        "Inconsistency still exists after correction"
    )

    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({"correction": {"field": "total_amount", "value": 100}}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True


# ============================================================================
# Error Response Format Tests
# ============================================================================


def test_error_response_format(client):
    """Test that error responses follow the standardized format."""
    response = client.get("/api/erp/query?table=invalid_table")

    assert response.status_code == 400
    data = json.loads(response.data)

    # Check required fields
    assert "error" in data
    assert data["error"] is True
    assert "error_type" in data
    assert "message" in data
    assert "suggested_actions" in data

    # Check types
    assert isinstance(data["error_type"], str)
    assert isinstance(data["message"], str)
    assert isinstance(data["suggested_actions"], list)


def test_error_response_with_details(client, mock_repository):
    """Test that error responses include details when available."""
    # Simulate an error with details
    mock_repository.query.side_effect = Exception("Detailed error information")

    response = client.get("/api/erp/query?table=customers")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert "details" in data
    assert "Detailed error information" in data["details"]


# ============================================================================
# Suggested Actions Tests
# ============================================================================


def test_not_found_suggested_actions(client, mock_repository):
    """Test that not found errors include helpful suggestions."""
    mock_repository.get_by_id.return_value = None

    response = client.get("/api/duplicates/nonexistent")

    assert response.status_code == 404
    data = json.loads(response.data)
    assert len(data["suggested_actions"]) > 0
    assert any("ID" in action for action in data["suggested_actions"])


def test_validation_error_suggested_actions(client):
    """Test that validation errors include helpful suggestions."""
    response = client.get("/api/erp/query")  # Missing table parameter

    assert response.status_code == 400
    data = json.loads(response.data)
    assert len(data["suggested_actions"]) > 0


# ============================================================================
# Edge Cases
# ============================================================================


def test_empty_request_body(client, mock_duplicate_engine):
    """Test handling of empty request body."""
    mock_duplicate_engine.detect_duplicates.return_value = []

    response = client.post(
        "/api/duplicates/detect",
        data="",
        content_type="application/json",
    )

    # Should succeed with defaults
    assert response.status_code == 200


def test_null_request_body(client, mock_duplicate_engine):
    """Test handling of null request body."""
    mock_duplicate_engine.detect_duplicates.return_value = []

    response = client.post(
        "/api/duplicates/detect",
        data=json.dumps(None),
        content_type="application/json",
    )

    # Should succeed with defaults
    assert response.status_code == 200


def test_unexpected_exception(client, mock_repository):
    """Test handling of unexpected exceptions."""
    # Simulate an unexpected error
    mock_repository.query.side_effect = RuntimeError("Unexpected error")

    response = client.get("/api/erp/query?table=customers")

    assert response.status_code == 500
    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "server_error"
    assert "unexpected" in data["message"].lower()
