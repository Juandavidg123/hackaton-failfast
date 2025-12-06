"""Duplicate detection engine for ERP data."""

import re
from typing import Any, Dict, List, Optional, Tuple

import Levenshtein

from models.data_models import DuplicateGroup
from repositories.supabase_repository import SupabaseRepository


class DuplicateDetectionEngine:
    """Engine for detecting duplicate records in ERP database."""

    def __init__(self, repository: SupabaseRepository, threshold: int = 80):
        """Initialize duplicate detection engine.

        Args:
            repository: Supabase repository for database access
            threshold: Similarity threshold (0-100) for considering records as duplicates
        """
        self.repository = repository
        self.threshold = threshold

    def detect_duplicates(
        self, table: str, threshold: Optional[int] = None
    ) -> List[DuplicateGroup]:
        """Detect duplicates in specified table.

        Args:
            table: Table name to analyze for duplicates
            threshold: Optional similarity threshold override

        Returns:
            List of detected duplicate groups
        """
        if threshold is None:
            threshold = self.threshold

        # Get all records from the table
        records = self.repository.get_all(table)

        if len(records) < 2:
            return []

        # Find duplicate groups
        duplicate_groups = []
        processed_ids = set()

        for i, record1 in enumerate(records):
            if record1["id"] in processed_ids:
                continue

            group_records = [record1["id"]]
            matching_fields = {}

            for j, record2 in enumerate(records[i + 1 :], start=i + 1):
                if record2["id"] in processed_ids:
                    continue

                similarity, fields = self.calculate_similarity(record1, record2)

                if similarity >= threshold:
                    group_records.append(record2["id"])
                    processed_ids.add(record2["id"])
                    # Store matching fields from first comparison
                    if not matching_fields:
                        matching_fields = fields

            # If we found duplicates, create a group
            if len(group_records) > 1:
                processed_ids.add(record1["id"])

                # Calculate average similarity for the group
                group_similarity = self._calculate_group_similarity(
                    [r for r in records if r["id"] in group_records]
                )

                # Store duplicate group in database
                duplicate_data = {
                    "table_name": table,
                    "record_ids": group_records,
                    "similarity_score": round(group_similarity, 2),
                    "matching_fields": matching_fields,
                    "status": "pending",
                }

                stored_group = self.repository.insert("duplicate_groups", duplicate_data)
                duplicate_groups.append(DuplicateGroup.from_dict(stored_group))

        return duplicate_groups

    def calculate_similarity(
        self, record1: Dict[str, Any], record2: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate similarity score between two records.

        Args:
            record1: First record
            record2: Second record

        Returns:
            Tuple of (similarity_score, matching_fields)
            similarity_score: Float between 0 and 100
            matching_fields: Dictionary of fields that matched
        """
        # Define fields to compare based on common ERP fields
        comparable_fields = ["name", "email", "phone", "sku"]

        field_scores = []
        matching_fields = {}

        for field in comparable_fields:
            if field not in record1 or field not in record2:
                continue

            value1 = record1[field]
            value2 = record2[field]

            # Skip if both values are None or empty
            if not value1 and not value2:
                continue

            # If one is None/empty and the other isn't, score is 0
            if not value1 or not value2:
                field_scores.append(0.0)
                continue

            # Calculate field-specific similarity
            if field == "email":
                score = self._compare_email(value1, value2)
            elif field == "phone":
                score = self._compare_phone(value1, value2)
            else:
                # Text field comparison using Levenshtein distance
                score = self._compare_text(value1, value2)

            field_scores.append(score)

            # Track which fields matched (>= 80% similarity)
            if score >= 80:
                matching_fields[field] = {
                    "value1": value1,
                    "value2": value2,
                    "similarity": round(score, 2),
                }

        # Calculate overall similarity as average of field scores
        if not field_scores:
            return 0.0, {}

        overall_similarity = sum(field_scores) / len(field_scores)
        return overall_similarity, matching_fields

    def _compare_text(self, text1: str, text2: str) -> float:
        """Compare two text strings using Levenshtein distance.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score between 0 and 100
        """
        # Normalize strings: lowercase and strip whitespace
        text1 = str(text1).lower().strip()
        text2 = str(text2).lower().strip()

        if text1 == text2:
            return 100.0

        # Calculate Levenshtein distance
        distance = Levenshtein.distance(text1, text2)
        max_length = max(len(text1), len(text2))

        if max_length == 0:
            return 100.0

        # Convert distance to similarity percentage
        similarity = (1 - distance / max_length) * 100
        return max(0.0, min(100.0, similarity))

    def _compare_email(self, email1: str, email2: str) -> float:
        """Compare two email addresses.

        Args:
            email1: First email address
            email2: Second email address

        Returns:
            Similarity score between 0 and 100
        """
        email1 = str(email1).lower().strip()
        email2 = str(email2).lower().strip()

        # Exact match
        if email1 == email2:
            return 100.0

        # Check if domains match
        if "@" in email1 and "@" in email2:
            domain1 = email1.split("@")[1]
            domain2 = email2.split("@")[1]

            if domain1 == domain2:
                # Same domain, compare local parts
                local1 = email1.split("@")[0]
                local2 = email2.split("@")[0]
                return self._compare_text(local1, local2) * 0.8 + 20
            else:
                # Different domains, use text comparison
                return self._compare_text(email1, email2) * 0.5

        # Fallback to text comparison
        return self._compare_text(email1, email2)

    def _compare_phone(self, phone1: str, phone2: str) -> float:
        """Compare two phone numbers with normalization.

        Args:
            phone1: First phone number
            phone2: Second phone number

        Returns:
            Similarity score between 0 and 100
        """
        # Normalize phone numbers: remove all non-digit characters
        normalized1 = self._normalize_phone(phone1)
        normalized2 = self._normalize_phone(phone2)

        if not normalized1 or not normalized2:
            return 0.0

        # Exact match after normalization
        if normalized1 == normalized2:
            return 100.0

        # Check if one is a substring of the other (e.g., with/without country code)
        if normalized1 in normalized2 or normalized2 in normalized1:
            return 90.0

        # Use text comparison on normalized numbers
        return self._compare_text(normalized1, normalized2)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number by removing non-digit characters.

        Args:
            phone: Phone number string

        Returns:
            Normalized phone number with only digits
        """
        return re.sub(r"\D", "", str(phone))

    def _calculate_group_similarity(self, records: List[Dict[str, Any]]) -> float:
        """Calculate average similarity for a group of records.

        Args:
            records: List of records in the group

        Returns:
            Average similarity score
        """
        if len(records) < 2:
            return 100.0

        similarities = []
        for i, record1 in enumerate(records):
            for record2 in records[i + 1 :]:
                similarity, _ = self.calculate_similarity(record1, record2)
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def get_duplicate_groups(
        self, table: Optional[str] = None, status: Optional[str] = None
    ) -> List[DuplicateGroup]:
        """Get all detected duplicate groups.

        Args:
            table: Optional table name filter
            status: Optional status filter

        Returns:
            List of duplicate groups
        """
        filters = {}
        if table:
            filters["table_name"] = table
        if status:
            filters["status"] = status

        groups = self.repository.query("duplicate_groups", filters)
        return [DuplicateGroup.from_dict(group) for group in groups]

    def merge_duplicates(
        self, group_id: str, keep_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge duplicate records into canonical record.

        Args:
            group_id: ID of the duplicate group to merge
            keep_values: Dictionary specifying which values to keep for conflicts

        Returns:
            Merged canonical record
        """
        # Get the duplicate group
        group_data = self.repository.get_by_id("duplicate_groups", group_id)
        if not group_data:
            raise ValueError(f"Duplicate group {group_id} not found")

        group = DuplicateGroup.from_dict(group_data)

        if len(group.record_ids) < 2:
            raise ValueError("Duplicate group must have at least 2 records")

        # Get all records in the group
        table = group.table_name
        records = [
            self.repository.get_by_id(table, record_id)
            for record_id in group.record_ids
        ]

        # Filter out any None records (in case some were deleted)
        records = [r for r in records if r is not None]

        if len(records) < 2:
            raise ValueError("Not enough records found to merge")

        # Create canonical record by merging all non-null values
        canonical = {}
        conflicts = {}

        # Get all unique fields across all records
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())

        # Merge fields
        for field in all_fields:
            # Skip metadata fields and id (we keep the canonical record's id)
            if field in ["id", "created_at", "updated_at"]:
                continue

            # Collect non-null values for this field
            values = [r.get(field) for r in records if r.get(field) is not None]

            if not values:
                canonical[field] = None
            elif len(set(str(v) for v in values)) == 1:
                # All values are the same
                canonical[field] = values[0]
            else:
                # Conflict: different non-null values
                if field in keep_values:
                    canonical[field] = keep_values[field]
                else:
                    # Store conflict for later resolution
                    conflicts[field] = values

        # If there are unresolved conflicts, raise an error
        if conflicts:
            raise ValueError(
                f"Merge conflicts detected in fields: {list(conflicts.keys())}. "
                f"Please provide keep_values for these fields."
            )

        # Keep the first record as canonical and update it
        canonical_id = group.record_ids[0]
        canonical["id"] = canonical_id

        # Update the canonical record
        updated_record = self.repository.update(table, canonical_id, canonical)

        # Update foreign key references for all duplicate records
        self._update_foreign_key_references(table, group.record_ids[1:], canonical_id)

        # Delete duplicate records (keep the first one)
        for record_id in group.record_ids[1:]:
            self.repository.delete(table, record_id)

        # Mark the duplicate group as resolved
        self.repository.update(
            "duplicate_groups", group_id, {"status": "resolved", "resolved_at": "NOW()"}
        )

        return updated_record

    def _update_foreign_key_references(
        self, table: str, old_ids: List[str], new_id: str
    ) -> None:
        """Update foreign key references after merge.

        Args:
            table: Table name of the merged records
            old_ids: List of old record IDs being deleted
            new_id: New canonical record ID
        """
        # Define foreign key relationships
        fk_relationships = {
            "customers": [("orders", "customer_id")],
            "products": [("order_items", "product_id")],
            "orders": [("order_items", "order_id")],
        }

        if table not in fk_relationships:
            return

        # Update each related table
        for related_table, fk_field in fk_relationships[table]:
            for old_id in old_ids:
                # Get all records referencing the old ID
                related_records = self.repository.query(
                    related_table, {fk_field: old_id}
                )

                # Update each record to point to the new ID
                for record in related_records:
                    self.repository.update(
                        related_table, record["id"], {fk_field: new_id}
                    )
