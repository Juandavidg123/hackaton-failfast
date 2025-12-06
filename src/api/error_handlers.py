"""Error handling utilities for Flask API."""

import traceback
from functools import wraps
from typing import Any, Callable, Dict, Tuple

from flask import jsonify
from postgrest.exceptions import APIError
from supabase.lib.client_options import ClientOptions

from api.validation import ValidationError


class DatabaseConnectionError(Exception):
    """Exception for database connection failures."""

    pass


class ConstraintViolationError(Exception):
    """Exception for database constraint violations."""

    def __init__(self, message: str, constraint: str = None):
        """Initialize constraint violation error.

        Args:
            message: Error message
            constraint: Name of the violated constraint
        """
        self.message = message
        self.constraint = constraint
        super().__init__(self.message)


def create_error_response(
    error_type: str,
    message: str,
    suggested_actions: list = None,
    details: Any = None,
    status_code: int = 500,
) -> Tuple[Dict[str, Any], int]:
    """Create standardized error response.

    Args:
        error_type: Type of error (validation_error, not_found, etc.)
        message: Human-readable error message
        suggested_actions: List of suggested actions to resolve the error
        details: Optional additional error details
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        "error": True,
        "error_type": error_type,
        "message": message,
        "suggested_actions": suggested_actions or [],
    }

    if details is not None:
        response["details"] = details

    return jsonify(response), status_code


def handle_api_errors(f: Callable) -> Callable:
    """Decorator to handle API errors and return standardized responses.

    This decorator catches common exceptions and converts them to
    standardized error responses following the design document format.

    Args:
        f: Function to wrap

    Returns:
        Wrapped function with error handling
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except ValidationError as e:
            # Validation errors (400)
            return create_error_response(
                error_type="validation_error",
                message=e.message,
                suggested_actions=["Check your input and try again"],
                details={"field": e.field} if e.field else None,
                status_code=400,
            )

        except ValueError as e:
            # Value errors from business logic
            error_msg = str(e)
            suggested_actions = ["Check your input and try again"]
            status_code = 400
            error_type = "validation_error"

            # Provide specific suggestions for common errors
            if "not found" in error_msg.lower():
                error_type = "not_found"
                status_code = 404
                suggested_actions = [
                    "Verify the ID exists",
                    "Check if the resource was already deleted",
                ]
            elif "conflict" in error_msg.lower():
                suggested_actions = [
                    "Resolve conflicts by providing keep_values",
                    "Review the conflicting data before merging",
                ]

            return create_error_response(
                error_type=error_type,
                message=error_msg,
                suggested_actions=suggested_actions,
                status_code=status_code,
            )

        except DatabaseConnectionError as e:
            # Database connection errors (503)
            return create_error_response(
                error_type="database_connection_error",
                message="Unable to connect to the database",
                suggested_actions=[
                    "Check database connection settings",
                    "Verify database is running",
                    "Try again in a few moments",
                ],
                details=str(e),
                status_code=503,
            )

        except ConstraintViolationError as e:
            # Database constraint violations (409)
            return create_error_response(
                error_type="constraint_violation",
                message=e.message,
                suggested_actions=[
                    "Check for duplicate values in unique fields",
                    "Verify foreign key references exist",
                    "Review the data constraints",
                ],
                details={"constraint": e.constraint} if e.constraint else None,
                status_code=409,
            )

        except APIError as e:
            # Supabase/PostgREST API errors
            error_msg = str(e)
            status_code = 500

            # Parse Supabase error for more specific handling
            if "duplicate key" in error_msg.lower():
                return create_error_response(
                    error_type="constraint_violation",
                    message="A record with this value already exists",
                    suggested_actions=[
                        "Use a different value for unique fields",
                        "Check if the record already exists",
                    ],
                    details=error_msg,
                    status_code=409,
                )

            elif "foreign key" in error_msg.lower():
                return create_error_response(
                    error_type="constraint_violation",
                    message="Referenced record does not exist",
                    suggested_actions=[
                        "Verify the referenced record exists",
                        "Create the referenced record first",
                    ],
                    details=error_msg,
                    status_code=409,
                )

            elif "not found" in error_msg.lower():
                return create_error_response(
                    error_type="not_found",
                    message="The requested resource was not found",
                    suggested_actions=["Check the ID and try again"],
                    status_code=404,
                )

            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                return create_error_response(
                    error_type="database_connection_error",
                    message="Database connection failed",
                    suggested_actions=[
                        "Check database connection",
                        "Try again in a few moments",
                    ],
                    details=error_msg,
                    status_code=503,
                )

            # Generic API error
            return create_error_response(
                error_type="database_error",
                message="A database error occurred",
                suggested_actions=[
                    "Check your request data",
                    "Try again later",
                    "Contact support if the problem persists",
                ],
                details=error_msg,
                status_code=status_code,
            )

        except Exception as e:
            # Unexpected errors (500)
            # Log the full traceback for debugging
            traceback.print_exc()

            return create_error_response(
                error_type="server_error",
                message="An unexpected error occurred",
                suggested_actions=[
                    "Try again later",
                    "Contact support if the problem persists",
                ],
                details=str(e),
                status_code=500,
            )

    return wrapper


def handle_database_operation(operation: Callable, *args, **kwargs) -> Any:
    """Execute a database operation with error handling.

    This function wraps database operations to catch connection errors
    and constraint violations, converting them to appropriate exceptions.

    Args:
        operation: Database operation function to execute
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the database operation

    Raises:
        DatabaseConnectionError: If database connection fails
        ConstraintViolationError: If a constraint is violated
    """
    try:
        return operation(*args, **kwargs)

    except APIError as e:
        error_msg = str(e)

        # Check for connection errors
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            raise DatabaseConnectionError(
                f"Database connection failed: {error_msg}"
            ) from e

        # Check for constraint violations
        if "duplicate key" in error_msg.lower():
            raise ConstraintViolationError(
                "A record with this value already exists",
                constraint="unique_constraint",
            ) from e

        if "foreign key" in error_msg.lower():
            raise ConstraintViolationError(
                "Referenced record does not exist",
                constraint="foreign_key_constraint",
            ) from e

        if "check constraint" in error_msg.lower():
            raise ConstraintViolationError(
                "Data violates a check constraint",
                constraint="check_constraint",
            ) from e

        # Re-raise as generic API error
        raise

    except ConnectionError as e:
        raise DatabaseConnectionError(
            f"Database connection failed: {str(e)}"
        ) from e

    except TimeoutError as e:
        raise DatabaseConnectionError(
            f"Database operation timed out: {str(e)}"
        ) from e
