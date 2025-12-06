#!/usr/bin/env python3
"""Reset database script - clears all ERP and data quality tables.

This script removes all data from:
- order_items
- orders
- products
- customers
- duplicate_groups
- inconsistencies

Usage:
    uv run python scripts/reset_database.py
    uv run python scripts/reset_database.py --confirm  # Skip confirmation prompt
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config
from repositories.supabase_repository import SupabaseRepository


def reset_database(skip_confirmation: bool = False):
    """Reset the database by clearing all tables.
    
    Args:
        skip_confirmation: If True, skip the confirmation prompt
    """
    print("=" * 60)
    print("ERP Voice Chat - Database Reset")
    print("=" * 60)
    print()
    print("WARNING: This will delete ALL data from the following tables:")
    print("  - order_items")
    print("  - orders")
    print("  - products")
    print("  - customers")
    print("  - duplicate_groups")
    print("  - inconsistencies")
    print()
    
    if not skip_confirmation:
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Reset cancelled.")
            sys.exit(0)
    
    print()
    print("Connecting to database...")
    
    # Initialize repository
    supabase_url, supabase_key = Config.get_supabase_config()
    
    if not supabase_url or not supabase_key:
        print("ERROR: Supabase configuration not found!")
        print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")
        sys.exit(1)
    
    repo = SupabaseRepository(supabase_url, supabase_key)
    print("Connected to Supabase")
    print()
    
    # Delete data in correct order (respecting foreign key constraints)
    tables_to_clear = [
        "order_items",      # Must be deleted before orders
        "orders",           # Must be deleted before customers
        "products",         # Independent
        "customers",        # Independent
        "duplicate_groups", # Independent
        "inconsistencies"   # Independent
    ]
    
    print("Clearing tables...")
    for table in tables_to_clear:
        try:
            # Get all records
            records = repo.get_all(table)
            count = len(records)
            
            if count > 0:
                # Delete all records
                for record in records:
                    repo.delete(table, record["id"])
                print(f"  ✓ Cleared {count} records from {table}")
            else:
                print(f"  ✓ {table} was already empty")
                
        except Exception as e:
            print(f"  ✗ Error clearing {table}: {str(e)}")
    
    print()
    print("=" * 60)
    print("Database reset completed!")
    print("=" * 60)
    print()
    print("To populate with sample data, run:")
    print("  uv run python scripts/seed_sample_data.py")


if __name__ == "__main__":
    # Check for --confirm flag
    skip_confirmation = "--confirm" in sys.argv
    reset_database(skip_confirmation)
