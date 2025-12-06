"""Tests for inconsistency analyzer."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from services.inconsistency_analyzer import InconsistencyAnalyzer
from models.data_models import Inconsistency, InconsistencyType


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    repo = Mock()
    return repo


@pytest.fixture
def analyzer(mock_repository):
    """Create an inconsistency analyzer with mock repository."""
    return InconsistencyAnalyzer(mock_repository)


class TestInconsistencyAnalyzer:
    """Test suite for InconsistencyAnalyzer."""

    def test_initialization(self, mock_repository):
        """Test analyzer initialization."""
        analyzer = InconsistencyAnalyzer(mock_repository)
        assert analyzer.repository == mock_repository

    def test_check_referential_integrity_valid(self, analyzer, mock_repository):
        """Test referential integrity check with valid references."""
        # Setup mock data with valid references
        orders = [
            {"id": "order-1", "customer_id": "customer-1", "total_amount": 100.00}
        ]
        customers = [{"id": "customer-1", "name": "John Doe"}]

        mock_repository.get_all.side_effect = lambda table: {
            "orders": orders,
            "order_items": [],
        }.get(table, [])

        mock_repository.get_by_id.side_effect = lambda table, id: {
            "customers": {"customer-1": customers[0]},
        }.get(table, {}).get(id)

        result = analyzer.check_referential_integrity()
        assert len(result) == 0

    def test_check_referential_integrity_invalid(self, analyzer, mock_repository):
        """Test referential integrity check with invalid references."""
        # Setup mock data with invalid reference
        orders = [
            {"id": "order-1", "customer_id": "nonexistent-customer", "total_amount": 100.00}
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "orders": orders,
            "order_items": [],
        }.get(table, [])

        mock_repository.get_by_id.side_effect = lambda table, id: None

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "referential",
            "table_name": "orders",
            "record_id": "order-1",
            "field_name": "customer_id",
            "description": "Order references non-existent customer: nonexistent-customer",
            "suggested_fix": {"action": "delete_or_update"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_referential_integrity()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.REFERENTIAL

    def test_check_calculations_order_total_mismatch(self, analyzer, mock_repository):
        """Test calculation check with order total mismatch."""
        orders = [
            {"id": "order-1", "customer_id": "customer-1", "total_amount": 100.00}
        ]
        order_items = [
            {"id": "item-1", "order_id": "order-1", "quantity": 5, "unit_price": 10.00, "line_total": 50.00},
            {"id": "item-2", "order_id": "order-1", "quantity": 3, "unit_price": 10.00, "line_total": 30.00},
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "orders": orders,
            "order_items": order_items,
        }.get(table, [])

        mock_repository.query.return_value = [
            {"id": "item-1", "order_id": "order-1", "quantity": 5, "unit_price": 10.00, "line_total": 50.00},
            {"id": "item-2", "order_id": "order-1", "quantity": 3, "unit_price": 10.00, "line_total": 30.00},
        ]

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "calculation",
            "table_name": "orders",
            "record_id": "order-1",
            "field_name": "total_amount",
            "description": "Order total mismatch: stored=100.00, calculated=80.00",
            "suggested_fix": {"action": "update_total"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_calculations()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.CALCULATION

    def test_check_calculations_line_total_mismatch(self, analyzer, mock_repository):
        """Test calculation check with line total mismatch."""
        orders = []
        order_items = [
            {
                "id": "item-1",
                "order_id": "order-1",
                "quantity": 5,
                "unit_price": 10.00,
                "line_total": 40.00,  # Should be 50.00
            }
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "orders": orders,
            "order_items": order_items,
        }.get(table, [])

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "calculation",
            "table_name": "order_items",
            "record_id": "item-1",
            "field_name": "line_total",
            "description": "Line total mismatch",
            "suggested_fix": {"action": "update_line_total"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_calculations()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.CALCULATION

    def test_check_formats_invalid_email(self, analyzer, mock_repository):
        """Test format check with invalid email."""
        customers = [
            {"id": "customer-1", "name": "John Doe", "email": "invalid-email", "phone": "5551234567"}
        ]

        mock_repository.get_all.return_value = customers

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format: invalid-email",
            "suggested_fix": {"action": "correct_format"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_formats()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.FORMAT

    def test_check_formats_valid_email(self, analyzer, mock_repository):
        """Test format check with valid email."""
        customers = [
            {"id": "customer-1", "name": "John Doe", "email": "john@example.com", "phone": "5551234567"}
        ]

        mock_repository.get_all.return_value = customers

        result = analyzer.check_formats()
        # Should not create any inconsistencies for valid email
        assert len(result) == 0

    def test_check_formats_invalid_phone(self, analyzer, mock_repository):
        """Test format check with invalid phone."""
        customers = [
            {"id": "customer-1", "name": "John Doe", "email": "john@example.com", "phone": "abc"}
        ]

        mock_repository.get_all.return_value = customers

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "phone",
            "description": "Invalid phone format: abc",
            "suggested_fix": {"action": "correct_format"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_formats()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.FORMAT

    def test_check_business_rules_negative_inventory(self, analyzer, mock_repository):
        """Test business rule check with negative inventory."""
        products = [
            {"id": "product-1", "name": "Widget", "price": 10.00, "inventory_count": -5}
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "products": products,
            "orders": [],
            "order_items": [],
        }.get(table, [])

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "business_rule",
            "table_name": "products",
            "record_id": "product-1",
            "field_name": "inventory_count",
            "description": "Negative inventory count: -5",
            "suggested_fix": {"action": "correct_value"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_business_rules()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.BUSINESS_RULE

    def test_check_business_rules_invalid_price(self, analyzer, mock_repository):
        """Test business rule check with invalid price."""
        products = [
            {"id": "product-1", "name": "Widget", "price": 0.00, "inventory_count": 10}
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "products": products,
            "orders": [],
            "order_items": [],
        }.get(table, [])

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "business_rule",
            "table_name": "products",
            "record_id": "product-1",
            "field_name": "price",
            "description": "Invalid product price: 0.00",
            "suggested_fix": {"action": "correct_value"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_business_rules()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.BUSINESS_RULE

    def test_check_business_rules_future_order_date(self, analyzer, mock_repository):
        """Test business rule check with future order date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        orders = [
            {"id": "order-1", "customer_id": "customer-1", "order_date": future_date.isoformat()}
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "products": [],
            "orders": orders,
            "order_items": [],
        }.get(table, [])

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "business_rule",
            "table_name": "orders",
            "record_id": "order-1",
            "field_name": "order_date",
            "description": f"Future order date: {future_date}",
            "suggested_fix": {"action": "correct_value"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_business_rules()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.BUSINESS_RULE

    def test_check_business_rules_invalid_quantity(self, analyzer, mock_repository):
        """Test business rule check with invalid quantity."""
        order_items = [
            {
                "id": "item-1",
                "order_id": "order-1",
                "quantity": 0,
                "unit_price": 10.00,
                "line_total": 0.00,
            }
        ]

        mock_repository.get_all.side_effect = lambda table: {
            "products": [],
            "orders": [],
            "order_items": order_items,
        }.get(table, [])

        mock_repository.insert.return_value = {
            "id": "inconsistency-1",
            "type": "business_rule",
            "table_name": "order_items",
            "record_id": "item-1",
            "field_name": "quantity",
            "description": "Invalid quantity: 0",
            "suggested_fix": {"action": "correct_value"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        result = analyzer.check_business_rules()
        assert len(result) >= 1
        assert result[0].type == InconsistencyType.BUSINESS_RULE

    def test_detect_inconsistencies_all_types(self, analyzer, mock_repository):
        """Test detect_inconsistencies runs all checks."""
        # Mock all get_all calls to return empty lists
        mock_repository.get_all.return_value = []
        mock_repository.get_by_id.return_value = None
        mock_repository.query.return_value = []

        result = analyzer.detect_inconsistencies()
        # Should return a list (even if empty)
        assert isinstance(result, list)

    def test_get_inconsistencies_with_filters(self, analyzer, mock_repository):
        """Test getting inconsistencies with filters."""
        mock_data = [
            {
                "id": "inconsistency-1",
                "type": "referential",
                "table_name": "orders",
                "record_id": "order-1",
                "field_name": "customer_id",
                "description": "Test inconsistency",
                "suggested_fix": None,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "resolved_at": None,
            }
        ]

        mock_repository.query.return_value = mock_data

        result = analyzer.get_inconsistencies(
            inconsistency_type=InconsistencyType.REFERENTIAL,
            table="orders",
            status="pending"
        )

        assert len(result) == 1
        assert result[0].type == InconsistencyType.REFERENTIAL
        mock_repository.query.assert_called_once_with(
            "inconsistencies",
            {"type": "referential", "table_name": "orders", "status": "pending"}
        )

    def test_is_valid_email(self, analyzer):
        """Test email validation."""
        assert analyzer._is_valid_email("john@example.com") is True
        assert analyzer._is_valid_email("user.name+tag@example.co.uk") is True
        assert analyzer._is_valid_email("invalid-email") is False
        assert analyzer._is_valid_email("@example.com") is False
        assert analyzer._is_valid_email("user@") is False

    def test_is_valid_phone(self, analyzer):
        """Test phone validation."""
        assert analyzer._is_valid_phone("5551234567") is True
        assert analyzer._is_valid_phone("+1 (555) 123-4567") is True
        assert analyzer._is_valid_phone("555-123-4567") is True
        assert analyzer._is_valid_phone("abc") is False
        assert analyzer._is_valid_phone("123") is False  # Too short
        assert analyzer._is_valid_phone("12345678901234567890") is False  # Too long


    def test_fix_inconsistency_field_update(self, analyzer, mock_repository):
        """Test fixing an inconsistency by updating a field."""
        inconsistency_id = "inconsistency-1"
        inconsistency_data = {
            "id": inconsistency_id,
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format",
            "suggested_fix": {"action": "correct_format", "field": "email"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        mock_repository.get_by_id.return_value = inconsistency_data

        updated_record = {
            "id": "customer-1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        mock_repository.update.return_value = updated_record

        # Mock the verification check to return no inconsistencies
        mock_repository.get_all.return_value = []

        correction = {"field": "email", "value": "john@example.com"}

        result = analyzer.fix_inconsistency(inconsistency_id, correction)

        # Verify the record was updated
        assert result["email"] == "john@example.com"

        # Verify inconsistency was marked as resolved
        mock_repository.update.assert_any_call(
            "inconsistencies",
            inconsistency_id,
            {"status": "resolved", "resolved_at": pytest.approx(datetime.now(timezone.utc).isoformat(), abs=5)}
        )

    def test_fix_inconsistency_record_deletion(self, analyzer, mock_repository):
        """Test fixing an inconsistency by deleting a record."""
        inconsistency_id = "inconsistency-1"
        inconsistency_data = {
            "id": inconsistency_id,
            "type": "referential",
            "table_name": "orders",
            "record_id": "order-1",
            "field_name": "customer_id",
            "description": "Order references non-existent customer",
            "suggested_fix": {"action": "delete_or_update"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        mock_repository.get_by_id.return_value = inconsistency_data
        mock_repository.delete.return_value = True

        # Mock the verification check
        mock_repository.get_all.return_value = []

        correction = {"delete_record": True}

        result = analyzer.fix_inconsistency(inconsistency_id, correction)

        # Verify the record was deleted
        assert result["action"] == "deleted"
        assert result["record_id"] == "order-1"
        mock_repository.delete.assert_called_once_with("orders", "order-1")

    def test_fix_inconsistency_calculation_with_dependent_update(self, analyzer, mock_repository):
        """Test fixing a calculation inconsistency updates dependent records."""
        inconsistency_id = "inconsistency-1"
        inconsistency_data = {
            "id": inconsistency_id,
            "type": "calculation",
            "table_name": "order_items",
            "record_id": "item-1",
            "field_name": "line_total",
            "description": "Line total mismatch",
            "suggested_fix": {"action": "update_line_total", "field": "line_total"},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        order_item = {
            "id": "item-1",
            "order_id": "order-1",
            "quantity": 5,
            "unit_price": 10.00,
            "line_total": 50.00,
        }

        mock_repository.get_by_id.side_effect = lambda table, id: {
            ("inconsistencies", inconsistency_id): inconsistency_data,
            ("order_items", "item-1"): order_item,
        }.get((table, id))

        updated_item = {**order_item, "line_total": 50.00}
        mock_repository.update.return_value = updated_item

        # Mock order items query for recalculating order total
        mock_repository.query.return_value = [
            {"id": "item-1", "order_id": "order-1", "line_total": 50.00},
            {"id": "item-2", "order_id": "order-1", "line_total": 30.00},
        ]

        # Mock verification check
        mock_repository.get_all.return_value = []

        correction = {"field": "line_total", "value": 50.00}

        result = analyzer.fix_inconsistency(inconsistency_id, correction)

        # Verify the order item was updated
        assert result["line_total"] == 50.00

        # Verify the order total was also updated (50 + 30 = 80)
        order_update_calls = [
            call for call in mock_repository.update.call_args_list
            if call[0][0] == "orders"
        ]
        assert len(order_update_calls) >= 1
        assert order_update_calls[0][0][1] == "order-1"
        assert order_update_calls[0][0][2]["total_amount"] == 80.00

    def test_fix_inconsistency_not_found(self, analyzer, mock_repository):
        """Test fixing a non-existent inconsistency raises error."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Inconsistency .* not found"):
            analyzer.fix_inconsistency("nonexistent-id", {"field": "test", "value": "test"})

    def test_fix_inconsistency_invalid_correction(self, analyzer, mock_repository):
        """Test fixing with invalid correction data raises error."""
        inconsistency_data = {
            "id": "inconsistency-1",
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format",
            "suggested_fix": None,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        mock_repository.get_by_id.return_value = inconsistency_data

        # Missing 'value' key
        with pytest.raises(ValueError, match="Correction must contain"):
            analyzer.fix_inconsistency("inconsistency-1", {"field": "email"})

    def test_fix_inconsistency_field_mismatch(self, analyzer, mock_repository):
        """Test fixing with mismatched field raises error."""
        inconsistency_data = {
            "id": "inconsistency-1",
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format",
            "suggested_fix": None,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        mock_repository.get_by_id.return_value = inconsistency_data

        # Wrong field name
        with pytest.raises(ValueError, match="does not match"):
            analyzer.fix_inconsistency(
                "inconsistency-1", {"field": "phone", "value": "5551234567"}
            )

    def test_fix_inconsistency_verification_fails(self, analyzer, mock_repository):
        """Test that verification catches unresolved inconsistencies."""
        inconsistency_id = "inconsistency-1"
        inconsistency_data = {
            "id": inconsistency_id,
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format",
            "suggested_fix": None,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        mock_repository.get_by_id.return_value = inconsistency_data

        updated_record = {
            "id": "customer-1",
            "email": "still-invalid",  # Still invalid
        }
        mock_repository.update.return_value = updated_record

        # Mock verification to still find the inconsistency
        mock_repository.get_all.return_value = [
            {"id": "customer-1", "email": "still-invalid", "phone": "5551234567"}
        ]

        mock_repository.insert.return_value = {
            "id": "inconsistency-2",
            "type": "format",
            "table_name": "customers",
            "record_id": "customer-1",
            "field_name": "email",
            "description": "Invalid email format: still-invalid",
            "suggested_fix": None,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        correction = {"field": "email", "value": "still-invalid"}

        with pytest.raises(ValueError, match="Inconsistency still exists"):
            analyzer.fix_inconsistency(inconsistency_id, correction)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
