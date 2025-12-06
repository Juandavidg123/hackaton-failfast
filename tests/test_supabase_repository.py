"""Tests for Supabase repository."""

import pytest

from repositories.supabase_repository import SupabaseRepository


def test_repository_initialization():
    """Test that repository can be initialized."""
    repo = SupabaseRepository(
        supabase_url="https://example.supabase.co",
        supabase_key="test-key"
    )
    
    assert repo.client is not None


def test_repository_has_required_methods():
    """Test that repository has all required CRUD methods."""
    repo = SupabaseRepository(
        supabase_url="https://example.supabase.co",
        supabase_key="test-key"
    )
    
    # Verify all required methods exist
    assert hasattr(repo, "query")
    assert hasattr(repo, "get_by_id")
    assert hasattr(repo, "insert")
    assert hasattr(repo, "update")
    assert hasattr(repo, "delete")
    assert hasattr(repo, "execute_sql")
    assert hasattr(repo, "get_all")
    assert hasattr(repo, "bulk_insert")
    assert hasattr(repo, "bulk_update")
    
    # Verify methods are callable
    assert callable(repo.query)
    assert callable(repo.get_by_id)
    assert callable(repo.insert)
    assert callable(repo.update)
    assert callable(repo.delete)
    assert callable(repo.execute_sql)
    assert callable(repo.get_all)
    assert callable(repo.bulk_insert)
    assert callable(repo.bulk_update)
