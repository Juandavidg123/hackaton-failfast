"""Flask API routes for ERP Voice Chat System."""

from typing import Any, Dict

from flask import Blueprint, jsonify, request

from api.error_handlers import handle_api_errors
from api.validation import RequestValidator, ValidationError
from config import Config
from models.data_models import DuplicateGroup, Inconsistency, InconsistencyType
from repositories.supabase_repository import SupabaseRepository
from services.duplicate_detection import DuplicateDetectionEngine
from services.inconsistency_analyzer import InconsistencyAnalyzer

# Initialize repository and services
supabase_url, supabase_key = Config.get_supabase_config()
repository = SupabaseRepository(supabase_url, supabase_key)
duplicate_engine = DuplicateDetectionEngine(
    repository, threshold=Config.DUPLICATE_SIMILARITY_THRESHOLD
)
inconsistency_analyzer = InconsistencyAnalyzer(repository)

# Create blueprints
erp_bp = Blueprint("erp", __name__)
duplicates_bp = Blueprint("duplicates", __name__)
inconsistencies_bp = Blueprint("inconsistencies", __name__)


# ============================================================================
# ERP Data Query Endpoints
# ============================================================================


@erp_bp.route("/query", methods=["GET"])
@handle_api_errors
def query_erp_data():
    """Query ERP data with filters.

    Query Parameters:
        table (str): Table name to query (customers, products, orders, order_items)
        filters (dict): Optional JSON filters to apply

    Returns:
        JSON response with matching records
    """
    # Validate table parameter
    table = request.args.get("table")
    table = RequestValidator.validate_table_name(table)

    # Parse filters from query string
    filters = {}
    for key, value in request.args.items():
        if key != "table":
            filters[key] = value

    # Query the data
    records = repository.query(table, filters if filters else None)

    return jsonify(
        {
            "table": table,
            "count": len(records),
            "records": records,
        }
    )


# ============================================================================
# Duplicate Detection Endpoints
# ============================================================================


@duplicates_bp.route("/detect", methods=["POST"])
@handle_api_errors
def detect_duplicates():
    """Trigger duplicate detection analysis.

    Request Body:
        table (str): Optional table name to analyze (default: all tables)
        threshold (int): Optional similarity threshold (default: 80)

    Returns:
        JSON response with detected duplicate groups
    """
    # Validate request body
    data = RequestValidator.get_json_or_empty(request)
    data = RequestValidator.validate_detect_duplicates_request(data)

    table = data.get("table")
    threshold = data.get("threshold")

    # Tables to analyze
    tables_to_analyze = (
        [table] if table else ["customers", "products", "orders"]
    )

    all_duplicate_groups = []

    for tbl in tables_to_analyze:
        duplicate_groups = duplicate_engine.detect_duplicates(tbl, threshold)
        all_duplicate_groups.extend(duplicate_groups)

    return jsonify(
        {
            "message": "Duplicate detection completed",
            "tables_analyzed": tables_to_analyze,
            "duplicate_groups_found": len(all_duplicate_groups),
            "duplicate_groups": [group.to_dict() for group in all_duplicate_groups],
        }
    )


@duplicates_bp.route("", methods=["GET"])
@handle_api_errors
def get_duplicates():
    """Get all detected duplicate groups.

    Query Parameters:
        table (str): Optional table name filter
        status (str): Optional status filter (pending, resolved)

    Returns:
        JSON response with duplicate groups
    """
    table = request.args.get("table")
    status = request.args.get("status")

    # Validate parameters if provided
    if table:
        table = RequestValidator.validate_table_name(table)
    if status:
        status = RequestValidator.validate_status(status)

    duplicate_groups = duplicate_engine.get_duplicate_groups(table, status)

    return jsonify(
        {
            "count": len(duplicate_groups),
            "duplicate_groups": [group.to_dict() for group in duplicate_groups],
        }
    )


@duplicates_bp.route("/<group_id>", methods=["GET"])
@handle_api_errors
def get_duplicate_details(group_id: str):
    """Get specific duplicate group details.

    Args:
        group_id: Duplicate group ID

    Returns:
        JSON response with duplicate group details including full records
    """
    # Get the duplicate group
    group_data = repository.get_by_id("duplicate_groups", group_id)

    if not group_data:
        raise ValueError(f"Duplicate group {group_id} not found")

    group = DuplicateGroup.from_dict(group_data)

    # Get full record details
    records = []
    for record_id in group.record_ids:
        record = repository.get_by_id(group.table_name, record_id)
        if record:
            records.append(record)

    return jsonify(
        {
            "duplicate_group": group.to_dict(),
            "records": records,
        }
    )


@duplicates_bp.route("/<group_id>/merge", methods=["POST"])
@handle_api_errors
def merge_duplicates(group_id: str):
    """Merge duplicate records.

    Args:
        group_id: Duplicate group ID

    Request Body:
        keep_values (dict): Dictionary specifying which values to keep for conflicts

    Returns:
        JSON response with merged record
    """
    # Validate request body
    data = RequestValidator.get_json_or_empty(request)
    data = RequestValidator.validate_merge_request(data)

    keep_values = data.get("keep_values", {})

    # Perform the merge with transaction support
    with repository.transaction():
        merged_record = duplicate_engine.merge_duplicates(group_id, keep_values)

    return jsonify(
        {
            "message": "Duplicates merged successfully",
            "merged_record": merged_record,
        }
    )


# ============================================================================
# Inconsistency Detection Endpoints
# ============================================================================


@inconsistencies_bp.route("/detect", methods=["POST"])
@handle_api_errors
def detect_inconsistencies():
    """Trigger inconsistency analysis.

    Returns:
        JSON response with detected inconsistencies
    """
    inconsistencies = inconsistency_analyzer.detect_inconsistencies()

    # Group by type for summary
    by_type = {}
    for inc in inconsistencies:
        type_name = inc.type.value
        if type_name not in by_type:
            by_type[type_name] = []
        by_type[type_name].append(inc.to_dict())

    return jsonify(
        {
            "message": "Inconsistency detection completed",
            "total_inconsistencies": len(inconsistencies),
            "by_type": {
                type_name: len(items) for type_name, items in by_type.items()
            },
            "inconsistencies": [inc.to_dict() for inc in inconsistencies],
        }
    )


@inconsistencies_bp.route("", methods=["GET"])
@handle_api_errors
def get_inconsistencies():
    """Get all detected inconsistencies.

    Query Parameters:
        type (str): Optional type filter (referential, calculation, format, business_rule)
        table (str): Optional table name filter
        status (str): Optional status filter (pending, resolved)

    Returns:
        JSON response with inconsistencies
    """
    inconsistency_type = request.args.get("type")
    table = request.args.get("table")
    status = request.args.get("status")

    # Validate parameters if provided
    if inconsistency_type:
        inconsistency_type = RequestValidator.validate_inconsistency_type(
            inconsistency_type
        )
    if table:
        table = RequestValidator.validate_table_name(table)
    if status:
        status = RequestValidator.validate_status(status)

    # Convert type string to enum if provided
    type_enum = None
    if inconsistency_type:
        type_enum = InconsistencyType(inconsistency_type)

    inconsistencies = inconsistency_analyzer.get_inconsistencies(
        type_enum, table, status
    )

    # Group by type for summary
    by_type = {}
    for inc in inconsistencies:
        type_name = inc.type.value
        if type_name not in by_type:
            by_type[type_name] = 0
        by_type[type_name] += 1

    return jsonify(
        {
            "count": len(inconsistencies),
            "by_type": by_type,
            "inconsistencies": [inc.to_dict() for inc in inconsistencies],
        }
    )


@inconsistencies_bp.route("/<inconsistency_id>", methods=["GET"])
@handle_api_errors
def get_inconsistency_details(inconsistency_id: str):
    """Get specific inconsistency details.

    Args:
        inconsistency_id: Inconsistency ID

    Returns:
        JSON response with inconsistency details including affected record
    """
    # Get the inconsistency
    inconsistency_data = repository.get_by_id("inconsistencies", inconsistency_id)

    if not inconsistency_data:
        raise ValueError(f"Inconsistency {inconsistency_id} not found")

    inconsistency = Inconsistency.from_dict(inconsistency_data)

    # Get the affected record
    affected_record = repository.get_by_id(
        inconsistency.table_name, inconsistency.record_id
    )

    return jsonify(
        {
            "inconsistency": inconsistency.to_dict(),
            "affected_record": affected_record,
        }
    )


@inconsistencies_bp.route("/<inconsistency_id>/fix", methods=["POST"])
@handle_api_errors
def fix_inconsistency(inconsistency_id: str):
    """Apply correction to inconsistency.

    Args:
        inconsistency_id: Inconsistency ID

    Request Body:
        correction (dict): Correction data with keys:
            - field: Field name to update
            - value: New value for the field
            - delete_record: (optional) If True, delete the record instead

    Returns:
        JSON response with updated record(s)
    """
    # Validate request body
    data = RequestValidator.get_json_or_empty(request)
    data = RequestValidator.validate_correction_request(data)

    correction = data.get("correction", {})

    # Apply the correction with transaction support
    with repository.transaction():
        result = inconsistency_analyzer.fix_inconsistency(inconsistency_id, correction)

    return jsonify(
        {
            "message": "Inconsistency fixed successfully",
            "result": result,
        }
    )
