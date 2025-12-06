"""Request validation for Flask API endpoints."""

from typing import Any, Dict, List, Optional

from flask import Request


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        """Initialize validation error.

        Args:
            message: Error message
            field: Optional field name that failed validation
        """
        self.message = message
        self.field = field
        super().__init__(self.message)


class RequestValidator:
    """Validator for API request data."""

    @staticmethod
    def validate_table_name(table: str) -> str:
        """Validate table name parameter.

        Args:
            table: Table name to validate

        Returns:
            Validated table name

        Raises:
            ValidationError: If table name is invalid
        """
        valid_tables = ["customers", "products", "orders", "order_items"]

        if not table:
            raise ValidationError("Table parameter is required", field="table")

        if table not in valid_tables:
            raise ValidationError(
                f"Invalid table: {table}. Must be one of: {', '.join(valid_tables)}",
                field="table",
            )

        return table

    @staticmethod
    def validate_status(status: str) -> str:
        """Validate status parameter.

        Args:
            status: Status to validate

        Returns:
            Validated status

        Raises:
            ValidationError: If status is invalid
        """
        valid_statuses = ["pending", "resolved"]

        if status not in valid_statuses:
            raise ValidationError(
                f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}",
                field="status",
            )

        return status

    @staticmethod
    def validate_inconsistency_type(inconsistency_type: str) -> str:
        """Validate inconsistency type parameter.

        Args:
            inconsistency_type: Type to validate

        Returns:
            Validated type

        Raises:
            ValidationError: If type is invalid
        """
        valid_types = ["referential", "calculation", "format", "business_rule"]

        if inconsistency_type not in valid_types:
            raise ValidationError(
                f"Invalid inconsistency type: {inconsistency_type}. "
                f"Must be one of: {', '.join(valid_types)}",
                field="type",
            )

        return inconsistency_type

    @staticmethod
    def validate_threshold(threshold: Any) -> int:
        """Validate similarity threshold parameter.

        Args:
            threshold: Threshold to validate

        Returns:
            Validated threshold as integer

        Raises:
            ValidationError: If threshold is invalid
        """
        if threshold is None:
            return 80  # Default threshold

        try:
            threshold_int = int(threshold)
        except (ValueError, TypeError):
            raise ValidationError(
                "Threshold must be an integer", field="threshold"
            )

        if not 0 <= threshold_int <= 100:
            raise ValidationError(
                "Threshold must be between 0 and 100", field="threshold"
            )

        return threshold_int

    @staticmethod
    def validate_merge_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate merge duplicate request body.

        Args:
            data: Request body data

        Returns:
            Validated data

        Raises:
            ValidationError: If request body is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        # keep_values is optional but must be a dict if provided
        keep_values = data.get("keep_values", {})
        if not isinstance(keep_values, dict):
            raise ValidationError(
                "keep_values must be an object", field="keep_values"
            )

        return data

    @staticmethod
    def validate_correction_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inconsistency fix request body.

        Args:
            data: Request body data

        Returns:
            Validated data

        Raises:
            ValidationError: If request body is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        correction = data.get("correction")
        if not correction:
            raise ValidationError(
                "Correction data is required", field="correction"
            )

        if not isinstance(correction, dict):
            raise ValidationError(
                "Correction must be an object", field="correction"
            )

        # If not deleting, must have field and value
        if not correction.get("delete_record"):
            if "field" not in correction:
                raise ValidationError(
                    "Correction must contain 'field' key", field="correction.field"
                )

            if "value" not in correction:
                raise ValidationError(
                    "Correction must contain 'value' key", field="correction.value"
                )

        return data

    @staticmethod
    def validate_detect_duplicates_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate duplicate detection request body.

        Args:
            data: Request body data

        Returns:
            Validated data

        Raises:
            ValidationError: If request body is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        # Validate table if provided
        if "table" in data and data["table"]:
            RequestValidator.validate_table_name(data["table"])

        # Validate threshold if provided
        if "threshold" in data:
            data["threshold"] = RequestValidator.validate_threshold(data["threshold"])

        return data

    @staticmethod
    def get_json_or_empty(request: Request) -> Dict[str, Any]:
        """Safely get JSON from request or return empty dict.

        Args:
            request: Flask request object

        Returns:
            JSON data or empty dict

        Raises:
            ValidationError: If JSON is malformed
        """
        if not request.data:
            return {}

        try:
            data = request.get_json(force=True)
            if data is None:
                return {}
            return data
        except Exception as e:
            raise ValidationError(f"Invalid JSON in request body: {str(e)}")
