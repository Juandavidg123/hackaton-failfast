"""Example usage of SupabaseRepository and data models.

This script demonstrates how to use the repository and data models
for the ERP Voice Chat System.
"""

from datetime import datetime

from config import Config
from models import DuplicateGroup, ERPRecord, Inconsistency, InconsistencyType
from repositories import SupabaseRepository


def main():
    """Demonstrate repository usage."""
    # Initialize repository with configuration
    supabase_url, supabase_key = Config.get_supabase_config()
    
    # Check if configuration is valid
    if not supabase_url or supabase_url.startswith("postgresql://"):
        print("⚠ Note: Valid Supabase URL not configured. Skipping database operations.")
        print("   Configure SUPABASE_URL in .env to test actual database operations.\n")
        repo = None
    else:
        repo = SupabaseRepository(supabase_url, supabase_key)
        print("Repository initialized successfully!")

    # Example 1: Create a customer record
    print("\n--- Example 1: Creating a customer ---")
    customer_data = {
        "name": "Juan Pérez",
        "email": "juan.perez@example.com",
        "phone": "+34 600 123 456",
        "address": "Calle Mayor 1, Madrid",
    }

    # Uncomment to actually insert (requires database connection)
    # customer = repo.insert("customers", customer_data)
    # print(f"Created customer: {customer['id']}")

    # Example 2: Query customers
    print("\n--- Example 2: Querying customers ---")
    # Uncomment to actually query (requires database connection)
    # customers = repo.query("customers", {"email": "juan.perez@example.com"})
    # print(f"Found {len(customers)} customers")

    # Example 3: Create a duplicate group
    print("\n--- Example 3: Creating a duplicate group ---")
    duplicate_group = DuplicateGroup(
        id="123e4567-e89b-12d3-a456-426614174000",
        table_name="customers",
        record_ids=["id1", "id2"],
        similarity_score=85.5,
        matching_fields={"name": "Juan Pérez", "email": "juan.perez@example.com"},
        status="pending",
        created_at=datetime.now(),
    )

    duplicate_dict = duplicate_group.to_dict()
    print(f"Duplicate group: {duplicate_dict['table_name']}")
    print(f"Similarity: {duplicate_dict['similarity_score']}%")

    # Uncomment to actually insert (requires database connection)
    # repo.insert("duplicate_groups", duplicate_dict)

    # Example 4: Create an inconsistency
    print("\n--- Example 4: Creating an inconsistency ---")
    inconsistency = Inconsistency(
        id="123e4567-e89b-12d3-a456-426614174001",
        type=InconsistencyType.CALCULATION,
        table_name="orders",
        record_id="order123",
        field_name="total_amount",
        description="El total del pedido no coincide con la suma de los artículos",
        suggested_fix={"total_amount": 100.00},
        status="pending",
        created_at=datetime.now(),
    )

    inconsistency_dict = inconsistency.to_dict()
    print(f"Inconsistency type: {inconsistency_dict['type']}")
    print(f"Description: {inconsistency_dict['description']}")

    # Uncomment to actually insert (requires database connection)
    # repo.insert("inconsistencies", inconsistency_dict)

    # Example 5: Working with ERP records
    print("\n--- Example 5: Working with ERP records ---")
    record_data = {
        "id": "customer123",
        "name": "María García",
        "email": "maria.garcia@example.com",
        "phone": "+34 600 987 654",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    erp_record = ERPRecord.from_dict("customers", record_data)
    print(f"ERP Record ID: {erp_record.id}")
    print(f"Table: {erp_record.table_name}")
    print(f"Data: {erp_record.data['name']}")

    print("\n✓ All examples completed successfully!")


if __name__ == "__main__":
    main()
