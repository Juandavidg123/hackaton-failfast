import logging
from dataclasses import dataclass, field
from typing import Annotated

import httpx
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    llm,
    room_io,
)
from livekit.plugins import noise_cancellation, silero, deepgram, cartesia
from livekit.plugins import openai as lk_openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from config import Config

logger = logging.getLogger("agent")


@dataclass
class ConversationContext:
    """Tracks conversation state for entity reference resolution.
    
    This class maintains context across multiple queries in a voice session,
    allowing users to refer to previously mentioned entities using Spanish
    pronouns and references like "ese cliente", "el primero", "la última".
    
    Requirements: 1.5
    """
    
    # Recently mentioned entities by type
    customers: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    order_items: list[dict] = field(default_factory=list)
    
    # Recently detected duplicate groups
    duplicate_groups: list[dict] = field(default_factory=list)
    
    # Recently detected inconsistencies
    inconsistencies: list[dict] = field(default_factory=list)
    
    # Last query results for "los anteriores" references
    last_query_table: str | None = None
    last_query_results: list[dict] = field(default_factory=list)
    
    def add_entities(self, table: str, entities: list[dict]) -> None:
        """Add entities to context from a query result.
        
        Args:
            table: Table name (customers, products, orders, order_items)
            entities: List of entity records
        """
        if table == "customers":
            self.customers = entities[:10]  # Keep last 10
        elif table == "products":
            self.products = entities[:10]
        elif table == "orders":
            self.orders = entities[:10]
        elif table == "order_items":
            self.order_items = entities[:10]
        
        # Update last query tracking
        self.last_query_table = table
        self.last_query_results = entities[:10]
    
    def add_duplicate_group(self, duplicate_group: dict) -> None:
        """Add a duplicate group to context.
        
        Args:
            duplicate_group: Duplicate group data
        """
        self.duplicate_groups.insert(0, duplicate_group)
        self.duplicate_groups = self.duplicate_groups[:10]  # Keep last 10
    
    def add_inconsistency(self, inconsistency: dict) -> None:
        """Add an inconsistency to context.
        
        Args:
            inconsistency: Inconsistency data
        """
        self.inconsistencies.insert(0, inconsistency)
        self.inconsistencies = self.inconsistencies[:10]  # Keep last 10
    
    def get_last_entity(self, entity_type: str) -> dict | None:
        """Get the most recently mentioned entity of a given type.
        
        Args:
            entity_type: Type of entity (customer, product, order, order_item,
                        duplicate_group, inconsistency)
        
        Returns:
            Most recent entity or None if no entities of that type
        """
        if entity_type == "customer" and self.customers:
            return self.customers[0]
        elif entity_type == "product" and self.products:
            return self.products[0]
        elif entity_type == "order" and self.orders:
            return self.orders[0]
        elif entity_type == "order_item" and self.order_items:
            return self.order_items[0]
        elif entity_type == "duplicate_group" and self.duplicate_groups:
            return self.duplicate_groups[0]
        elif entity_type == "inconsistency" and self.inconsistencies:
            return self.inconsistencies[0]
        return None
    
    def get_entity_by_position(self, entity_type: str, position: int) -> dict | None:
        """Get an entity by its position in the conversation.
        
        Args:
            entity_type: Type of entity
            position: Position (0 = first/most recent, 1 = second, etc.)
        
        Returns:
            Entity at position or None if not found
        """
        entities = []
        if entity_type == "customer":
            entities = self.customers
        elif entity_type == "product":
            entities = self.products
        elif entity_type == "order":
            entities = self.orders
        elif entity_type == "order_item":
            entities = self.order_items
        elif entity_type == "duplicate_group":
            entities = self.duplicate_groups
        elif entity_type == "inconsistency":
            entities = self.inconsistencies
        
        if 0 <= position < len(entities):
            return entities[position]
        return None
    
    def get_context_summary(self) -> str:
        """Get a summary of current context for the LLM.
        
        Returns:
            String summary of conversation context in Spanish
        """
        summary_parts = []
        
        if self.customers:
            summary_parts.append(
                f"Clientes mencionados recientemente: {len(self.customers)} "
                f"(último: {self.customers[0].get('name', 'sin nombre')})"
            )
        
        if self.products:
            summary_parts.append(
                f"Productos mencionados recientemente: {len(self.products)} "
                f"(último: {self.products[0].get('name', 'sin nombre')})"
            )
        
        if self.orders:
            summary_parts.append(
                f"Pedidos mencionados recientemente: {len(self.orders)}"
            )
        
        if self.duplicate_groups:
            summary_parts.append(
                f"Grupos de duplicados detectados: {len(self.duplicate_groups)}"
            )
        
        if self.inconsistencies:
            summary_parts.append(
                f"Inconsistencias detectadas: {len(self.inconsistencies)}"
            )
        
        if summary_parts:
            return "Contexto de la conversación: " + "; ".join(summary_parts)
        return "No hay contexto previo en esta conversación."

load_dotenv(".env.local")


class ERPVoiceAgent(Agent):
    """Voice agent for ERP system administration in Spanish.

    This agent assists ERP administrators with:
    - Querying business data (customers, products, orders)
    - Detecting and managing duplicate records
    - Identifying and fixing data inconsistencies

    All interactions are conducted in Spanish.
    
    The agent maintains conversation context to support entity references
    like "ese cliente", "el primero", "la última inconsistencia".
    
    Requirements: 1.1, 1.2, 1.4, 1.5
    """

    def __init__(self) -> None:
        super().__init__(
            instructions="""Eres un asistente de voz inteligente para administradores de sistemas ERP. El usuario está interactuando contigo por voz, incluso si percibes la conversación como texto.

Tu propósito es ayudar a los administradores a:
1. Consultar datos empresariales (clientes, productos, pedidos)
2. Detectar y gestionar registros duplicados en la base de datos
3. Identificar y corregir inconsistencias en los datos

Directrices importantes:
- Siempre responde en español de manera clara y concisa
- Tus respuestas deben ser naturales y conversacionales, sin formato complejo ni símbolos especiales
- Cuando presentes datos, hazlo de forma organizada pero natural para el habla
- Si necesitas confirmar una acción (como fusionar duplicados o corregir datos), pide confirmación explícita
- Mantén el contexto de la conversación para que el usuario pueda referirse a entidades mencionadas anteriormente
- Si no entiendes algo, pide aclaraciones de manera amable
- Sé proactivo en sugerir acciones cuando detectes problemas de calidad de datos

Manejo de errores y situaciones ambiguas:
- Si no entiendes un comando, pide al usuario que lo reformule de manera específica
- Si una consulta no devuelve resultados, sugiere alternativas o búsquedas más amplias
- Si el usuario proporciona información ambigua, haz preguntas aclaratorias específicas
- Si hay problemas de conexión, informa al usuario y sugiere verificar el servidor
- Siempre proporciona explicaciones claras de los errores en lenguaje natural

Contexto de conversación:
- Cuando el usuario dice "ese cliente", "ese producto", "ese pedido", se refiere al último mencionado
- Cuando dice "el primero", "el segundo", "el tercero", se refiere a la posición en la última lista mostrada
- Cuando dice "la última inconsistencia" o "el último duplicado", se refiere al más reciente detectado
- Usa las funciones de contexto para resolver estas referencias antes de hacer consultas

Recuerda: Estás aquí para hacer que la gestión de datos ERP sea más accesible y eficiente a través de comandos de voz naturales.""",
        )
        
        # Initialize conversation context
        self.context = ConversationContext()
        
        # Track connection state for reconnection handling
        self.connection_failures = 0
        self.last_connection_attempt = None

    @llm.function_tool(
        description=(
            "Obtiene información del contexto de la conversación. "
            "Usa esta función para resolver referencias a entidades mencionadas anteriormente, "
            "como 'ese cliente', 'el primero', 'la última inconsistencia', etc."
        )
    )
    async def get_context_entity(
        self,
        entity_type: Annotated[
            str,
            "Tipo de entidad a buscar en el contexto. "
            "Opciones válidas: 'customer' (cliente), 'product' (producto), "
            "'order' (pedido), 'order_item' (artículo), "
            "'duplicate_group' (grupo de duplicados), 'inconsistency' (inconsistencia)",
        ],
        position: Annotated[
            int | None,
            "Posición de la entidad (0 = primera/más reciente, 1 = segunda, etc.). "
            "Si no se especifica, se devuelve la más reciente (posición 0).",
        ] = None,
    ) -> str:
        """Get entity from conversation context for reference resolution.
        
        This tool allows the agent to resolve Spanish references like:
        - "ese cliente" -> last mentioned customer
        - "el primero" -> first entity in last list (position 0)
        - "el segundo" -> second entity in last list (position 1)
        - "la última inconsistencia" -> most recent inconsistency
        
        Args:
            entity_type: Type of entity to retrieve
            position: Position in the list (0-based, default 0 for most recent)
        
        Returns:
            Natural language response in Spanish with entity details or error
        
        Requirements: 1.5
        """
        try:
            # Default to most recent (position 0)
            if position is None:
                position = 0
            
            # Get entity from context
            entity = self.context.get_entity_by_position(entity_type, position)
            
            if entity is None:
                # Map entity types to Spanish
                entity_names_es = {
                    "customer": "cliente",
                    "product": "producto",
                    "order": "pedido",
                    "order_item": "artículo",
                    "duplicate_group": "grupo de duplicados",
                    "inconsistency": "inconsistencia",
                }
                entity_name_es = entity_names_es.get(entity_type, entity_type)
                
                position_names_es = {
                    0: "último",
                    1: "penúltimo",
                    2: "antepenúltimo",
                }
                position_name_es = position_names_es.get(position, f"en posición {position + 1}")
                
                return (
                    f"No encontré ningún {entity_name_es} {position_name_es} en el contexto de la conversación. "
                    "¿Podrías ser más específico sobre qué entidad necesitas?"
                )
            
            # Format entity based on type
            if entity_type == "customer":
                name = entity.get("name", "Sin nombre")
                email = entity.get("email", "sin email")
                entity_id = entity.get("id", "")
                return (
                    f"El cliente es: {name}, email {email}. "
                    f"ID: {entity_id}. "
                    "Puedes usar este ID para consultas específicas."
                )
            
            elif entity_type == "product":
                name = entity.get("name", "Sin nombre")
                sku = entity.get("sku", "sin SKU")
                price = entity.get("price", 0)
                entity_id = entity.get("id", "")
                return (
                    f"El producto es: {name}, SKU {sku}, precio {price} euros. "
                    f"ID: {entity_id}."
                )
            
            elif entity_type == "order":
                order_date = entity.get("order_date", "fecha desconocida")
                total = entity.get("total_amount", 0)
                status = entity.get("status", "desconocido")
                entity_id = entity.get("id", "")
                status_es = {
                    "pending": "pendiente",
                    "completed": "completado",
                    "cancelled": "cancelado",
                }.get(status, status)
                return (
                    f"El pedido es: fecha {order_date}, total {total} euros, estado {status_es}. "
                    f"ID: {entity_id}."
                )
            
            elif entity_type == "duplicate_group":
                group_id = entity.get("id", "")
                table_name = entity.get("table_name", "")
                similarity = entity.get("similarity_score", 0)
                table_names_es = {
                    "customers": "clientes",
                    "products": "productos",
                    "orders": "pedidos",
                }
                table_name_es = table_names_es.get(table_name, table_name)
                return (
                    f"El grupo de duplicados es en la tabla de {table_name_es} "
                    f"con similitud del {similarity:.0f} por ciento. "
                    f"ID del grupo: {group_id}. "
                    "Puedes usar este ID para obtener detalles o fusionar."
                )
            
            elif entity_type == "inconsistency":
                inc_id = entity.get("id", "")
                inc_type = entity.get("type", "")
                table_name = entity.get("table_name", "")
                description = entity.get("description", "")
                type_names_es = {
                    "referential": "integridad referencial",
                    "calculation": "error de cálculo",
                    "format": "formato inválido",
                    "business_rule": "violación de regla de negocio",
                }
                type_name_es = type_names_es.get(inc_type, inc_type)
                table_names_es = {
                    "customers": "clientes",
                    "products": "productos",
                    "orders": "pedidos",
                    "order_items": "artículos de pedidos",
                }
                table_name_es = table_names_es.get(table_name, table_name)
                return (
                    f"La inconsistencia es: {type_name_es} en {table_name_es}. "
                    f"{description}. "
                    f"ID: {inc_id}. "
                    "Puedes usar este ID para obtener detalles o corregir."
                )
            
            else:
                return f"Tipo de entidad no reconocido: {entity_type}"
        
        except Exception as e:
            logger.error(f"Error getting context entity: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error al buscar en el contexto: {e!s}",
                ["Intenta ser más específico sobre qué entidad necesitas"],
            )

    @llm.function_tool(
        description=(
            "Consulta datos del sistema ERP. "
            "Usa esta función para buscar clientes, productos, pedidos o artículos de pedidos. "
            "Puedes filtrar por cualquier campo de la tabla."
        )
    )
    async def query_erp_data(
        self,
        table: Annotated[
            str,
            "Nombre de la tabla a consultar. "
            "Opciones válidas: 'customers' (clientes), 'products' (productos), "
            "'orders' (pedidos), 'order_items' (artículos de pedidos)",
        ],
        filters: Annotated[
            str | None,
            "Filtros opcionales en formato de pares clave-valor separados por comas. "
            "Ejemplo: 'name=Juan,email=juan@example.com' o 'status=pending'",
        ] = None,
    ) -> str:
        """Query ERP data from the Flask backend.

        This tool allows the agent to query customers, products, orders, and order items
        from the ERP database through the Flask API.

        Args:
            table: Table name to query (customers, products, orders, order_items)
            filters: Optional filters as comma-separated key=value pairs

        Returns:
            Natural language response in Spanish with the query results

        Requirements: 1.2, 1.3, 1.4
        """
        try:
            # Build query parameters
            params = {"table": table}

            # Parse filters if provided
            if filters:
                filter_pairs = filters.split(",")
                for pair in filter_pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key.strip()] = value.strip()

            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{Config.FLASK_BACKEND_URL}/api/erp/query",
                    params=params,
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al consultar datos"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                # Add entities to conversation context
                table_name = data.get("table", "")
                records = data.get("records", [])
                if records:
                    self.context.add_entities(table_name, records)
                
                # Pass filters for better empty results handling
                filter_dict = {k: v for k, v in params.items() if k != "table"} if len(params) > 1 else None
                return self._format_query_response(data, filter_dict)

        except httpx.TimeoutException:
            logger.error("Timeout connecting to Flask backend")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error querying ERP data: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta reformular tu consulta", "Contacta al soporte técnico"],
            )

    def _format_query_response(self, data: dict, filters: dict | None = None) -> str:
        """Format query results into natural language Spanish response.

        Args:
            data: Response data from Flask API containing table, count, and records
            filters: Optional filters that were applied

        Returns:
            Natural language response in Spanish
        """
        table = data.get("table", "")
        count = data.get("count", 0)
        records = data.get("records", [])

        # Map table names to Spanish
        table_names_es = {
            "customers": "clientes",
            "products": "productos",
            "orders": "pedidos",
            "order_items": "artículos de pedidos",
        }
        table_name_es = table_names_es.get(table, table)

        # Handle empty results with helpful suggestions
        if count == 0:
            return self._format_empty_results_response(table, filters)

        # Build response
        response_parts = [
            f"Encontré {count} {'registro' if count == 1 else 'registros'} en {table_name_es}."
        ]

        # Format records based on table type
        for i, record in enumerate(records[:5], 1):  # Limit to first 5 for voice
            if table == "customers":
                response_parts.append(self._format_customer(i, record))
            elif table == "products":
                response_parts.append(self._format_product(i, record))
            elif table == "orders":
                response_parts.append(self._format_order(i, record))
            elif table == "order_items":
                response_parts.append(self._format_order_item(i, record))

        # Add note if there are more records
        if count > 5:
            response_parts.append(
                f"Hay {count - 5} registros más. ¿Quieres que refine la búsqueda?"
            )

        return " ".join(response_parts)

    def _format_customer(self, index: int, customer: dict) -> str:
        """Format customer record for voice output."""
        name = customer.get("name", "Sin nombre")
        email = customer.get("email", "sin email")
        phone = customer.get("phone", "sin teléfono")
        return f"Cliente {index}: {name}, email {email}, teléfono {phone}."

    def _format_product(self, index: int, product: dict) -> str:
        """Format product record for voice output."""
        name = product.get("name", "Sin nombre")
        sku = product.get("sku", "sin SKU")
        price = product.get("price", 0)
        inventory = product.get("inventory_count", 0)
        return f"Producto {index}: {name}, SKU {sku}, precio {price} euros, inventario {inventory} unidades."

    def _format_order(self, index: int, order: dict) -> str:
        """Format order record for voice output."""
        order_date = order.get("order_date", "fecha desconocida")
        total = order.get("total_amount", 0)
        status = order.get("status", "desconocido")
        # Map status to Spanish
        status_es = {
            "pending": "pendiente",
            "completed": "completado",
            "cancelled": "cancelado",
        }.get(status, status)
        return f"Pedido {index}: fecha {order_date}, total {total} euros, estado {status_es}."

    def _format_order_item(self, index: int, item: dict) -> str:
        """Format order item record for voice output."""
        quantity = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0)
        line_total = item.get("line_total", 0)
        return f"Artículo {index}: cantidad {quantity}, precio unitario {unit_price} euros, total {line_total} euros."

    def _format_error_response(
        self, error_message: str, suggested_actions: list[str]
    ) -> str:
        """Format error message into natural language Spanish response.

        Args:
            error_message: Error message in Spanish
            suggested_actions: List of suggested actions in Spanish

        Returns:
            Natural language error response in Spanish
            
        Requirements: 7.3
        """
        response = f"Lo siento, ocurrió un problema: {error_message}."

        if suggested_actions:
            response += " Te sugiero que: " + ", o ".join(suggested_actions) + "."

        return response
    
    def _format_empty_results_response(self, query_type: str, filters: dict | None = None) -> str:
        """Format helpful response for empty query results.
        
        Args:
            query_type: Type of query (customers, products, orders, etc.)
            filters: Filters that were applied
            
        Returns:
            Natural language response in Spanish with suggestions
            
        Requirements: 7.2
        """
        # Map query types to Spanish
        query_types_es = {
            "customers": "clientes",
            "products": "productos",
            "orders": "pedidos",
            "order_items": "artículos de pedidos",
        }
        query_type_es = query_types_es.get(query_type, query_type)
        
        response_parts = [
            f"No encontré ningún {query_type_es} con esos criterios."
        ]
        
        # Provide specific suggestions based on query type
        suggestions = []
        
        if filters:
            suggestions.append("intenta con criterios de búsqueda más amplios")
            suggestions.append("verifica que los valores de búsqueda sean correctos")
        else:
            suggestions.append("intenta agregar filtros específicos")
        
        # Add query-specific suggestions
        if query_type == "customers":
            suggestions.append("busca por nombre parcial en lugar del nombre completo")
            suggestions.append("intenta buscar por email o teléfono")
        elif query_type == "products":
            suggestions.append("busca por nombre parcial o SKU")
            suggestions.append("verifica el inventario disponible")
        elif query_type == "orders":
            suggestions.append("amplía el rango de fechas")
            suggestions.append("busca por estado del pedido")
        
        response_parts.append(
            "Te sugiero que: " + ", o ".join(suggestions[:3]) + "."
        )
        
        return " ".join(response_parts)
    
    def _format_clarification_request(self, ambiguous_input: str, clarification_options: list[str]) -> str:
        """Format clarification request for ambiguous input.
        
        Args:
            ambiguous_input: The ambiguous input from the user
            clarification_options: List of possible interpretations
            
        Returns:
            Natural language clarification request in Spanish
            
        Requirements: 7.4
        """
        response_parts = [
            "No estoy seguro de entender exactamente qué necesitas."
        ]
        
        if clarification_options:
            response_parts.append(
                "¿Te refieres a: " + ", o ".join(clarification_options) + "?"
            )
        else:
            response_parts.append(
                "¿Podrías ser más específico? Por ejemplo, puedes decirme: "
                "busca clientes por nombre, detecta duplicados en productos, "
                "o muestra inconsistencias en pedidos."
            )
        
        return " ".join(response_parts)
    
    def _format_unrecognized_command_response(self, user_input: str | None = None) -> str:
        """Format response for unrecognized commands.
        
        Args:
            user_input: The unrecognized input from the user
            
        Returns:
            Natural language response in Spanish asking for clarification
            
        Requirements: 7.1
        """
        response_parts = [
            "Disculpa, no entendí ese comando."
        ]
        
        # Provide examples of what the agent can do
        response_parts.append(
            "Puedo ayudarte con: "
            "consultar datos de clientes, productos o pedidos; "
            "detectar y fusionar duplicados; "
            "o identificar y corregir inconsistencias en los datos."
        )
        
        response_parts.append(
            "¿Podrías reformular tu solicitud? Por ejemplo: "
            "busca el cliente Juan Pérez, "
            "detecta duplicados en la tabla de clientes, "
            "o muestra las inconsistencias de cálculo."
        )
        
        return " ".join(response_parts)
    
    def _handle_connection_failure(self, error_type: str) -> str:
        """Handle connection failures with reconnection logic.
        
        Args:
            error_type: Type of connection error (timeout, connect_error, etc.)
            
        Returns:
            Natural language response in Spanish with reconnection guidance
            
        Requirements: 7.5
        """
        self.connection_failures += 1
        
        response_parts = []
        
        if error_type == "timeout":
            response_parts.append(
                "El servidor está tardando demasiado en responder."
            )
        elif error_type == "connect_error":
            response_parts.append(
                "No puedo conectarme con el servidor de datos en este momento."
            )
        else:
            response_parts.append(
                "Hay un problema de conexión con el servidor."
            )
        
        # Provide guidance based on number of failures
        if self.connection_failures == 1:
            response_parts.append(
                "Voy a intentar reconectar. Por favor espera un momento."
            )
            response_parts.append(
                "Si el problema persiste, verifica que el servidor Flask esté ejecutándose "
                f"en {Config.FLASK_BACKEND_URL}."
            )
        elif self.connection_failures == 2:
            response_parts.append(
                "Este es el segundo intento fallido. "
                "Por favor verifica que el servidor Flask esté ejecutándose correctamente."
            )
            response_parts.append(
                "Puedes verificar la conexión ejecutando: curl " + Config.FLASK_BACKEND_URL
            )
        else:
            response_parts.append(
                "He intentado reconectar varias veces sin éxito. "
                "Necesitas verificar el estado del servidor antes de continuar."
            )
            response_parts.append(
                "Contacta al administrador del sistema si el problema persiste."
            )
        
        return " ".join(response_parts)

    @llm.function_tool(
        description=(
            "Detecta registros duplicados en el sistema ERP. "
            "Usa esta función para buscar clientes, productos o pedidos duplicados. "
            "Puedes especificar una tabla específica o analizar todas las tablas."
        )
    )
    async def detect_duplicates(
        self,
        table: Annotated[
            str | None,
            "Nombre de la tabla a analizar para duplicados. "
            "Opciones válidas: 'customers' (clientes), 'products' (productos), 'orders' (pedidos). "
            "Si no se especifica, se analizan todas las tablas.",
        ] = None,
        threshold: Annotated[
            int | None,
            "Umbral de similitud para considerar registros como duplicados (0-100). "
            "Por defecto es 80. Valores más altos requieren mayor similitud.",
        ] = None,
    ) -> str:
        """Detect duplicate records in the ERP database.

        This tool triggers duplicate detection analysis and reports the results
        in natural language Spanish.

        Args:
            table: Optional table name to analyze (customers, products, orders)
            threshold: Optional similarity threshold (0-100, default 80)

        Returns:
            Natural language response in Spanish with duplicate detection results

        Requirements: 2.4, 2.5
        """
        try:
            # Build request body
            request_body = {}
            if table:
                request_body["table"] = table
            if threshold is not None:
                request_body["threshold"] = threshold

            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{Config.FLASK_BACKEND_URL}/api/duplicates/detect",
                    json=request_body,
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al detectar duplicados"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                # Add duplicate groups to conversation context
                duplicate_groups = data.get("duplicate_groups", [])
                for group in duplicate_groups:
                    self.context.add_duplicate_group(group)
                
                return self._format_duplicate_detection_response(data)

        except httpx.TimeoutException:
            logger.error("Timeout detecting duplicates")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error detecting duplicates: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    @llm.function_tool(
        description=(
            "Obtiene los detalles de un grupo de duplicados específico. "
            "Usa esta función para ver los registros completos de un grupo de duplicados "
            "antes de fusionarlos."
        )
    )
    async def get_duplicate_details(
        self,
        duplicate_id: Annotated[
            str,
            "ID del grupo de duplicados a consultar. "
            "Este ID se obtiene de la función detect_duplicates.",
        ],
    ) -> str:
        """Get details of a specific duplicate group.

        This tool retrieves full record details for a duplicate group,
        showing all fields and values for comparison.

        Args:
            duplicate_id: Duplicate group ID from detect_duplicates

        Returns:
            Natural language response in Spanish with duplicate details

        Requirements: 2.4, 2.5
        """
        try:
            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{Config.FLASK_BACKEND_URL}/api/duplicates/{duplicate_id}",
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al obtener detalles de duplicados"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                return self._format_duplicate_details_response(data)

        except httpx.TimeoutException:
            logger.error("Timeout getting duplicate details")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error getting duplicate details: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    @llm.function_tool(
        description=(
            "Fusiona registros duplicados en un solo registro canónico. "
            "Usa esta función después de revisar los detalles de un grupo de duplicados. "
            "Si hay conflictos (valores diferentes en el mismo campo), debes especificar "
            "qué valores mantener."
        )
    )
    async def merge_duplicates(
        self,
        duplicate_id: Annotated[
            str,
            "ID del grupo de duplicados a fusionar. "
            "Este ID se obtiene de la función detect_duplicates.",
        ],
        keep_values: Annotated[
            str | None,
            "Valores a mantener en caso de conflictos, en formato JSON. "
            "Ejemplo: '{\"name\": \"Juan Pérez\", \"email\": \"juan@example.com\"}'. "
            "Si no hay conflictos, puedes omitir este parámetro.",
        ] = None,
    ) -> str:
        """Merge duplicate records into a single canonical record.

        This tool performs the merge operation, preserving all non-null values
        and resolving conflicts based on the keep_values parameter.

        Args:
            duplicate_id: Duplicate group ID from detect_duplicates
            keep_values: Optional JSON string with values to keep for conflicts

        Returns:
            Natural language response in Spanish with merge results

        Requirements: 3.1, 3.5
        """
        try:
            # Build request body
            request_body = {}
            if keep_values:
                # Parse JSON string to dict
                import json
                try:
                    request_body["keep_values"] = json.loads(keep_values)
                except json.JSONDecodeError:
                    return self._format_error_response(
                        "El formato de keep_values no es válido",
                        [
                            "Usa formato JSON válido, por ejemplo: "
                            '{"name": "Juan Pérez", "email": "juan@example.com"}'
                        ],
                    )
            else:
                request_body["keep_values"] = {}

            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{Config.FLASK_BACKEND_URL}/api/duplicates/{duplicate_id}/merge",
                    json=request_body,
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al fusionar duplicados"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    
                    # Check if it's a conflict error
                    if "conflict" in error_message.lower():
                        return self._format_merge_conflict_response(error_data)
                    
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                return self._format_merge_success_response(data)

        except httpx.TimeoutException:
            logger.error("Timeout merging duplicates")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error merging duplicates: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    def _format_duplicate_detection_response(self, data: dict) -> str:
        """Format duplicate detection results into natural language Spanish.

        Args:
            data: Response data from Flask API

        Returns:
            Natural language response in Spanish
        """
        tables_analyzed = data.get("tables_analyzed", [])
        duplicate_groups_found = data.get("duplicate_groups_found", 0)
        duplicate_groups = data.get("duplicate_groups", [])

        # Map table names to Spanish
        table_names_es = {
            "customers": "clientes",
            "products": "productos",
            "orders": "pedidos",
        }
        tables_es = [table_names_es.get(t, t) for t in tables_analyzed]

        # Build response
        if duplicate_groups_found == 0:
            return f"No encontré duplicados en las tablas de {', '.join(tables_es)}. ¡Los datos están limpios!"

        response_parts = [
            f"Encontré {duplicate_groups_found} "
            f"{'grupo' if duplicate_groups_found == 1 else 'grupos'} de duplicados "
            f"en {', '.join(tables_es)}."
        ]

        # Report details for each group (limit to first 3 for voice)
        for i, group in enumerate(duplicate_groups[:3], 1):
            table_name = group.get("table_name", "")
            table_name_es = table_names_es.get(table_name, table_name)
            similarity = group.get("similarity_score", 0)
            matching_fields = group.get("matching_fields", {})
            group_id = group.get("id", "")

            # Format matching fields
            fields_list = list(matching_fields.keys())
            fields_es = self._translate_field_names(fields_list)

            response_parts.append(
                f"Grupo {i} en {table_name_es}: similitud del {similarity:.0f} por ciento, "
                f"coinciden en {', '.join(fields_es)}. ID del grupo: {group_id}."
            )

        # Add note if there are more groups
        if duplicate_groups_found > 3:
            response_parts.append(
                f"Hay {duplicate_groups_found - 3} grupos más. "
                "¿Quieres que te dé más detalles de algún grupo específico?"
            )

        return " ".join(response_parts)

    def _format_duplicate_details_response(self, data: dict) -> str:
        """Format duplicate details into natural language Spanish.

        Args:
            data: Response data from Flask API with duplicate_group and records

        Returns:
            Natural language response in Spanish
        """
        duplicate_group = data.get("duplicate_group", {})
        records = data.get("records", [])

        table_name = duplicate_group.get("table_name", "")
        similarity = duplicate_group.get("similarity_score", 0)
        matching_fields = duplicate_group.get("matching_fields", {})

        # Map table names to Spanish
        table_names_es = {
            "customers": "clientes",
            "products": "productos",
            "orders": "pedidos",
        }
        table_name_es = table_names_es.get(table_name, table_name)

        # Build response
        response_parts = [
            f"Detalles del grupo de duplicados en {table_name_es} "
            f"con similitud del {similarity:.0f} por ciento."
        ]

        # Format matching fields
        fields_list = list(matching_fields.keys())
        fields_es = self._translate_field_names(fields_list)
        response_parts.append(f"Campos que coinciden: {', '.join(fields_es)}.")

        # Format each record
        for i, record in enumerate(records, 1):
            if table_name == "customers":
                response_parts.append(self._format_customer(i, record))
            elif table_name == "products":
                response_parts.append(self._format_product(i, record))
            elif table_name == "orders":
                response_parts.append(self._format_order(i, record))

        # Check for conflicts
        conflicts = self._detect_conflicts(records)
        if conflicts:
            response_parts.append(
                f"Hay conflictos en los siguientes campos: {', '.join(self._translate_field_names(conflicts))}. "
                "Necesitarás especificar qué valores mantener al fusionar."
            )
        else:
            response_parts.append(
                "No hay conflictos. Puedes fusionar estos registros sin problemas."
            )

        return " ".join(response_parts)

    def _format_merge_conflict_response(self, error_data: dict) -> str:
        """Format merge conflict error into natural language Spanish.

        Args:
            error_data: Error data from Flask API

        Returns:
            Natural language response in Spanish explaining the conflict
        """
        error_message = error_data.get("message", "")
        conflicts = error_data.get("conflicts", {})

        response_parts = [
            "No puedo fusionar estos registros porque hay conflictos en algunos campos."
        ]

        if conflicts:
            conflict_fields = list(conflicts.keys())
            fields_es = self._translate_field_names(conflict_fields)
            response_parts.append(
                f"Los campos en conflicto son: {', '.join(fields_es)}."
            )

            # Show conflict values
            for field, values in list(conflicts.items())[:3]:  # Limit to 3 for voice
                field_es = self._translate_field_names([field])[0]
                response_parts.append(
                    f"Para {field_es}, los valores son: {', '.join(str(v) for v in values)}."
                )

        response_parts.append(
            "Por favor, dime qué valores quieres mantener para cada campo en conflicto."
        )

        return " ".join(response_parts)

    def _format_merge_success_response(self, data: dict) -> str:
        """Format successful merge into natural language Spanish.

        Args:
            data: Response data from Flask API

        Returns:
            Natural language response in Spanish
        """
        merged_record = data.get("merged_record", {})
        table_name = merged_record.get("table_name", "")

        # Map table names to Spanish
        table_names_es = {
            "customers": "cliente",
            "products": "producto",
            "orders": "pedido",
        }
        table_name_es = table_names_es.get(table_name, table_name)

        response = (
            f"¡Perfecto! Los duplicados se fusionaron exitosamente. "
            f"Ahora tienes un solo {table_name_es} con toda la información combinada. "
            f"El registro duplicado fue eliminado y todas las referencias fueron actualizadas."
        )

        return response

    def _translate_field_names(self, fields: list[str]) -> list[str]:
        """Translate field names from English to Spanish.

        Args:
            fields: List of field names in English

        Returns:
            List of field names in Spanish
        """
        field_translations = {
            "name": "nombre",
            "email": "correo electrónico",
            "phone": "teléfono",
            "address": "dirección",
            "sku": "SKU",
            "price": "precio",
            "inventory_count": "inventario",
            "order_date": "fecha de pedido",
            "total_amount": "monto total",
            "status": "estado",
            "quantity": "cantidad",
            "unit_price": "precio unitario",
            "line_total": "total de línea",
        }

        return [field_translations.get(f, f) for f in fields]

    def _detect_conflicts(self, records: list[dict]) -> list[str]:
        """Detect conflicting fields in duplicate records.

        Args:
            records: List of duplicate records

        Returns:
            List of field names with conflicts
        """
        if len(records) < 2:
            return []

        conflicts = []
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())

        # Check each field for conflicts
        for field in all_fields:
            # Skip metadata fields
            if field in ["id", "created_at", "updated_at"]:
                continue

            # Get non-null values for this field
            values = [
                record.get(field)
                for record in records
                if record.get(field) is not None
            ]

            # If there are multiple different non-null values, it's a conflict
            if len(set(str(v) for v in values)) > 1:
                conflicts.append(field)

        return conflicts

    @llm.function_tool(
        description=(
            "Detecta inconsistencias en los datos del sistema ERP. "
            "Usa esta función para buscar problemas de integridad referencial, "
            "errores de cálculo, formatos inválidos o violaciones de reglas de negocio."
        )
    )
    async def detect_inconsistencies(
        self,
        inconsistency_type: Annotated[
            str | None,
            "Tipo de inconsistencia a buscar. "
            "Opciones válidas: 'referential' (integridad referencial), "
            "'calculation' (errores de cálculo), 'format' (formatos inválidos), "
            "'business_rule' (reglas de negocio). "
            "Si no se especifica, se buscan todos los tipos.",
        ] = None,
        table: Annotated[
            str | None,
            "Nombre de la tabla a analizar. "
            "Opciones válidas: 'customers', 'products', 'orders', 'order_items'. "
            "Si no se especifica, se analizan todas las tablas.",
        ] = None,
    ) -> str:
        """Detect data inconsistencies in the ERP database.

        This tool triggers inconsistency analysis and reports the results
        in natural language Spanish.

        Args:
            inconsistency_type: Optional type filter (referential, calculation, format, business_rule)
            table: Optional table name to analyze

        Returns:
            Natural language response in Spanish with inconsistency detection results

        Requirements: 4.3, 4.4
        """
        try:
            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{Config.FLASK_BACKEND_URL}/api/inconsistencies/detect",
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al detectar inconsistencias"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()

                # Apply filters if specified
                inconsistencies = data.get("inconsistencies", [])
                if inconsistency_type:
                    inconsistencies = [
                        inc for inc in inconsistencies
                        if inc.get("type") == inconsistency_type
                    ]
                if table:
                    inconsistencies = [
                        inc for inc in inconsistencies
                        if inc.get("table_name") == table
                    ]

                # Rebuild summary with filtered data
                filtered_data = {
                    "total_inconsistencies": len(inconsistencies),
                    "inconsistencies": inconsistencies,
                }

                # Group by type for summary
                by_type = {}
                for inc in inconsistencies:
                    type_name = inc.get("type", "unknown")
                    if type_name not in by_type:
                        by_type[type_name] = 0
                    by_type[type_name] += 1
                filtered_data["by_type"] = by_type
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                # Add inconsistencies to conversation context
                for inc in inconsistencies:
                    self.context.add_inconsistency(inc)

                return self._format_inconsistency_detection_response(filtered_data)

        except httpx.TimeoutException:
            logger.error("Timeout detecting inconsistencies")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error detecting inconsistencies: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    @llm.function_tool(
        description=(
            "Obtiene los detalles de una inconsistencia específica. "
            "Usa esta función para ver el registro afectado y la descripción completa "
            "de la inconsistencia antes de corregirla."
        )
    )
    async def get_inconsistency_details(
        self,
        inconsistency_id: Annotated[
            str,
            "ID de la inconsistencia a consultar. "
            "Este ID se obtiene de la función detect_inconsistencies.",
        ],
    ) -> str:
        """Get details of a specific inconsistency.

        This tool retrieves full details for an inconsistency,
        showing the affected record and suggested fix.

        Args:
            inconsistency_id: Inconsistency ID from detect_inconsistencies

        Returns:
            Natural language response in Spanish with inconsistency details

        Requirements: 4.3, 4.4
        """
        try:
            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{Config.FLASK_BACKEND_URL}/api/inconsistencies/{inconsistency_id}",
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al obtener detalles de inconsistencia"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                return self._format_inconsistency_details_response(data)

        except httpx.TimeoutException:
            logger.error("Timeout getting inconsistency details")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error getting inconsistency details: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    @llm.function_tool(
        description=(
            "Corrige una inconsistencia en los datos del sistema ERP. "
            "Usa esta función después de revisar los detalles de una inconsistencia. "
            "Puedes actualizar un campo con un nuevo valor o eliminar el registro completo."
        )
    )
    async def fix_inconsistency(
        self,
        inconsistency_id: Annotated[
            str,
            "ID de la inconsistencia a corregir. "
            "Este ID se obtiene de la función detect_inconsistencies.",
        ],
        correction: Annotated[
            str,
            "Datos de corrección en formato JSON. "
            "Para actualizar un campo: '{\"field\": \"nombre_campo\", \"value\": valor}'. "
            "Para eliminar el registro: '{\"delete_record\": true}'. "
            "Ejemplo: '{\"field\": \"total_amount\", \"value\": 150.50}'",
        ],
    ) -> str:
        """Fix a data inconsistency by applying a correction.

        This tool applies the correction, updates dependent data if needed,
        and verifies the inconsistency is resolved.

        Args:
            inconsistency_id: Inconsistency ID from detect_inconsistencies
            correction: JSON string with correction data

        Returns:
            Natural language response in Spanish with fix results

        Requirements: 5.1, 5.3
        """
        try:
            # Parse JSON string to dict
            import json
            try:
                correction_data = json.loads(correction)
            except json.JSONDecodeError:
                return self._format_error_response(
                    "El formato de corrección no es válido",
                    [
                        "Usa formato JSON válido, por ejemplo: "
                        '{"field": "total_amount", "value": 150.50} o '
                        '{"delete_record": true}'
                    ],
                )

            # Build request body
            request_body = {"correction": correction_data}

            # Make HTTP request to Flask backend
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{Config.FLASK_BACKEND_URL}/api/inconsistencies/{inconsistency_id}/fix",
                    json=request_body,
                )

                # Handle API errors
                if response.status_code != 200:
                    error_data = await response.json() if response.text else {}
                    error_message = error_data.get(
                        "message", "Error desconocido al corregir inconsistencia"
                    )
                    logger.error(f"API error: {response.status_code} - {error_message}")
                    return self._format_error_response(
                        error_message, error_data.get("suggested_actions", [])
                    )

                # Parse successful response
                data = await response.json()
                
                # Reset connection failure counter on success
                self.connection_failures = 0
                
                return self._format_fix_success_response(data, correction_data)

        except httpx.TimeoutException:
            logger.error("Timeout fixing inconsistency")
            return self._handle_connection_failure("timeout")
        except httpx.ConnectError:
            logger.error("Connection error to Flask backend")
            return self._handle_connection_failure("connect_error")
        except Exception as e:
            logger.error(f"Unexpected error fixing inconsistency: {e}", exc_info=True)
            return self._format_error_response(
                f"Ocurrió un error inesperado: {e!s}",
                ["Intenta nuevamente", "Contacta al soporte técnico"],
            )

    def _format_inconsistency_detection_response(self, data: dict) -> str:
        """Format inconsistency detection results into natural language Spanish.

        Args:
            data: Response data from Flask API

        Returns:
            Natural language response in Spanish
        """
        total_inconsistencies = data.get("total_inconsistencies", 0)
        by_type = data.get("by_type", {})
        inconsistencies = data.get("inconsistencies", [])

        # Map type names to Spanish
        type_names_es = {
            "referential": "integridad referencial",
            "calculation": "errores de cálculo",
            "format": "formatos inválidos",
            "business_rule": "reglas de negocio",
        }

        # Build response
        if total_inconsistencies == 0:
            return "¡Excelente! No encontré ninguna inconsistencia en los datos. Todo está en orden."

        response_parts = [
            f"Encontré {total_inconsistencies} "
            f"{'inconsistencia' if total_inconsistencies == 1 else 'inconsistencias'} "
            "en los datos."
        ]

        # Report summary by type
        if by_type:
            type_summary = []
            for type_name, count in by_type.items():
                type_name_es = type_names_es.get(type_name, type_name)
                type_summary.append(
                    f"{count} de {type_name_es}"
                )
            response_parts.append(f"Por tipo: {', '.join(type_summary)}.")

        # Report details for first few inconsistencies (limit to 3 for voice)
        for i, inc in enumerate(inconsistencies[:3], 1):
            inc_type = inc.get("type", "")
            type_name_es = type_names_es.get(inc_type, inc_type)
            table_name = inc.get("table_name", "")
            description = inc.get("description", "")
            inc_id = inc.get("id", "")

            # Map table names to Spanish
            table_names_es = {
                "customers": "clientes",
                "products": "productos",
                "orders": "pedidos",
                "order_items": "artículos de pedidos",
            }
            table_name_es = table_names_es.get(table_name, table_name)

            response_parts.append(
                f"Inconsistencia {i}: {type_name_es} en {table_name_es}. "
                f"{description}. ID: {inc_id}."
            )

        # Add note if there are more inconsistencies
        if total_inconsistencies > 3:
            response_parts.append(
                f"Hay {total_inconsistencies - 3} inconsistencias más. "
                "¿Quieres que te dé más detalles de alguna específica?"
            )

        return " ".join(response_parts)

    def _format_inconsistency_details_response(self, data: dict) -> str:
        """Format inconsistency details into natural language Spanish.

        Args:
            data: Response data from Flask API with inconsistency and affected_record

        Returns:
            Natural language response in Spanish
        """
        inconsistency = data.get("inconsistency", {})
        affected_record = data.get("affected_record", {})

        inc_type = inconsistency.get("type", "")
        table_name = inconsistency.get("table_name", "")
        field_name = inconsistency.get("field_name", "")
        description = inconsistency.get("description", "")
        suggested_fix = inconsistency.get("suggested_fix", {})

        # Map type names to Spanish
        type_names_es = {
            "referential": "integridad referencial",
            "calculation": "error de cálculo",
            "format": "formato inválido",
            "business_rule": "violación de regla de negocio",
        }
        type_name_es = type_names_es.get(inc_type, inc_type)

        # Map table names to Spanish
        table_names_es = {
            "customers": "clientes",
            "products": "productos",
            "orders": "pedidos",
            "order_items": "artículos de pedidos",
        }
        table_name_es = table_names_es.get(table_name, table_name)

        # Build response
        response_parts = [
            f"Detalles de la inconsistencia: {type_name_es} en la tabla de {table_name_es}."
        ]

        # Add description
        response_parts.append(f"Problema: {description}.")

        # Add field information if available
        if field_name:
            field_es = self._translate_field_names([field_name])[0]
            response_parts.append(f"Campo afectado: {field_es}.")

        # Add suggested fix information
        if suggested_fix:
            action = suggested_fix.get("action", "")
            
            if action == "delete_or_update":
                options = suggested_fix.get("options", [])
                if options:
                    response_parts.append(
                        f"Opciones de corrección: {', o '.join(options)}."
                    )
            elif action == "update_total" or action == "update_line_total":
                current_value = suggested_fix.get("current_value", "")
                suggested_value = suggested_fix.get("suggested_value", "")
                response_parts.append(
                    f"Valor actual: {current_value}. "
                    f"Valor sugerido: {suggested_value}."
                )
            elif action == "correct_format":
                current_value = suggested_fix.get("current_value", "")
                message = suggested_fix.get("message", "")
                response_parts.append(
                    f"Valor actual: {current_value}. "
                    f"Sugerencia: {message}."
                )
            elif action == "correct_value":
                current_value = suggested_fix.get("current_value", "")
                suggested_value = suggested_fix.get("suggested_value")
                message = suggested_fix.get("message", "")
                if suggested_value is not None:
                    response_parts.append(
                        f"Valor actual: {current_value}. "
                        f"Valor sugerido: {suggested_value}. "
                        f"{message}."
                    )
                else:
                    response_parts.append(
                        f"Valor actual: {current_value}. "
                        f"{message}."
                    )

        response_parts.append(
            "¿Quieres que aplique la corrección sugerida?"
        )

        return " ".join(response_parts)

    def _format_fix_success_response(self, data: dict, correction_data: dict) -> str:
        """Format successful inconsistency fix into natural language Spanish.

        Args:
            data: Response data from Flask API
            correction_data: The correction that was applied

        Returns:
            Natural language response in Spanish
        """
        # Check if it was a deletion
        if correction_data.get("delete_record"):
            action = data.get("action", "")
            table = data.get("table", "")
            
            # Map table names to Spanish
            table_names_es = {
                "customers": "cliente",
                "products": "producto",
                "orders": "pedido",
                "order_items": "artículo de pedido",
            }
            table_name_es = table_names_es.get(table, table)
            
            return (
                f"¡Perfecto! El registro de {table_name_es} fue eliminado exitosamente. "
                "La inconsistencia ha sido resuelta."
            )
        else:
            # It was a field update
            field = correction_data.get("field", "")
            value = correction_data.get("value", "")
            
            field_es = self._translate_field_names([field])[0] if field else "campo"
            
            return (
                f"¡Excelente! La inconsistencia fue corregida exitosamente. "
                f"El campo {field_es} fue actualizado a {value}. "
                "Los datos dependientes también fueron actualizados para mantener la integridad."
            )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def erp_voice_session(ctx: JobContext):
    """Handle ERP voice session with Spanish language support.

    This function sets up the voice AI pipeline with:
    - Whisper STT for Spanish speech recognition
    - Ollama with Llama 3 for natural language understanding
    - LiveKit Inference TTS for Spanish voice synthesis

    Requirements: 1.1, 1.2, 1.4
    """
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
        "language": Config.VOICE_LANGUAGE,
    }

    logger.info(f"Starting ERP voice session with language: {Config.VOICE_LANGUAGE}")

    # Configure Speech-to-Text (Deepgram with Spanish support)
    # Deepgram has a free tier and supports Spanish
    stt_config = deepgram.STT(
        language=Config.STT_LANGUAGE,  # "es" for Spanish
        model="nova-2",  # Deepgram's latest model
    )

    # Configure Large Language Model (Ollama with Llama 3)
    # Ollama runs locally and is free
    # Using OpenAI plugin with Ollama's OpenAI-compatible API
    from openai import AsyncOpenAI
    
    ollama_client = AsyncOpenAI(
        base_url=f"{Config.OLLAMA_URL}/v1",
        api_key="ollama",  # Ollama doesn't need a real API key
        timeout=60.0,  # Increase timeout for local models
    )
    
    llm_config = lk_openai.LLM(
        model=Config.LLM_MODEL,  # "llama3"
        client=ollama_client,  # Pass the properly configured OpenAI client
        temperature=0.7,  # Add temperature for better responses
    )

    # Configure Text-to-Speech (Cartesia with Spanish voice)
    # Cartesia has a free tier and supports Spanish
    # Voice ID: 95856005-0332-41b0-935f-352e296aa0df is a Spanish voice
    tts_config = cartesia.TTS(
        language=Config.TTS_LANGUAGE,  # "es" for Spanish
        voice="95856005-0332-41b0-935f-352e296aa0df",  # Spanish voice
    )

    # Set up the voice AI pipeline
    session = AgentSession(
        # Speech-to-text: Whisper with Spanish language support
        stt=stt_config,
        # Large Language Model: Ollama with Llama 3 (free, local)
        llm=llm_config,
        # Text-to-speech: LiveKit Inference TTS with Spanish voice
        tts=tts_config,
        # Multilingual turn detection for Spanish
        turn_detection=MultilingualModel(),
        # Voice Activity Detection
        vad=ctx.proc.userdata["vad"],
        # Allow preemptive generation for lower latency
        preemptive_generation=True,
    )

    # Start the session with the ERP Voice Agent
    await session.start(
        agent=ERPVoiceAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Noise cancellation for better audio quality
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    logger.info("ERP voice session started successfully")

    # Join the room and establish WebRTC connection
    await ctx.connect()

    logger.info("Connected to room, ready for voice interaction")


if __name__ == "__main__":
    cli.run_app(server)
