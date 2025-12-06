#!/usr/bin/env python3
"""Seed script for creating sample ERP data with intentional duplicates and inconsistencies.

This script creates:
- Sample customers (with intentional duplicates)
- Sample products (with intentional duplicates)
- Sample orders (with intentional calculation inconsistencies)
- Sample order items (with referential and calculation issues)

Usage:
    uv run python scripts/seed_sample_data.py
"""

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def convert_decimals_to_float(data):
    """Convert all Decimal values in a dict or list to float for JSON serialization."""
    if isinstance(data, list):
        return [convert_decimals_to_float(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_decimals_to_float(value) for key, value in data.items()}
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data

from config import Config
from repositories.supabase_repository import SupabaseRepository


def create_sample_customers(repo: SupabaseRepository) -> list[dict]:
    """Create sample customers with intentional duplicates.
    
    Returns:
        List of created customer records
    """
    print("Creating sample customers...")
    
    customers = [
        # Normal customers
        {
            "name": "María García López",
            "email": "maria.garcia@example.com",
            "phone": "+34 612 345 678",
            "address": "Calle Mayor 123, Madrid, España"
        },
        {
            "name": "Juan Martínez Rodríguez",
            "email": "juan.martinez@example.com",
            "phone": "+34 623 456 789",
            "address": "Avenida Libertad 45, Barcelona, España"
        },
        {
            "name": "Carmen Sánchez Pérez",
            "email": "carmen.sanchez@example.com",
            "phone": "+34 634 567 890",
            "address": "Plaza España 7, Valencia, España"
        },
        
        # DUPLICATE 1: Exact duplicate with slight name variation
        {
            "name": "Maria Garcia Lopez",  # Same person, different formatting
            "email": "maria.garcia@example.com",  # Same email
            "phone": "612345678",  # Same phone, different format
            "address": "Calle Mayor 123, Madrid"
        },
        
        # DUPLICATE 2: Similar customer with typo
        {
            "name": "Juan Martinez Rodriguez",  # Same person, no accents
            "email": "j.martinez@example.com",  # Different email
            "phone": "+34 623 456 789",  # Same phone
            "address": "Av. Libertad 45, Barcelona"
        },
        
        {
            "name": "Ana Fernández Torres",
            "email": "ana.fernandez@example.com",
            "phone": "+34 645 678 901",
            "address": "Calle Sol 89, Sevilla, España"
        },
        
        # DUPLICATE 3: Duplicate with missing data
        {
            "name": "Ana Fernandez",  # Same person, incomplete name
            "email": "ana.fernandez@example.com",  # Same email
            "phone": None,  # Missing phone
            "address": None  # Missing address
        },
        
        {
            "name": "Pedro González Ruiz",
            "email": "pedro.gonzalez@example.com",
            "phone": "+34 656 789 012",
            "address": "Paseo Gracia 234, Barcelona, España"
        },
        
        {
            "name": "Laura Díaz Moreno",
            "email": "laura.diaz@example.com",
            "phone": "+34 667 890 123",
            "address": "Calle Luna 56, Málaga, España"
        },
        
        # Customer with invalid email format (for format inconsistency testing)
        {
            "name": "Roberto Jiménez Castro",
            "email": "roberto.jimenez.invalid",  # Invalid email format
            "phone": "+34 678 901 234",
            "address": "Avenida Mar 12, Alicante, España"
        }
    ]
    
    created_customers = repo.bulk_insert("customers", customers)
    print(f"Created {len(created_customers)} customers")
    return created_customers


def create_sample_products(repo: SupabaseRepository) -> list[dict]:
    """Create sample products with intentional duplicates.
    
    Returns:
        List of created product records
    """
    print("Creating sample products...")
    
    products = [
        # Normal products
        {
            "name": "Laptop HP ProBook 450",
            "sku": "LAP-HP-450",
            "price": Decimal("899.99"),
            "inventory_count": 25
        },
        {
            "name": "Mouse Logitech MX Master 3",
            "sku": "MOU-LOG-MX3",
            "price": Decimal("99.99"),
            "inventory_count": 150
        },
        {
            "name": "Teclado Mecánico Corsair K95",
            "sku": "KEY-COR-K95",
            "price": Decimal("179.99"),
            "inventory_count": 75
        },
        
        # DUPLICATE 1: Same product, different SKU
        {
            "name": "Laptop HP Probook 450",  # Slight variation in capitalization
            "sku": "LAP-HP450",  # Different SKU format
            "price": Decimal("899.99"),  # Same price
            "inventory_count": 30  # Different inventory
        },
        
        {
            "name": "Monitor Dell UltraSharp 27",
            "sku": "MON-DEL-U27",
            "price": Decimal("449.99"),
            "inventory_count": 40
        },
        
        # DUPLICATE 2: Duplicate with typo
        {
            "name": "Mouse Logitech MX Master3",  # Missing space
            "sku": "MOU-LOG-MX3-ALT",  # Different SKU
            "price": Decimal("99.99"),
            "inventory_count": 145  # Slightly different inventory
        },
        
        {
            "name": "Webcam Logitech C920",
            "sku": "WEB-LOG-C920",
            "price": Decimal("79.99"),
            "inventory_count": 60
        },
        
        {
            "name": "Auriculares Sony WH-1000XM4",
            "sku": "AUD-SON-XM4",
            "price": Decimal("349.99"),
            "inventory_count": 35
        },
        
        # Product with negative inventory (business rule violation)
        {
            "name": "Cable HDMI 2m",
            "sku": "CAB-HDMI-2M",
            "price": Decimal("12.99"),
            "inventory_count": -5  # INCONSISTENCY: Negative inventory
        },
        
        {
            "name": "Hub USB-C 7 puertos",
            "sku": "HUB-USBC-7P",
            "price": Decimal("45.99"),
            "inventory_count": 90
        }
    ]
    
    # Convert Decimal to float for JSON serialization
    products_json = convert_decimals_to_float(products)
    
    created_products = repo.bulk_insert("products", products_json)
    print(f"Created {len(created_products)} products")
    return created_products


def create_sample_orders(repo: SupabaseRepository, customers: list[dict], products: list[dict]) -> list[dict]:
    """Create sample orders with intentional inconsistencies.
    
    Args:
        customers: List of customer records
        products: List of product records
        
    Returns:
        List of created order records
    """
    print("Creating sample orders...")
    
    # Use first few customers for orders
    base_date = datetime.now() - timedelta(days=30)
    
    orders = [
        # Normal order
        {
            "customer_id": customers[0]["id"],
            "order_date": (base_date + timedelta(days=1)).isoformat(),
            "total_amount": Decimal("999.98"),  # Will match order items
            "status": "completed"
        },
        # Order with calculation inconsistency
        {
            "customer_id": customers[1]["id"],
            "order_date": (base_date + timedelta(days=3)).isoformat(),
            "total_amount": Decimal("500.00"),  # INCONSISTENCY: Won't match order items sum
            "status": "completed"
        },
        # Normal order
        {
            "customer_id": customers[2]["id"],
            "order_date": (base_date + timedelta(days=5)).isoformat(),
            "total_amount": Decimal("179.99"),
            "status": "pending"
        },
        # Order with future date (business rule violation)
        {
            "customer_id": customers[5]["id"],
            "order_date": (datetime.now() + timedelta(days=10)).isoformat(),  # INCONSISTENCY: Future date
            "total_amount": Decimal("449.99"),
            "status": "pending"
        },
        # Order with referential integrity issue (will be created with invalid customer_id)
        {
            "customer_id": "00000000-0000-0000-0000-000000000000",  # INCONSISTENCY: Non-existent customer
            "order_date": (base_date + timedelta(days=7)).isoformat(),
            "total_amount": Decimal("99.99"),
            "status": "pending"
        },
        # Normal order
        {
            "customer_id": customers[7]["id"],
            "order_date": (base_date + timedelta(days=10)).isoformat(),
            "total_amount": Decimal("529.98"),
            "status": "completed"
        }
    ]
    
    # Convert Decimal to float for JSON serialization
    orders_json = convert_decimals_to_float(orders)
    
    created_orders = []
    for order in orders_json:
        try:
            created_order = repo.insert("orders", order)
            created_orders.append(created_order)
        except Exception as e:
            # Some orders might fail due to referential integrity
            # This is intentional for testing
            print(f"  Note: Order with customer_id {order['customer_id']} may have issues (expected for testing)")
            # Try to insert anyway for testing purposes
            created_orders.append(order)
    
    print(f"Created {len(created_orders)} orders")
    return created_orders


def create_sample_order_items(repo: SupabaseRepository, orders: list[dict], products: list[dict]) -> list[dict]:
    """Create sample order items with intentional inconsistencies.
    
    Args:
        orders: List of order records
        products: List of product records
        
    Returns:
        List of created order item records
    """
    print("Creating sample order items...")
    
    order_items = [
        # Order 1 items (total should be 999.98)
        {
            "order_id": orders[0]["id"],
            "product_id": products[0]["id"],  # Laptop HP ProBook 450
            "quantity": 1,
            "unit_price": Decimal("899.99"),
            "line_total": Decimal("899.99")
        },
        {
            "order_id": orders[0]["id"],
            "product_id": products[1]["id"],  # Mouse Logitech
            "quantity": 1,
            "unit_price": Decimal("99.99"),
            "line_total": Decimal("99.99")
        },
        
        # Order 2 items (total should be 629.98, but order says 500.00 - INCONSISTENCY)
        {
            "order_id": orders[1]["id"],
            "product_id": products[4]["id"],  # Monitor Dell
            "quantity": 1,
            "unit_price": Decimal("449.99"),
            "line_total": Decimal("449.99")
        },
        {
            "order_id": orders[1]["id"],
            "product_id": products[2]["id"],  # Teclado Corsair
            "quantity": 1,
            "unit_price": Decimal("179.99"),
            "line_total": Decimal("179.99")
        },
        
        # Order 3 items (total should be 179.99)
        {
            "order_id": orders[2]["id"],
            "product_id": products[2]["id"],  # Teclado Corsair
            "quantity": 1,
            "unit_price": Decimal("179.99"),
            "line_total": Decimal("179.99")
        },
        
        # Order 4 items (total should be 449.99)
        {
            "order_id": orders[3]["id"],
            "product_id": products[4]["id"],  # Monitor Dell
            "quantity": 1,
            "unit_price": Decimal("449.99"),
            "line_total": Decimal("449.99")
        },
        
        # Order 6 items (total should be 529.98)
        {
            "order_id": orders[5]["id"],
            "product_id": products[7]["id"],  # Auriculares Sony
            "quantity": 1,
            "unit_price": Decimal("349.99"),
            "line_total": Decimal("349.99")
        },
        {
            "order_id": orders[5]["id"],
            "product_id": products[2]["id"],  # Teclado Corsair
            "quantity": 1,
            "unit_price": Decimal("179.99"),
            "line_total": Decimal("179.99")
        },
        
        # Order item with calculation inconsistency
        {
            "order_id": orders[5]["id"],
            "product_id": products[1]["id"],  # Mouse Logitech
            "quantity": 3,
            "unit_price": Decimal("99.99"),
            "line_total": Decimal("250.00")  # INCONSISTENCY: Should be 299.97
        },
        
        # Order item with non-existent product (referential integrity issue)
        {
            "order_id": orders[2]["id"],
            "product_id": "00000000-0000-0000-0000-000000000000",  # INCONSISTENCY: Non-existent product
            "quantity": 1,
            "unit_price": Decimal("50.00"),
            "line_total": Decimal("50.00")
        }
    ]
    
    # Convert Decimal to float for JSON serialization
    order_items_json = convert_decimals_to_float(order_items)
    
    created_items = []
    for item in order_items_json:
        try:
            created_item = repo.insert("order_items", item)
            created_items.append(created_item)
        except Exception as e:
            # Some items might fail due to referential integrity
            print(f"  Note: Order item may have referential integrity issues (expected for testing)")
            created_items.append(item)
    
    print(f"Created {len(created_items)} order items")
    return created_items


def seed_database():
    """Main function to seed the database with sample data."""
    print("=" * 60)
    print("ERP Voice Chat - Sample Data Seeding")
    print("=" * 60)
    print()
    
    # Initialize repository
    supabase_url, supabase_key = Config.get_supabase_config()
    
    if not supabase_url or not supabase_key:
        print("ERROR: Supabase configuration not found!")
        print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")
        sys.exit(1)
    
    repo = SupabaseRepository(supabase_url, supabase_key)
    
    print("Connected to Supabase")
    print()
    
    # Create sample data
    customers = create_sample_customers(repo)
    print()
    
    products = create_sample_products(repo)
    print()
    
    orders = create_sample_orders(repo, customers, products)
    print()
    
    order_items = create_sample_order_items(repo, orders, products)
    print()
    
    print("=" * 60)
    print("Sample Data Summary")
    print("=" * 60)
    print(f"Customers created: {len(customers)}")
    print(f"  - Intentional duplicates: 3 groups")
    print(f"  - Format issues: 1 (invalid email)")
    print()
    print(f"Products created: {len(products)}")
    print(f"  - Intentional duplicates: 2 groups")
    print(f"  - Business rule violations: 1 (negative inventory)")
    print()
    print(f"Orders created: {len(orders)}")
    print(f"  - Calculation inconsistencies: 1")
    print(f"  - Business rule violations: 1 (future date)")
    print(f"  - Referential integrity issues: 1 (invalid customer)")
    print()
    print(f"Order items created: {len(order_items)}")
    print(f"  - Calculation inconsistencies: 1")
    print(f"  - Referential integrity issues: 1 (invalid product)")
    print()
    print("=" * 60)
    print("Seeding completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
