"""
Compatibility layer to ensure existing code works with the new database_enhanced.py
This provides the same interface as your old database.py while using the new enhanced features
"""

import os
from typing import Optional, Dict, Any, List
import logging

# Import the new enhanced database
from database_enhanced import db_manager, get_repository, DatabaseError, DatabaseErrorContext
from config import config

logger = logging.getLogger(__name__)


class SupabaseCompatibilityWrapper:
    """
    Compatibility wrapper that mimics your old Supabase client interface
    while using the new enhanced database pool underneath
    """

    def __init__(self):
        self.is_initialized = False

    def table(self, table_name: str):
        """Return a table interface that mimics Supabase"""
        return SupabaseTableWrapper(table_name)

    async def initialize(self):
        """Initialize the enhanced database"""
        if not self.is_initialized:
            await db_manager.initialize()
            self.is_initialized = True

    def __bool__(self):
        """Return True if database is available (for 'if supabase:' checks)"""
        return self.is_initialized


class SupabaseTableWrapper:
    """
    Wrapper that provides Supabase-like table interface
    while using our enhanced database operations
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        self._select_columns = "*"
        self._where_conditions = []
        self._limit_value = None
        self._order_conditions = []

    def select(self, columns: str = "*"):
        """Set columns to select"""
        self._select_columns = columns
        return self

    def eq(self, column: str, value: Any):
        """Add equality condition"""
        self._where_conditions.append((column, "=", value))
        return self

    def limit(self, count: int):
        """Set limit"""
        self._limit_value = count
        return self

    def order(self, column: str, desc: bool = False):
        """Add order condition"""
        direction = "DESC" if desc else "ASC"
        self._order_conditions.append(f"{column} {direction}")
        return self

    async def execute(self):
        """Execute the query and return Supabase-like result"""
        try:
            # Build the query
            query_parts = [f"SELECT {self._select_columns} FROM {self.table_name}"]
            params = []

            # Add WHERE conditions
            if self._where_conditions:
                where_parts = []
                for column, operator, value in self._where_conditions:
                    params.append(value)
                    where_parts.append(f"{column} {operator} ${len(params)}")
                query_parts.append(f"WHERE {' AND '.join(where_parts)}")

            # Add ORDER BY
            if self._order_conditions:
                query_parts.append(f"ORDER BY {', '.join(self._order_conditions)}")

            # Add LIMIT
            if self._limit_value:
                query_parts.append(f"LIMIT {self._limit_value}")

            query = " ".join(query_parts)

            # Execute using enhanced database
            async with DatabaseErrorContext("supabase_compatibility", self.table_name):
                db_pool = await db_manager.get_db_pool()
                result = await db_pool.execute_query(query, tuple(params), f"select_{self.table_name}")

                # Convert to Supabase-like response
                data = [dict(row) for row in result] if result else []

                return SupabaseResult(data=data, error=None)

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return SupabaseResult(data=None, error=str(e))

    def insert(self, data: Dict[str, Any]):
        """Insert data"""
        return SupabaseInsertWrapper(self.table_name, data)

    def update(self, data: Dict[str, Any]):
        """Update data"""
        return SupabaseUpdateWrapper(self.table_name, data, self._where_conditions)


class SupabaseInsertWrapper:
    """Wrapper for insert operations"""

    def __init__(self, table_name: str, data: Dict[str, Any]):
        self.table_name = table_name
        self.data = data

    async def execute(self):
        """Execute insert"""
        try:
            # Use repository pattern for common tables
            if self.table_name in ["recipes", "user_preferences", "users"]:
                repo = await get_repository(self.table_name)
                result = await repo.create(self.data)
                return SupabaseResult(data=[result] if result else [], error=None)
            else:
                # Direct database insert for other tables
                columns = list(self.data.keys())
                placeholders = [f"${i + 1}" for i in range(len(columns))]
                values = list(self.data.values())

                query = f"""
                    INSERT INTO {self.table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    RETURNING *
                """

                async with DatabaseErrorContext("insert", self.table_name):
                    db_pool = await db_manager.get_db_pool()
                    result = await db_pool.execute_query(query, tuple(values), f"insert_{self.table_name}")

                    data = [dict(row) for row in result] if result else []
                    return SupabaseResult(data=data, error=None)

        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return SupabaseResult(data=None, error=str(e))


class SupabaseUpdateWrapper:
    """Wrapper for update operations"""

    def __init__(self, table_name: str, data: Dict[str, Any], where_conditions: List):
        self.table_name = table_name
        self.data = data
        self.where_conditions = where_conditions

    def eq(self, column: str, value: Any):
        """Add equality condition for update"""
        self.where_conditions.append((column, "=", value))
        return self

    async def execute(self):
        """Execute update"""
        try:
            # Build update query
            columns = list(self.data.keys())
            set_parts = [f"{col} = ${i + 1}" for i, col in enumerate(columns)]
            params = list(self.data.values())

            query_parts = [f"UPDATE {self.table_name} SET {', '.join(set_parts)}"]

            if self.where_conditions:
                where_parts = []
                for column, operator, value in self.where_conditions:
                    params.append(value)
                    where_parts.append(f"{column} {operator} ${len(params)}")
                query_parts.append(f"WHERE {' AND '.join(where_parts)}")

            query_parts.append("RETURNING *")
            query = " ".join(query_parts)

            async with DatabaseErrorContext("update", self.table_name):
                db_pool = await db_manager.get_db_pool()
                result = await db_pool.execute_query(query, tuple(params), f"update_{self.table_name}")

                data = [dict(row) for row in result] if result else []
                return SupabaseResult(data=data, error=None)

        except Exception as e:
            logger.error(f"Update failed: {e}")
            return SupabaseResult(data=None, error=str(e))


class SupabaseResult:
    """Mimics Supabase result structure"""

    def __init__(self, data: List[Dict] = None, error: str = None):
        self.data = data
        self.error = error


# Create the global compatibility instance
supabase = SupabaseCompatibilityWrapper()


# Initialization function for FastAPI startup
async def init_supabase_compatibility():
    """Initialize the compatibility layer"""
    try:
        await supabase.initialize()
        logger.info("✅ Supabase compatibility layer initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize compatibility layer: {e}")
        raise


# Export for backward compatibility
__all__ = ['supabase', 'init_supabase_compatibility']