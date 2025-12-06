#!/usr/bin/env python3
"""Combined script to reset database and seed with sample data.

This script:
1. Clears all existing data from ERP and data quality tables
2. Seeds the database with sample data including intentional duplicates and inconsistencies

Usage:
    uv run python scripts/reset_and_seed.py
    uv run python scripts/reset_and_seed.py --confirm  # Skip confirmation prompt
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config
from repositories.supabase_repository import SupabaseRepository


def clear_all_tables(repo: SupabaseRepository):
    """Clear all data from ERP and data quality tables.
    
    Args:
        repo: Supabase repository instance
    """
    print("Clearing existing data...")
    
    # Delete data in correct order (respecting foreign key constraints)
    tables_to_clear = [
        "order_items",      # Must be deleted before orders
        "orders",           # Must be deleted before customers
        "products",         # Independent
        "customers",        # Independent
        "duplicate_groups", # Independent
        "inconsistencies"   # Independent
    ]
    
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


def main():
    """Main function to reset and seed the database."""
    skip_confirmation = "--confirm" in sys.argv
    
    print("=" * 60)
    print("ERP Voice Chat - Reset and Seed Database")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Delete ALL existing data")
    print("  2. Create fresh sample data with test cases")
    print()
    
    if not skip_confirmation:
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Operation cancelled.")
            sys.exit(0)
    
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
    
    # Step 1: Clear existing data
    clear_all_tables(repo)
    
    # Step 2: Import and run seeding
    print("Seeding sample data...")
    print()
    
    # Import seed functions
    from seed_sample_data import (
        create_sample_customers,
        create_sample_products,
        create_sample_orders,
        create_sample_order_items
    )
    
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
    print("Reset and seed completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
