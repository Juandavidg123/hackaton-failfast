"""Inconsistency analyzer for ERP data quality."""

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional

from models.data_models import Inconsistency, InconsistencyType
from repositories.supabase_repository import SupabaseRepository


class InconsistencyAnalyzer:
    """Analyzer for detecting data inconsistencies in ERP database."""

    def __init__(self, repository: SupabaseRepository):
        """Initialize inconsistency analyzer.

        Args:
            repository: Supabase repository for database access
        """
        self.repository = repository

    def detect_inconsistencies(self) -> List[Inconsistency]:
        """Detect all types of inconsistencies.

        Returns:
            List of detected inconsistencies
        """
        inconsistencies = []

        # Run all inconsistency checks
        inconsistencies.extend(self.check_referential_integrity())
        inconsistencies.extend(self.check_calculations())
        inconsistencies.extend(self.check_formats())
        inconsistencies.extend(self.check_business_rules())

        return inconsistencies

    def check_referential_integrity(self) -> List[Inconsistency]:
        """Check foreign key constraints and referential integrity.

        Returns:
            List of referential integrity inconsistencies
        """
        inconsistencies = []

        # Define foreign key relationships to check
        fk_checks = [
            {
                "table": "orders",
                "fk_field": "customer_id",
                "referenced_table": "customers",
                "description_template": "Order references non-existent customer",
            },
            {
                "table": "order_items",
                "fk_field": "order_id",
                "referenced_table": "orders",
                "description_template": "Order item references non-existent order",
            },
            {
                "table": "order_items",
                "fk_field": "product_id",
                "referenced_table": "products",
                "description_template": "Order item references non-existent product",
            },
        ]

        for check in fk_checks:
            # Get all records from the table
            records = self.repository.get_all(check["table"])

            for record in records:
                fk_value = record.get(check["fk_field"])

                # Skip if foreign key is null (allowed in some cases)
                if fk_value is None:
                    continue

                # Check if referenced record exists
                referenced_record = self.repository.get_by_id(
                    check["referenced_table"], fk_value
                )

                if referenced_record is None:
                    # Create inconsistency record
                    inconsistency_data = {
                        "type": InconsistencyType.REFERENTIAL.value,
                        "table_name": check["table"],
                        "record_id": record["id"],
                        "field_name": check["fk_field"],
                        "description": f"{check['description_template']}: {fk_value}",
                        "suggested_fix": {
                            "action": "delete_or_update",
                            "options": [
                                f"Delete the {check['table']} record",
                                f"Update {check['fk_field']} to a valid {check['referenced_table']} ID",
                            ],
                        },
                        "status": "pending",
                    }

                    stored = self.repository.insert("inconsistencies", inconsistency_data)
                    inconsistencies.append(Inconsistency.from_dict(stored))

        return inconsistencies

    def check_calculations(self) -> List[Inconsistency]:
        """Check computed totals and calculated values.

        Returns:
            List of calculation inconsistencies
        """
        inconsistencies = []

        # Check order totals match sum of order items
        orders = self.repository.get_all("orders")

        for order in orders:
            order_id = order["id"]
            stored_total = Decimal(str(order["total_amount"]))

            # Get all order items for this order
            order_items = self.repository.query("order_items", {"order_id": order_id})

            # Calculate actual total from order items
            calculated_total = Decimal("0")
            for item in order_items:
                calculated_total += Decimal(str(item["line_total"]))

            # Check if totals match (allow small rounding differences)
            if abs(stored_total - calculated_total) > Decimal("0.01"):
                inconsistency_data = {
                    "type": InconsistencyType.CALCULATION.value,
                    "table_name": "orders",
                    "record_id": order_id,
                    "field_name": "total_amount",
                    "description": (
                        f"Order total mismatch: stored={stored_total}, "
                        f"calculated={calculated_total}"
                    ),
                    "suggested_fix": {
                        "action": "update_total",
                        "field": "total_amount",
                        "current_value": float(stored_total),
                        "suggested_value": float(calculated_total),
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        # Check order item line totals
        order_items = self.repository.get_all("order_items")

        for item in order_items:
            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["unit_price"]))
            stored_line_total = Decimal(str(item["line_total"]))

            calculated_line_total = quantity * unit_price

            # Check if line totals match
            if abs(stored_line_total - calculated_line_total) > Decimal("0.01"):
                inconsistency_data = {
                    "type": InconsistencyType.CALCULATION.value,
                    "table_name": "order_items",
                    "record_id": item["id"],
                    "field_name": "line_total",
                    "description": (
                        f"Line total mismatch: stored={stored_line_total}, "
                        f"calculated={calculated_line_total} "
                        f"(quantity={quantity} × unit_price={unit_price})"
                    ),
                    "suggested_fix": {
                        "action": "update_line_total",
                        "field": "line_total",
                        "current_value": float(stored_line_total),
                        "suggested_value": float(calculated_line_total),
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        return inconsistencies

    def check_formats(self) -> List[Inconsistency]:
        """Validate data formats (email, phone, etc.).

        Returns:
            List of format inconsistencies
        """
        inconsistencies = []

        # Check customer email formats
        customers = self.repository.get_all("customers")

        for customer in customers:
            email = customer.get("email")

            # Skip if email is null
            if email is None:
                continue

            # Validate email format
            if not self._is_valid_email(email):
                inconsistency_data = {
                    "type": InconsistencyType.FORMAT.value,
                    "table_name": "customers",
                    "record_id": customer["id"],
                    "field_name": "email",
                    "description": f"Invalid email format: {email}",
                    "suggested_fix": {
                        "action": "correct_format",
                        "field": "email",
                        "current_value": email,
                        "message": "Update to a valid email format (e.g., user@example.com)",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

            # Validate phone format
            phone = customer.get("phone")
            if phone is not None and not self._is_valid_phone(phone):
                inconsistency_data = {
                    "type": InconsistencyType.FORMAT.value,
                    "table_name": "customers",
                    "record_id": customer["id"],
                    "field_name": "phone",
                    "description": f"Invalid phone format: {phone}",
                    "suggested_fix": {
                        "action": "correct_format",
                        "field": "phone",
                        "current_value": phone,
                        "message": "Update to a valid phone format",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        return inconsistencies

    def check_business_rules(self) -> List[Inconsistency]:
        """Validate business constraints and rules.

        Returns:
            List of business rule inconsistencies
        """
        inconsistencies = []

        # Check for negative inventory
        products = self.repository.get_all("products")

        for product in products:
            inventory_count = product.get("inventory_count", 0)

            if inventory_count < 0:
                inconsistency_data = {
                    "type": InconsistencyType.BUSINESS_RULE.value,
                    "table_name": "products",
                    "record_id": product["id"],
                    "field_name": "inventory_count",
                    "description": f"Negative inventory count: {inventory_count}",
                    "suggested_fix": {
                        "action": "correct_value",
                        "field": "inventory_count",
                        "current_value": inventory_count,
                        "suggested_value": 0,
                        "message": "Inventory count cannot be negative",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

            # Check for negative or zero prices
            price = Decimal(str(product.get("price", 0)))
            if price <= 0:
                inconsistency_data = {
                    "type": InconsistencyType.BUSINESS_RULE.value,
                    "table_name": "products",
                    "record_id": product["id"],
                    "field_name": "price",
                    "description": f"Invalid product price: {price}",
                    "suggested_fix": {
                        "action": "correct_value",
                        "field": "price",
                        "current_value": float(price),
                        "message": "Product price must be greater than zero",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        # Check for future order dates
        orders = self.repository.get_all("orders")

        for order in orders:
            order_date = order.get("order_date")

            if order_date is None:
                continue

            # Parse order date if it's a string
            if isinstance(order_date, str):
                from datetime import datetime

                order_date = datetime.fromisoformat(order_date.replace("Z", "+00:00"))

            # Check if order date is in the future
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            if order_date > now:
                inconsistency_data = {
                    "type": InconsistencyType.BUSINESS_RULE.value,
                    "table_name": "orders",
                    "record_id": order["id"],
                    "field_name": "order_date",
                    "description": f"Future order date: {order_date}",
                    "suggested_fix": {
                        "action": "correct_value",
                        "field": "order_date",
                        "current_value": order_date.isoformat(),
                        "suggested_value": now.isoformat(),
                        "message": "Order date cannot be in the future",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        # Check for negative quantities in order items
        order_items = self.repository.get_all("order_items")

        for item in order_items:
            quantity = item.get("quantity", 0)

            if quantity <= 0:
                inconsistency_data = {
                    "type": InconsistencyType.BUSINESS_RULE.value,
                    "table_name": "order_items",
                    "record_id": item["id"],
                    "field_name": "quantity",
                    "description": f"Invalid quantity: {quantity}",
                    "suggested_fix": {
                        "action": "correct_value",
                        "field": "quantity",
                        "current_value": quantity,
                        "message": "Quantity must be greater than zero",
                    },
                    "status": "pending",
                }

                stored = self.repository.insert("inconsistencies", inconsistency_data)
                inconsistencies.append(Inconsistency.from_dict(stored))

        return inconsistencies

    def get_inconsistencies(
        self,
        inconsistency_type: Optional[InconsistencyType] = None,
        table: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Inconsistency]:
        """Get detected inconsistencies with optional filters.

        Args:
            inconsistency_type: Optional type filter
            table: Optional table name filter
            status: Optional status filter

        Returns:
            List of inconsistencies
        """
        filters = {}
        if inconsistency_type:
            filters["type"] = inconsistency_type.value
        if table:
            filters["table_name"] = table
        if status:
            filters["status"] = status

        inconsistencies_data = self.repository.query("inconsistencies", filters)
        return [Inconsistency.from_dict(data) for data in inconsistencies_data]

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if email format is valid
        """
        # Basic email validation pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone format.

        Args:
            phone: Phone number to validate

        Returns:
            True if phone format is valid
        """
        # Remove common formatting characters
        cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)

        # Check if it contains only digits and has reasonable length
        return cleaned.isdigit() and 7 <= len(cleaned) <= 15

    def fix_inconsistency(
        self, inconsistency_id: str, correction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply correction to an inconsistency.

        This method:
        1. Validates the correction data
        2. Applies the correction to the affected record
        3. Updates dependent data if needed for referential integrity
        4. Marks the inconsistency as resolved
        5. Verifies the inconsistency is actually resolved

        Args:
            inconsistency_id: ID of the inconsistency to fix
            correction: Dictionary containing correction data with keys:
                - field: Field name to update
                - value: New value for the field
                - delete_record: (optional) If True, delete the record instead

        Returns:
            Dictionary containing the updated record(s)

        Raises:
            ValueError: If inconsistency not found or correction is invalid
        """
        # Get the inconsistency record
        inconsistency_data = self.repository.get_by_id(
            "inconsistencies", inconsistency_id
        )

        if inconsistency_data is None:
            raise ValueError(f"Inconsistency {inconsistency_id} not found")

        inconsistency = Inconsistency.from_dict(inconsistency_data)

        # Validate correction data
        if "delete_record" in correction and correction["delete_record"]:
            # Handle record deletion (for referential integrity issues)
            result = self._handle_record_deletion(inconsistency)
        else:
            # Handle field update
            if "field" not in correction or "value" not in correction:
                raise ValueError(
                    "Correction must contain 'field' and 'value' keys, "
                    "or 'delete_record': True"
                )

            result = self._handle_field_update(inconsistency, correction)

        # Update dependent data if needed for referential integrity
        if inconsistency.type == InconsistencyType.CALCULATION:
            self._update_dependent_calculations(inconsistency, correction)

        # Mark inconsistency as resolved
        from datetime import datetime, timezone

        self.repository.update(
            "inconsistencies",
            inconsistency_id,
            {"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat()},
        )

        # Verify the inconsistency is resolved by re-running detection
        self._verify_inconsistency_resolved(inconsistency)

        return result

    def _handle_record_deletion(self, inconsistency: Inconsistency) -> Dict[str, Any]:
        """Handle deletion of a record to fix inconsistency.

        Args:
            inconsistency: The inconsistency to fix

        Returns:
            Dictionary with deletion result
        """
        # Delete the record
        success = self.repository.delete(
            inconsistency.table_name, inconsistency.record_id
        )

        if not success:
            raise ValueError(
                f"Failed to delete record {inconsistency.record_id} "
                f"from {inconsistency.table_name}"
            )

        return {
            "action": "deleted",
            "table": inconsistency.table_name,
            "record_id": inconsistency.record_id,
        }

    def _handle_field_update(
        self, inconsistency: Inconsistency, correction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle updating a field to fix inconsistency.

        Args:
            inconsistency: The inconsistency to fix
            correction: Correction data with field and value

        Returns:
            Updated record
        """
        field = correction["field"]
        value = correction["value"]

        # Validate the field matches the inconsistency
        if (
            inconsistency.field_name
            and field != inconsistency.field_name
        ):
            raise ValueError(
                f"Correction field '{field}' does not match "
                f"inconsistency field '{inconsistency.field_name}'"
            )

        # Apply the correction
        update_data = {field: value}

        # For calculation inconsistencies, we may need to update timestamps
        from datetime import datetime, timezone

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated_record = self.repository.update(
            inconsistency.table_name, inconsistency.record_id, update_data
        )

        return updated_record

    def _update_dependent_calculations(
        self, inconsistency: Inconsistency, correction: Dict[str, Any]
    ) -> None:
        """Update dependent calculations to maintain referential integrity.

        For example, if we fix an order item line total, we should also
        update the order total.

        Args:
            inconsistency: The inconsistency being fixed
            correction: Correction data
        """
        # If we're fixing an order item line total, update the order total
        if (
            inconsistency.table_name == "order_items"
            and inconsistency.field_name == "line_total"
        ):
            # Get the order item to find the order_id
            order_item = self.repository.get_by_id(
                "order_items", inconsistency.record_id
            )

            if order_item and order_item.get("order_id"):
                order_id = order_item["order_id"]

                # Recalculate order total from all order items
                order_items = self.repository.query(
                    "order_items", {"order_id": order_id}
                )

                total = Decimal("0")
                for item in order_items:
                    # Use the corrected value if this is the item we just fixed
                    if item["id"] == inconsistency.record_id:
                        total += Decimal(str(correction["value"]))
                    else:
                        total += Decimal(str(item["line_total"]))

                # Update the order total
                from datetime import datetime, timezone

                self.repository.update(
                    "orders",
                    order_id,
                    {
                        "total_amount": float(total),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

        # If we're fixing an order total directly, no dependent updates needed
        # (the order items are the source of truth)

    def _verify_inconsistency_resolved(self, inconsistency: Inconsistency) -> None:
        """Verify that the inconsistency is actually resolved.

        Re-runs the appropriate detection method and checks if the same
        inconsistency still exists.

        Args:
            inconsistency: The inconsistency that was fixed

        Raises:
            ValueError: If the inconsistency still exists after correction
        """
        # Re-run the appropriate check based on inconsistency type
        if inconsistency.type == InconsistencyType.REFERENTIAL:
            new_inconsistencies = self.check_referential_integrity()
        elif inconsistency.type == InconsistencyType.CALCULATION:
            new_inconsistencies = self.check_calculations()
        elif inconsistency.type == InconsistencyType.FORMAT:
            new_inconsistencies = self.check_formats()
        elif inconsistency.type == InconsistencyType.BUSINESS_RULE:
            new_inconsistencies = self.check_business_rules()
        else:
            # Unknown type, skip verification
            return

        # Check if the same record/field combination still has an inconsistency
        for new_inc in new_inconsistencies:
            if (
                new_inc.table_name == inconsistency.table_name
                and new_inc.record_id == inconsistency.record_id
                and new_inc.field_name == inconsistency.field_name
            ):
                raise ValueError(
                    f"Inconsistency still exists after correction: {new_inc.description}"
                )
