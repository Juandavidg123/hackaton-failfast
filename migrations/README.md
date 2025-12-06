# Database Migrations

This directory contains SQL migration files for the ERP Voice Chat System database schema.

## Migration Files

1. `001_create_erp_tables.sql` - Creates core ERP tables (customers, products, orders, order_items)
2. `002_create_data_quality_tables.sql` - Creates data quality tracking tables (duplicate_groups, inconsistencies)

## Applying Migrations

### Using Supabase Dashboard

1. Log in to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of each migration file in order
4. Execute each migration

### Using Supabase CLI

If you have the Supabase CLI installed:

```bash
# Apply all migrations
supabase db push

# Or apply individual migrations
psql $SUPABASE_URL -f migrations/001_create_erp_tables.sql
psql $SUPABASE_URL -f migrations/002_create_data_quality_tables.sql
```

### Using psql directly

```bash
# Set your database URL
export DB_URL="postgresql://postgres.xxx:password@xxx.supabase.co:5432/postgres"

# Apply migrations in order
psql $DB_URL -f migrations/001_create_erp_tables.sql
psql $DB_URL -f migrations/002_create_data_quality_tables.sql
```

## Schema Overview

### ERP Tables

- **customers**: Customer information (name, email, phone, address)
- **products**: Product catalog (name, SKU, price, inventory)
- **orders**: Customer orders (customer_id, order_date, total_amount, status)
- **order_items**: Line items for orders (order_id, product_id, quantity, prices)

### Data Quality Tables

- **duplicate_groups**: Detected duplicate record groups with similarity scores
- **inconsistencies**: Detected data inconsistencies with categorization and suggested fixes

## Notes

- All tables use UUID primary keys
- Foreign key constraints are enforced
- Indexes are created for common query patterns
- Automatic `updated_at` timestamp triggers are configured for ERP tables
