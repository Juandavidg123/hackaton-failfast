"""Tests for ERP query tool functionality."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent import ERPVoiceAgent


@pytest.mark.asyncio
async def test_query_erp_data_success():
    """Test successful ERP data query."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "table": "customers",
            "count": 2,
            "records": [
                {
                    "id": "1",
                    "name": "Juan Pérez",
                    "email": "juan@example.com",
                    "phone": "+34123456789",
                },
                {
                    "id": "2",
                    "name": "María García",
                    "email": "maria@example.com",
                    "phone": "+34987654321",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.query_erp_data("customers", None)

        # Verify response is in Spanish and contains expected data
        assert "Encontré 2 registros en clientes" in result
        assert "Juan Pérez" in result
        assert "María García" in result


@pytest.mark.asyncio
async def test_query_erp_data_with_filters():
    """Test ERP data query with filters."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "table": "products",
            "count": 1,
            "records": [
                {
                    "id": "1",
                    "name": "Laptop",
                    "sku": "LAP-001",
                    "price": 999.99,
                    "inventory_count": 50,
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.query_erp_data("products", "name=Laptop")

        # Verify response is in Spanish and contains expected data
        assert "Encontré 1 registro en productos" in result
        assert "Laptop" in result
        assert "LAP-001" in result


@pytest.mark.asyncio
async def test_query_erp_data_no_results():
    """Test ERP data query with no results."""
    agent = ERPVoiceAgent()

    # Mock empty response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "table": "customers",
            "count": 0,
            "records": [],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.query_erp_data("customers", "name=NoExiste")

        # Verify response is in Spanish and indicates no results
        assert "No encontré ningún" in result
        assert "clientes" in result


@pytest.mark.asyncio
async def test_query_erp_data_connection_error():
    """Test ERP data query with connection error."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        result = await agent.query_erp_data("customers", None)

        # Verify error response is in Spanish with connection failure handling
        assert "puedo conectarme" in result or "conexión" in result
        assert "servidor" in result
        assert "reconectar" in result or "verifica" in result


@pytest.mark.asyncio
async def test_query_erp_data_timeout():
    """Test ERP data query with timeout."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = await agent.query_erp_data("customers", None)

        # Verify error response is in Spanish
        assert "tardando demasiado" in result or "Lo siento, ocurrió un problema" in result


@pytest.mark.asyncio
async def test_query_erp_data_api_error():
    """Test ERP data query with API error response."""
    agent = ERPVoiceAgent()

    # Mock error response
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": true}'
    mock_response.json = AsyncMock(
        return_value={
            "error": True,
            "message": "Tabla inválida",
            "suggested_actions": ["Verifica el nombre de la tabla"],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.query_erp_data("invalid_table", None)

        # Verify error response is in Spanish
        assert "Lo siento, ocurrió un problema" in result
        assert "Tabla inválida" in result


@pytest.mark.asyncio
async def test_format_customer():
    """Test customer record formatting."""
    agent = ERPVoiceAgent()

    customer = {
        "name": "Juan Pérez",
        "email": "juan@example.com",
        "phone": "+34123456789",
    }

    result = agent._format_customer(1, customer)

    assert "Cliente 1" in result
    assert "Juan Pérez" in result
    assert "juan@example.com" in result
    assert "+34123456789" in result


@pytest.mark.asyncio
async def test_format_product():
    """Test product record formatting."""
    agent = ERPVoiceAgent()

    product = {
        "name": "Laptop",
        "sku": "LAP-001",
        "price": 999.99,
        "inventory_count": 50,
    }

    result = agent._format_product(1, product)

    assert "Producto 1" in result
    assert "Laptop" in result
    assert "LAP-001" in result
    assert "999.99" in result
    assert "50" in result


@pytest.mark.asyncio
async def test_format_order():
    """Test order record formatting."""
    agent = ERPVoiceAgent()

    order = {
        "order_date": "2024-01-15",
        "total_amount": 1500.00,
        "status": "pending",
    }

    result = agent._format_order(1, order)

    assert "Pedido 1" in result
    assert "2024-01-15" in result
    assert "1500.0" in result
    assert "pendiente" in result


@pytest.mark.asyncio
async def test_format_error_response():
    """Test error response formatting."""
    agent = ERPVoiceAgent()

    result = agent._format_error_response(
        "Error de conexión",
        ["Verifica la red", "Intenta nuevamente"],
    )

    assert "Lo siento, ocurrió un problema" in result
    assert "Error de conexión" in result
    assert "Verifica la red" in result
    assert "Intenta nuevamente" in result
