-- Migration: Create data quality tables
-- Description: Creates tables for tracking duplicate groups and inconsistencies

-- Duplicate groups table
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_ids UUID[] NOT NULL,
    similarity_score DECIMAL(5, 2) NOT NULL CHECK (similarity_score >= 0 AND similarity_score <= 100),
    matching_fields JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Inconsistencies table
CREATE TABLE IF NOT EXISTS inconsistencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL CHECK (type IN ('referential', 'calculation', 'format', 'business_rule')),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    field_name VARCHAR(100),
    description TEXT NOT NULL,
    suggested_fix JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_table_name ON duplicate_groups(table_name);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_status ON duplicate_groups(status);
CREATE INDEX IF NOT EXISTS idx_inconsistencies_type ON inconsistencies(type);
CREATE INDEX IF NOT EXISTS idx_inconsistencies_table_name ON inconsistencies(table_name);
CREATE INDEX IF NOT EXISTS idx_inconsistencies_status ON inconsistencies(status);
CREATE INDEX IF NOT EXISTS idx_inconsistencies_record_id ON inconsistencies(record_id);
