"""Tests for data models."""

from datetime import datetime

import pytest

from models.data_models import DuplicateGroup, ERPRecord, Inconsistency, InconsistencyType


def test_duplicate_group_from_dict():
    """Test DuplicateGroup creation from dictionary."""
    data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "table_name": "customers",
        "record_ids": ["id1", "id2"],
        "similarity_score": 85.5,
        "matching_fields": {"name": "John Doe", "email": "john@example.com"},
        "status": "pending",
        "created_at": "2024-01-01T00:00:00",
    }

    duplicate_group = DuplicateGroup.from_dict(data)

    assert duplicate_group.id == data["id"]
    assert duplicate_group.table_name == "customers"
    assert duplicate_group.record_ids == ["id1", "id2"]
    assert duplicate_group.similarity_score == 85.5
    assert duplicate_group.status == "pending"


def test_duplicate_group_to_dict():
    """Test DuplicateGroup conversion to dictionary."""
    duplicate_group = DuplicateGroup(
        id="123e4567-e89b-12d3-a456-426614174000",
        table_name="customers",
        record_ids=["id1", "id2"],
        similarity_score=85.5,
        matching_fields={"name": "John Doe"},
        status="pending",
        created_at=datetime(2024, 1, 1),
    )

    result = duplicate_group.to_dict()

    assert result["id"] == duplicate_group.id
    assert result["table_name"] == "customers"
    assert result["similarity_score"] == 85.5


def test_inconsistency_from_dict():
    """Test Inconsistency creation from dictionary."""
    data = {
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "type": "calculation",
        "table_name": "orders",
        "record_id": "order123",
        "field_name": "total_amount",
        "description": "Order total does not match sum of line items",
        "suggested_fix": {"total_amount": 100.00},
        "status": "pending",
        "created_at": "2024-01-01T00:00:00",
    }

    inconsistency = Inconsistency.from_dict(data)

    assert inconsistency.id == data["id"]
    assert inconsistency.type == InconsistencyType.CALCULATION
    assert inconsistency.table_name == "orders"
    assert inconsistency.record_id == "order123"
    assert inconsistency.field_name == "total_amount"


def test_inconsistency_to_dict():
    """Test Inconsistency conversion to dictionary."""
    inconsistency = Inconsistency(
        id="123e4567-e89b-12d3-a456-426614174001",
        type=InconsistencyType.REFERENTIAL,
        table_name="orders",
        record_id="order123",
        field_name="customer_id",
        description="Customer does not exist",
        suggested_fix=None,
        status="pending",
        created_at=datetime(2024, 1, 1),
    )

    result = inconsistency.to_dict()

    assert result["id"] == inconsistency.id
    assert result["type"] == "referential"
    assert result["table_name"] == "orders"


def test_erp_record_from_dict():
    """Test ERPRecord creation from dictionary."""
    data = {
        "id": "customer123",
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    record = ERPRecord.from_dict("customers", data)

    assert record.id == "customer123"
    assert record.table_name == "customers"
    assert record.data["name"] == "John Doe"
    assert record.data["email"] == "john@example.com"


def test_erp_record_to_dict():
    """Test ERPRecord conversion to dictionary."""
    data = {
        "id": "customer123",
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 1),
    }

    record = ERPRecord(
        id="customer123",
        table_name="customers",
        data=data,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    result = record.to_dict()

    assert result["id"] == "customer123"
    assert result["name"] == "John Doe"
