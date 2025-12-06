"""Tests for duplicate management tool functionality."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent import ERPVoiceAgent


@pytest.mark.asyncio
async def test_detect_duplicates_success():
    """Test successful duplicate detection."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Duplicate detection completed",
            "tables_analyzed": ["customers"],
            "duplicate_groups_found": 2,
            "duplicate_groups": [
                {
                    "id": "dup-1",
                    "table_name": "customers",
                    "record_ids": ["rec-1", "rec-2"],
                    "similarity_score": 85.5,
                    "matching_fields": {"name": True, "email": True},
                    "status": "pending",
                },
                {
                    "id": "dup-2",
                    "table_name": "customers",
                    "record_ids": ["rec-3", "rec-4"],
                    "similarity_score": 92.0,
                    "matching_fields": {"name": True, "phone": True},
                    "status": "pending",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.detect_duplicates("customers", None)

        # Verify response is in Spanish and contains expected data
        assert "Encontré 2 grupos de duplicados" in result
        assert "clientes" in result
        assert "86" in result or "85" in result  # Similarity percentage (rounded)
        assert "92" in result
        assert "nombre" in result  # Translated field name
        assert "correo electrónico" in result
        assert "teléfono" in result


@pytest.mark.asyncio
async def test_detect_duplicates_no_duplicates():
    """Test duplicate detection with no duplicates found."""
    agent = ERPVoiceAgent()

    # Mock response with no duplicates
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Duplicate detection completed",
            "tables_analyzed": ["products"],
            "duplicate_groups_found": 0,
            "duplicate_groups": [],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.detect_duplicates("products", None)

        # Verify response is in Spanish and indicates no duplicates
        assert "No encontré duplicados" in result
        assert "productos" in result
        assert "limpios" in result


@pytest.mark.asyncio
async def test_detect_duplicates_all_tables():
    """Test duplicate detection across all tables."""
    agent = ERPVoiceAgent()

    # Mock response for all tables
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Duplicate detection completed",
            "tables_analyzed": ["customers", "products", "orders"],
            "duplicate_groups_found": 1,
            "duplicate_groups": [
                {
                    "id": "dup-1",
                    "table_name": "orders",
                    "record_ids": ["ord-1", "ord-2"],
                    "similarity_score": 88.0,
                    "matching_fields": {"order_date": True, "total_amount": True},
                    "status": "pending",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.detect_duplicates(None, None)

        # Verify response mentions all tables
        assert "clientes" in result
        assert "productos" in result
        assert "pedidos" in result


@pytest.mark.asyncio
async def test_detect_duplicates_connection_error():
    """Test duplicate detection with connection error."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        result = await agent.detect_duplicates("customers", None)

        # Verify error response is in Spanish with connection failure handling
        assert "puedo conectarme" in result or "conexión" in result
        assert "servidor" in result
        assert "reconectar" in result or "verifica" in result


@pytest.mark.asyncio
async def test_get_duplicate_details_success():
    """Test getting duplicate details successfully."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "duplicate_group": {
                "id": "dup-1",
                "table_name": "customers",
                "record_ids": ["rec-1", "rec-2"],
                "similarity_score": 85.5,
                "matching_fields": {"name": True, "email": True},
                "status": "pending",
            },
            "records": [
                {
                    "id": "rec-1",
                    "name": "Juan Pérez",
                    "email": "juan@example.com",
                    "phone": "+34123456789",
                },
                {
                    "id": "rec-2",
                    "name": "Juan Perez",
                    "email": "juan@example.com",
                    "phone": "+34987654321",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_duplicate_details("dup-1")

        # Verify response is in Spanish and contains expected data
        assert "Detalles del grupo de duplicados" in result
        assert "clientes" in result
        assert "86" in result or "85" in result  # Similarity percentage (rounded)
        assert "Juan Pérez" in result
        assert "Juan Perez" in result
        assert "nombre" in result
        assert "correo electrónico" in result


@pytest.mark.asyncio
async def test_get_duplicate_details_with_conflicts():
    """Test getting duplicate details with conflicting fields."""
    agent = ERPVoiceAgent()

    # Mock response with conflicting records
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "duplicate_group": {
                "id": "dup-1",
                "table_name": "customers",
                "record_ids": ["rec-1", "rec-2"],
                "similarity_score": 85.5,
                "matching_fields": {"name": True},
                "status": "pending",
            },
            "records": [
                {
                    "id": "rec-1",
                    "name": "Juan Pérez",
                    "email": "juan@example.com",
                    "phone": "+34123456789",
                },
                {
                    "id": "rec-2",
                    "name": "Juan Pérez",
                    "email": "juan.perez@example.com",
                    "phone": "+34987654321",
                },
            ],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_duplicate_details("dup-1")

        # Verify response mentions conflicts
        assert "conflictos" in result
        assert "correo electrónico" in result or "teléfono" in result


@pytest.mark.asyncio
async def test_get_duplicate_details_not_found():
    """Test getting duplicate details for non-existent group."""
    agent = ERPVoiceAgent()

    # Mock 404 response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = '{"error": true}'
    mock_response.json = AsyncMock(
        return_value={
            "error": True,
            "message": "Grupo de duplicados no encontrado",
            "suggested_actions": ["Verifica el ID del grupo"],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await agent.get_duplicate_details("invalid-id")

        # Verify error response is in Spanish
        assert "Lo siento, ocurrió un problema" in result
        assert "no encontrado" in result


@pytest.mark.asyncio
async def test_merge_duplicates_success():
    """Test successful duplicate merge."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Duplicates merged successfully",
            "merged_record": {
                "id": "rec-1",
                "table_name": "customers",
                "name": "Juan Pérez",
                "email": "juan@example.com",
                "phone": "+34123456789",
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.merge_duplicates("dup-1", None)

        # Verify response is in Spanish and indicates success
        assert "Perfecto" in result or "exitosamente" in result
        assert "fusionaron" in result
        assert "cliente" in result


@pytest.mark.asyncio
async def test_merge_duplicates_with_keep_values():
    """Test duplicate merge with conflict resolution."""
    agent = ERPVoiceAgent()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={
            "message": "Duplicates merged successfully",
            "merged_record": {
                "id": "rec-1",
                "table_name": "customers",
                "name": "Juan Pérez",
                "email": "juan@example.com",
                "phone": "+34123456789",
            },
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        keep_values_json = '{"email": "juan@example.com", "phone": "+34123456789"}'
        result = await agent.merge_duplicates("dup-1", keep_values_json)

        # Verify response is in Spanish and indicates success
        assert "fusionaron" in result
        assert "exitosamente" in result


@pytest.mark.asyncio
async def test_merge_duplicates_conflict_error():
    """Test duplicate merge with unresolved conflicts."""
    agent = ERPVoiceAgent()

    # Mock conflict error response
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": true}'
    mock_response.json = AsyncMock(
        return_value={
            "error": True,
            "message": "Merge conflict: multiple values for field",
            "conflicts": {
                "email": ["juan@example.com", "juan.perez@example.com"],
                "phone": ["+34123456789", "+34987654321"],
            },
            "suggested_actions": ["Especifica qué valores mantener"],
        }
    )

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await agent.merge_duplicates("dup-1", None)

        # Verify response explains the conflict
        assert "conflictos" in result
        assert "correo electrónico" in result
        assert "teléfono" in result
        assert "qué valores quieres mantener" in result


@pytest.mark.asyncio
async def test_merge_duplicates_invalid_json():
    """Test duplicate merge with invalid JSON in keep_values."""
    agent = ERPVoiceAgent()

    result = await agent.merge_duplicates("dup-1", "invalid json")

    # Verify error response about invalid JSON
    assert "Lo siento, ocurrió un problema" in result
    assert "formato" in result or "válido" in result


@pytest.mark.asyncio
async def test_merge_duplicates_connection_error():
    """Test duplicate merge with connection error."""
    agent = ERPVoiceAgent()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        result = await agent.merge_duplicates("dup-1", None)

        # Verify error response is in Spanish with connection failure handling
        assert "puedo conectarme" in result or "conexión" in result
        assert "servidor" in result
        assert "reconectar" in result or "verifica" in result


@pytest.mark.asyncio
async def test_translate_field_names():
    """Test field name translation to Spanish."""
    agent = ERPVoiceAgent()

    fields = ["name", "email", "phone", "address", "price"]
    translated = agent._translate_field_names(fields)

    assert "nombre" in translated
    assert "correo electrónico" in translated
    assert "teléfono" in translated
    assert "dirección" in translated
    assert "precio" in translated


@pytest.mark.asyncio
async def test_detect_conflicts():
    """Test conflict detection in duplicate records."""
    agent = ERPVoiceAgent()

    # Records with conflicts
    records = [
        {
            "id": "rec-1",
            "name": "Juan Pérez",
            "email": "juan@example.com",
            "phone": "+34123456789",
        },
        {
            "id": "rec-2",
            "name": "Juan Pérez",
            "email": "juan.perez@example.com",
            "phone": "+34987654321",
        },
    ]

    conflicts = agent._detect_conflicts(records)

    # Should detect conflicts in email and phone
    assert "email" in conflicts
    assert "phone" in conflicts
    # Should not detect conflict in name (same value)
    assert "name" not in conflicts


@pytest.mark.asyncio
async def test_detect_conflicts_no_conflicts():
    """Test conflict detection with no conflicts."""
    agent = ERPVoiceAgent()

    # Records with no conflicts (one has null values)
    records = [
        {
            "id": "rec-1",
            "name": "Juan Pérez",
            "email": "juan@example.com",
            "phone": None,
        },
        {
            "id": "rec-2",
            "name": "Juan Pérez",
            "email": "juan@example.com",
            "phone": "+34123456789",
        },
    ]

    conflicts = agent._detect_conflicts(records)

    # Should not detect any conflicts
    assert len(conflicts) == 0
