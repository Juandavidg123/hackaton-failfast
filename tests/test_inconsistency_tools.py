"""Tests for inconsistency management tool functionality."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent import ERPVoiceAgent


@pytest.mark.asyncio
async def test_detect_inconsistencies_success():
    """Test successful inconsistency detection."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Inconsistency detection completed",
            "total_inconsistencies": 3,
            "by_type": {
                "referential": 1,
                "calculation": 1,
                "format": 1,
            },
            "inconsistencies": [
                {
                    "id": "inc-1",
                    "type": "referential",
                    "table_name": "orders",
                    "record_id": "ord-1",
                    "field_name": "customer_id",
                    "description": "Order references non-existent customer: cust-999",
                    "status": "pending",
                },
                {
                    "id": "inc-2",
                    "type": "calculation",
                    "table_name": "orders",
                    "record_id": "ord-2",
                    "field_name": "total_amount",
                    "description": "Order total mismatch: stored=100.00, calculated=95.50",
                    "status": "pending",
                },
                {
                    "id": "inc-3",
                    "type": "format",
                    "table_name": "customers",
                    "record_id": "cust-1",
                    "field_name": "email",
                    "description": "Invalid email format: invalid-email",
                    "status": "pending",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.detect_inconsistencies(None, None)

        # Verify response is in Spanish and contains expected data
        assert "Encontré 3 inconsistencias" in result or "Encontré 3 inconsistencia" in result
        assert "integridad referencial" in result
        assert "errores de cálculo" in result
        assert "formatos inválidos" in result


@pytest.mark.asyncio
async def test_detect_inconsistencies_no_issues():
    """Test inconsistency detection with no issues found."""
    agent = ERPVoiceAgent()

    # Mock response with no inconsistencies
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Inconsistency detection completed",
            "total_inconsistencies": 0,
            "by_type": {},
            "inconsistencies": [],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.detect_inconsistencies(None, None)

        # Verify response is in Spanish and indicates no inconsistencies
        assert "Excelente" in result or "No encontré" in result
        assert "inconsistencia" in result
        assert "orden" in result or "Todo está en orden" in result


@pytest.mark.asyncio
async def test_detect_inconsistencies_with_type_filter():
    """Test inconsistency detection with type filter."""
    agent = ERPVoiceAgent()

    # Mock response with all types
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Inconsistency detection completed",
            "total_inconsistencies": 3,
            "by_type": {
                "referential": 1,
                "calculation": 2,
            },
            "inconsistencies": [
                {
                    "id": "inc-1",
                    "type": "referential",
                    "table_name": "orders",
                    "record_id": "ord-1",
                    "field_name": "customer_id",
                    "description": "Order references non-existent customer",
                    "status": "pending",
                },
                {
                    "id": "inc-2",
                    "type": "calculation",
                    "table_name": "orders",
                    "record_id": "ord-2",
                    "field_name": "total_amount",
                    "description": "Order total mismatch",
                    "status": "pending",
                },
                {
                    "id": "inc-3",
                    "type": "calculation",
                    "table_name": "order_items",
                    "record_id": "item-1",
                    "field_name": "line_total",
                    "description": "Line total mismatch",
                    "status": "pending",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Filter for calculation type only
        result = await agent.detect_inconsistencies("calculation", None)

        # Verify response only includes calculation inconsistencies
        assert "2 inconsistencias" in result or "2 inconsistencia" in result
        assert "errores de cálculo" in result


@pytest.mark.asyncio
async def test_detect_inconsistencies_with_table_filter():
    """Test inconsistency detection with table filter."""
    agent = ERPVoiceAgent()

    # Mock response with multiple tables
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Inconsistency detection completed",
            "total_inconsistencies": 3,
            "by_type": {
                "calculation": 2,
                "format": 1,
            },
            "inconsistencies": [
                {
                    "id": "inc-1",
                    "type": "calculation",
                    "table_name": "orders",
                    "record_id": "ord-1",
                    "field_name": "total_amount",
                    "description": "Order total mismatch",
                    "status": "pending",
                },
                {
                    "id": "inc-2",
                    "type": "calculation",
                    "table_name": "order_items",
                    "record_id": "item-1",
                    "field_name": "line_total",
                    "description": "Line total mismatch",
                    "status": "pending",
                },
                {
                    "id": "inc-3",
                    "type": "format",
                    "table_name": "customers",
                    "record_id": "cust-1",
                    "field_name": "email",
                    "description": "Invalid email format",
                    "status": "pending",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Filter for orders table only
        result = await agent.detect_inconsistencies(None, "orders")

        # Verify response only includes orders table
        assert "1 inconsistencia" in result or "1 inconsistencias" in result
        assert "pedidos" in result


@pytest.mark.asyncio
async def test_detect_inconsistencies_connection_error():
    """Test inconsistency detection with connection error."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        result = await agent.detect_inconsistencies(None, None)

        # Verify error response is in Spanish with connection failure handling
        assert "puedo conectarme" in result or "conexión" in result
        assert "servidor" in result
        assert "reconectar" in result or "verifica" in result


@pytest.mark.asyncio
async def test_get_inconsistency_details_success():
    """Test getting inconsistency details successfully."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "inconsistency": {
                "id": "inc-1",
                "type": "calculation",
                "table_name": "orders",
                "record_id": "ord-1",
                "field_name": "total_amount",
                "description": "Order total mismatch: stored=100.00, calculated=95.50",
                "suggested_fix": {
                    "action": "update_total",
                    "field": "total_amount",
                    "current_value": 100.00,
                    "suggested_value": 95.50,
                },
                "status": "pending",
            },
            "affected_record": {
                "id": "ord-1",
                "customer_id": "cust-1",
                "order_date": "2024-01-15",
                "total_amount": 100.00,
                "status": "completed",
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_inconsistency_details("inc-1")

        # Verify response is in Spanish and contains expected data
        assert "Detalles de la inconsistencia" in result
        assert "error de cálculo" in result
        assert "pedidos" in result
        assert "100" in result
        assert "95.5" in result
        assert "monto total" in result


@pytest.mark.asyncio
async def test_get_inconsistency_details_referential():
    """Test getting referential integrity inconsistency details."""
    agent = ERPVoiceAgent()

    # Mock response for referential integrity issue
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "inconsistency": {
                "id": "inc-1",
                "type": "referential",
                "table_name": "orders",
                "record_id": "ord-1",
                "field_name": "customer_id",
                "description": "Order references non-existent customer: cust-999",
                "suggested_fix": {
                    "action": "delete_or_update",
                    "options": [
                        "Delete the orders record",
                        "Update customer_id to a valid customers ID",
                    ],
                },
                "status": "pending",
            },
            "affected_record": {
                "id": "ord-1",
                "customer_id": "cust-999",
                "order_date": "2024-01-15",
                "total_amount": 100.00,
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_inconsistency_details("inc-1")

        # Verify response mentions options
        assert "integridad referencial" in result
        assert "Opciones de corrección" in result


@pytest.mark.asyncio
async def test_get_inconsistency_details_format():
    """Test getting format inconsistency details."""
    agent = ERPVoiceAgent()

    # Mock response for format issue
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "inconsistency": {
                "id": "inc-1",
                "type": "format",
                "table_name": "customers",
                "record_id": "cust-1",
                "field_name": "email",
                "description": "Invalid email format: invalid-email",
                "suggested_fix": {
                    "action": "correct_format",
                    "field": "email",
                    "current_value": "invalid-email",
                    "message": "Update to a valid email format (e.g., user@example.com)",
                },
                "status": "pending",
            },
            "affected_record": {
                "id": "cust-1",
                "name": "Juan Pérez",
                "email": "invalid-email",
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_inconsistency_details("inc-1")

        # Verify response mentions format issue
        assert "formato inválido" in result
        assert "invalid-email" in result
        assert "Sugerencia" in result


@pytest.mark.asyncio
async def test_get_inconsistency_details_not_found():
    """Test getting inconsistency details for non-existent inconsistency."""
    agent = ERPVoiceAgent()

    # Mock 404 response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = '{"error": true}'
    mock_response.json = AsyncMock(
        return_value={
            "error": True,
            "message": "Inconsistencia no encontrada",
            "suggested_actions": ["Verifica el ID de la inconsistencia"],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_inconsistency_details("invalid-id")

        # Verify error response is in Spanish
        assert "Lo siento, ocurrió un problema" in result
        assert "no encontrada" in result


@pytest.mark.asyncio
async def test_fix_inconsistency_success():
    """Test successful inconsistency fix."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Inconsistency fixed successfully",
            "updated_record": {
                "id": "ord-1",
                "customer_id": "cust-1",
                "order_date": "2024-01-15",
                "total_amount": 95.50,
                "status": "completed",
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        correction_json = '{"field": "total_amount", "value": 95.50}'
        result = await agent.fix_inconsistency("inc-1", correction_json)

        # Verify response is in Spanish and indicates success
        assert "Excelente" in result or "exitosamente" in result
        assert "corregida" in result
        assert "monto total" in result
        assert "95.5" in result


@pytest.mark.asyncio
async def test_fix_inconsistency_delete_record():
    """Test fixing inconsistency by deleting record."""
    agent = ERPVoiceAgent()

    # Mock successful deletion response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "action": "deleted",
            "table": "orders",
            "record_id": "ord-1",
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        correction_json = '{"delete_record": true}'
        result = await agent.fix_inconsistency("inc-1", correction_json)

        # Verify response indicates deletion
        assert "Perfecto" in result
        assert "eliminado" in result
        assert "pedido" in result


@pytest.mark.asyncio
async def test_fix_inconsistency_invalid_json():
    """Test fixing inconsistency with invalid JSON."""
    agent = ERPVoiceAgent()

    result = await agent.fix_inconsistency("inc-1", "invalid json")

    # Verify error response about invalid JSON
    assert "Lo siento, ocurrió un problema" in result
    assert "formato" in result or "válido" in result


@pytest.mark.asyncio
async def test_fix_inconsistency_connection_error():
    """Test fixing inconsistency with connection error."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        correction_json = '{"field": "total_amount", "value": 95.50}'
        result = await agent.fix_inconsistency("inc-1", correction_json)

        # Verify error response is in Spanish with connection failure handling
        assert "puedo conectarme" in result or "conexión" in result
        assert "servidor" in result
        assert "reconectar" in result or "verifica" in result


@pytest.mark.asyncio
async def test_format_inconsistency_detection_response():
    """Test formatting of inconsistency detection response."""
    agent = ERPVoiceAgent()

    data = {
        "total_inconsistencies": 2,
        "by_type": {
            "calculation": 1,
            "format": 1,
        },
        "inconsistencies": [
            {
                "id": "inc-1",
                "type": "calculation",
                "table_name": "orders",
                "description": "Order total mismatch",
            },
            {
                "id": "inc-2",
                "type": "format",
                "table_name": "customers",
                "description": "Invalid email format",
            },
        ],
    }

    result = agent._format_inconsistency_detection_response(data)

    # Verify formatting
    assert "2 inconsistencias" in result or "2 inconsistencia" in result
    assert "errores de cálculo" in result
    assert "formatos inválidos" in result
    assert "pedidos" in result
    assert "clientes" in result


@pytest.mark.asyncio
async def test_format_inconsistency_details_response():
    """Test formatting of inconsistency details response."""
    agent = ERPVoiceAgent()

    data = {
        "inconsistency": {
            "type": "calculation",
            "table_name": "orders",
            "field_name": "total_amount",
            "description": "Order total mismatch: stored=100.00, calculated=95.50",
            "suggested_fix": {
                "action": "update_total",
                "field": "total_amount",
                "current_value": 100.00,
                "suggested_value": 95.50,
            },
        },
        "affected_record": {},
    }

    result = agent._format_inconsistency_details_response(data)

    # Verify formatting
    assert "error de cálculo" in result
    assert "pedidos" in result
    assert "monto total" in result
    assert "100" in result
    assert "95.5" in result
    assert "Quieres que aplique la corrección" in result


@pytest.mark.asyncio
async def test_format_fix_success_response_update():
    """Test formatting of successful fix response for field update."""
    agent = ERPVoiceAgent()

    data = {"updated_record": {}}
    correction_data = {"field": "total_amount", "value": 95.50}

    result = agent._format_fix_success_response(data, correction_data)

    # Verify formatting
    assert "Excelente" in result
    assert "corregida" in result
    assert "monto total" in result
    assert "95.5" in result


@pytest.mark.asyncio
async def test_format_fix_success_response_delete():
    """Test formatting of successful fix response for record deletion."""
    agent = ERPVoiceAgent()

    data = {"action": "deleted", "table": "orders", "record_id": "ord-1"}
    correction_data = {"delete_record": True}

    result = agent._format_fix_success_response(data, correction_data)

    # Verify formatting
    assert "Perfecto" in result
    assert "eliminado" in result
    assert "pedido" in result
