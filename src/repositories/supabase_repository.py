"""Supabase repository for data access operations."""

from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

from postgrest.exceptions import APIError
from supabase import Client, create_client


class SupabaseRepository:
    """Repository class for Supabase database operations."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase repository.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
        """
        self.client: Client = create_client(supabase_url, supabase_key)
        self._in_transaction = False
        self._transaction_operations = []

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        This provides a simple transaction-like behavior by collecting
        operations and rolling back on error. Note: Supabase doesn't
        support true transactions via the REST API, so this is a
        best-effort implementation.

        Usage:
            with repository.transaction():
                repository.insert("table1", data1)
                repository.update("table2", id2, data2)

        Yields:
            Self for chaining operations
        """
        self._in_transaction = True
        self._transaction_operations = []

        try:
            yield self
            # Commit: operations already executed
            self._transaction_operations = []
        except Exception as e:
            # Rollback: attempt to undo operations
            self._rollback_transaction()
            raise
        finally:
            self._in_transaction = False
            self._transaction_operations = []

    def _rollback_transaction(self):
        """Attempt to rollback transaction operations.

        This is a best-effort rollback that reverses operations
        in reverse order. Not all operations can be rolled back.
        """
        # Reverse the operations
        for operation in reversed(self._transaction_operations):
            try:
                op_type = operation["type"]
                table = operation["table"]

                if op_type == "insert":
                    # Delete the inserted record
                    record_id = operation["result"]["id"]
                    self.client.table(table).delete().eq("id", record_id).execute()

                elif op_type == "update":
                    # Restore the old values
                    record_id = operation["record_id"]
                    old_data = operation["old_data"]
                    if old_data:
                        self.client.table(table).update(old_data).eq(
                            "id", record_id
                        ).execute()

                elif op_type == "delete":
                    # Re-insert the deleted record
                    old_data = operation["old_data"]
                    if old_data:
                        self.client.table(table).insert(old_data).execute()

            except Exception:
                # If rollback fails, continue trying other operations
                pass

    def _record_operation(
        self, op_type: str, table: str, result: Any = None, **kwargs
    ):
        """Record an operation for potential rollback.

        Args:
            op_type: Type of operation (insert, update, delete)
            table: Table name
            result: Operation result
            **kwargs: Additional operation details
        """
        if self._in_transaction:
            self._transaction_operations.append(
                {"type": op_type, "table": table, "result": result, **kwargs}
            )

    def query(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query table with optional filters.

        Args:
            table: Table name to query
            filters: Optional dictionary of filters to apply

        Returns:
            List of matching records
        """
        query_builder = self.client.table(table).select("*")

        if filters:
            for key, value in filters.items():
                query_builder = query_builder.eq(key, value)

        response = query_builder.execute()
        return response.data

    def get_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get record by ID.

        Args:
            table: Table name
            record_id: Record ID

        Returns:
            Record data or None if not found
        """
        response = self.client.table(table).select("*").eq("id", record_id).execute()
        return response.data[0] if response.data else None

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new record.

        Args:
            table: Table name
            data: Record data to insert

        Returns:
            Inserted record with generated ID

        Raises:
            APIError: If database operation fails
        """
        response = self.client.table(table).insert(data).execute()
        result = response.data[0]

        # Record operation for potential rollback
        self._record_operation("insert", table, result=result)

        return result

    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing record.

        Args:
            table: Table name
            record_id: Record ID to update
            data: Updated record data

        Returns:
            Updated record

        Raises:
            APIError: If database operation fails
        """
        # Get old data for potential rollback
        old_data = None
        if self._in_transaction:
            old_data = self.get_by_id(table, record_id)

        response = (
            self.client.table(table).update(data).eq("id", record_id).execute()
        )
        result = response.data[0]

        # Record operation for potential rollback
        self._record_operation(
            "update", table, result=result, record_id=record_id, old_data=old_data
        )

        return result

    def delete(self, table: str, record_id: str) -> bool:
        """Delete record.

        Args:
            table: Table name
            record_id: Record ID to delete

        Returns:
            True if deleted successfully

        Raises:
            APIError: If database operation fails
        """
        # Get old data for potential rollback
        old_data = None
        if self._in_transaction:
            old_data = self.get_by_id(table, record_id)

        response = self.client.table(table).delete().eq("id", record_id).execute()
        success = len(response.data) > 0

        # Record operation for potential rollback
        if success:
            self._record_operation("delete", table, old_data=old_data)

        return success

    def execute_sql(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Query results
        """
        response = self.client.rpc("execute_sql", {"query": query, "params": params or {}}).execute()
        return response.data

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        """Get all records from a table.

        Args:
            table: Table name

        Returns:
            List of all records
        """
        response = self.client.table(table).select("*").execute()
        return response.data

    def bulk_insert(self, table: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple records.

        Args:
            table: Table name
            records: List of records to insert

        Returns:
            List of inserted records
        """
        response = self.client.table(table).insert(records).execute()
        return response.data

    def bulk_update(self, table: str, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple records.

        Args:
            table: Table name
            updates: List of records with id and updated fields

        Returns:
            List of updated records
        """
        results = []
        for update in updates:
            record_id = update.pop("id")
            result = self.update(table, record_id, update)
            results.append(result)
        return results
