# Database Scripts

This directory contains utility scripts for managing the ERP Voice Chat database.

## Available Scripts

### 1. Seed Sample Data

**File:** `seed_sample_data.py`

Creates sample ERP data with intentional duplicates and inconsistencies for testing the duplicate detection and inconsistency analysis features.

**Usage:**
```bash
uv run python scripts/seed_sample_data.py
```

**What it creates:**
- **10 Customers** including:
  - 3 groups of intentional duplicates (same person with variations)
  - 1 customer with invalid email format
  
- **10 Products** including:
  - 2 groups of intentional duplicates (same product with variations)
  - 1 product with negative inventory (business rule violation)
  
- **6 Orders** including:
  - 1 order with calculation inconsistency (total doesn't match items)
  - 1 order with future date (business rule violation)
  - 1 order with non-existent customer (referential integrity issue)
  
- **10 Order Items** including:
  - 1 item with calculation inconsistency (line total doesn't match quantity × price)
  - 1 item with non-existent product (referential integrity issue)

### 2. Reset Database

**File:** `reset_database.py`

Clears all data from ERP and data quality tables, returning the database to an empty state.

**Usage:**
```bash
# With confirmation prompt
uv run python scripts/reset_database.py

# Skip confirmation (useful for automation)
uv run python scripts/reset_database.py --confirm
```

**Tables cleared:**
- `order_items`
- `orders`
- `products`
- `customers`
- `duplicate_groups`
- `inconsistencies`

### 3. Reset and Seed (Combined)

**File:** `reset_and_seed.py`

Combines both operations: first clears all data, then seeds with fresh sample data.

**Usage:**
```bash
# With confirmation prompt
uv run python scripts/reset_and_seed.py

# Skip confirmation (useful for automation)
uv run python scripts/reset_and_seed.py --confirm
```

This is the recommended way to get a clean, consistent test environment.

## Prerequisites

Before running these scripts, ensure:

1. **Environment variables are set** in your `.env` file:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   ```

2. **Database migrations have been applied**:
   ```bash
   uv run python scripts/apply_migrations.py
   ```

3. **Dependencies are installed**:
   ```bash
   uv sync
   ```

## Testing Workflow

### Initial Setup
```bash
# 1. Apply migrations
uv run python scripts/apply_migrations.py

# 2. Seed sample data
uv run python scripts/seed_sample_data.py
```

### Reset for Fresh Testing
```bash
# Quick reset and seed
uv run python scripts/reset_and_seed.py --confirm
```

### Manual Testing Cycle
```bash
# 1. Test your features with the sample data
# 2. Reset when you need a clean slate
uv run python scripts/reset_database.py --confirm

# 3. Seed again
uv run python scripts/seed_sample_data.py
```

## Sample Data Details

### Duplicate Groups

**Customer Duplicates:**
1. **María García López** (variations: "Maria Garcia Lopez", different phone formats)
2. **Juan Martínez Rodríguez** (variations: "Juan Martinez Rodriguez", different email)
3. **Ana Fernández Torres** (variations: "Ana Fernandez", missing data)

**Product Duplicates:**
1. **Laptop HP ProBook 450** (variations: capitalization, SKU format)
2. **Mouse Logitech MX Master 3** (variations: spacing, SKU)

### Inconsistencies

**Format Issues:**
- Customer "Roberto Jiménez Castro" has invalid email: `roberto.jimenez.invalid`

**Business Rule Violations:**
- Product "Cable HDMI 2m" has negative inventory: `-5`
- One order has a future order date

**Calculation Inconsistencies:**
- Order with customer "Juan Martínez" has `total_amount = 500.00` but items sum to `629.98`
- One order item has `line_total = 250.00` but should be `299.97` (3 × 99.99)

**Referential Integrity Issues:**
- One order references non-existent customer ID
- One order item references non-existent product ID

## Troubleshooting

### "Supabase configuration not found"
Make sure your `.env` file contains valid `SUPABASE_URL` and `SUPABASE_KEY` values.

### "Table does not exist"
Run the migration script first:
```bash
uv run python scripts/apply_migrations.py
```

### Foreign Key Constraint Errors
Some intentional inconsistencies may cause warnings during seeding. This is expected behavior for testing referential integrity detection.

### Permission Errors
Ensure your Supabase key has sufficient permissions to insert and delete data.

## Integration with Testing

These scripts are designed to support:

1. **Unit Tests**: Use `reset_and_seed.py` in test setup to ensure consistent state
2. **Integration Tests**: Seed data provides realistic scenarios for end-to-end testing
3. **Manual Testing**: Use the voice agent to query and manipulate the sample data
4. **Duplicate Detection Testing**: Intentional duplicates validate detection algorithms
5. **Inconsistency Analysis Testing**: Intentional inconsistencies validate analysis logic

## Automation

For CI/CD pipelines or automated testing:

```bash
# Non-interactive reset and seed
uv run python scripts/reset_and_seed.py --confirm
```

This ensures a clean, reproducible test environment for every test run.
