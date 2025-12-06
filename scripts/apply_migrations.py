"""Apply database migrations to Supabase."""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def apply_migration(conn, migration_file: Path) -> None:
    """Apply a single migration file.

    Args:
        conn: Database connection
        migration_file: Path to migration SQL file
    """
    print(f"\n📄 Applying migration: {migration_file.name}")

    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
        conn.commit()
        print(f"✓ Successfully applied {migration_file.name}")
    except Exception as e:
        conn.rollback()
        print(f"✗ Error applying {migration_file.name}: {e}")
        raise


def main():
    """Apply all migrations in order."""
    # Get database URL from environment
    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url or not db_url.startswith("postgresql://"):
        print("❌ Error: SUPABASE_DB_URL must be a PostgreSQL connection string")
        print("   Example: postgresql://user:password@host:port/database")
        sys.exit(1)

    print("🔌 Connecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        print("✓ Connected successfully")

        # Get migration files in order
        migrations_dir = Path("migrations")
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            print("⚠ No migration files found in migrations/")
            sys.exit(0)

        print(f"\n📋 Found {len(migration_files)} migration(s) to apply")

        # Apply each migration
        for migration_file in migration_files:
            apply_migration(conn, migration_file)

        print("\n✅ All migrations applied successfully!")

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
