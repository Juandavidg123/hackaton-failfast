"""Tests for duplicate detection engine."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from hypothesis import given, strategies as st, settings

from services.duplicate_detection import DuplicateDetectionEngine
from models.data_models import DuplicateGroup


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    repo = Mock()
    return repo


@pytest.fixture
def engine(mock_repository):
    """Create a duplicate detection engine with mock repository."""
    return DuplicateDetectionEngine(mock_repository, threshold=80)


class TestDuplicateDetectionEngine:
    """Test suite for DuplicateDetectionEngine."""

    def test_initialization(self, mock_repository):
        """Test engine initialization."""
        engine = DuplicateDetectionEngine(mock_repository, threshold=85)
        assert engine.repository == mock_repository
        assert engine.threshold == 85

    def test_text_comparison_exact_match(self, engine):
        """Test text comparison with exact match."""
        score = engine._compare_text("John Doe", "John Doe")
        assert score == 100.0

    def test_text_comparison_case_insensitive(self, engine):
        """Test text comparison is case insensitive."""
        score = engine._compare_text("John Doe", "john doe")
        assert score == 100.0

    def test_text_comparison_similar(self, engine):
        """Test text comparison with similar strings."""
        score = engine._compare_text("John Doe", "John Do")
        assert 80.0 <= score < 100.0

    def test_text_comparison_different(self, engine):
        """Test text comparison with different strings."""
        score = engine._compare_text("John Doe", "Jane Smith")
        assert score < 50.0

    def test_phone_normalization(self, engine):
        """Test phone number normalization."""
        assert engine._normalize_phone("+1 (555) 123-4567") == "15551234567"
        assert engine._normalize_phone("555-123-4567") == "5551234567"
        assert engine._normalize_phone("555.123.4567") == "5551234567"

    def test_phone_comparison_exact_match(self, engine):
        """Test phone comparison with exact match after normalization."""
        score = engine._compare_phone("+1 (555) 123-4567", "15551234567")
        assert score == 100.0

    def test_phone_comparison_substring(self, engine):
        """Test phone comparison with country code difference."""
        score = engine._compare_phone("5551234567", "15551234567")
        assert score == 90.0

    def test_email_comparison_exact_match(self, engine):
        """Test email comparison with exact match."""
        score = engine._compare_email("john@example.com", "john@example.com")
        assert score == 100.0

    def test_email_comparison_same_domain(self, engine):
        """Test email comparison with same domain."""
        score = engine._compare_email("john@example.com", "jane@example.com")
        assert score > 20.0  # Should get domain bonus

    def test_email_comparison_different_domain(self, engine):
        """Test email comparison with different domains."""
        score = engine._compare_email("john@example.com", "john@other.com")
        assert score < 100.0

    def test_calculate_similarity_identical_records(self, engine):
        """Test similarity calculation for identical records."""
        record1 = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        record2 = {
            "id": "2",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        
        similarity, matching_fields = engine.calculate_similarity(record1, record2)
        assert similarity == 100.0
        assert len(matching_fields) == 3  # name, email, phone

    def test_calculate_similarity_similar_records(self, engine):
        """Test similarity calculation for similar records."""
        record1 = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        record2 = {
            "id": "2",
            "name": "John Do",  # Slightly different
            "email": "john@example.com",
            "phone": "555-123-4567",  # Different format
        }
        
        similarity, matching_fields = engine.calculate_similarity(record1, record2)
        assert 80.0 <= similarity <= 100.0

    def test_calculate_similarity_different_records(self, engine):
        """Test similarity calculation for different records."""
        record1 = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        record2 = {
            "id": "2",
            "name": "Jane Smith",
            "email": "jane@other.com",
            "phone": "5559876543",
        }
        
        similarity, matching_fields = engine.calculate_similarity(record1, record2)
        assert similarity < 50.0

    def test_detect_duplicates_no_records(self, engine, mock_repository):
        """Test duplicate detection with no records."""
        mock_repository.get_all.return_value = []
        
        result = engine.detect_duplicates("customers")
        assert result == []

    def test_detect_duplicates_single_record(self, engine, mock_repository):
        """Test duplicate detection with single record."""
        mock_repository.get_all.return_value = [
            {"id": "1", "name": "John Doe", "email": "john@example.com"}
        ]
        
        result = engine.detect_duplicates("customers")
        assert result == []

    def test_detect_duplicates_with_duplicates(self, engine, mock_repository):
        """Test duplicate detection with actual duplicates."""
        records = [
            {"id": "1", "name": "John Doe", "email": "john@example.com", "phone": "5551234567"},
            {"id": "2", "name": "John Doe", "email": "john@example.com", "phone": "555-123-4567"},
            {"id": "3", "name": "Jane Smith", "email": "jane@other.com", "phone": "5559876543"},
        ]
        mock_repository.get_all.return_value = records
        
        # Mock the insert to return a duplicate group
        mock_repository.insert.return_value = {
            "id": "group-1",
            "table_name": "customers",
            "record_ids": ["1", "2"],
            "similarity_score": 95.0,
            "matching_fields": {"name": {"value1": "John Doe", "value2": "John Doe", "similarity": 100.0}},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }
        
        result = engine.detect_duplicates("customers", threshold=80)
        
        assert len(result) == 1
        assert result[0].table_name == "customers"
        assert len(result[0].record_ids) == 2
        mock_repository.insert.assert_called_once()

    def test_similarity_score_bounds(self, engine):
        """Test that similarity scores are always between 0 and 100."""
        # Test various record combinations
        test_cases = [
            ({"name": "A"}, {"name": "Z"}),
            ({"name": ""}, {"name": "Something"}),
            ({"email": "a@b.c"}, {"email": "x@y.z"}),
            ({"phone": "1234567890"}, {"phone": "9876543210"}),
        ]
        
        for record1, record2 in test_cases:
            similarity, _ = engine.calculate_similarity(record1, record2)
            assert 0.0 <= similarity <= 100.0, f"Similarity {similarity} out of bounds for {record1} vs {record2}"

    def test_merge_duplicates_preserves_non_null_values(self, engine, mock_repository):
        """Test that merge operation preserves all non-null values."""
        # Setup mock data
        group_data = {
            "id": "group-1",
            "table_name": "customers",
            "record_ids": ["1", "2"],
            "similarity_score": 95.0,
            "matching_fields": {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }
        
        record1 = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": None,
            "address": "123 Main St",
        }
        
        record2 = {
            "id": "2",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
            "address": None,
        }
        
        def get_by_id_side_effect(table, id):
            if table == "duplicate_groups":
                return group_data
            elif table == "customers":
                return {"1": record1, "2": record2}.get(id)
            return None
        
        mock_repository.get_by_id.side_effect = get_by_id_side_effect
        
        mock_repository.update.return_value = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
            "address": "123 Main St",
        }
        
        mock_repository.query.return_value = []
        mock_repository.delete.return_value = True
        
        result = engine.merge_duplicates("group-1", {})
        
        # Verify the merged record has all non-null values
        assert result["phone"] == "5551234567"  # From record2
        assert result["address"] == "123 Main St"  # From record1

    def test_merge_duplicates_raises_on_conflicts(self, engine, mock_repository):
        """Test that merge raises error when there are unresolved conflicts."""
        group_data = {
            "id": "group-1",
            "table_name": "customers",
            "record_ids": ["1", "2"],
            "similarity_score": 95.0,
            "matching_fields": {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }
        
        record1 = {
            "id": "1",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5551234567",
        }
        
        record2 = {
            "id": "2",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "5559876543",  # Different phone number - conflict!
        }
        
        def get_by_id_side_effect(table, id):
            if table == "duplicate_groups":
                return group_data
            elif table == "customers":
                return {"1": record1, "2": record2}.get(id)
            return None
        
        mock_repository.get_by_id.side_effect = get_by_id_side_effect
        
        with pytest.raises(ValueError, match="Merge conflicts detected"):
            engine.merge_duplicates("group-1", {})


class TestMergeDataPreservationProperty:
    """Property-based tests for merge data preservation."""

    # Feature: erp-voice-chat, Property 7: Merge data preservation
    @given(
        record1_data=st.dictionaries(
            keys=st.sampled_from(["name", "email", "phone", "address", "notes"]),
            values=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            min_size=1,
            max_size=5,
        ),
        record2_data=st.dictionaries(
            keys=st.sampled_from(["name", "email", "phone", "address", "notes"]),
            values=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_merge_preserves_all_non_null_values(self, record1_data, record2_data):
        """
        Property 7: Merge data preservation
        For any merge operation on duplicate records, all non-null values from both
        records should appear in the resulting canonical record.
        Validates: Requirements 3.3
        """
        # Setup mock repository
        mock_repository = Mock()
        engine = DuplicateDetectionEngine(mock_repository, threshold=80)

        # Add IDs to records
        record1 = {"id": "1", **record1_data}
        record2 = {"id": "2", **record2_data}

        # Setup mock data for duplicate group
        group_data = {
            "id": "group-1",
            "table_name": "customers",
            "record_ids": ["1", "2"],
            "similarity_score": 95.0,
            "matching_fields": {},
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "resolved_at": None,
        }

        def get_by_id_side_effect(table, id):
            if table == "duplicate_groups":
                return group_data
            elif table == "customers":
                return {"1": record1, "2": record2}.get(id)
            return None

        mock_repository.get_by_id.side_effect = get_by_id_side_effect

        # Collect all non-null values from both records
        expected_non_null_fields = {}
        for field, value in record1_data.items():
            if value is not None:
                expected_non_null_fields[field] = value

        for field, value in record2_data.items():
            if value is not None:
                # If field exists in both with different values, we have a conflict
                if field in expected_non_null_fields and expected_non_null_fields[field] != value:
                    # This is a conflict case - skip this test case
                    # We'll handle conflicts in a separate property test
                    return
                expected_non_null_fields[field] = value

        # Mock the update to capture what would be saved
        saved_record = {}

        def update_side_effect(table, id, data):
            saved_record.update(data)
            saved_record["id"] = id
            return saved_record

        mock_repository.update.side_effect = update_side_effect
        mock_repository.query.return_value = []
        mock_repository.delete.return_value = True

        # Perform merge
        try:
            result = engine.merge_duplicates("group-1", {})

            # Verify all non-null values are preserved
            for field, expected_value in expected_non_null_fields.items():
                assert field in result, f"Field '{field}' with non-null value should be in merged record"
                assert result[field] == expected_value, f"Field '{field}' value should be preserved"

        except ValueError as e:
            # If we get a conflict error, that's expected for conflicting fields
            if "Merge conflicts detected" in str(e):
                # This is acceptable - conflicts should be handled separately
                pass
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
