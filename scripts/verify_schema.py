"""Verify database schema after migrations."""

import os
import sys

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def verify_schema(conn) -> bool:
    """Verify that all expected tables exist.

    Args:
        conn: Database connection

    Returns:
        True if all tables exist
    """
    expected_tables = [
        "customers",
        "products",
        "orders",
        "order_items",
        "duplicate_groups",
        "inconsistencies",
    ]

    print("\n🔍 Verifying database schema...")

    with conn.cursor() as cursor:
        # Get all tables in public schema
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """
        )

        existing_tables = [row[0] for row in cursor.fetchall()]

        print(f"\n📊 Found {len(existing_tables)} tables in database:")
        for table in existing_tables:
            print(f"  • {table}")

        # Check for expected tables
        print("\n✓ Checking expected tables:")
        all_found = True
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (MISSING)")
                all_found = False

        return all_found


def get_table_info(conn, table_name: str) -> None:
    """Get column information for a table.

    Args:
        conn: Database connection
        table_name: Name of the table
    """
    print(f"\n📋 Table: {table_name}")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """,
            (table_name,),
        )

        columns = cursor.fetchall()
        print(f"  Columns ({len(columns)}):")
        for col_name, data_type, is_nullable in columns:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"    • {col_name}: {data_type} ({nullable})")


def main():
    """Verify database schema."""
    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url or not db_url.startswith("postgresql://"):
        print("❌ Error: SUPABASE_DB_URL must be a PostgreSQL connection string")
        sys.exit(1)

    print("🔌 Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        print("✓ Connected successfully")

        # Verify schema
        if verify_schema(conn):
            print("\n✅ All expected tables exist!")

            # Show details for key tables
            print("\n" + "=" * 60)
            print("TABLE DETAILS")
            print("=" * 60)

            for table in ["customers", "duplicate_groups", "inconsistencies"]:
                get_table_info(conn, table)

            print("\n✅ Schema verification complete!")
        else:
            print("\n❌ Some expected tables are missing!")
            sys.exit(1)

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()
            print("\n🔌 Database connection closed")


if __name__ == "__main__":
    main()
