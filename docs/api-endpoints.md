# ERP Voice Chat API Documentation

This document describes the REST API endpoints for the ERP Voice Chat System.

## Base URL

```
http://localhost:5000
```

## Health Check

### GET /health

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "erp-voice-chat-backend"
}
```

---

## ERP Data Query Endpoints

### GET /api/erp/query

Query ERP data with optional filters.

**Query Parameters:**
- `table` (required): Table name (`customers`, `products`, `orders`, `order_items`)
- Additional parameters are treated as filters

**Example Request:**
```bash
curl "http://localhost:5000/api/erp/query?table=customers&name=John"
```

**Response:**
```json
{
  "table": "customers",
  "count": 2,
  "records": [
    {
      "id": "uuid-1",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890"
    }
  ]
}
```

---

## Duplicate Detection Endpoints

### POST /api/duplicates/detect

Trigger duplicate detection analysis.

**Request Body:**
```json
{
  "table": "customers",  // Optional: specific table or all tables
  "threshold": 85        // Optional: similarity threshold (default: 80)
}
```

**Response:**
```json
{
  "message": "Duplicate detection completed",
  "tables_analyzed": ["customers"],
  "duplicate_groups_found": 2,
  "duplicate_groups": [
    {
      "id": "group-uuid",
      "table_name": "customers",
      "record_ids": ["uuid-1", "uuid-2"],
      "similarity_score": 85.5,
      "matching_fields": {
        "name": {
          "value1": "John Doe",
          "value2": "John D.",
          "similarity": 90
        }
      },
      "status": "pending",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### GET /api/duplicates

Get all detected duplicate groups.

**Query Parameters:**
- `table` (optional): Filter by table name
- `status` (optional): Filter by status (`pending`, `resolved`)

**Response:**
```json
{
  "count": 2,
  "duplicate_groups": [...]
}
```

### GET /api/duplicates/{group_id}

Get specific duplicate group details with full records.

**Response:**
```json
{
  "duplicate_group": {
    "id": "group-uuid",
    "table_name": "customers",
    "record_ids": ["uuid-1", "uuid-2"],
    "similarity_score": 85.5,
    "status": "pending"
  },
  "records": [
    {
      "id": "uuid-1",
      "name": "John Doe",
      "email": "john@example.com"
    },
    {
      "id": "uuid-2",
      "name": "John D.",
      "email": "john@example.com"
    }
  ]
}
```

### POST /api/duplicates/{group_id}/merge

Merge duplicate records.

**Request Body:**
```json
{
  "keep_values": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Response:**
```json
{
  "message": "Duplicates merged successfully",
  "merged_record": {
    "id": "uuid-1",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  }
}
```

---

## Inconsistency Detection Endpoints

### POST /api/inconsistencies/detect

Trigger inconsistency analysis.

**Response:**
```json
{
  "message": "Inconsistency detection completed",
  "total_inconsistencies": 5,
  "by_type": {
    "referential": 2,
    "calculation": 1,
    "format": 1,
    "business_rule": 1
  },
  "inconsistencies": [
    {
      "id": "inc-uuid",
      "type": "calculation",
      "table_name": "orders",
      "record_id": "order-uuid",
      "field_name": "total_amount",
      "description": "Order total mismatch: stored=100.00, calculated=150.00",
      "suggested_fix": {
        "action": "update_total",
        "field": "total_amount",
        "current_value": 100.0,
        "suggested_value": 150.0
      },
      "status": "pending",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### GET /api/inconsistencies

Get all detected inconsistencies.

**Query Parameters:**
- `type` (optional): Filter by type (`referential`, `calculation`, `format`, `business_rule`)
- `table` (optional): Filter by table name
- `status` (optional): Filter by status (`pending`, `resolved`)

**Response:**
```json
{
  "count": 5,
  "by_type": {
    "referential": 2,
    "calculation": 1
  },
  "inconsistencies": [...]
}
```

### GET /api/inconsistencies/{inconsistency_id}

Get specific inconsistency details with affected record.

**Response:**
```json
{
  "inconsistency": {
    "id": "inc-uuid",
    "type": "calculation",
    "table_name": "orders",
    "record_id": "order-uuid",
    "field_name": "total_amount",
    "description": "Order total mismatch",
    "suggested_fix": {...}
  },
  "affected_record": {
    "id": "order-uuid",
    "customer_id": "customer-uuid",
    "total_amount": 100.0
  }
}
```

### POST /api/inconsistencies/{inconsistency_id}/fix

Apply correction to inconsistency.

**Request Body:**
```json
{
  "correction": {
    "field": "total_amount",
    "value": 150.0
  }
}
```

Or to delete the record:
```json
{
  "correction": {
    "delete_record": true
  }
}
```

**Response:**
```json
{
  "message": "Inconsistency fixed successfully",
  "result": {
    "id": "order-uuid",
    "total_amount": 150.0,
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## Error Responses

All endpoints return standardized error responses:

```json
{
  "error": true,
  "error_type": "validation_error",
  "message": "Human-readable error message",
  "suggested_actions": [
    "Action 1 to resolve the error",
    "Action 2 to resolve the error"
  ],
  "details": "Additional technical details (optional)"
}
```

**Error Types:**
- `validation_error` (400): Invalid request parameters
- `not_found` (404): Resource not found
- `method_not_allowed` (405): HTTP method not allowed
- `server_error` (500): Internal server error

---

## Running the API

Start the Flask development server:

```bash
uv run python src/api/app.py
```

Or set a custom port:

```bash
FLASK_PORT=8000 uv run python src/api/app.py
```

The API will be available at `http://localhost:5000` (or your custom port).

---

## Testing

Run the API tests:

```bash
uv run pytest tests/test_api_routes.py -v
```

Run all tests:

```bash
uv run pytest tests/ -v
```
