"""Test repository with live database operations."""

from datetime import datetime

from config import Config
from models import DuplicateGroup, ERPRecord, Inconsistency, InconsistencyType
from repositories import SupabaseRepository


def main():
    """Test repository operations with live database."""
    print("🔌 Initializing repository...")

    # Initialize repository
    supabase_url, supabase_key = Config.get_supabase_config()
    repo = SupabaseRepository(supabase_url, supabase_key)

    print("✓ Repository initialized\n")

    # Test 1: Insert a customer
    print("=" * 60)
    print("TEST 1: Insert Customer")
    print("=" * 60)

    customer_data = {
        "name": "Juan Pérez",
        "email": "juan.perez@example.com",
        "phone": "+34 600 123 456",
        "address": "Calle Mayor 1, Madrid",
    }

    customer = repo.insert("customers", customer_data)
    print(f"✓ Created customer: {customer['id']}")
    print(f"  Name: {customer['name']}")
    print(f"  Email: {customer['email']}")

    # Test 2: Query customer
    print("\n" + "=" * 60)
    print("TEST 2: Query Customer")
    print("=" * 60)

    customers = repo.query("customers", {"email": "juan.perez@example.com"})
    print(f"✓ Found {len(customers)} customer(s)")
    for c in customers:
        print(f"  • {c['name']} ({c['email']})")

    # Test 3: Insert a product
    print("\n" + "=" * 60)
    print("TEST 3: Insert Product")
    print("=" * 60)

    product_data = {
        "name": "Laptop Dell XPS 15",
        "sku": "DELL-XPS15-001",
        "price": 1299.99,
        "inventory_count": 10,
    }

    product = repo.insert("products", product_data)
    print(f"✓ Created product: {product['id']}")
    print(f"  Name: {product['name']}")
    print(f"  SKU: {product['sku']}")
    print(f"  Price: ${product['price']}")

    # Test 4: Create duplicate group
    print("\n" + "=" * 60)
    print("TEST 4: Create Duplicate Group")
    print("=" * 60)

    duplicate_group = DuplicateGroup(
        id=None,  # Will be generated
        table_name="customers",
        record_ids=[customer["id"], customer["id"]],  # Simulated duplicate
        similarity_score=95.5,
        matching_fields={"name": "Juan Pérez", "email": "juan.perez@example.com"},
        status="pending",
        created_at=datetime.now(),
    )

    duplicate_dict = duplicate_group.to_dict()
    duplicate_dict.pop("id")  # Remove None id, let DB generate it

    saved_duplicate = repo.insert("duplicate_groups", duplicate_dict)
    print(f"✓ Created duplicate group: {saved_duplicate['id']}")
    print(f"  Table: {saved_duplicate['table_name']}")
    print(f"  Similarity: {saved_duplicate['similarity_score']}%")

    # Test 5: Create inconsistency
    print("\n" + "=" * 60)
    print("TEST 5: Create Inconsistency")
    print("=" * 60)

    inconsistency = Inconsistency(
        id=None,  # Will be generated
        type=InconsistencyType.FORMAT,
        table_name="customers",
        record_id=customer["id"],
        field_name="phone",
        description="Formato de teléfono no válido",
        suggested_fix={"phone": "+34600123456"},
        status="pending",
        created_at=datetime.now(),
    )

    inconsistency_dict = inconsistency.to_dict()
    inconsistency_dict.pop("id")  # Remove None id

    saved_inconsistency = repo.insert("inconsistencies", inconsistency_dict)
    print(f"✓ Created inconsistency: {saved_inconsistency['id']}")
    print(f"  Type: {saved_inconsistency['type']}")
    print(f"  Description: {saved_inconsistency['description']}")

    # Test 6: Update customer
    print("\n" + "=" * 60)
    print("TEST 6: Update Customer")
    print("=" * 60)

    updated_customer = repo.update(
        "customers", customer["id"], {"phone": "+34 600 999 888"}
    )
    print(f"✓ Updated customer: {updated_customer['id']}")
    print(f"  New phone: {updated_customer['phone']}")

    # Test 7: Get by ID
    print("\n" + "=" * 60)
    print("TEST 7: Get Customer by ID")
    print("=" * 60)

    fetched_customer = repo.get_by_id("customers", customer["id"])
    print(f"✓ Fetched customer: {fetched_customer['id']}")
    print(f"  Name: {fetched_customer['name']}")
    print(f"  Phone: {fetched_customer['phone']}")

    # Test 8: Query all duplicates
    print("\n" + "=" * 60)
    print("TEST 8: Query All Duplicate Groups")
    print("=" * 60)

    all_duplicates = repo.get_all("duplicate_groups")
    print(f"✓ Found {len(all_duplicates)} duplicate group(s)")
    for dup in all_duplicates:
        print(f"  • {dup['table_name']}: {dup['similarity_score']}% similarity")

    # Test 9: Query all inconsistencies
    print("\n" + "=" * 60)
    print("TEST 9: Query All Inconsistencies")
    print("=" * 60)

    all_inconsistencies = repo.get_all("inconsistencies")
    print(f"✓ Found {len(all_inconsistencies)} inconsistenc(ies)")
    for inc in all_inconsistencies:
        print(f"  • {inc['type']}: {inc['description']}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
