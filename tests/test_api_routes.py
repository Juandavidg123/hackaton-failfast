"""Tests for Flask API routes."""

import json
from unittest.mock import MagicMock, patch

import pytest

from api.app import create_app


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
# Health Check Tests
# ============================================================================


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"
    assert data["service"] == "erp-voice-chat-backend"


# ============================================================================
# ERP Query Endpoint Tests
# ============================================================================


def test_query_erp_data_success(client, mock_repository):
    """Test successful ERP data query."""
    # Mock repository response
    mock_repository.query.return_value = [
        {"id": "1", "name": "Customer 1"},
        {"id": "2", "name": "Customer 2"},
    ]

    response = client.get("/api/erp/query?table=customers")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["table"] == "customers"
    assert data["count"] == 2
    assert len(data["records"]) == 2


def test_query_erp_data_missing_table(client):
    """Test ERP query without table parameter."""
    response = client.get("/api/erp/query")
    assert response.status_code == 400

    data = json.loads(response.data)
    assert data["error"] is True
    assert "Table parameter is required" in data["message"]


def test_query_erp_data_invalid_table(client):
    """Test ERP query with invalid table."""
    response = client.get("/api/erp/query?table=invalid_table")
    assert response.status_code == 400

    data = json.loads(response.data)
    assert data["error"] is True
    assert "Invalid table" in data["message"]


def test_query_erp_data_with_filters(client, mock_repository):
    """Test ERP query with filters."""
    mock_repository.query.return_value = [{"id": "1", "name": "Customer 1"}]

    response = client.get("/api/erp/query?table=customers&name=Customer%201")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["count"] == 1

    # Verify filters were passed to repository
    mock_repository.query.assert_called_once()
    call_args = mock_repository.query.call_args
    assert call_args[0][0] == "customers"
    assert "name" in call_args[0][1]


# ============================================================================
# Duplicate Detection Endpoint Tests
# ============================================================================


def test_detect_duplicates_success(client, mock_duplicate_engine):
    """Test successful duplicate detection."""
    from models.data_models import DuplicateGroup
    from datetime import datetime

    # Mock duplicate groups
    mock_group = MagicMock(spec=DuplicateGroup)
    mock_group.to_dict.return_value = {
        "id": "group1",
        "table_name": "customers",
        "record_ids": ["1", "2"],
        "similarity_score": 85.5,
        "matching_fields": {"name": {"similarity": 90}},
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    mock_duplicate_engine.detect_duplicates.return_value = [mock_group]

    response = client.post(
        "/api/duplicates/detect",
        data=json.dumps({"table": "customers"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["duplicate_groups_found"] == 1
    assert len(data["duplicate_groups"]) == 1


def test_get_duplicates(client, mock_duplicate_engine):
    """Test getting all duplicate groups."""
    from models.data_models import DuplicateGroup
    from datetime import datetime

    mock_group = MagicMock(spec=DuplicateGroup)
    mock_group.to_dict.return_value = {
        "id": "group1",
        "table_name": "customers",
        "record_ids": ["1", "2"],
        "similarity_score": 85.5,
        "matching_fields": {},
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    mock_duplicate_engine.get_duplicate_groups.return_value = [mock_group]

    response = client.get("/api/duplicates")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["count"] == 1
    assert len(data["duplicate_groups"]) == 1


def test_get_duplicate_details_success(client, mock_repository):
    """Test getting specific duplicate group details."""
    from datetime import datetime

    # Mock duplicate group
    mock_repository.get_by_id.side_effect = [
        {
            "id": "group1",
            "table_name": "customers",
            "record_ids": ["1", "2"],
            "similarity_score": 85.5,
            "matching_fields": {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        },
        {"id": "1", "name": "Customer 1"},
        {"id": "2", "name": "Customer 2"},
    ]

    response = client.get("/api/duplicates/group1")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert "duplicate_group" in data
    assert "records" in data
    assert len(data["records"]) == 2


def test_get_duplicate_details_not_found(client, mock_repository):
    """Test getting non-existent duplicate group."""
    mock_repository.get_by_id.return_value = None

    response = client.get("/api/duplicates/nonexistent")
    assert response.status_code == 404

    data = json.loads(response.data)
    assert data["error"] is True


def test_merge_duplicates_success(client, mock_duplicate_engine):
    """Test successful duplicate merge."""
    mock_duplicate_engine.merge_duplicates.return_value = {
        "id": "1",
        "name": "Merged Customer",
    }

    response = client.post(
        "/api/duplicates/group1/merge",
        data=json.dumps({"keep_values": {"name": "Merged Customer"}}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "merged_record" in data


# ============================================================================
# Inconsistency Detection Endpoint Tests
# ============================================================================


def test_detect_inconsistencies_success(client, mock_inconsistency_analyzer):
    """Test successful inconsistency detection."""
    from models.data_models import Inconsistency, InconsistencyType
    from datetime import datetime

    mock_inc = MagicMock(spec=Inconsistency)
    mock_inc.type = InconsistencyType.CALCULATION
    mock_inc.to_dict.return_value = {
        "id": "inc1",
        "type": "calculation",
        "table_name": "orders",
        "record_id": "order1",
        "field_name": "total_amount",
        "description": "Order total mismatch",
        "suggested_fix": {},
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    mock_inconsistency_analyzer.detect_inconsistencies.return_value = [mock_inc]

    response = client.post("/api/inconsistencies/detect")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["total_inconsistencies"] == 1
    assert len(data["inconsistencies"]) == 1


def test_get_inconsistencies(client, mock_inconsistency_analyzer):
    """Test getting all inconsistencies."""
    from models.data_models import Inconsistency, InconsistencyType
    from datetime import datetime

    mock_inc = MagicMock(spec=Inconsistency)
    mock_inc.type = InconsistencyType.REFERENTIAL
    mock_inc.to_dict.return_value = {
        "id": "inc1",
        "type": "referential",
        "table_name": "orders",
        "record_id": "order1",
        "field_name": "customer_id",
        "description": "Invalid customer reference",
        "suggested_fix": {},
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    mock_inconsistency_analyzer.get_inconsistencies.return_value = [mock_inc]

    response = client.get("/api/inconsistencies")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["count"] == 1
    assert len(data["inconsistencies"]) == 1


def test_get_inconsistency_details_success(client, mock_repository):
    """Test getting specific inconsistency details."""
    from datetime import datetime

    mock_repository.get_by_id.side_effect = [
        {
            "id": "inc1",
            "type": "calculation",
            "table_name": "orders",
            "record_id": "order1",
            "field_name": "total_amount",
            "description": "Order total mismatch",
            "suggested_fix": {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        },
        {"id": "order1", "total_amount": 100.0},
    ]

    response = client.get("/api/inconsistencies/inc1")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert "inconsistency" in data
    assert "affected_record" in data


def test_get_inconsistency_details_not_found(client, mock_repository):
    """Test getting non-existent inconsistency."""
    mock_repository.get_by_id.return_value = None

    response = client.get("/api/inconsistencies/nonexistent")
    assert response.status_code == 404

    data = json.loads(response.data)
    assert data["error"] is True


def test_fix_inconsistency_success(client, mock_inconsistency_analyzer):
    """Test successful inconsistency fix."""
    mock_inconsistency_analyzer.fix_inconsistency.return_value = {
        "id": "order1",
        "total_amount": 150.0,
    }

    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({"correction": {"field": "total_amount", "value": 150.0}}),
        content_type="application/json",
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert "result" in data


def test_fix_inconsistency_missing_correction(client):
    """Test fixing inconsistency without correction data."""
    response = client.post(
        "/api/inconsistencies/inc1/fix",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"] is True


# ============================================================================
# Error Handler Tests
# ============================================================================


def test_404_error_handler(client):
    """Test 404 error handler."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404

    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "not_found"


def test_405_error_handler(client):
    """Test 405 error handler."""
    response = client.post("/health")
    assert response.status_code == 405

    data = json.loads(response.data)
    assert data["error"] is True
    assert data["error_type"] == "method_not_allowed"
