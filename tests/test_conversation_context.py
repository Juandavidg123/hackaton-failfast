"""Tests for conversation context management.

This module tests the conversation context tracking and entity reference
resolution functionality of the ERP voice agent.

Requirements: 1.5
"""

import pytest

from agent import ConversationContext, ERPVoiceAgent


class TestConversationContext:
    """Test conversation context tracking."""

    def test_add_customers_to_context(self):
        """Test adding customer entities to context."""
        context = ConversationContext()
        
        customers = [
            {"id": "1", "name": "Juan Pérez", "email": "juan@example.com"},
            {"id": "2", "name": "María García", "email": "maria@example.com"},
        ]
        
        context.add_entities("customers", customers)
        
        assert len(context.customers) == 2
        assert context.last_query_table == "customers"
        assert len(context.last_query_results) == 2

    def test_add_products_to_context(self):
        """Test adding product entities to context."""
        context = ConversationContext()
        
        products = [
            {"id": "1", "name": "Laptop", "sku": "LAP-001", "price": 999.99},
            {"id": "2", "name": "Mouse", "sku": "MOU-001", "price": 29.99},
        ]
        
        context.add_entities("products", products)
        
        assert len(context.products) == 2
        assert context.last_query_table == "products"

    def test_context_limits_to_10_entities(self):
        """Test that context only keeps last 10 entities."""
        context = ConversationContext()
        
        # Add 15 customers
        customers = [
            {"id": str(i), "name": f"Customer {i}"}
            for i in range(15)
        ]
        
        context.add_entities("customers", customers)
        
        # Should only keep 10
        assert len(context.customers) == 10
        assert len(context.last_query_results) == 10

    def test_get_last_entity(self):
        """Test getting the most recent entity."""
        context = ConversationContext()
        
        customers = [
            {"id": "1", "name": "Juan Pérez"},
            {"id": "2", "name": "María García"},
        ]
        
        context.add_entities("customers", customers)
        
        last_customer = context.get_last_entity("customer")
        
        assert last_customer is not None
        assert last_customer["id"] == "1"
        assert last_customer["name"] == "Juan Pérez"

    def test_get_entity_by_position(self):
        """Test getting entity by position."""
        context = ConversationContext()
        
        customers = [
            {"id": "1", "name": "Juan Pérez"},
            {"id": "2", "name": "María García"},
            {"id": "3", "name": "Carlos López"},
        ]
        
        context.add_entities("customers", customers)
        
        # Get first (position 0)
        first = context.get_entity_by_position("customer", 0)
        assert first["name"] == "Juan Pérez"
        
        # Get second (position 1)
        second = context.get_entity_by_position("customer", 1)
        assert second["name"] == "María García"
        
        # Get third (position 2)
        third = context.get_entity_by_position("customer", 2)
        assert third["name"] == "Carlos López"

    def test_get_entity_by_position_out_of_bounds(self):
        """Test getting entity with invalid position."""
        context = ConversationContext()
        
        customers = [
            {"id": "1", "name": "Juan Pérez"},
        ]
        
        context.add_entities("customers", customers)
        
        # Position 5 doesn't exist
        entity = context.get_entity_by_position("customer", 5)
        assert entity is None

    def test_add_duplicate_group_to_context(self):
        """Test adding duplicate groups to context."""
        context = ConversationContext()
        
        duplicate_group = {
            "id": "dup-1",
            "table_name": "customers",
            "similarity_score": 85.5,
            "matching_fields": {"name": True, "email": True},
        }
        
        context.add_duplicate_group(duplicate_group)
        
        assert len(context.duplicate_groups) == 1
        assert context.duplicate_groups[0]["id"] == "dup-1"

    def test_add_inconsistency_to_context(self):
        """Test adding inconsistencies to context."""
        context = ConversationContext()
        
        inconsistency = {
            "id": "inc-1",
            "type": "calculation",
            "table_name": "orders",
            "description": "Order total doesn't match line items sum",
        }
        
        context.add_inconsistency(inconsistency)
        
        assert len(context.inconsistencies) == 1
        assert context.inconsistencies[0]["id"] == "inc-1"

    def test_duplicate_groups_maintain_order(self):
        """Test that duplicate groups are kept in reverse chronological order."""
        context = ConversationContext()
        
        # Add three duplicate groups
        for i in range(3):
            context.add_duplicate_group({
                "id": f"dup-{i}",
                "table_name": "customers",
                "similarity_score": 80.0,
            })
        
        # Most recent should be first
        assert context.duplicate_groups[0]["id"] == "dup-2"
        assert context.duplicate_groups[1]["id"] == "dup-1"
        assert context.duplicate_groups[2]["id"] == "dup-0"

    def test_context_summary_empty(self):
        """Test context summary with no entities."""
        context = ConversationContext()
        
        summary = context.get_context_summary()
        
        assert "No hay contexto previo" in summary

    def test_context_summary_with_entities(self):
        """Test context summary with entities."""
        context = ConversationContext()
        
        customers = [{"id": "1", "name": "Juan Pérez"}]
        context.add_entities("customers", customers)
        
        products = [{"id": "1", "name": "Laptop"}]
        context.add_entities("products", products)
        
        summary = context.get_context_summary()
        
        assert "Clientes mencionados recientemente: 1" in summary
        assert "Juan Pérez" in summary
        assert "Productos mencionados recientemente: 1" in summary
        assert "Laptop" in summary


class TestERPVoiceAgentContext:
    """Test ERP voice agent context integration."""

    def test_agent_initializes_with_context(self):
        """Test that agent initializes with empty context."""
        agent = ERPVoiceAgent()
        
        assert agent.context is not None
        assert isinstance(agent.context, ConversationContext)
        assert len(agent.context.customers) == 0
        assert len(agent.context.products) == 0

    @pytest.mark.asyncio
    async def test_get_context_entity_customer(self):
        """Test getting customer from context."""
        agent = ERPVoiceAgent()
        
        # Add a customer to context
        customers = [
            {"id": "cust-123", "name": "Juan Pérez", "email": "juan@example.com"}
        ]
        agent.context.add_entities("customers", customers)
        
        # Get the customer using the tool
        result = await agent.get_context_entity("customer", 0)
        
        assert "Juan Pérez" in result
        assert "juan@example.com" in result
        assert "cust-123" in result

    @pytest.mark.asyncio
    async def test_get_context_entity_not_found(self):
        """Test getting entity that doesn't exist in context."""
        agent = ERPVoiceAgent()
        
        # Try to get a customer when none exist
        result = await agent.get_context_entity("customer", 0)
        
        assert "No encontré" in result
        assert "cliente" in result

    @pytest.mark.asyncio
    async def test_get_context_entity_duplicate_group(self):
        """Test getting duplicate group from context."""
        agent = ERPVoiceAgent()
        
        # Add a duplicate group to context
        duplicate_group = {
            "id": "dup-456",
            "table_name": "customers",
            "similarity_score": 92.5,
        }
        agent.context.add_duplicate_group(duplicate_group)
        
        # Get the duplicate group using the tool
        result = await agent.get_context_entity("duplicate_group", 0)
        
        assert "dup-456" in result
        assert "clientes" in result
        assert "92" in result  # Similarity percentage

    @pytest.mark.asyncio
    async def test_get_context_entity_inconsistency(self):
        """Test getting inconsistency from context."""
        agent = ERPVoiceAgent()
        
        # Add an inconsistency to context
        inconsistency = {
            "id": "inc-789",
            "type": "calculation",
            "table_name": "orders",
            "description": "El total del pedido no coincide con la suma de artículos",
        }
        agent.context.add_inconsistency(inconsistency)
        
        # Get the inconsistency using the tool
        result = await agent.get_context_entity("inconsistency", 0)
        
        assert "inc-789" in result
        assert "error de cálculo" in result
        assert "pedidos" in result

    @pytest.mark.asyncio
    async def test_get_context_entity_by_position(self):
        """Test getting entity by position (el primero, el segundo)."""
        agent = ERPVoiceAgent()
        
        # Add multiple customers
        customers = [
            {"id": "1", "name": "Juan Pérez", "email": "juan@example.com"},
            {"id": "2", "name": "María García", "email": "maria@example.com"},
            {"id": "3", "name": "Carlos López", "email": "carlos@example.com"},
        ]
        agent.context.add_entities("customers", customers)
        
        # Get first customer (el primero)
        result_first = await agent.get_context_entity("customer", 0)
        assert "Juan Pérez" in result_first
        
        # Get second customer (el segundo)
        result_second = await agent.get_context_entity("customer", 1)
        assert "María García" in result_second
        
        # Get third customer (el tercero)
        result_third = await agent.get_context_entity("customer", 2)
        assert "Carlos López" in result_third

    @pytest.mark.asyncio
    async def test_get_context_entity_product(self):
        """Test getting product from context."""
        agent = ERPVoiceAgent()
        
        # Add a product to context
        products = [
            {"id": "prod-123", "name": "Laptop", "sku": "LAP-001", "price": 999.99}
        ]
        agent.context.add_entities("products", products)
        
        # Get the product using the tool
        result = await agent.get_context_entity("product", 0)
        
        assert "Laptop" in result
        assert "LAP-001" in result
        assert "999.99" in result
        assert "prod-123" in result

    @pytest.mark.asyncio
    async def test_get_context_entity_order(self):
        """Test getting order from context."""
        agent = ERPVoiceAgent()
        
        # Add an order to context
        orders = [
            {
                "id": "order-123",
                "order_date": "2024-01-15",
                "total_amount": 1500.50,
                "status": "pending",
            }
        ]
        agent.context.add_entities("orders", orders)
        
        # Get the order using the tool
        result = await agent.get_context_entity("order", 0)
        
        assert "2024-01-15" in result
        assert "1500.5" in result
        assert "pendiente" in result
        assert "order-123" in result
