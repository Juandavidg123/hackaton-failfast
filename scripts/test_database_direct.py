"""Test database operations using direct PostgreSQL connection."""

import os
from datetime import datetime
from uuid import uuid4

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def main():
    """Test database operations."""
    db_url = os.getenv("SUPABASE_DB_URL")

    print("🔌 Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        cursor = conn.cursor()

        # Cleanup: Delete test data from previous runs
        print("\n🧹 Cleaning up test data from previous runs...")
        cursor.execute("DELETE FROM order_items;")
        cursor.execute("DELETE FROM orders;")
        cursor.execute("DELETE FROM products;")
        cursor.execute("DELETE FROM customers;")
        cursor.execute("DELETE FROM duplicate_groups;")
        cursor.execute("DELETE FROM inconsistencies;")
        conn.commit()
        print("✓ Cleanup complete\n")

        # Test 1: Insert customer
        print("\n" + "=" * 60)
        print("TEST 1: Insert Customer")
        print("=" * 60)

        customer_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO customers (id, name, email, phone, address)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, email, phone;
        """,
            (
                customer_id,
                "María García",
                "maria.garcia@example.com",
                "+34 600 987 654",
                "Calle Gran Vía 10, Madrid",
            ),
        )

        customer = cursor.fetchone()
        conn.commit()
        print(f"✓ Created customer: {customer[0]}")
        print(f"  Name: {customer[1]}")
        print(f"  Email: {customer[2]}")

        # Test 2: Insert product
        print("\n" + "=" * 60)
        print("TEST 2: Insert Product")
        print("=" * 60)

        product_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO products (id, name, sku, price, inventory_count)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, sku, price;
        """,
            (product_id, "MacBook Pro 16", "APPLE-MBP16-001", 2499.99, 5),
        )

        product = cursor.fetchone()
        conn.commit()
        print(f"✓ Created product: {product[0]}")
        print(f"  Name: {product[1]}")
        print(f"  SKU: {product[2]}")
        print(f"  Price: ${product[3]}")

        # Test 3: Insert order
        print("\n" + "=" * 60)
        print("TEST 3: Insert Order")
        print("=" * 60)

        order_id = str(uuid4())
        cursor.execute(
            """
            INSERT INTO orders (id, customer_id, order_date, total_amount, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, total_amount, status;
        """,
            (order_id, customer_id, datetime.now(), 2499.99, "pending"),
        )

        order = cursor.fetchone()
        conn.commit()
        print(f"✓ Created order: {order[0]}")
        print(f"  Total: ${order[1]}")
        print(f"  Status: {order[2]}")

        # Test 4: Insert order item
        print("\n" + "=" * 60)
        print("TEST 4: Insert Order Item")
        print("=" * 60)

        cursor.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, quantity, line_total;
        """,
            (order_id, product_id, 1, 2499.99, 2499.99),
        )

        order_item = cursor.fetchone()
        conn.commit()
        print(f"✓ Created order item: {order_item[0]}")
        print(f"  Quantity: {order_item[1]}")
        print(f"  Line total: ${order_item[2]}")

        # Test 5: Insert duplicate group
        print("\n" + "=" * 60)
        print("TEST 5: Insert Duplicate Group")
        print("=" * 60)

        cursor.execute(
            """
            INSERT INTO duplicate_groups 
            (table_name, record_ids, similarity_score, matching_fields, status)
            VALUES (%s, ARRAY[%s::uuid, %s::uuid], %s, %s::jsonb, %s)
            RETURNING id, table_name, similarity_score;
        """,
            (
                "customers",
                customer_id,
                customer_id,
                92.5,
                '{"name": "María García", "email": "maria.garcia@example.com"}',
                "pending",
            ),
        )

        duplicate = cursor.fetchone()
        conn.commit()
        print(f"✓ Created duplicate group: {duplicate[0]}")
        print(f"  Table: {duplicate[1]}")
        print(f"  Similarity: {duplicate[2]}%")

        # Test 6: Insert inconsistency
        print("\n" + "=" * 60)
        print("TEST 6: Insert Inconsistency")
        print("=" * 60)

        cursor.execute(
            """
            INSERT INTO inconsistencies 
            (type, table_name, record_id, field_name, description, suggested_fix, status)
            VALUES (%s, %s, %s::uuid, %s, %s, %s::jsonb, %s)
            RETURNING id, type, description;
        """,
            (
                "format",
                "customers",
                customer_id,
                "phone",
                "Formato de teléfono no estándar",
                '{"phone": "+34600987654"}',
                "pending",
            ),
        )

        inconsistency = cursor.fetchone()
        conn.commit()
        print(f"✓ Created inconsistency: {inconsistency[0]}")
        print(f"  Type: {inconsistency[1]}")
        print(f"  Description: {inconsistency[2]}")

        # Test 7: Query data
        print("\n" + "=" * 60)
        print("TEST 7: Query All Customers")
        print("=" * 60)

        cursor.execute("SELECT id, name, email FROM customers;")
        customers = cursor.fetchall()
        print(f"✓ Found {len(customers)} customer(s):")
        for cust in customers:
            print(f"  • {cust[1]} ({cust[2]})")

        # Test 8: Query duplicates
        print("\n" + "=" * 60)
        print("TEST 8: Query Duplicate Groups")
        print("=" * 60)

        cursor.execute(
            "SELECT id, table_name, similarity_score, status FROM duplicate_groups;"
        )
        duplicates = cursor.fetchall()
        print(f"✓ Found {len(duplicates)} duplicate group(s):")
        for dup in duplicates:
            print(f"  • {dup[1]}: {dup[2]}% similarity ({dup[3]})")

        # Test 9: Query inconsistencies
        print("\n" + "=" * 60)
        print("TEST 9: Query Inconsistencies")
        print("=" * 60)

        cursor.execute("SELECT id, type, description, status FROM inconsistencies;")
        inconsistencies = cursor.fetchall()
        print(f"✓ Found {len(inconsistencies)} inconsistenc(ies):")
        for inc in inconsistencies:
            print(f"  • {inc[1]}: {inc[2]} ({inc[3]})")

        # Test 10: Update customer
        print("\n" + "=" * 60)
        print("TEST 10: Update Customer")
        print("=" * 60)

        cursor.execute(
            """
            UPDATE customers 
            SET phone = %s 
            WHERE id = %s
            RETURNING id, name, phone;
        """,
            ("+34 600 111 222", customer_id),
        )

        updated = cursor.fetchone()
        conn.commit()
        print(f"✓ Updated customer: {updated[0]}")
        print(f"  Name: {updated[1]}")
        print(f"  New phone: {updated[2]}")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📊 Database Summary:")
        print(f"  • Customers: {len(customers)}")
        print(f"  • Duplicate Groups: {len(duplicates)}")
        print(f"  • Inconsistencies: {len(inconsistencies)}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    main()
